"""Tests for redaction: nothing that reaches the screen, the log or an email may carry a live secret.

Diagnostic output exists to be pasted into a public bug report, so the tests drive the real print paths rather
than the redaction helper alone.
"""

import pytest

import xbox_monitor as monitor

CLIENT_SECRET = "Xy8Q~aVeryLongClientSecretValue"
REFRESH_TOKEN = "M.C123_BAY.0.U.-CkAbcdefghijklmnopqrstuvwxyz0123456789"


@pytest.fixture(autouse=True)
# Loads a realistic set of secrets, since redaction by known value only works once a value is known
def loaded_secrets(monkeypatch):
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "11111111-2222-3333-4444-555555555555")
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "an-smtp-password")


# A secret that is loaded has to be removed wherever it appears, whatever text happens to surround it
def test_a_loaded_secret_is_removed_from_arbitrary_text():
    text = monitor.sanitize_error_text(f"POST failed for secret {CLIENT_SECRET} at 12:00")
    assert CLIENT_SECRET not in text
    assert "<redacted>" in text


# A value shorter than the floor is more likely a common word than a credential, and blanking it hides the error
def test_a_short_value_is_not_treated_as_a_secret(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "abc")
    assert monitor.sanitize_error_text("the abc failed") == "the abc failed"


@pytest.mark.parametrize("text, leaked", [
    ("MS_APP_CLIENT_SECRET = some-unloaded-value", "some-unloaded-value"),
    ('{"refresh_token": "a-token-nobody-loaded"}', "a-token-nobody-loaded"),
    ("Authorization: Bearer an-unloaded-bearer-token", "an-unloaded-bearer-token"),
    ("Authorization: XBL3.0 x=1234;an-unloaded-xbl-token", "an-unloaded-xbl-token"),
    ("https://login.live.com/oauth?code=an-unloaded-authorization-code", "an-unloaded-authorization-code"),
])
# A secret the process never loaded still has a recognisable shape, which is the only handle redaction has
def test_a_secret_shaped_value_is_removed_even_when_it_was_never_loaded(text, leaked):
    assert leaked not in monitor.sanitize_error_text(text)


# Redaction must not eat the message around the secret, or the error stops being diagnosable
def test_the_surrounding_message_survives_redaction():
    assert "could not be refreshed" in monitor.sanitize_error_text(f"The token {REFRESH_TOKEN} could not be refreshed")


# Which secret is loaded is answered by its name and source, so not even a prefix of a live key is shown
@pytest.mark.parametrize("value, shown", [(CLIENT_SECRET, "<redacted>"), ("", "(not set)"), ("your_client_secret", "(not set)")])
def test_a_secret_is_reported_as_presence_only(value, shown):
    assert monitor.mask_secret(value) == shown


# Debug output is the most likely thing to be pasted in public, so it is redacted at the printer
def test_debug_output_is_redacted(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.debug_print(f"Refreshing with {CLIENT_SECRET}")
    assert CLIENT_SECRET not in capsys.readouterr().out


# Advice is built from exception text, which is exactly where a library tends to echo the value it was given
def test_advice_is_redacted_when_it_is_built():
    advice = monitor.classify_recovery_error(context="config.invalid", detail=f"rejected {CLIENT_SECRET}")
    assert CLIENT_SECRET not in advice.summary + advice.fix + advice.detail


# The technical detail is only printed in debug mode, and that is the path most likely to carry raw text
def test_the_printed_technical_detail_is_redacted(monkeypatch, capsys):
    advice = monitor.make_recovery_advice("unknown", "Something broke", "Try again", True, f"raw {CLIENT_SECRET}")
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.print_recovery_advice(advice)
    assert CLIENT_SECRET not in capsys.readouterr().out


# The report is written to be shared, so a value must not reach it through a check label or detail either
def test_a_doctor_row_is_redacted():
    check = monitor.make_doctor_check("Authentication", "FAIL", f"Rejected {CLIENT_SECRET}", f"Sent {CLIENT_SECRET}")
    assert CLIENT_SECRET not in check.label + check.detail


# A rendered report goes into issue trackers whole, so the sweep runs over the finished text as well
def test_a_rendered_report_carries_no_secret():
    report = monitor.DoctorReport(checks=monitor.doctor_check_configuration() + monitor.doctor_secret_checks())
    rendered = monitor.render_doctor_sections(report)
    assert CLIENT_SECRET not in rendered
    assert "MS_APP_CLIENT_SECRET" in rendered
