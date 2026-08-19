import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

import xbox_monitor


# Minimal auth manager stub whose token refresh replays a scripted sequence of outcomes
class FakeAuthManager:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.oauth = None

    async def refresh_tokens(self):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome


# Builds an HTTPStatusError carrying the given status code
def make_status_error(status_code):
    request = httpx.Request("POST", "https://login.live.com/oauth20_token.srf")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


# Verifies transient network and server-side errors are classified as retryable
def test_transient_errors_are_detected():
    assert xbox_monitor.is_transient_auth_error(httpx.ReadTimeout("timed out"))
    assert xbox_monitor.is_transient_auth_error(httpx.ConnectError("no route"))
    assert xbox_monitor.is_transient_auth_error(make_status_error(503))
    assert xbox_monitor.is_transient_auth_error(make_status_error(429))
    assert not xbox_monitor.is_transient_auth_error(make_status_error(400))
    assert not xbox_monitor.is_transient_auth_error(ValueError("bad token"))


# Verifies a read timeout is retried instead of aborting the tool
def test_refresh_retries_read_timeout(monkeypatch):
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRIES", 3)
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRY_DELAY", 0)
    auth_mgr = FakeAuthManager([httpx.ReadTimeout("timed out"), httpx.ReadTimeout("timed out"), None])
    asyncio.run(xbox_monitor.refresh_tokens_with_retry(auth_mgr))
    assert auth_mgr.calls == 3


# Verifies the last transient failure is raised once all attempts are exhausted
def test_refresh_gives_up_after_last_attempt(monkeypatch):
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRIES", 2)
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRY_DELAY", 0)
    auth_mgr = FakeAuthManager([httpx.ReadTimeout("timed out"), httpx.ReadTimeout("timed out")])
    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(xbox_monitor.refresh_tokens_with_retry(auth_mgr))
    assert auth_mgr.calls == 2


# Verifies a credential error is raised immediately without consuming retries
def test_refresh_does_not_retry_credential_error(monkeypatch):
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRIES", 3)
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRY_DELAY", 0)
    auth_mgr = FakeAuthManager([make_status_error(400), None])
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(xbox_monitor.refresh_tokens_with_retry(auth_mgr))
    assert auth_mgr.calls == 1


# Verifies a network timeout never falls through to the interactive OAuth prompt
def test_network_timeout_does_not_trigger_interactive_auth(monkeypatch, tmp_path):
    tokens_file = tmp_path / "xbox_tokens.json"
    tokens_file.write_text("{}")
    monkeypatch.setattr(xbox_monitor, "MS_AUTH_TOKENS_FILE", str(tokens_file))
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRIES", 2)
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRY_DELAY", 0)
    auth_mgr = FakeAuthManager([httpx.ReadTimeout("timed out"), httpx.ReadTimeout("timed out")])
    with patch.object(xbox_monitor.OAuth2TokenResponse, "model_validate_json", return_value=None) as validate, patch.object(xbox_monitor, "oauth_interactive_auth") as interactive:
        with pytest.raises(httpx.ReadTimeout):
            asyncio.run(xbox_monitor.authenticate_and_refresh_tokens(auth_mgr))
    assert validate.called
    assert not interactive.called
    assert auth_mgr.calls == 2


# Verifies a temporary server-side error never falls through to the interactive OAuth prompt
def test_server_error_does_not_trigger_interactive_auth(monkeypatch, tmp_path):
    tokens_file = tmp_path / "xbox_tokens.json"
    tokens_file.write_text("{}")
    monkeypatch.setattr(xbox_monitor, "MS_AUTH_TOKENS_FILE", str(tokens_file))
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRIES", 2)
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRY_DELAY", 0)
    auth_mgr = FakeAuthManager([make_status_error(503), make_status_error(503)])
    with patch.object(xbox_monitor.OAuth2TokenResponse, "model_validate_json", return_value=None), patch.object(xbox_monitor, "oauth_interactive_auth") as interactive:
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(xbox_monitor.authenticate_and_refresh_tokens(auth_mgr))
    assert not interactive.called


# Verifies an expired refresh token still triggers interactive re-authentication
def test_credential_error_triggers_interactive_auth(monkeypatch, tmp_path):
    tokens_file = tmp_path / "xbox_tokens.json"
    tokens_file.write_text("{}")
    monkeypatch.setattr(xbox_monitor, "MS_AUTH_TOKENS_FILE", str(tokens_file))
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRIES", 2)
    monkeypatch.setattr(xbox_monitor, "TOKEN_REFRESH_RETRY_DELAY", 0)
    auth_mgr = FakeAuthManager([make_status_error(400), None])
    fake_token = SimpleNamespace(model_dump_json=lambda: "{}")

    async def fake_interactive(mgr):
        mgr.oauth = fake_token

    with patch.object(xbox_monitor.OAuth2TokenResponse, "model_validate_json", return_value=fake_token), patch.object(xbox_monitor, "oauth_interactive_auth", side_effect=fake_interactive) as interactive:
        asyncio.run(xbox_monitor.authenticate_and_refresh_tokens(auth_mgr))
    assert interactive.called
    assert auth_mgr.calls == 2


# Verifies the Xbox HTTP session overrides the aggressive default library timeout
def test_signed_session_uses_configured_timeout(monkeypatch):
    monkeypatch.setattr(xbox_monitor, "XBOX_API_TIMEOUT", 42)
    session = xbox_monitor.create_signed_session()
    try:
        request = session.build_request("POST", "https://login.live.com/oauth20_token.srf")
        assert request.extensions["timeout"] == {"connect": 42.0, "read": 42.0, "write": 42.0, "pool": 42.0}
    finally:
        asyncio.run(session.aclose())
