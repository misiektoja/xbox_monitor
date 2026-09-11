"""Tests for webhook delivery: the destination, the request each provider gets and the bounded retry."""

import pytest

import xbox_monitor as monitor


DISCORD_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"
NTFY_URL = "https://ntfy.sh/private-topic-name"


# Stands in for one HTTP response with just the fields the delivery path reads
class FakeResponse:
    def __init__(self, status_code=204, headers=None, payload=None, text=""):
        self.status_code = status_code
        self.headers = headers if headers is not None else {}
        self.text = text
        self._payload = payload

    # Returns the canned JSON body or refuses the way an HTTP client does when there is none
    def json(self):
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload


# Records every webhook request instead of sending one and replays scripted responses
class FakeClient:
    def __init__(self, log, responses, failure=None, **client_kwargs):
        self.log = log
        self.responses = responses
        self.failure = failure
        self.client_kwargs = client_kwargs
        log["clients"].append(client_kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    # Records one POST and returns the next scripted response, repeating the last one when the script runs out
    def post(self, url, **kwargs):
        self.log["requests"].append(dict(kwargs, url=url))
        if self.failure is not None:
            raise self.failure
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


@pytest.fixture
# Installs the recording client and returns a factory that scripts the responses it replays
def webhook_client(monkeypatch):
    log = {"requests": [], "clients": []}

    # Enclosed so a test can script the responses after the fixture was requested
    def install(responses=None, failure=None):
        scripted = list(responses) if responses is not None else [FakeResponse()]
        monkeypatch.setattr(monitor.httpx, "Client", lambda **kwargs: FakeClient(log, scripted, failure, **kwargs))
        return log

    return install


@pytest.fixture
# Turns on a working Discord destination, which most delivery tests start from
def discord_enabled(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", DISCORD_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    return monitor


@pytest.fixture
# Turns on a working ntfy destination
def ntfy_enabled(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", NTFY_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    return monitor


# Verifies only a complete private HTTPS destination is accepted
@pytest.mark.parametrize("url, accepted", [
    (DISCORD_URL, True),
    (NTFY_URL, True),
    ("https://ntfy.example.test/topic", True),
    ("http://discord.com/api/webhooks/1/token", False),
    ("https://discord.com", False),
    ("https://discord.com/", False),
    ("https://user:secret@ntfy.sh/topic", False),
    ("your_webhook_url", False),
    ("", False),
    (None, False),
    (12345, False),
])
def test_only_a_complete_https_destination_is_accepted(url, accepted):
    assert monitor.validate_webhook_url(url) is accepted


# Verifies a bare ntfy.sh topic name becomes a complete URL and anything unusable becomes nothing
@pytest.mark.parametrize("entered, expected", [
    ("private-topic-name", "https://ntfy.sh/private-topic-name"),
    ("Topic_1", "https://ntfy.sh/Topic_1"),
    (NTFY_URL, NTFY_URL),
    ("https://ntfy.example.test/topic", "https://ntfy.example.test/topic"),
    ("topic with spaces", ""),
    ("topic/with/slashes", ""),
    ("x" * 65, ""),
    ("", ""),
    (None, ""),
])
def test_an_ntfy_topic_name_is_expanded_to_a_url(entered, expected):
    assert monitor.normalize_ntfy_topic_url(entered) == expected


# Verifies the service is recognised from the URL shape and that an unknown host stays unrecognised
@pytest.mark.parametrize("url, provider", [
    (DISCORD_URL, "discord"),
    ("https://canary.discord.com/api/v10/webhooks/1/token", "discord"),
    ("https://discordapp.com/api/webhooks/1/token", "discord"),
    (NTFY_URL, "ntfy"),
    ("https://ntfy.example.test/topic", ""),
    ("https://discord.com/api/webhooks/1/token/extra/parts", ""),
    ("https://example.test/hook", ""),
])
def test_the_service_is_detected_from_the_url(url, provider):
    assert monitor.detect_webhook_provider(url) == provider


# Verifies an unsupported provider name is rejected rather than quietly treated as one of the two
@pytest.mark.parametrize("configured, normalized", [("discord", "discord"), ("  NTFY ", "ntfy"), ("slack", ""), ("", ""), (12345, "")])
def test_only_the_two_supported_providers_normalize(configured, normalized):
    assert monitor.normalized_webhook_provider(configured) == normalized


# Verifies the display name falls back to the configured text, so a typo is visible in the report
def test_an_unsupported_provider_is_still_named_in_output():
    assert monitor.webhook_provider_display_name("discord") == "Discord"
    assert monitor.webhook_provider_display_name("ntfy") == "ntfy"
    assert monitor.webhook_provider_display_name("slack") == "slack"


# Verifies the master switch overrides every individual alert setting
def test_the_master_switch_turns_every_alert_off(monkeypatch):
    for name in ("WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", "WEBHOOK_GAME_CHANGE_NOTIFICATION", "WEBHOOK_STATUS_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, name, True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)

    assert [monitor.webhook_event_enabled(name) for name in ("status", "all_status", "game", "error")] == [False, False, False, False]

    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    assert [monitor.webhook_event_enabled(name) for name in ("status", "all_status", "game", "error")] == [True, True, True, True]


# Verifies a disabled alert type is recorded as a debug trace, since it repeats on every notification
def test_a_disabled_alert_type_is_traced_in_debug_only(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)

    assert monitor.send_webhook("alert", "body", "status") == 1
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(monitor, "DEBUG_MODE", True)

    assert monitor.send_webhook("alert", "body", "status") == 1

    assert "Webhook delivery: outcome=skipped, type=status, reason=alerts are disabled" in capsys.readouterr().out


# Verifies an alert type nothing defines cannot switch itself on
def test_an_unknown_alert_type_is_never_enabled(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)

    assert monitor.webhook_event_enabled("achievements") is False


# Verifies the Discord payload carries the alert, disables mentions and sends the colour as a number
def test_the_discord_payload_carries_the_alert_and_disables_mentions(discord_enabled, webhook_client):
    log = webhook_client()

    assert monitor.send_webhook("Xbox user is now online", "body text", "status") == 0

    payload = log["requests"][0]["json"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["username"] == "Xbox Monitor"
    embed = payload["embeds"][0]
    assert embed["title"] == "Xbox user is now online"
    assert embed["description"] == "body text"
    assert embed["color"] == monitor.WEBHOOK_EVENT_COLORS["status"]
    assert embed["footer"]["text"] == f"Xbox Monitor v{monitor.VERSION}"


# Verifies a delivered webhook names the provider and quotes the alert, the way the sibling monitors report it
def test_a_delivered_webhook_is_reported_in_verbose(discord_enabled, webhook_client, monkeypatch, capsys):
    webhook_client()
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)

    assert monitor.send_webhook("Xbox user is now online", "body text", "status") == 0

    printed = capsys.readouterr().out
    assert "* Webhook delivered through Discord: 'Xbox user is now online'" in printed
    assert DISCORD_URL not in printed


# Verifies DELIVERY_CONFIRMATIONS drops the delivery line without turning the rest of verbose mode off
def test_delivery_confirmations_can_be_turned_off(discord_enabled, webhook_client, monkeypatch, capsys):
    webhook_client()
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DELIVERY_CONFIRMATIONS", False)

    assert monitor.send_webhook("Xbox user is now online", "body text", "status") == 0

    assert "Webhook delivered" not in capsys.readouterr().out


# Verifies every status alert is drawn in one colour, so the two status settings do not look like two events
def test_every_status_alert_shares_one_colour(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_STATUS_NOTIFICATION", True)
    log = webhook_client()

    monitor.send_webhook("alert", "body", "status")
    monitor.send_webhook("alert", "body", "all_status")

    colors = [request["json"]["embeds"][0]["color"] for request in log["requests"]]
    assert colors == [monitor.WEBHOOK_EVENT_COLORS["status"]] * 2


# Verifies a template that asks for mentions cannot re-enable them
def test_a_template_cannot_re_enable_mentions(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", {"content": "@everyone {title}", "allowed_mentions": {"parse": ["everyone"]}})
    log = webhook_client()

    assert monitor.send_webhook("alert", "body", "status") == 0

    assert log["requests"][0]["json"]["allowed_mentions"] == {"parse": []}


# Verifies an empty display name or avatar is left out, so Discord applies the webhook's own defaults
def test_an_empty_name_or_avatar_is_omitted(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_USERNAME", "")
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "")
    log = webhook_client()

    monitor.send_webhook("alert", "body", "status")

    payload = log["requests"][0]["json"]
    assert "username" not in payload
    assert "avatar_url" not in payload


# Verifies ntfy receives the body as a plain text message with the subject as its title
def test_the_ntfy_request_sends_a_native_message(ntfy_enabled, webhook_client):
    log = webhook_client()

    assert monitor.send_webhook("Xbox user is now online", "body text", "status") == 0

    request = log["requests"][0]
    assert request["content"] == b"body text"
    assert request["params"] == {"title": "Xbox user is now online"}
    assert request["headers"]["Content-Type"] == "text/plain; charset=utf-8"
    assert "json" not in request


# Verifies an ntfy access token is sent as Bearer authentication and never appears in the topic URL
def test_an_ntfy_token_is_sent_as_bearer_authentication(ntfy_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "  tk_a_real_looking_token  ")
    log = webhook_client()

    monitor.send_webhook("alert", "body", "status")

    assert log["requests"][0]["headers"]["Authorization"] == "Bearer tk_a_real_looking_token"
    assert log["requests"][0]["url"] == NTFY_URL


# Verifies a token that already carries a scheme is refused rather than sent twice over
@pytest.mark.parametrize("token", ["Bearer tk_value", "basic dXNlcjpwYXNz", "tk_value\nX-Header: injected"])
def test_a_token_with_a_scheme_or_line_break_is_refused(monkeypatch, token):
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", token)

    assert monitor.validate_webhook_headers("ntfy") is not None


# Verifies custom headers reach the request and the shipped user agent fills in when none was configured
def test_custom_headers_reach_the_request(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Priority": "5", "X-Title": "{title}"})
    log = webhook_client()

    monitor.send_webhook("alert title", "body", "status")

    headers = log["requests"][0]["headers"]
    assert headers["X-Priority"] == "5"
    assert headers["X-Title"] == "alert title"
    assert headers["User-Agent"] == f"XboxMonitor/{monitor.VERSION}"


# Verifies a configured user agent is kept instead of being replaced
def test_a_configured_user_agent_is_kept(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"user-agent": "MyIntegration/2.0"})
    log = webhook_client()

    monitor.send_webhook("alert", "body", "status")

    headers = log["requests"][0]["headers"]
    assert headers["user-agent"] == "MyIntegration/2.0"
    assert "User-Agent" not in headers


# Verifies unusable header mappings are named rather than sent
@pytest.mark.parametrize("headers, fragment", [
    ("not a mapping", "must be a dictionary"),
    ({"Bad Header": "value"}, "invalid HTTP header name"),
    ({"X-Tag": "a", "x-tag": "b"}, "duplicate case-insensitive"),
    ({"X-Tag": 5}, "must be a string"),
    ({"X-Tag": "value\r\nX-Injected: 1"}, "must not contain line breaks"),
])
def test_an_unusable_header_mapping_is_named(monkeypatch, headers, fragment):
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", headers)

    assert fragment in monitor.validate_webhook_headers("discord")


# Verifies a header value that only becomes dangerous after substitution is still refused
def test_a_placeholder_cannot_smuggle_a_second_header(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Title": "{title}"})
    values = monitor.build_webhook_values("first line\nX-Injected: 1", "body", "status")
    values["title"] = "first line\nX-Injected: 1"

    with pytest.raises(ValueError, match="line breaks"):
        monitor.build_webhook_headers("discord", values)


# Verifies the alert title and body are bounded before either provider sees them
def test_an_over_long_alert_is_trimmed_for_discord():
    values = monitor.build_webhook_values("t" * 500, "d" * 6000, "status")

    assert len(values["title"]) == monitor.WEBHOOK_EMBED_TITLE_LIMIT
    assert len(values["description"]) == monitor.WEBHOOK_EMBED_DESCRIPTION_LIMIT


# Verifies an over-long ntfy message is trimmed to whole characters within the byte limit
def test_an_over_long_ntfy_message_is_trimmed_to_whole_characters():
    _title, message = monitor.build_ntfy_webhook_message("alert", "é" * 4000)

    encoded = message.encode("utf-8")
    assert len(encoded) <= monitor.NTFY_MESSAGE_LIMIT_BYTES
    assert message.endswith(monitor.NTFY_TRUNCATION_SUFFIX)
    assert encoded.decode("utf-8") == message


# Verifies a message that fits is left exactly as it was
def test_a_message_that_fits_is_untouched():
    assert monitor.truncate_utf8_bytes("short", 100, "...") == "short"


# Verifies a title with a line break cannot break the embed or the ntfy header it is sent in
def test_a_title_never_carries_a_line_break():
    values = monitor.build_webhook_values("first\nsecond", "body", "status")
    title, _message = monitor.build_ntfy_webhook_message("first\nsecond", "body")

    assert values["title"] == "first second"
    assert title == "first second"


# Verifies a secret that reached the alert text is redacted before it leaves the process
def test_a_secret_in_the_alert_is_redacted_before_delivery(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "client-secret-value-1234")
    log = webhook_client()

    monitor.send_webhook("alert", "The secret client-secret-value-1234 expired", "status")

    assert "client-secret-value-1234" not in log["requests"][0]["json"]["embeds"][0]["description"]


# Verifies the configured transformations are applied to the values the template and headers share
def test_transformations_are_applied_to_the_alert_values(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [("title", "upper"), ("description", "replace", "**", "")])

    values = monitor.build_webhook_values("online", "**bold** text", "status")

    assert values["title"] == "ONLINE"
    assert values["description"] == "bold text"


# Verifies a transformation cannot reach a private attribute or an unknown method
@pytest.mark.parametrize("transform, fragment", [
    (("title", "__class__"), "unsupported string method"),
    (("title", "explode"), "unsupported string method"),
    (("title",), "field name and a string method name"),
    ("title.upper", "field name and a string method name"),
])
def test_an_unsafe_transformation_is_refused(monkeypatch, transform, fragment):
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [transform])

    assert fragment in monitor.validate_webhook_customization("discord")


# Verifies an avatar that is not a complete HTTPS link is refused before anything is sent
def test_an_unusable_avatar_is_refused(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "http://example.test/avatar.png")

    assert "WEBHOOK_AVATAR_URL" in str(monitor.validate_webhook_customization("discord"))


# Verifies delivery refuses before the first request when a setting cannot be used
@pytest.mark.parametrize("setting, value", [
    ("WEBHOOK_URL", "your_webhook_url"),
    ("WEBHOOK_PROVIDER", "slack"),
    ("WEBHOOK_AVATAR_URL", "not-a-url"),
    ("WEBHOOK_HEADERS", {"Bad Header": "value"}),
])
def test_an_unusable_setting_stops_delivery_before_the_request(discord_enabled, webhook_client, monkeypatch, capsys, setting, value):
    monkeypatch.setattr(monitor, setting, value)
    log = webhook_client()

    assert monitor.send_webhook("alert", "body", "status") == 1

    assert log["requests"] == []
    assert "* Error:" in capsys.readouterr().out


# Verifies a disabled alert type is skipped and that a forced send ignores the alert settings
def test_a_disabled_alert_is_skipped_unless_it_is_forced(discord_enabled, webhook_client, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", False)
    log = webhook_client()

    assert monitor.send_webhook("alert", "body", "status") == 1
    assert log["requests"] == []

    assert monitor.send_webhook("alert", "body", "status", force=True) == 0
    assert len(log["requests"]) == 1


# Verifies every delivery refuses redirects, verifies the certificate and carries the shared deadline
def test_delivery_refuses_redirects_and_carries_the_deadline(discord_enabled, webhook_client):
    log = webhook_client()

    monitor.send_webhook("alert", "body", "status")

    client_kwargs = log["clients"][0]
    assert client_kwargs["follow_redirects"] is False
    assert client_kwargs["timeout"] == monitor.WEBHOOK_TIMEOUT_SECONDS
    assert client_kwargs["verify"] is not False


# Verifies the destination is checked again inside the request, so a reload cannot redirect a live delivery
def test_the_destination_is_rechecked_inside_the_request(discord_enabled, webhook_client, monkeypatch):
    log = webhook_client()
    client = monitor.httpx.Client()
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "http://evil.example.test/hook")

    with pytest.raises(monitor.httpx.InvalidURL):
        monitor.post_webhook_request(client, json={})

    assert log["requests"] == []


# Verifies a rate limit waits the delay the service asked for, then delivers on the second attempt
def test_a_rate_limit_waits_the_requested_delay_then_retries(discord_enabled, webhook_client):
    log = webhook_client([FakeResponse(429, {"Retry-After": "2"}), FakeResponse(204)])
    slept = []

    assert monitor.send_webhook("alert", "body", "status", sleeper=slept.append) == 0

    assert slept == [2.0]
    assert len(log["requests"]) == 2


# Verifies an untrusted retry delay is bounded instead of being waited out in full
@pytest.mark.parametrize("retry_after, waited", [("900", 5.0), ("-30", 0.0), ("not a number", 1.0), ("", 1.0)])
def test_an_untrusted_retry_delay_is_bounded(discord_enabled, webhook_client, retry_after, waited):
    webhook_client([FakeResponse(429, {"Retry-After": retry_after}), FakeResponse(204)])
    slept = []

    monitor.send_webhook("alert", "body", "status", sleeper=slept.append)

    assert slept == [waited]


# Verifies the JSON body is read when the service reports its delay there instead of in a header
def test_a_retry_delay_in_the_body_is_used(discord_enabled, webhook_client):
    webhook_client([FakeResponse(429, {}, {"retry_after": 3}), FakeResponse(204)])
    slept = []

    monitor.send_webhook("alert", "body", "status", sleeper=slept.append)

    assert slept == [3.0]


# Verifies a server fault is retried once and a rejected request is not retried at all
@pytest.mark.parametrize("status, attempts", [(500, 2), (503, 2), (400, 1), (401, 1), (404, 1)])
def test_only_a_server_fault_is_retried(discord_enabled, webhook_client, status, attempts):
    log = webhook_client([FakeResponse(status), FakeResponse(status)])

    assert monitor.send_webhook("alert", "body", "status", sleeper=lambda seconds: None) == 1

    assert len(log["requests"]) == attempts


# Verifies a network failure is retried once and then reported through the shared recovery renderer
def test_a_network_failure_is_retried_once_then_reported(discord_enabled, webhook_client, capsys):
    log = webhook_client(failure=monitor.httpx.ConnectError("connection refused"))

    assert monitor.send_webhook("alert", "body", "status", sleeper=lambda seconds: None) == 1

    assert len(log["requests"]) == monitor.WEBHOOK_MAX_ATTEMPTS
    output = capsys.readouterr().out
    assert "* Error: The webhook service could not be reached" in output
    assert "To fix:" in output


# Verifies the failure the service reported is classified rather than printed as a bare line
def test_a_rejected_delivery_is_classified(discord_enabled, webhook_client, capsys):
    webhook_client([FakeResponse(404, text="Unknown Webhook")])

    assert monitor.send_webhook("alert", "body", "status") == 1

    output = capsys.readouterr().out
    assert "* Error:" in output
    assert "To fix:" in output


# Verifies the two channels are switched on independently and each reports its own delivery
def test_each_channel_reports_its_own_delivery(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "alerts@example.test")
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 1)
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: 0)

    delivered = monitor.send_notification_channels("status", "subject", "body", email_enabled=True, webhook_enabled=True)

    assert delivered == (False, True)
    output = capsys.readouterr().out
    assert "Sending email notification to alerts@example.test" in output
    assert "Sending webhook notification" in output


# Verifies a channel that was not asked for is left alone
def test_a_channel_that_is_off_is_not_contacted(monkeypatch):
    calls = []
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: calls.append("email") or 0)
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: calls.append("webhook") or 0)

    assert monitor.send_notification_channels("status", "subject", "body", email_enabled=False, webhook_enabled=False) == (False, False)

    assert calls == []


# Verifies the webhook channel falls back to its own alert settings when the caller names no preference
def test_the_webhook_channel_falls_back_to_its_own_settings(monkeypatch):
    calls = []
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: calls.append(args[2]) or 0)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)

    monitor.send_notification_channels("game", "subject", "body")

    assert calls == ["game"]


# Verifies a private webhook URL is redacted wherever it appears in reported text
def test_a_private_destination_is_redacted_in_reported_text():
    sanitized = monitor.sanitize_error_text(f"POST {DISCORD_URL} failed")

    assert "aVeryLongWebhookTokenValue" not in sanitized
    assert "<redacted>" in sanitized


# Verifies a token carried in a query string is redacted too
def test_a_token_in_a_query_string_is_redacted():
    sanitized = monitor.sanitize_error_text("https://ntfy.example.test/topic?access_token=tk_secret_value")

    assert "tk_secret_value" not in sanitized


# Verifies the destination is reported by host only, so diagnostics never carry the private path
def test_diagnostics_name_the_host_without_the_private_path(discord_enabled):
    assert monitor.webhook_destination_host() == "discord.com"
    assert monitor.webhook_destination_host("not a url") == "unknown host"


# Returns the monitoring loop as a parsed tree, so its notification sites can be inspected without running it
def monitoring_loop_tree():
    import ast

    source = monitor.Path(monitor.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "xbox_monitor_user":
            return node
    raise AssertionError("the monitoring loop was not found")


# Verifies every alert the monitoring loop raises goes through the shared channel, not to email alone
def test_the_monitoring_loop_sends_every_alert_through_both_channels():
    import ast

    loop = monitoring_loop_tree()
    calls = [node for node in ast.walk(loop) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("send_email", "send_notification_channels")]
    names = [getattr(call.func, "id", "") for call in calls]
    types = [str(call.args[0].value) for call in calls if getattr(call.func, "id", "") == "send_notification_channels" and isinstance(call.args[0], ast.Constant)]

    assert "send_email" not in names
    assert sorted(types) == ["error", "game", "status", "status"]


# Verifies the error alert is guarded per channel, so a poll that keeps failing does not repeat it every cycle
def test_the_error_alert_is_raised_once_per_channel_and_reset_on_recovery():
    import ast

    loop = monitoring_loop_tree()
    error_calls = [node for node in ast.walk(loop) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "send_notification_channels" and isinstance(node.args[0], ast.Constant) and node.args[0].value == "error"]
    assert len(error_calls) == 1
    guards = {keyword.arg: ast.unparse(keyword.value) for keyword in error_calls[0].keywords}
    assert guards["email_enabled"] == "error_email_pending"
    assert guards["webhook_enabled"] == "error_webhook_pending"
    source = ast.unparse(loop)
    assert 'error_email_pending = alert_due and error_alert.pending(\'email\', ERROR_NOTIFICATION, now)' in source
    assert source.count("error_alert.record(") == 2
    # The state has to be cleared when a poll succeeds or one error would silence every later one
    assert source.count("error_alert = ErrorAlertState()") == 1
    assert source.count("error_alert.reset()") == 1
