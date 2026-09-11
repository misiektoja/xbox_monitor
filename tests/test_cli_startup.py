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
# Verifies email alerts switch off at startup while any SMTP setting is a shipped placeholder and stay on otherwise
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
@pytest.mark.parametrize("flag, runner", (("--set-ms-app-credentials", "run_set_ms_app_credentials"), ("--set-smtp-password", "run_set_smtp_password"), ("--set-webhook-url", "run_set_webhook_url")))
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


# Verifies --setup is not warned that the dotenv file is missing, since the path it was given is where the
# wizard is about to write the secrets
def test_setup_is_not_warned_that_the_dotenv_file_it_writes_is_missing(tmp_path, monkeypatch, capsys):
    pytest.importorskip("dotenv")
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: 0)
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--setup", "--config-file", str(tmp_path / "absent.conf"), "--env-file", str(tmp_path / "absent.env")])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
    assert "does not exist" not in capsys.readouterr().out


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


# Verifies the status file follows the setting, so a run from another directory resumes from the same file
def test_the_status_file_setting_relocates_the_saved_status(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "XBOX_STATUS_FILE", str(tmp_path / "state" / "SomeTag.json"))
    assert monitor.resolve_status_file("SomeTag") == str(tmp_path / "state" / "SomeTag.json")


# Verifies the default keeps the per-target name in the working directory, the behaviour earlier versions had
def test_an_empty_status_file_setting_keeps_the_default_name(monkeypatch):
    monkeypatch.setattr(monitor, "XBOX_STATUS_FILE", "")
    assert monitor.resolve_status_file("SomeTag") == "xbox_SomeTag_last_status.json"


# Verifies --status-file wins over the configured value, the precedence every other output path follows
def test_the_status_file_flag_overrides_the_configured_path(tmp_path, monkeypatch):
    config, env = write_startup_files(tmp_path)
    config.write_text(config.read_text(encoding="utf-8") + f'XBOX_STATUS_FILE = "{tmp_path / "from-config.json"}"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--doctor", "SomeTag", "--status-file", str(tmp_path / "from-flag.json"), "--config-file", str(config), "--env-file", str(env)])

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.resolve_status_file("SomeTag") == str(tmp_path / "from-flag.json")


GAMERTAG = "SomeTag"
DISCORD_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"
NTFY_URL = "https://ntfy.sh/private-topic-name"


# Verifies the webhook flags reach the run and that naming one alert also switches the channel on
def test_the_webhook_flags_reach_the_run(tmp_path, monkeypatch):
    config, env = write_startup_files(tmp_path)
    observed = run_startup(monkeypatch, [GAMERTAG, "--webhook-url", DISCORD_URL, "--webhook-game-change", "--config-file", str(config), "--env-file", str(env)], observe=("WEBHOOK_ENABLED", "WEBHOOK_URL", "WEBHOOK_GAME_CHANGE_NOTIFICATION"))
    assert observed["WEBHOOK_ENABLED"] is True
    assert observed["WEBHOOK_URL"] == DISCORD_URL
    assert observed["WEBHOOK_GAME_CHANGE_NOTIFICATION"] is True
    assert monitor.SECRET_SOURCES["WEBHOOK_URL"] == "command line"


# Verifies a destination that cannot be used stops the run at the flag rather than at the first delivery
def test_an_insecure_webhook_url_is_refused_by_the_parser(tmp_path, monkeypatch, capsys):
    config, env = write_startup_files(tmp_path)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", GAMERTAG, "--webhook-url", "http://discord.com/api/webhooks/1/token", "--config-file", str(config), "--env-file", str(env)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 2
    assert "--webhook-url needs a complete HTTPS link" in capsys.readouterr().err


# Verifies a destination that names its own service corrects a configured provider that disagrees with it
def test_a_recognised_destination_corrects_the_configured_provider(tmp_path, monkeypatch, capsys):
    config, env = write_startup_files(tmp_path, 'WEBHOOK_PROVIDER = "discord"\n')
    observed = run_startup(monkeypatch, [GAMERTAG, "--webhook-url", NTFY_URL, "--config-file", str(config), "--env-file", str(env)], observe=("WEBHOOK_PROVIDER",))
    assert observed["WEBHOOK_PROVIDER"] == "ntfy"
    assert "Configured webhook provider did not match the URL. Using ntfy." in capsys.readouterr().out


# Verifies a provider named on the command line is kept, since it was chosen deliberately for this run
def test_a_named_provider_is_never_corrected(tmp_path, monkeypatch, capsys):
    config, env = write_startup_files(tmp_path)
    observed = run_startup(monkeypatch, [GAMERTAG, "--webhook-url", NTFY_URL, "--webhook-provider", "discord", "--config-file", str(config), "--env-file", str(env)], observe=("WEBHOOK_PROVIDER",))
    assert observed["WEBHOOK_PROVIDER"] == "discord"
    assert "does not match the destination URL" not in capsys.readouterr().out


# Verifies the test command publishes one notification past the alert settings and exits on the result
@pytest.mark.parametrize("result, code", ((0, 0), (1, 1)))
def test_the_test_webhook_command_sends_one_forced_notification(tmp_path, monkeypatch, capsys, result, code):
    config, env = write_startup_files(tmp_path)
    sent = []
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: sent.append((args, kwargs)) or result)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--send-test-webhook", "--webhook-url", DISCORD_URL, "--config-file", str(config), "--env-file", str(env)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == code
    assert len(sent) == 1
    assert sent[0][1]["force"] is True
    assert "discord.com" in capsys.readouterr().out


# Verifies a printed command carries the files this run was given, so the retest reads the settings that failed
def test_printed_commands_carry_the_files_this_run_was_given(monkeypatch):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/xbox.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/xbox.env")

    assert monitor.tool_command("--send-test-webhook", method="pip") == "xbox_monitor --send-test-webhook --config-file /etc/xbox.conf --env-file /etc/xbox.env"
    assert monitor.tool_command("--generate-config", "plain.conf", method="pip", include_paths=False) == "xbox_monitor --generate-config plain.conf"


# Verifies the missing-target fix carries this run's files and leaves the placeholder readable
def test_the_missing_target_command_carries_the_files_and_the_placeholder(monkeypatch):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/xbox.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/xbox.env")

    fix = monitor.classify_recovery_error(None, context="target.missing").fix

    assert "xbox_monitor.py <xbox_gamertag> --config-file /etc/xbox.conf --env-file /etc/xbox.env" in fix
    assert "'<xbox_gamertag>'" not in fix


# Verifies a <placeholder> is printed for the reader to replace rather than quoted as a literal value
def test_a_placeholder_argument_is_left_unquoted():
    assert monitor.render_command(["<xbox_gamertag>", "-u", "<client_id>"]) == "<xbox_gamertag> -u <client_id>"
    assert monitor.render_command(["a value"]) == "'a value'"


# Verifies the disabled dotenv search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_dotenv_search_is_carried_only_where_it_is_accepted(monkeypatch):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")

    assert monitor.tool_command("--doctor", method="pip") == "xbox_monitor --doctor --env-file none"
    assert monitor.tool_command("--set-ms-app-credentials", method="pip") == "xbox_monitor --set-ms-app-credentials"
    assert monitor.tool_command("--setup", method="pip") == "xbox_monitor --setup"


# Verifies the disabled config search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_config_search_is_carried_only_where_it_is_accepted(monkeypatch):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "CONFIG_DISCOVERY_DISABLED", True)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")

    assert monitor.tool_command("--doctor", method="pip") == "xbox_monitor --doctor --config-file none"
    assert monitor.tool_command("--set-ms-app-credentials", method="pip") == "xbox_monitor --set-ms-app-credentials --config-file none"
    assert monitor.tool_command("--setup", method="pip") == "xbox_monitor --setup"
    assert monitor.tool_command("--doctor", method="pip", include_paths=False) == "xbox_monitor --doctor"


# Verifies a caller that already names a file is not given a second copy of it
def test_a_path_the_caller_passed_is_not_repeated(monkeypatch):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/xbox.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/xbox.env")

    assert monitor.tool_command("--doctor", "--env-file", "/tmp/other.env", method="pip") == "xbox_monitor --doctor --env-file /tmp/other.env --config-file /etc/xbox.conf"


# Verifies both test commands carry the subject, title and body shared with the sibling monitors
def test_the_test_messages_use_the_shared_wording(tmp_path, monkeypatch):
    config, env = write_startup_files(tmp_path)
    emails, webhooks = [], []
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: emails.append(args) or 0)
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: webhooks.append(args) or 0)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    for flag in ("--send-test-email", "--send-test-webhook"):
        monkeypatch.setattr(sys, "argv", ["xbox_monitor", flag, "--webhook-url", DISCORD_URL, "--config-file", str(config), "--env-file", str(env)])
        with pytest.raises(SystemExit) as raised:
            monitor.main()
        assert raised.value.code == 0

    assert emails[0][:2] == ("xbox_monitor: test email", "This test email was sent by --send-test-email. Your SMTP settings work.")
    assert webhooks[0][:2] == ("xbox_monitor: test webhook", "This test notification was sent by --send-test-webhook. Your webhook settings work.")

# Verifies the liveness reminder follows the configured interval whatever the check interval is
@pytest.mark.parametrize("check_interval,liveness_interval,expected", [(300, 43200, 43200), (86400, 43200, 43200), (300, 0, 0)])
def test_the_liveness_reminder_follows_the_configured_interval(monkeypatch, check_interval, liveness_interval, expected):
    monkeypatch.setattr(monitor, "XBOX_CHECK_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", liveness_interval)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 99)

    monitor.validate_monitor_timers()

    assert monitor.LIVENESS_REMINDER_SECONDS == expected


# Verifies the guide link opens the setup page the sibling monitors link, with no section fragment
def test_the_welcome_guide_link_opens_the_shared_setup_page():
    assert monitor.QUICK_START_GUIDE_URL.endswith("/setup-and-first-run/")


# Verifies --setup runs before the connectivity probe, since it writes files and needs no network
def test_setup_runs_before_the_connectivity_probe(tmp_path, monkeypatch):
    def refuse_probe(*args, **kwargs):
        raise AssertionError("the connectivity probe ran before setup")

    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: 0)
    monkeypatch.setattr(monitor, "check_internet", refuse_probe)
    monkeypatch.setattr(sys, "argv", ["xbox_monitor", "--setup", "--config-file", str(tmp_path / "new.conf"), "--env-file", str(tmp_path / ".env")])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    assert raised.value.code == 0
