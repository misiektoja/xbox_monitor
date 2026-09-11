"""Exercise Xbox authentication, presence and title history with real clients."""

import asyncio
import errno
import json
import os
from pathlib import Path

import httpx
import pytest

import xbox_monitor as monitor


# Ends a bounded monitoring run after enough real presence requests have completed
class EndOfEvidence(BaseException):
    pass


# Provides protocol responses to the real Xbox authentication manager and API clients
def setup_xbox_transport(monkeypatch, tmp_path, scenario):
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
    calls = []
    counts = {"presence": 0, "history": 0}

    # Substitutes only the network boundary and leaves request signing and model parsing intact
    async def boundary(transport, request):
        host = request.url.host
        calls.append(host)
        if host == "login.live.com":
            payload = token
        elif host in ("user.auth.xboxlive.com", "xsts.auth.xboxlive.com"):
            if scenario == "xsts" and host == "xsts.auth.xboxlive.com":
                return httpx.Response(401, json={"XErr": 2148916233, "Message": "The account does not have an Xbox profile"}, request=request)
            payload = {"IssueInstant": "2026-01-01T00:00:00Z", "NotAfter": "2099-01-01T00:00:00Z", "Token": "synthetic-xbox-token", "DisplayClaims": {"xui": [{"uhs": "123", "xid": "1234", "gtg": "ExampleTag"}]}}
        elif host == "profile.xboxlive.com":
            payload = {"profileUsers": [{"id": "1234", "hostId": "synthetic-host", "isSponsoredUser": False, "settings": [{"id": "Gamerscore", "value": "12"}]}]}
        elif host == "userpresence.xboxlive.com":
            counts["presence"] += 1
            if scenario == "private":
                return httpx.Response(403, json={"error": "Activity is private"}, request=request)
            if counts["presence"] > 3:
                raise EndOfEvidence()
            payload = {"xuid": "1234", "state": "Offline", "lastSeen": {"deviceType": "XboxOne", "titleName": "Home", "timestamp": "2026-01-01T00:00:00Z"}}
        elif host == "titlehub.xboxlive.com":
            counts["history"] += 1
            if scenario == "exhausted":
                raise httpx.ConnectError("Could not open socket", request=request) from OSError(errno.EMFILE, "Too many open files")
            stamp = "2026-01-01T00:00:00Z" if counts["history"] <= 2 else "2026-01-02T00:00:00Z"
            title = "Home" if scenario == "home" else "Example Game"
            payload = {"xuid": "1234", "titles": [{"titleId": "123", "name": title, "type": "Game", "devices": ["XboxOne"], "displayImage": "https://example.test/image.png", "mediaItemType": "Game", "isBundle": False, "titleHistory": {"lastTimePlayed": stamp, "visible": True, "canHide": True}}]}
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
    return calls, cache


# Checks activity permission with the same real client used by monitoring
def test_doctor_rejects_inaccessible_presence(monkeypatch, tmp_path, capsys):
    calls, cache = setup_xbox_transport(monkeypatch, tmp_path, "private")
    before = cache.read_bytes()
    assert monitor.run_doctor("ExampleTag") == 1
    assert "userpresence.xboxlive.com" in calls
    assert cache.read_bytes() == before
    assert "does not share its activity" in capsys.readouterr().out


# Reads a valid tilde-prefixed token cache without rewriting it
def test_doctor_expands_token_cache_path(monkeypatch, tmp_path):
    calls, cache = setup_xbox_transport(monkeypatch, tmp_path, "normal")
    monkeypatch.setattr(monitor, "MS_AUTH_TOKENS_FILE", "~/" + os.path.relpath(cache, Path.home()))
    before = cache.read_bytes()
    assert monitor.run_doctor("ExampleTag") == 0
    assert "userpresence.xboxlive.com" in calls
    assert cache.read_bytes() == before


# Classifies the real library exception produced by an XSTS rejection
def test_xsts_rejection_is_nonretryable_authorization(monkeypatch, tmp_path):
    setup_xbox_transport(monkeypatch, tmp_path, "xsts")

    # Runs the real cached-token authentication sequence
    async def authenticate():
        async with monitor.create_signed_session() as session:
            auth = monitor.AuthenticationManager(session, monitor.MS_APP_CLIENT_ID, monitor.MS_APP_CLIENT_SECRET, "")
            with pytest.raises(monitor.AuthenticationException) as rejected:
                await monitor.authenticate_and_refresh_tokens(auth)
            advice = monitor.classify_recovery_error(rejected.value, context="monitor")
            assert advice.code == "auth.authorization"
            assert not advice.retryable
            assert advice.code in monitor.AUTH_RECOVERY_CODES

    asyncio.run(authenticate())


# Stops before friends or another presence lookup after optional history exhausts resources
def test_title_history_resource_failure_stops_monitoring(monkeypatch, tmp_path, capsys):
    calls, _ = setup_xbox_transport(monkeypatch, tmp_path, "exhausted")
    with pytest.raises(SystemExit) as stopped:
        asyncio.run(monitor.xbox_monitor_user("ExampleTag", ""))
    assert stopped.value.code == 1
    assert calls[-1] == "titlehub.xboxlive.com"
    assert "peoplehub.xboxlive.com" not in calls
    assert "file descriptors" in capsys.readouterr().out


@pytest.mark.parametrize("scenario, expected", [("home", "User activity detected"), ("game", "User detected playing a game 'Example Game'")])
# Distinguishes system activity from gameplay while preserving both activity timestamps
def test_history_announcements_match_the_record(monkeypatch, tmp_path, capsys, scenario, expected):
    setup_xbox_transport(monkeypatch, tmp_path, scenario)
    with pytest.raises(EndOfEvidence):
        asyncio.run(monitor.xbox_monitor_user("ExampleTag", ""))
    output = capsys.readouterr().out
    assert expected in output
    if scenario == "home":
        assert "detected playing" not in output
