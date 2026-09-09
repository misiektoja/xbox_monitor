from unittest.mock import patch

import xbox_monitor


# Verifies SIGHUP schedules Xbox client recreation after application credentials change
def test_sighup_reload_increments_auth_refresh_version(monkeypatch):
    replacements = {"MS_APP_CLIENT_ID": "new-client-id", "MS_APP_CLIENT_SECRET": "new-client-secret"}
    monkeypatch.setattr(xbox_monitor, "DOTENV_FILE", "test.env")
    monkeypatch.setattr(xbox_monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(xbox_monitor, "MS_APP_CLIENT_ID", "old-client-id")
    monkeypatch.setattr(xbox_monitor, "MS_APP_CLIENT_SECRET", "old-client-secret")
    monkeypatch.setattr(xbox_monitor, "XBOX_AUTH_REFRESH_VERSION", 2)
    with patch("dotenv.load_dotenv"), patch.object(xbox_monitor.os, "getenv", side_effect=replacements.get):
        xbox_monitor.reload_secrets_signal_handler(xbox_monitor.signal.SIGHUP, None)
    assert xbox_monitor.MS_APP_CLIENT_ID == "new-client-id"
    assert xbox_monitor.MS_APP_CLIENT_SECRET == "new-client-secret"
    assert xbox_monitor.XBOX_AUTH_REFRESH_VERSION == 3


# Verifies a reloaded destination that belongs to the other service moves the provider with it
def test_sighup_reload_follows_the_provider_of_the_new_webhook_url(monkeypatch, capsys):
    replacements = {"WEBHOOK_URL": "https://ntfy.sh/private-topic-name"}
    monkeypatch.setattr(xbox_monitor, "DOTENV_FILE", "test.env")
    monkeypatch.setattr(xbox_monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(xbox_monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(xbox_monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/1/token")
    with patch("dotenv.load_dotenv"), patch.object(xbox_monitor.os, "getenv", side_effect=replacements.get):
        xbox_monitor.reload_secrets_signal_handler(xbox_monitor.signal.SIGHUP, None)
    assert xbox_monitor.WEBHOOK_PROVIDER == "ntfy"
    assert "Updated webhook provider to ntfy" in capsys.readouterr().out


# Verifies a destination whose service cannot be recognised leaves the configured provider alone
def test_sighup_reload_keeps_the_provider_for_an_unrecognised_url(monkeypatch):
    replacements = {"WEBHOOK_URL": "https://ntfy.example.test/topic"}
    monkeypatch.setattr(xbox_monitor, "DOTENV_FILE", "test.env")
    monkeypatch.setattr(xbox_monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(xbox_monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(xbox_monitor, "WEBHOOK_URL", "https://ntfy.sh/old-topic")
    with patch("dotenv.load_dotenv"), patch.object(xbox_monitor.os, "getenv", side_effect=replacements.get):
        xbox_monitor.reload_secrets_signal_handler(xbox_monitor.signal.SIGHUP, None)
    assert xbox_monitor.WEBHOOK_PROVIDER == "ntfy"
