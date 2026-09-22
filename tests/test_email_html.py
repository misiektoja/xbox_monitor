"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import asyncio
import difflib
import html as html_module
import json
import os
import re
from pathlib import Path

import httpx
import pytest

import xbox_monitor as monitor

GAMERTAG = "ExampleTag"
PROFILE_URL = "https://account.xbox.com/en-us/profile?gamertag=ExampleTag"


# Ends a bounded monitoring run once the scripted presence timeline is exhausted
class EndOfTimeline(BaseException):
    pass


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Returns the unified diff between the plain body and the text the HTML body reduces to, empty when they match
def structural_diff(body, body_html):
    reduced = html_to_text(body_html)
    if reduced == body:
        return ""
    return "\n".join(difflib.unified_diff(body.split("\n"), reduced.split("\n"), fromfile="plain", tofile="html-reduced", lineterm=""))


# Builds one presence response, always carrying a last-seen stamp so an offline poll needs no grace retry
def presence_payload(state, game="", stamp="2026-01-01T00:00:00Z"):
    devices = [{"type": "XboxSeriesX", "titles": [{"id": "1", "name": game, "placement": "Full", "state": "Active"}]}] if game else []
    return {"xuid": "1234", "state": state, "lastSeen": {"deviceType": "XboxSeriesX", "titleName": "Home", "timestamp": stamp}, "devices": devices}


# The presence timeline the alerts are captured from. The first two entries answer the profile summary and the
# startup snapshot, so the third is the first poll the monitoring loop compares against a baseline
TIMELINE = [
    presence_payload("Offline"),
    presence_payload("Offline"),
    presence_payload("Online"),
    presence_payload("Online", game="Example Game"),
    presence_payload("Online", game="Another Game"),
    presence_payload("Online"),
    presence_payload("Offline"),
    presence_payload("Offline"),
    presence_payload("Online"),
]

# The second offline poll, where a newer title history entry makes the loop report appear-offline activity
ACTIVITY_POLL = 7


@pytest.fixture
# Collects every alert the monitoring loop tries to send, without delivering any of them
def captured_alerts(monkeypatch):
    captured = []

    def fake_send(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, webhook_body="", webhook_body_html=""):
        captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": webhook_body or body, "discord": monitor.html_body_to_discord_markdown(webhook_body_html or body_html)})
        return bool(email_enabled), bool(webhook_enabled)

    monkeypatch.setattr(monitor, "send_notification_channels", fake_send)
    return captured


# Answers the Xbox endpoints from the scripted timeline, leaving request signing and model parsing intact
def scripted_xbox_transport(monkeypatch, tmp_path):
    token = {"token_type": "bearer", "expires_in": 3600, "scope": "Xboxlive.signin Xboxlive.offline_access", "access_token": "synthetic-oauth-access", "refresh_token": "synthetic-oauth-refresh", "user_id": "1234"}
    cache = tmp_path / "tokens.json"
    cache.write_text(json.dumps(token), encoding="utf-8")
    cache.chmod(0o600)
    monkeypatch.setattr(monitor, "MS_AUTH_TOKENS_FILE", str(cache))
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "synthetic-app-id")
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "synthetic-app-secret")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "XBOX_CHECK_INTERVAL", 0.001)
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", 0.001)
    monkeypatch.setattr(monitor, "XBOX_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", True)
    counts = {"presence": 0, "history": 0}

    # Substitutes only the network boundary, so the loop parses the same models it parses in production
    async def boundary(transport, request):
        host = request.url.host
        if host == "login.live.com":
            payload = token
        elif host in ("user.auth.xboxlive.com", "xsts.auth.xboxlive.com"):
            payload = {"IssueInstant": "2026-01-01T00:00:00Z", "NotAfter": "2099-01-01T00:00:00Z", "Token": "synthetic-xbox-token", "DisplayClaims": {"xui": [{"uhs": "123", "xid": "1234", "gtg": GAMERTAG}]}}
        elif host == "profile.xboxlive.com":
            payload = {"profileUsers": [{"id": "1234", "hostId": "synthetic-host", "isSponsoredUser": False, "settings": [{"id": "Gamerscore", "value": "12"}]}]}
        elif host == "userpresence.xboxlive.com":
            if counts["presence"] >= len(TIMELINE):
                raise EndOfTimeline()
            payload = TIMELINE[counts["presence"]]
            counts["presence"] += 1
        elif host == "titlehub.xboxlive.com":
            counts["history"] += 1
            # A newer entry only from the activity poll on, since the offline transition before it resets the baseline
            stamp = "2026-01-03T00:00:00Z" if counts["presence"] > ACTIVITY_POLL else "2026-01-01T00:00:00Z"
            payload = {"xuid": "1234", "titles": [{"titleId": "123", "name": "Example Game", "type": "Game", "devices": ["XboxSeriesX"], "displayImage": "https://example.test/image.png", "mediaItemType": "Game", "isBundle": False, "titleHistory": {"lastTimePlayed": stamp, "visible": True, "canHide": True}}]}
        elif host == "peoplehub.xboxlive.com":
            payload = {"people": []}
        else:
            raise AssertionError("Unexpected endpoint: " + host)
        return httpx.Response(200, json=payload, request=request)

    # Answers the unrelated connectivity check without contacting an external service
    def connectivity(transport, request):
        return httpx.Response(200, text="reachable", request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", boundary)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", connectivity)


@pytest.fixture
# Every alert the scripted presence timeline produces, covering status changes, game changes and title history
def timeline_alerts(monkeypatch, tmp_path, captured_alerts, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "STATUS_NOTIFICATION", True)
    scripted_xbox_transport(monkeypatch, tmp_path)
    with pytest.raises(EndOfTimeline):
        asyncio.run(monitor.xbox_monitor_user(GAMERTAG, ""))
    capsys.readouterr()
    return captured_alerts


# Verifies a value taken from Xbox Live is escaped before it reaches the HTML body
def test_untrusted_text_is_escaped():
    assert monitor.html_text("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert monitor.html_text("line\nbreak") == "line<br>break"
    assert monitor.escape_html_attr('" onload="x') == "&quot; onload=&quot;x"


# Verifies a crafted gamertag or game title cannot inject markup through the bolded subject
def test_a_crafted_name_cannot_inject_markup():
    assert monitor.xbox_game_html("<b>Game</b>") == "<b>&lt;b&gt;Game&lt;/b&gt;</b>"
    assert "<img" not in monitor.xbox_user_html("<img src=x>")


# Verifies the profile link carries the gamertag as an escaped query value
def test_the_profile_link_escapes_the_gamertag():
    assert monitor.xbox_profile_url("Some Tag") == "https://account.xbox.com/en-us/profile?gamertag=Some%20Tag"
    assert monitor.xbox_profile_url("") == ""
    assert monitor.xbox_user_html(GAMERTAG) == f'<b><a href="{PROFILE_URL}">{GAMERTAG}</a></b>'


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once():
    assert monitor.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert monitor.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body():
    body_html = monitor.html_email_body('Xbox user <b>ExampleTag</b> is now <b>online</b><br><br>Guide: <a href="https://example.test/a">docs</a>')

    assert monitor.html_body_to_discord_markdown(body_html) == "Xbox user **ExampleTag** is now **online**\n\nGuide: [docs](https://example.test/a)"


# Verifies a link whose label repeats its destination is left bare, which Discord turns into a link itself
def test_a_self_labeled_link_stays_bare_in_discord():
    assert monitor.html_body_to_discord_markdown('<a href="https://example.test/a">https://example.test/a</a>') == "https://example.test/a"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    advice = monitor.make_recovery_advice("network.timeout", "Xbox Live did not answer in time", "Retry later", True)

    rendered = monitor.recovery_alert_body_html(advice, 60, failed_checks=2, failing_since=1700000000)

    assert rendered.startswith("<html><head></head><body><b>Xbox Live did not answer in time</b><br><br>")
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered
    assert rendered.endswith("</body></html>")


# Verifies the webhook copy of an alert leaves out the timestamp the email carries
def test_the_webhook_body_has_no_timestamp(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    advice = monitor.make_recovery_advice("network.timeout", "Xbox Live did not answer in time", "Retry later", True)

    assert "Timestamp: " not in monitor.recovery_alert_body_html(advice, 60, timestamp=False)
    assert "Timestamp: " in monitor.recovery_alert_body_html(advice, 60)


# Verifies the timeline reaches both alert types, so the structural check is not silently narrow
def test_the_timeline_covers_status_and_game_alerts(timeline_alerts):
    assert {alert["type"] for alert in timeline_alerts} == {"status", "game"}


# Verifies the appear-offline activity alert is part of the timeline, since it builds its own HTML body
def test_the_timeline_reaches_the_title_history_alert(timeline_alerts):
    assert [alert for alert in timeline_alerts if "via title history" in alert["subject"]]


# Verifies a status subject names when the state started rather than the whole range, which the body already reports
def test_a_status_subject_names_when_the_state_started(timeline_alerts):
    subjects = [alert["subject"] for alert in timeline_alerts if re.search(r" is (?:online|away)\b", alert["subject"])]

    assert subjects
    for subject in subjects:
        assert re.fullmatch(r"Xbox user \w+ is \w+ \(.*after .+ - (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{1,2} \w{3} \d{2}, \d{2}:\d{2}\)", subject), subject
        assert len(re.findall(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", subject)) == 1


# Verifies going offline keeps the range, since that names the session the user was available for
def test_the_offline_subject_carries_the_availability_range(timeline_alerts):
    offline = [alert["subject"] for alert in timeline_alerts if " is offline (" in alert["subject"]]

    assert offline
    for subject in offline:
        assert re.fullmatch(r"Xbox user \w+ is offline \(.*after .+: (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{1,2} \w{3} \d{2}, \d{2}:\d{2} - .+\)", subject), subject


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(timeline_alerts):
    assert [alert["subject"] for alert in timeline_alerts if not alert["body_html"]] == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(timeline_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in timeline_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(timeline_alerts):
    for alert in timeline_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Verifies the Discord body keeps the wording the ntfy body carries once its markers are removed
def test_discord_bodies_keep_the_plain_wording(timeline_alerts):
    for alert in timeline_alerts:
        stripped = re.sub(r"\[([^\]]*)\]\((?:[^)]*)\)", r"\1", alert["discord"]).replace("**", "").replace("*", "")

        assert stripped == alert["webhook_body"].strip()


# Verifies the gamertag is a bold profile link and the game title is the bold subject of the alerts that name it
def test_alerts_bold_the_entities_they_name(timeline_alerts):
    for alert in timeline_alerts:
        assert f'<b><a href="{PROFILE_URL}">{GAMERTAG}</a></b>' in alert["body_html"]
    game_alerts = [alert for alert in timeline_alerts if alert["type"] == "game"]

    assert game_alerts
    assert any("<b>Example Game</b>" in alert["body_html"] for alert in game_alerts)


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(timeline_alerts):
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(timeline_alerts, indent=2), encoding="utf-8")
