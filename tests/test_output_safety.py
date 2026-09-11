"""Tests for what may reach the screen, the log file or an email: no live secret and no terminal control sequence.

Diagnostic output exists to be pasted into a public bug report. Game titles and gamertags arrive from Xbox
Live, so the tests drive the real print and send paths rather than the helpers alone.
"""

import re
import sys

import pytest

import xbox_monitor as monitor

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
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


# A value shorter than the floor is more likely a common word than a credential and blanking it hides the error
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


# Redaction must not eat the message around the secret or the error stops being diagnosable
def test_the_surrounding_message_survives_redaction():
    assert "could not be refreshed" in monitor.sanitize_error_text(f"The token {REFRESH_TOKEN} could not be refreshed")


# Which secret is loaded is answered by its name and source, so not even a prefix of a live key is shown
@pytest.mark.parametrize("value, shown", [(CLIENT_SECRET, "set"), ("", "not set"), ("your_client_secret", "not set")])
def test_a_secret_is_reported_as_presence_only(value, shown):
    assert monitor.secret_fingerprint(value) == shown


# Debug output is the most likely thing to be pasted in public, so it is redacted at the printer
def test_debug_output_is_redacted(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.debug_print(f"Refreshing with {CLIENT_SECRET}")
    assert CLIENT_SECRET not in capsys.readouterr().out


# Advice is built from exception text, which is exactly where a library tends to echo the value it was given
def test_advice_is_redacted_when_it_is_built():
    advice = monitor.classify_recovery_error(context="config.invalid", detail=f"rejected {CLIENT_SECRET}")
    assert CLIENT_SECRET not in advice.summary + advice.fix + advice.detail


# The technical detail is only printed in debug mode and that is the path most likely to carry raw text
def test_the_printed_technical_detail_is_redacted(monkeypatch, capsys):
    advice = monitor.make_recovery_advice("unknown", "Something broke", "Try again", True, f"raw {CLIENT_SECRET}")
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.print_recovery_advice(advice)
    assert CLIENT_SECRET not in capsys.readouterr().out


# The report is written to be shared, so a value must not reach it through a check label or detail either
def test_a_doctor_row_is_redacted():
    check = monitor.make_doctor_check("Authentication", "FAIL", f"Rejected {CLIENT_SECRET}", f"Sent {CLIENT_SECRET}", monitor.make_recovery_advice("unknown", "a summary", "do the thing", False))
    assert CLIENT_SECRET not in check.label + check.detail


# A rendered report goes into issue trackers whole, so the sweep runs over the finished text as well
def test_a_rendered_report_carries_no_secret():
    report = monitor.DoctorReport(checks=monitor.doctor_check_configuration() + monitor.doctor_secret_checks())
    rendered = monitor.render_doctor_sections(report)
    assert CLIENT_SECRET not in rendered
    assert "MS_APP_CLIENT_SECRET" in rendered


# --- Terminal control sequences in text that arrives from Xbox Live ---

# A gamertag, a game title or a bio is attacker-controlled text, so it must not be able to drive the terminal
@pytest.mark.parametrize("sequence, name", [
    ("\x1b[2J", "clear screen"),
    ("\x1b[H", "cursor home"),
    ("\x1b]0;pwned\x07", "window title"),
    ("\x1bc", "terminal reset"),
    ("\x07", "bell"),
    ("\x08\x08", "backspace"),
    ("\x7f", "delete"),
    ("\x9b31m", "single-byte CSI"),
])
def test_a_control_sequence_from_upstream_cannot_reach_the_terminal(sequence, name):
    cleaned = monitor.sanitize_terminal_text(f"Current game: {sequence}Halo")
    assert not CONTROL_CHARACTERS.search(cleaned), f"{name} survived as {cleaned!r}"
    assert cleaned.startswith("Current game: ") and cleaned.endswith("Halo")


# The sanitizer runs after this tool has coloured its own output, so removing colour would remove the feature
def test_this_tools_own_colours_survive_the_sanitizer():
    assert monitor.sanitize_terminal_text("\x1b[96;4mmisiektoja\x1b[0m") == "\x1b[96;4mmisiektoja\x1b[0m"


# A colour sequence rebuilt out of fragments would slip through a naive splitter, so the pieces are checked
def test_a_control_sequence_wrapped_in_colour_is_still_removed():
    cleaned = monitor.sanitize_terminal_text("\x1b[93mHalo\x1b[2J\x1b[0m")
    assert re.findall(r"\x1b\[[0-9;]*m", cleaned) == ["\x1b[93m", "\x1b[0m"]
    assert not CONTROL_CHARACTERS.search(re.sub(r"\x1b\[[0-9;]*m", "", cleaned))


# Tabs and newlines are layout, not control and stripping them would collapse every report into one line
def test_layout_whitespace_is_kept():
    assert monitor.sanitize_terminal_text("Gamertag:\tx\nXUID:\t1\n") == "Gamertag:\tx\nXUID:\t1\n"


# The whole console path has to sanitize, since a title reaches the screen through the ordinary print
def test_the_console_path_sanitizes_what_it_prints(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    stream = monitor.TerminalStream(sys.stdout)
    stream.write("Xbox user x started playing 'Halo\x1b[2J'\n")
    assert "\x1b" not in capsys.readouterr().out


# The log file is read later by a person or a tool, so it keeps no escape at all, not even this tool's own
def test_the_log_file_keeps_no_escape_sequence(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items()})
    log_path = tmp_path / "xbox_monitor.log"
    logger = monitor.Logger(str(log_path))
    logger.write(monitor.colorize("username", "misiektoja") + " started playing 'Halo\x1b[2J'\n")
    logger.logfile.close()
    written = log_path.read_text(encoding="utf-8")
    assert "\x1b" not in written
    assert "misiektoja" in written and "Halo" in written


# A truncated line must not end in the middle of a colour, since the terminal would keep that colour afterwards
def test_a_truncated_line_leaves_no_colour_open(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items()})
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 30)
    monitor.TerminalStream(sys.stdout).write("Xbox user misiektoja started playing 'Halo Infinite' on Xbox Series X\n")
    printed = capsys.readouterr().out
    assert len(re.sub(r"\x1b\[[0-9;]*m", "", printed).rstrip("\n")) == 30
    assert re.findall(r"\x1b\[[0-9;]*m", printed)[-1] == monitor.ANSI_RESET


# A subject line is built from a game title, so a line break in it would start a second mail header
@pytest.mark.parametrize("injected", ["Halo\nBcc: attacker@example.com", "Halo\r\nBcc: attacker@example.com", "Halo\x0bBcc: x"])
def test_a_mail_header_cannot_be_split_by_upstream_text(injected):
    header = monitor.sanitize_email_header(injected)
    assert "\n" not in header and "\r" not in header
    assert header.startswith("Halo")


# The real send path has to sanitize, since the subject is assembled far from the header it becomes
def test_the_sent_subject_carries_no_line_break(monkeypatch):
    captured = {}

    class RecordingSMTP:
        def __init__(self, host, port, timeout=None):
            pass

        def starttls(self, context=None):
            pass

        def login(self, user, password):
            pass

        def sendmail(self, sender, receiver, message):
            captured["message"] = message

        def quit(self):
            pass

    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_USER", "sender@example.com")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.com")
    monkeypatch.setattr(monitor.smtplib, "SMTP", RecordingSMTP)
    assert monitor.send_email("Xbox user x started playing 'Halo\nBcc: attacker@example.com'", "body", "", True) == 0
    headers = captured["message"].split("\n\n", 1)[0].splitlines()
    assert [line for line in headers if line.lower().startswith("bcc:")] == []


# Verifies a cut line closes the colour it opened, so the truncated tail does not paint every line printed after it
def test_a_truncated_line_closes_its_open_colour():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10) == "\x1b[31m0123456789" + monitor.ANSI_RESET


# Verifies no extra reset is added when the colour closed before the cut or the line was never cut
def test_a_closed_or_uncut_colour_gains_no_extra_reset():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("\x1b[31m0123\x1b[0m456789ABCDEF", 10) == "\x1b[31m0123\x1b[0m456789"
    assert monitor.truncate_string_per_line("\x1b[31m0123\x1b[0m", 10) == "\x1b[31m0123\x1b[0m"
    assert monitor.truncate_string_per_line("0123456789ABCDEF", 10) == "0123456789"
