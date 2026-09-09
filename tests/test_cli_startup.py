"""Tests that drive real startup through main() and assert on what a user sees on the paths they walk."""

import io
import os
import sys

import pytest

import xbox_monitor as monitor


# Raised by a stubbed step to stop startup once the part under test has run
class StartupStopped(BaseException):
    pass


# Writes a config file and a dotenv file into the temporary directory and returns both paths
def write_startup_files(tmp_path, config_text="", env_text=""):
    config = tmp_path / "xbox_monitor.conf"
    config.write_text('LOCAL_TIMEZONE = "UTC"\n' + config_text, encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text(env_text, encoding="utf-8")
    return config, env


# Runs main() with the given arguments, stops it at the named step and returns the module state seen there
def run_startup(monkeypatch, arguments, stop_at="check_internet", observe=()):
    observed = {}

    def stop(*args, **kwargs):
        for name in observe:
            observed[name] = getattr(monitor, name)
        raise StartupStopped

    monkeypatch.setattr(sys, "argv", ["xbox_monitor", *map(str, arguments)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)
    monkeypatch.setattr(monitor, stop_at, stop)
    with pytest.raises(StartupStopped):
        monitor.main()
    return observed


# Verifies --debug is already on while the config file loads and stays on after a config that disables it
def test_the_debug_flag_beats_a_config_that_disables_it(tmp_path, monkeypatch, capsys):
    config, _ = write_startup_files(tmp_path, "DEBUG_MODE = False\n")
    seen = {}
    real_load = monitor.load_config_file

    def observing_load(config_path, namespace=None, report_errors=True, advice_out=None):
        seen["during_load"] = monitor.DEBUG_MODE
        return real_load(config_path, namespace, report_errors, advice_out)

    monkeypatch.setattr(monitor, "load_config_file", observing_load)

    observed = run_startup(monkeypatch, ["gamer", "--debug", "--config-file", config, "--env-file", "none"], observe=("DEBUG_MODE",))

    assert seen["during_load"] is True
    assert observed["DEBUG_MODE"] is True
    assert "[DEBUG " in capsys.readouterr().out


@pytest.mark.parametrize("config_text, expected", [("DEBUG_MODE = True\n", True), ("", False)])
# Verifies the config file still decides debug mode when the command line says nothing about it
def test_the_config_file_decides_debug_mode_without_the_flag(tmp_path, monkeypatch, config_text, expected):
    config, _ = write_startup_files(tmp_path, config_text)

    observed = run_startup(monkeypatch, ["gamer", "--config-file", config, "--env-file", "none"], observe=("DEBUG_MODE",))

    assert observed["DEBUG_MODE"] is expected


# Verifies an exported secret wins over the dotenv file and each secret is attributed to the source that supplied it
def test_secret_sources_name_where_each_value_came_from(tmp_path, monkeypatch, capsys):
    config, env = write_startup_files(tmp_path, env_text='MS_APP_CLIENT_ID="dotenv-client-id-value"\nMS_APP_CLIENT_SECRET="dotenv-client-secret-value"\n')
    monkeypatch.setenv("MS_APP_CLIENT_SECRET", "exported-client-secret-value")

    observed = run_startup(monkeypatch, ["gamer", "--debug", "--config-file", config, "--env-file", env], observe=("SECRET_SOURCES", "MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"))

    assert observed["MS_APP_CLIENT_ID"] == "dotenv-client-id-value"
    assert observed["MS_APP_CLIENT_SECRET"] == "exported-client-secret-value"
    assert observed["SECRET_SOURCES"] == {"MS_APP_CLIENT_ID": "dotenv file", "MS_APP_CLIENT_SECRET": "environment"}
    out = capsys.readouterr().out
    assert "Secret resolved: name=MS_APP_CLIENT_ID, source=dotenv file" in out
    assert "Secret resolved: name=MS_APP_CLIENT_SECRET, source=environment" in out
    assert "Secret resolved: name=SMTP_PASSWORD, source=nowhere" in out


# Verifies a secret kept in the config file is attributed to it and one from the command line overrides that
def test_config_file_and_command_line_secrets_are_attributed(tmp_path, monkeypatch):
    config, _ = write_startup_files(tmp_path, 'SMTP_PASSWORD = "config-file-password-value"\nMS_APP_CLIENT_ID = "config-file-client-id"\n')
    monkeypatch.setattr(monitor, "check_internet", lambda url=None, timeout=None: True)

    observed = run_startup(monkeypatch, ["gamer", "--config-file", config, "--env-file", "none", "-u", "command-line-client-id", "-w", "command-line-client-secret", "-d"], stop_at="xbox_monitor_user", observe=("SECRET_SOURCES",))

    assert observed["SECRET_SOURCES"] == {"SMTP_PASSWORD": "configuration file", "MS_APP_CLIENT_ID": "command line", "MS_APP_CLIENT_SECRET": "command line"}


# Verifies a shipped placeholder loaded from the dotenv file is never recorded as a source
def test_a_placeholder_in_the_dotenv_file_is_not_a_source(tmp_path, monkeypatch):
    config, env = write_startup_files(tmp_path, env_text='SMTP_PASSWORD="your_smtp_password"\n')

    observed = run_startup(monkeypatch, ["gamer", "--config-file", config, "--env-file", env], observe=("SECRET_SOURCES", "SMTP_PASSWORD"))

    assert observed["SMTP_PASSWORD"] == "your_smtp_password"
    assert "SMTP_PASSWORD" not in observed["SECRET_SOURCES"]


@pytest.mark.parametrize("smtp_user, expected", [("your_smtp_user", False), ("monitor@example.test", True)])
# Verifies email alerts switch off at startup while any SMTP setting is a shipped placeholder, and stay on otherwise
def test_email_alerts_follow_the_smtp_placeholders(tmp_path, monkeypatch, capsys, smtp_user, expected):
    config, env = write_startup_files(tmp_path, f'SMTP_HOST = "smtp.example.test"\nSMTP_USER = "{smtp_user}"\nSENDER_EMAIL = "monitor@example.test"\nRECEIVER_EMAIL = "alerts@example.test"\n', env_text='MS_APP_CLIENT_ID="dotenv-client-id-value"\nMS_APP_CLIENT_SECRET="dotenv-client-secret-value"\nSMTP_PASSWORD="dotenv-smtp-password-value"\n')
    monkeypatch.setattr(monitor, "check_internet", lambda url=None, timeout=None: True)

    observed = run_startup(monkeypatch, ["gamer", "--config-file", config, "--env-file", env, "-d"], stop_at="xbox_monitor_user", observe=("ERROR_NOTIFICATION",))

    assert observed["ERROR_NOTIFICATION"] is expected
    out = capsys.readouterr().out
    assert ("errors" in out.split("Notifications (email):")[1].splitlines()[0]) is expected


# Verifies a placeholder client secret is rejected before anything talks to Xbox Live
def test_a_placeholder_client_secret_stops_startup(tmp_path, monkeypatch, capsys):
    config, env = write_startup_files(tmp_path, env_text='MS_APP_CLIENT_ID="dotenv-client-id-value"\nMS_APP_CLIENT_SECRET="your_ms_application_secret_value"\n')
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "gamer", "--config-file", str(config), "--env-file", str(env)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)
    monkeypatch.setattr(monitor, "check_internet", lambda url=None, timeout=None: True)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 1
    assert "MS_APP_CLIENT_SECRET" in capsys.readouterr().out


@pytest.mark.parametrize("value, expected", [("real-value", True), ("  spaced  ", True), ("", False), ("   ", False), (None, False), (42, False), ("your_smtp_password", False), (" your_anything", False)])
# Verifies the one placeholder predicate treats blanks, non-strings and shipped placeholders as unset
def test_secret_is_set_recognizes_placeholders(value, expected):
    assert monitor.secret_is_set(value) is expected


# Verifies the install method follows how the tool was started and shapes the commands it prints
def test_install_method_follows_how_the_tool_was_started(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["/usr/local/bin/xbox_monitor"])
    assert monitor.detect_install_method() == "pip"
    assert monitor.tool_command_prefix() == "xbox_monitor"
    assert monitor.install_method_display_name() == "PyPI install"

    monkeypatch.setattr(sys, "argv", ["xbox_monitor.py"])
    assert monitor.detect_install_method() == "manual"
    assert monitor.tool_command_prefix().endswith(" xbox_monitor.py")
    assert monitor.install_method_display_name() == "downloaded script"


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell quoting")
# Verifies a rendered command quotes arguments for the shell the user pastes it into
def test_rendered_commands_quote_arguments_for_the_shell():
    assert monitor.tool_command("--generate-config", "my conf.conf", method="pip") == "xbox_monitor --generate-config 'my conf.conf'"
    assert monitor.tool_command("--generate-config", "plain.conf", method="pip") == "xbox_monitor --generate-config plain.conf"


# Verifies --generate-config refuses to replace an existing file outside a terminal and names the way around it
def test_generate_config_refuses_to_replace_a_file_outside_a_terminal(tmp_path, monkeypatch, capsys):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--generate-config", str(destination)])
    monkeypatch.setattr(monitor.sys, "stdin", io.StringIO(""))

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 1
    out = capsys.readouterr().out
    assert "already exists" in out
    assert f"--generate-config {destination} --force" in out
    assert destination.read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"
    assert [entry.name for entry in tmp_path.iterdir()] == ["xbox_monitor.conf"]


# Verifies --generate-config --force replaces the file, keeps a backup and says where it is
def test_generate_config_force_replaces_the_file_and_names_the_backup(tmp_path, monkeypatch, capsys):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--generate-config", str(destination), "--force"])
    monkeypatch.setattr(monitor.sys, "stdin", io.StringIO(""))

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    out = capsys.readouterr().out
    assert f"Config written to: {destination}" in out
    assert "Previous config backed up to:" in out
    assert destination.read_text(encoding="utf-8") == monitor.CONFIG_BLOCK.strip("\n") + "\n"
    backups = [entry for entry in tmp_path.iterdir() if entry.name.endswith(".bak")]
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"


# Verifies --generate-config still prints the template to stdout when no file is named
def test_generate_config_without_a_file_prints_the_template(monkeypatch, capsysbinary):
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--generate-config"])

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    assert capsysbinary.readouterr().out == (monitor.CONFIG_BLOCK.strip("\n") + "\n").encode("utf-8")


# Verifies a bare invocation with a saved gamertag starts monitoring instead of printing the welcome screen
def test_a_saved_gamertag_starts_monitoring_instead_of_the_welcome_screen(tmp_path, monkeypatch, capsys):
    config, _ = write_startup_files(tmp_path, 'XBOX_GAMERTAG = "SomeTag"\n')
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", str(config))
    observed = run_startup(monkeypatch, [], observe=("XBOX_GAMERTAG",))

    assert observed["XBOX_GAMERTAG"] == "SomeTag"
    assert "Run the guided setup wizard now?" not in capsys.readouterr().out


# Verifies a gamertag given on the command line wins over the saved one
def test_a_gamertag_argument_beats_the_saved_one(tmp_path, monkeypatch):
    config, _ = write_startup_files(tmp_path, 'XBOX_GAMERTAG = "SavedTag"\n')
    seen = {}
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: seen.update({"target": args[0]}) or 0)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--doctor", "TypedTag", "--config-file", str(config)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit):
        monitor.main()

    assert seen["target"] == "TypedTag"


# Verifies --setup is reached without a gamertag, since choosing one is part of what it does
def test_setup_runs_without_a_gamertag(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: seen.update(kwargs) or 0)
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--setup", "--config-file", str(tmp_path / "new.conf"), "--env-file", str(tmp_path / ".env")])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    assert seen["config_file"] == str(tmp_path / "new.conf")


# Verifies the commands that write a secret are reached without a gamertag, which they exist to help configure
@pytest.mark.parametrize("flag, runner", (("--set-ms-app-credentials", "run_set_ms_app_credentials"), ("--set-smtp-password", "run_set_smtp_password")))
def test_a_secret_command_runs_without_a_gamertag(tmp_path, monkeypatch, flag, runner):
    config, env = write_startup_files(tmp_path)
    calls = []
    monkeypatch.setattr(monitor, runner, lambda **kwargs: calls.append(kwargs) or str(env))
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", flag, "--config-file", str(config), "--env-file", str(env)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    assert len(calls) == 1
    assert calls[0]["env_file"] == str(env)


# Verifies two secret commands at once are refused rather than silently running only the first
def test_two_secret_commands_at_once_are_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--set-ms-app-credentials", "--set-smtp-password"])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 2
    assert "cannot be combined with" in capsys.readouterr().err


# Verifies --generate-config does not swallow a run whose point is writing a secret
def test_generate_config_does_not_swallow_a_secret_command(tmp_path, monkeypatch):
    config, env = write_startup_files(tmp_path)
    calls = []
    monkeypatch.setattr(monitor, "run_set_smtp_password", lambda **kwargs: calls.append(kwargs) or str(env))
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--generate-config", "--set-smtp-password", "--config-file", str(config), "--env-file", str(env)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    assert len(calls) == 1


# Verifies --setup may name a config file that does not exist yet, since creating it is the point
def test_setup_may_name_a_config_file_that_does_not_exist_yet(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: 0)
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--setup", "--config-file", str(tmp_path / "absent.conf")])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    assert "does not exist" not in capsys.readouterr().out
