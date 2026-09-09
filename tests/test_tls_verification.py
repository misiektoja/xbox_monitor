"""Tests for VERIFY_SSL: which connections honour it, what is reported while it is off and its shipped default."""

import ssl
from pathlib import Path

import pytest

import xbox_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "xbox_monitor.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("verify", [True, False])
# The shared builder is the only place the setting is read, so every caller inherits the same decision
def test_the_shared_context_honours_the_setting(monkeypatch, verify):
    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    context = monitor.tls_context()
    assert context.check_hostname is verify
    assert (context.verify_mode == ssl.CERT_REQUIRED) is verify


# A second context anywhere would keep one connection verifying while the reader believes it is off
def test_only_the_shared_helper_builds_a_context():
    assert SOURCE.count("ssl.create_default_context()") == 1


@pytest.mark.parametrize("verify", [True, False])
# The connectivity probe runs before anything else, so it is where an intercepted network is first met
def test_the_connectivity_check_honours_the_setting(monkeypatch, verify):
    captured = {}

    class RecordingClient:
        def __init__(self, verify=None, timeout=None):
            captured["verify"] = verify
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            captured["url"] = url

    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    monkeypatch.setattr(monitor.httpx, "Client", RecordingClient)
    assert monitor.check_internet("https://xbox.example/probe", 5) is True
    assert captured["url"] == "https://xbox.example/probe"
    assert captured["verify"].check_hostname is verify


@pytest.mark.parametrize("verify", [True, False])
# Every Xbox Live call goes through this session, so the setting has to reach the library rather than stop here
def test_the_signed_session_honours_the_setting(monkeypatch, verify):
    captured = {}
    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    monkeypatch.setattr(monitor, "SignedSession", lambda ssl_context=None: captured.setdefault("context", ssl_context))
    monitor.create_signed_session()
    assert captured["context"].check_hostname is verify


@pytest.mark.parametrize("verify", [True, False])
# Email must not be the one channel that keeps verifying after the reader switched verification off
def test_the_smtp_handshake_honours_the_setting(monkeypatch, verify):
    captured = {}

    class RecordingSMTP:
        def __init__(self, host, port, timeout=None):
            pass

        def starttls(self, context=None):
            captured["context"] = context

        def login(self, user, password):
            pass

        def quit(self):
            pass

    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_SSL", True)
    monkeypatch.setattr(monitor, "SMTP_USER", "sender@example.com")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.com")
    monkeypatch.setattr(monitor.smtplib, "SMTP", RecordingSMTP)
    monitor.smtp_sign_in("smtp-password-value")
    assert captured["context"].check_hostname is verify


# While verification is on there is nothing for the reader to act on, so the row stays quiet
def test_the_doctor_passes_while_verification_is_on():
    check = next(item for item in monitor.doctor_check_configuration() if "TLS" in item.label)
    assert (check.status, check.advice) == ("PASS", None)


# While it is off the report has to name the setting to change and where that decision is documented
def test_the_doctor_warns_while_verification_is_off(monkeypatch):
    monkeypatch.setattr(monitor, "VERIFY_SSL", False)
    check = next(item for item in monitor.doctor_check_configuration() if "TLS" in item.label)
    assert check.status == "WARN"
    assert "VERIFY_SSL" in check.detail
    assert "VERIFY_SSL" in check.advice.fix
    assert monitor.TLS_GUIDE_URL in check.advice.fix


# Certificates are verified unless the reader turns that off, in the shipped config and the fallback alike
def test_certificates_are_verified_by_default():
    shipped = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")
    assert shipped["VERIFY_SSL"] is True
    assert monitor.VERIFY_SSL is True
