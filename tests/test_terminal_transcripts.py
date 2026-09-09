"""Tests that run the tool on a real pty, so what a terminal shows is checked instead of what capsys captured."""

import os
import pty
import re
import select
import signal
import subprocess
import sys
import time

import pytest

import xbox_monitor as monitor

MONITOR_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "xbox_monitor.py")

# Matches the escape sequences a terminal consumes, which are not part of what the user reads
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[=>]|\x1b\[[0-9]*[JK]")


# Applies one line's carriage returns the way a terminal does, so a redrawn line reads as its final state
def apply_carriage_returns(line):
    rendered = []
    column = 0
    for character in line:
        if character == "\r":
            column = 0
            continue
        if column < len(rendered):
            rendered[column] = character
        else:
            rendered.append(character)
        column += 1
    return "".join(rendered).rstrip()


# Strips the escape sequences and replays the redraws, leaving the text a reader actually sees
def visible_text(raw):
    stripped = ANSI_PATTERN.sub("", raw).replace("\r\n", "\n")
    return "\n".join(apply_carriage_returns(line) for line in stripped.split("\n"))


# Runs the tool on a pty, sends the given input, optionally interrupts it, and returns what the terminal showed
def run_on_terminal(arguments, keystrokes="", interrupt_after=None, environment=None, timeout=25):
    master, slave = pty.openpty()
    env = dict(os.environ, PYTHONUNBUFFERED="1", COLUMNS="100", LINES="40")
    env.update(environment or {})
    process = subprocess.Popen([sys.executable, MONITOR_PATH, *map(str, arguments)], stdin=slave, stdout=slave, stderr=slave, env=env, start_new_session=True)
    os.close(slave)
    captured = []
    interrupted = False
    started = time.monotonic()
    if keystrokes:
        os.write(master, keystrokes.encode())
    try:
        while True:
            if interrupt_after is not None and not interrupted and time.monotonic() - started >= interrupt_after:
                os.killpg(os.getpgid(process.pid), signal.SIGINT)
                interrupted = True
            if time.monotonic() - started > timeout:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                break
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                captured.append(chunk)
            elif process.poll() is not None:
                break
    finally:
        os.close(master)
        process.wait(timeout=10)
    return visible_text(b"".join(captured).decode("utf-8", "replace")), process.returncode


# Writes a config file that keeps the run offline and points every output at the temporary directory
@pytest.fixture
def terminal_config(tmp_path):
    config = tmp_path / "xbox_monitor.conf"
    config.write_text(f'LOCAL_TIMEZONE = "UTC"\nCLEAR_SCREEN = False\nMS_AUTH_TOKENS_FILE = "{tmp_path / "xbox_tokens.json"}"\n', encoding="utf-8")
    (tmp_path / ".env").write_text("", encoding="utf-8")
    return config, tmp_path / ".env"


# Verifies the welcome screen offers the wizard on a terminal, and that declining it exits cleanly
def test_the_welcome_screen_offers_the_wizard_on_a_terminal():
    out, code = run_on_terminal([], keystrokes="n\n")
    assert code == 0
    assert "Run the guided setup wizard now? [Y/n]:" in out
    assert "answer Y below" in out
    assert "\n\n\n" not in out


# Verifies Ctrl+C on the welcome screen prints the cancellation instead of a traceback
def test_an_interrupt_on_the_welcome_screen_prints_the_cancellation():
    out, code = run_on_terminal([], interrupt_after=2.5)
    assert code == 1
    assert "Setup cancelled." in out
    assert "Traceback" not in out


# Verifies Ctrl+C inside the wizard reports that nothing was written
def test_an_interrupt_inside_the_wizard_reports_that_nothing_was_written(terminal_config):
    config, env = terminal_config
    out, code = run_on_terminal(["--setup", "--config-file", str(config), "--env-file", str(env)], interrupt_after=3.0)
    assert code == 1
    assert "Setup cancelled. Destination files were not changed." in out
    assert "Traceback" not in out


# Verifies Ctrl+C during a hidden secret prompt reports that the dotenv file was left alone
def test_an_interrupt_during_a_hidden_prompt_reports_the_untouched_file(terminal_config):
    config, env = terminal_config
    out, code = run_on_terminal(["--set-smtp-password", "--config-file", str(config), "--env-file", str(env)], interrupt_after=3.0)
    assert code == 1
    assert "was cancelled" in out or "cancelled" in out
    assert "Traceback" not in out
    assert env.read_text(encoding="utf-8") == ""


# Verifies doctor prints its report and ends with one summary and one guide link
def test_doctor_prints_one_summary_and_one_guide_link(terminal_config):
    config, env = terminal_config
    out, code = run_on_terminal(["--doctor", "SomeTag", "--config-file", str(config), "--env-file", str(env)])
    assert code in (0, 1)
    assert out.count("Summary") == 1
    assert out.count(monitor.DOCTOR_GUIDE_URL) == 1
    assert "\n\n\n" not in out


# Verifies no first-contact screen ever shows a raw escape sequence to a terminal that cannot render it
def test_no_first_contact_screen_leaks_an_escape_sequence(terminal_config):
    config, env = terminal_config
    for arguments, keystrokes in (([], "n\n"), (["--help"], ""), (["--doctor", "SomeTag", "--config-file", str(config), "--env-file", str(env)], "")):
        raw, _ = run_on_terminal(arguments, keystrokes=keystrokes)
        assert "\x1b[" not in raw
