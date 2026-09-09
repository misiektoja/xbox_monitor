"""Tests for the --help screen and the zero-argument welcome screen, which are the two first-contact surfaces."""

import sys

import pytest

import xbox_monitor as monitor


# Returns the --help output, which argparse prints before exiting
def help_output(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--help"])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)
    with pytest.raises(SystemExit) as raised:
        monitor.main()
    assert raised.value.code == 0
    return capsys.readouterr().out


# Verifies every argument group is named for what a reader is looking for rather than for the code behind it
def test_the_argument_groups_say_what_they_are_for(monkeypatch, capsys):
    out = help_output(monkeypatch, capsys)
    for heading in ("Configuration & dotenv files:", "API credentials:", "Email notifications:", "User information & listing:", "Intervals & timers:", "Features & output:"):
        assert heading in out


# Verifies the commands that write a secret are listed with the files they write
def test_the_one_shot_commands_are_listed_with_the_files_they_write(monkeypatch, capsys):
    out = help_output(monkeypatch, capsys)
    configuration = out.split("Configuration & dotenv files:")[1].split("API credentials:")[0]
    for flag in ("--setup", "--set-ms-app-credentials", "--set-smtp-password", "--doctor"):
        assert flag in configuration


# Verifies the examples name the first run, the alerts and the diagnostics and end with one guide link
def test_the_examples_cover_the_three_things_a_newcomer_does(monkeypatch, capsys):
    out = help_output(monkeypatch, capsys)
    examples = out.split("Examples:")[1]
    assert examples.count("Guide: ") == 1
    for heading in ("Getting started:", "Notifications:", "Information and diagnostics:"):
        assert heading in examples
    assert "--setup" in examples and "--doctor <xbox_gamertag>" in examples


# Verifies the banner is printed before argparse can exit, so --help still identifies the tool
def test_the_banner_prints_before_the_help_screen(monkeypatch, capsys):
    out = help_output(monkeypatch, capsys)
    assert out.index(f"v{monitor.VERSION}") < out.index("usage: xbox_monitor")


# Verifies the rendered examples put one blank line between blocks and none inside a command
def test_the_rendered_examples_keep_one_blank_line_between_blocks():
    rendered = monitor.render_help_examples((("First", (("a comment", "a command"), ("another comment", "another command"))),), "https://example.com/guide")
    assert "\n\n\n" not in rendered
    assert rendered.splitlines()[:6] == ["Examples:", "", "First:", "  # a comment", "  a command", ""]


# Verifies the welcome screen names the four commands a newcomer needs and one guide link
def test_the_welcome_screen_names_the_commands_a_newcomer_needs(capsys):
    code = monitor.print_welcome_screen(interactive=False)
    out = capsys.readouterr().out
    assert code == 1
    assert "--setup" in out and "--doctor <xbox_gamertag>" in out and "-i <xbox_gamertag>" in out and "--help" in out
    assert out.count("Guide:") == 1
    assert monitor.XBOX_TARGET_FORMS in out


# Verifies the welcome screen offers the wizard only when there is a terminal to answer on
def test_the_wizard_is_offered_only_when_a_terminal_can_answer(capsys):
    monitor.print_welcome_screen(interactive=False)
    assert "answer Y below" not in capsys.readouterr().out


# Verifies answering yes on the welcome screen starts the wizard with the paths this run was given
def test_answering_yes_starts_the_wizard_with_the_given_paths(monkeypatch):
    seen = {}
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: seen.update(kwargs) or 0)
    code = monitor.print_welcome_screen(input_func=lambda prompt="": "y", interactive=True, config_file="some.conf", env_file="some.env")
    assert code == 0
    assert seen["config_file"] == "some.conf" and seen["env_file"] == "some.env"


# Verifies declining the wizard is a clean exit rather than the usage error it replaced
def test_declining_the_wizard_exits_cleanly(capsys):
    assert monitor.print_welcome_screen(input_func=lambda prompt="": "n", interactive=True) == 0


# Verifies Ctrl+C on the welcome screen reports the cancellation instead of a traceback
def test_an_interrupt_on_the_welcome_screen_reports_the_cancellation(capsys):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    code = monitor.print_welcome_screen(input_func=interrupt, interactive=True)
    out = capsys.readouterr().out
    assert code == 1
    assert "Setup cancelled." in out


# Verifies no block on the welcome screen is separated by more than one blank line
def test_the_welcome_screen_keeps_one_blank_line_between_blocks(capsys):
    monitor.print_welcome_screen(interactive=False)
    assert "\n\n\n" not in capsys.readouterr().out
