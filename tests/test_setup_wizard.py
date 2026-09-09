"""Tests that drive the setup wizard end to end and assert on what it writes and what it refuses to write."""

import pytest

import xbox_monitor as monitor


# Feeds scripted answers to the wizard and records the prompts it asked, so an unexpected question fails loudly
class ScriptedAnswers:
    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt=""):
        self.prompts.append(str(prompt))
        if not self.answers:
            raise AssertionError(f"The wizard asked one question too many: {prompt!r}")
        return self.answers.pop(0)


# Stands in for the interactive OAuth flow, recording its arguments instead of opening a browser
class TokenAuthorizer:
    def __init__(self, result='{"access_token": "test"}', error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def __call__(self, client_id, client_secret, input_func=None):
        self.calls.append((client_id, client_secret))
        if self.error is not None:
            raise self.error
        return self.result


# Points every destination at the temporary directory, so nothing the wizard writes escapes the test
@pytest.fixture
def wizard_paths(tmp_path, monkeypatch):
    tokens = tmp_path / "xbox_tokens.json"
    monkeypatch.setattr(monitor, "MS_AUTH_TOKENS_FILE", str(tokens))
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_USER", "someone@example.com")
    return {"config": tmp_path / "xbox_monitor.conf", "env": tmp_path / ".env", "tokens": tokens}


# Runs the wizard with scripted answers and the given stubs, returning its exit code and the answers object
def run_wizard(monkeypatch, paths, answers, secrets=("client-id", "client-secret"), authorizer=None, initial_target=None):
    scripted = ScriptedAnswers(answers)
    hidden = list(secrets)
    monkeypatch.setattr(monitor, "_wizard_request_tokens", authorizer or TokenAuthorizer())
    code = monitor.run_setup_wizard(
        initial_target=initial_target,
        config_file=str(paths["config"]),
        env_file=str(paths["env"]),
        input_func=scripted,
        getpass_func=lambda prompt="": hidden.pop(0) if hidden else "",
        interactive=True,
    )
    return code, scripted


# The answers for a complete run that saves, declines email, declines doctor and declines the launch offer
BASIC_ANSWERS = ["SomeTag", "", "5m", "90", "", "n", "", "", "", "1", "n", "n"]


# Verifies a complete run writes the config, the secrets and the token cache, and reports each destination
def test_a_complete_run_writes_every_destination(monkeypatch, wizard_paths, capsys):
    code, _ = run_wizard(monkeypatch, wizard_paths, BASIC_ANSWERS)
    out = capsys.readouterr().out
    assert code == 0
    assert wizard_paths["config"].is_file()
    assert "XBOX_GAMERTAG = 'SomeTag'" in wizard_paths["config"].read_text(encoding="utf-8")
    assert "XBOX_CHECK_INTERVAL = 300" in wizard_paths["config"].read_text(encoding="utf-8")
    assert 'MS_APP_CLIENT_ID="client-id"' in wizard_paths["env"].read_text(encoding="utf-8")
    assert 'MS_APP_CLIENT_SECRET="client-secret"' in wizard_paths["env"].read_text(encoding="utf-8")
    assert wizard_paths["tokens"].read_text(encoding="utf-8") == '{"access_token": "test"}'
    assert str(wizard_paths["config"]) in out and str(wizard_paths["env"]) in out and str(wizard_paths["tokens"]) in out


# Verifies the durations people type reach the config as whole seconds
def test_a_typed_duration_reaches_the_config_as_seconds(monkeypatch, wizard_paths):
    answers = ["SomeTag", "", "1h 30m", "2m", "", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "XBOX_CHECK_INTERVAL = 5400" in written
    assert "XBOX_ACTIVE_CHECK_INTERVAL = 120" in written


# Verifies a target the user declines to persist is left out of the config but still drives the printed commands
def test_a_target_the_user_declines_to_persist_stays_out_of_the_config(monkeypatch, wizard_paths, capsys):
    answers = ["SomeTag", "n", "5m", "90", "", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    out = capsys.readouterr().out
    assert "XBOX_GAMERTAG = ''" in wizard_paths["config"].read_text(encoding="utf-8")
    assert "--doctor SomeTag" in out


# Verifies a gamertag copied out of a profile link is accepted and an e-mail address is rejected by name
def test_the_target_question_accepts_a_link_and_rejects_an_email(monkeypatch, wizard_paths, capsys):
    answers = ["someone@example.com", "https://www.xbox.com/play/user/SomeTag", "", "5m", "90", "", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    out = capsys.readouterr().out
    assert "e-mail address" in out
    assert "XBOX_GAMERTAG = 'SomeTag'" in wizard_paths["config"].read_text(encoding="utf-8")


# Verifies discarding the answers leaves every destination file untouched
def test_discarding_the_answers_writes_nothing(monkeypatch, wizard_paths, capsys):
    answers = ["SomeTag", "", "5m", "90", "", "n", "", "", "", "3", "y"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers)
    out = capsys.readouterr().out
    assert code == 1
    assert not wizard_paths["config"].exists()
    assert not wizard_paths["env"].exists()
    assert not wizard_paths["tokens"].exists()
    assert "Setup cancelled. Destination files were not changed." in out


# Verifies Ctrl+C during questioning leaves every destination file untouched and says so
def test_an_interrupt_during_questioning_writes_nothing(monkeypatch, wizard_paths, capsys):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr(monitor, "_wizard_request_tokens", TokenAuthorizer())
    code = monitor.run_setup_wizard(config_file=str(wizard_paths["config"]), env_file=str(wizard_paths["env"]), input_func=interrupt, getpass_func=lambda prompt="": "", interactive=True)
    out = capsys.readouterr().out
    assert code == 1
    assert not wizard_paths["config"].exists()
    assert "Setup cancelled. Destination files were not changed." in out


# Verifies a run without a terminal explains itself and names the command that works instead
def test_without_a_terminal_the_wizard_names_generate_config(wizard_paths, capsys):
    code = monitor.run_setup_wizard(config_file=str(wizard_paths["config"]), env_file=str(wizard_paths["env"]), interactive=False)
    out = capsys.readouterr().out
    assert code == 1
    assert "interactive terminal" in out
    assert "--generate-config" in out
    assert not wizard_paths["config"].exists()


# Verifies the disabled dotenv setting is refused rather than writing secrets to a file named 'none'
def test_a_disabled_dotenv_is_refused_before_anything_is_asked(wizard_paths, capsys):
    code = monitor.run_setup_wizard(config_file=str(wizard_paths["config"]), env_file="none", interactive=True)
    out = capsys.readouterr().out
    assert code == 1
    assert "--setup needs a dotenv destination" in out


# Verifies a failing sign-in can be escaped, and that escaping it keeps the credentials the user entered
def test_a_failing_sign_in_can_be_escaped_without_losing_the_credentials(monkeypatch, wizard_paths, capsys):
    failing = TokenAuthorizer(error=RuntimeError("network down"))
    answers = ["SomeTag", "", "5m", "90", "", "y", "n", "", "", "", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, authorizer=failing)
    out = capsys.readouterr().out
    assert code == 0
    assert not wizard_paths["tokens"].exists()
    assert 'MS_APP_CLIENT_ID="client-id"' in wizard_paths["env"].read_text(encoding="utf-8")
    assert "Microsoft sign-in:" in out and "not done yet" in out


# Verifies the credentials question can be abandoned, which the summary then reports as incomplete
def test_abandoning_the_credentials_is_reported_as_incomplete(monkeypatch, wizard_paths, capsys):
    answers = ["SomeTag", "", "5m", "90", "y", "n", "", "", "", "1", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=["", ""])
    out = capsys.readouterr().out
    assert code == 0
    assert "Application credentials:" in out and "incomplete" in out
    assert not wizard_paths["env"].exists()


# Verifies a mail server that refuses the sign-in switches email off instead of writing half a configuration
def test_a_refused_mail_server_switches_email_off(monkeypatch, wizard_paths, capsys):
    advice = monitor.make_recovery_advice("smtp.authentication", "The mail server rejected the sign-in", "Check the password", False)

    def refuse(password, timeout=15):
        raise monitor.RecoveryError(advice)

    monkeypatch.setattr(monitor, "smtp_sign_in", refuse)
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "n", "", "", "", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "smtp-password"])
    out = capsys.readouterr().out
    assert code == 0
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "ACTIVE_INACTIVE_NOTIFICATION = False" in written
    assert "ERROR_NOTIFICATION = False" in written
    assert "Email notifications stay off" in out


# Verifies a mail server that can be reached but not contacted keeps the answers instead of discarding them
def test_a_retryable_mail_server_failure_keeps_the_answers(monkeypatch, wizard_paths, capsys):
    advice = monitor.make_recovery_advice("smtp.connection", "The mail server could not be reached", "Check the connection", True)

    def refuse(password, timeout=15):
        raise monitor.RecoveryError(advice)

    monkeypatch.setattr(monitor, "smtp_sign_in", refuse)
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "n", "1", "", "", "", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "smtp-password"])
    out = capsys.readouterr().out
    assert code == 0
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "SMTP_HOST = 'smtp.example.com'" in written
    assert "ACTIVE_INACTIVE_NOTIFICATION = True" in written
    assert "Run --doctor to check the sign-in again" in out


# Verifies the recommended email preset leaves the every-status alert off, since it also mails away transitions
def test_the_recommended_email_preset_leaves_the_every_status_alert_off(monkeypatch, wizard_paths):
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "1", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "smtp-password"])
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "ACTIVE_INACTIVE_NOTIFICATION = True" in written
    assert "GAME_CHANGE_NOTIFICATION = True" in written
    assert "STATUS_NOTIFICATION = False" in written
    assert "ERROR_NOTIFICATION = True" in written


# Verifies re-entering one section reverts only the keys that section owns
def test_editing_one_section_leaves_the_other_answers_alone(monkeypatch, wizard_paths):
    answers = ["SomeTag", "", "5m", "90", "", "n", "", "", "", "2", "2", "10m", "3m", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers)
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert code == 0
    assert "XBOX_CHECK_INTERVAL = 600" in written
    assert "XBOX_ACTIVE_CHECK_INTERVAL = 180" in written
    assert "XBOX_GAMERTAG = 'SomeTag'" in written


# Verifies a config file already in place is replaced only after the user agrees and a backup is taken
def test_an_existing_config_is_backed_up_before_it_is_replaced(monkeypatch, wizard_paths, capsys):
    wizard_paths["config"].write_text("# earlier config\n", encoding="utf-8")
    run_wizard(monkeypatch, wizard_paths, ["y", *BASIC_ANSWERS])
    out = capsys.readouterr().out
    backups = [path for path in wizard_paths["config"].parent.iterdir() if path.name.startswith("xbox_monitor.conf.")]
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# earlier config\n"
    assert "Backup:" in out


# Verifies a target already known from the command line is offered as the default rather than asked for again
def test_a_target_given_on_the_command_line_is_the_offered_default(monkeypatch, wizard_paths):
    answers = ["", "", "5m", "90", "", "n", "", "", "", "1", "n", "n"]
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers, initial_target="SomeTag")
    assert code == 0
    assert any("[SomeTag]" in prompt for prompt in scripted.prompts)
    assert "XBOX_GAMERTAG = 'SomeTag'" in wizard_paths["config"].read_text(encoding="utf-8")


# Verifies no secret the user typed is ever echoed back to the terminal
def test_no_entered_secret_reaches_the_screen(monkeypatch, wizard_paths, capsys):
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "1", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id-secret-value", "client-secret-value", "smtp-password-value"])
    out = capsys.readouterr().out
    for secret in ("client-id-secret-value", "client-secret-value", "smtp-password-value"):
        assert secret not in out


# Verifies the generated config still parses as a config file the tool would accept
def test_the_generated_config_is_one_the_tool_accepts(monkeypatch, wizard_paths):
    run_wizard(monkeypatch, wizard_paths, BASIC_ANSWERS)
    monitor.validate_config_content(wizard_paths["config"].read_text(encoding="utf-8"), str(wizard_paths["config"]))


# Verifies the token cache is written privately, since it holds a refresh token
def test_the_token_cache_is_written_privately(monkeypatch, wizard_paths):
    run_wizard(monkeypatch, wizard_paths, BASIC_ANSWERS)
    assert wizard_paths["tokens"].stat().st_mode & 0o077 == 0


# Verifies the wizard offers to launch monitoring only once a target and both credentials are settled
def test_the_launch_offer_needs_a_target_and_credentials(monkeypatch, wizard_paths, capsys):
    launched = []
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)
    answers = ["SomeTag", "", "5m", "90", "", "n", "", "", "", "1", "n", "y"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers)
    assert code == 0
    assert len(launched) == 1
    assert str(wizard_paths["config"]) in [str(argument) for argument in launched[0]]


# Verifies the doctor offer runs against the files setup just wrote rather than the state it started from
def test_the_doctor_offer_checks_the_saved_files(monkeypatch, wizard_paths):
    seen = {}

    def fake_doctor(xbox_gamertag=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None):
        seen.update({"target": xbox_gamertag, "config": config_path, "env": env_path, "client_id": monitor.MS_APP_CLIENT_ID})
        return 0

    monkeypatch.setattr(monitor, "run_doctor", fake_doctor)
    answers = ["SomeTag", "", "5m", "90", "", "n", "", "", "", "1", "y", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    assert seen["target"] == "SomeTag"
    assert seen["config"] == str(wizard_paths["config"])
    assert seen["env"] == str(wizard_paths["env"])
    assert seen["client_id"] == "client-id"


# Verifies a destination that cannot be written is refused before the first question is asked
def test_an_unwritable_destination_is_refused_before_any_question(wizard_paths, capsys):
    def refuse_every_question(prompt=""):
        raise AssertionError(f"Setup asked a question before checking its destinations: {prompt!r}")

    code = monitor.run_setup_wizard(config_file="/xbox_monitor_unwritable_root.conf", env_file=str(wizard_paths["env"]), input_func=refuse_every_question, interactive=True)
    out = capsys.readouterr().out
    assert code == 1
    assert "Configuration destination is not writable" in out
    assert "To fix:" in out


# Verifies a directory given as a destination is refused rather than failing at the save step
def test_a_directory_destination_is_refused(tmp_path, wizard_paths, capsys):
    code = monitor.run_setup_wizard(config_file=str(tmp_path), env_file=str(wizard_paths["env"]), interactive=True)
    out = capsys.readouterr().out
    assert code == 1
    assert "must be a file path, not a directory" in out


# Verifies the disabled config setting is refused, since setup exists to write one
def test_a_disabled_config_destination_is_refused(wizard_paths, capsys):
    code = monitor.run_setup_wizard(config_file="none", env_file=str(wizard_paths["env"]), interactive=True)
    out = capsys.readouterr().out
    assert code == 1
    assert "--setup needs a config destination" in out


# Verifies an existing config can be kept by sending the run to another path instead
def test_an_existing_config_can_be_redirected_to_another_path(monkeypatch, wizard_paths, tmp_path):
    wizard_paths["config"].write_text("# earlier config\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere.conf"
    code, _ = run_wizard(monkeypatch, wizard_paths, ["n", str(elsewhere), *BASIC_ANSWERS])
    assert code == 0
    assert wizard_paths["config"].read_text(encoding="utf-8") == "# earlier config\n"
    assert "XBOX_GAMERTAG = 'SomeTag'" in elsewhere.read_text(encoding="utf-8")


# Verifies declining to replace an existing config and naming no alternative ends the run without writing
def test_declining_an_existing_config_without_an_alternative_writes_nothing(monkeypatch, wizard_paths, capsys):
    wizard_paths["config"].write_text("# earlier config\n", encoding="utf-8")
    code, _ = run_wizard(monkeypatch, wizard_paths, ["n", ""])
    out = capsys.readouterr().out
    assert code == 1
    assert wizard_paths["config"].read_text(encoding="utf-8") == "# earlier config\n"
    assert not wizard_paths["env"].exists()
    assert "Setup cancelled. Destination files were not changed." in out


# Verifies a secret already in the dotenv file is kept when the replacement is declined
def test_an_existing_dotenv_secret_is_kept_unless_the_replacement_is_confirmed(monkeypatch, wizard_paths):
    wizard_paths["env"].write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "n", "1", "", "", "", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "typed-password"])
    written = wizard_paths["env"].read_text(encoding="utf-8")
    assert code == 0
    assert 'SMTP_PASSWORD="original"' in written
    assert "typed-password" not in written


# Verifies a confirmed replacement does reach the dotenv file
def test_a_confirmed_dotenv_secret_replacement_is_written(monkeypatch, wizard_paths):
    wizard_paths["env"].write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "y", "1", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "typed-password"])
    assert 'SMTP_PASSWORD="typed-password"' in wizard_paths["env"].read_text(encoding="utf-8")


# Verifies credentials already in the dotenv file are noticed even when this run did not load them
def test_credentials_in_the_dotenv_file_prompt_before_being_replaced(monkeypatch, wizard_paths):
    wizard_paths["env"].write_text('MS_APP_CLIENT_ID="stored-id"\nMS_APP_CLIENT_SECRET="stored-secret"\n', encoding="utf-8")
    answers = ["SomeTag", "", "5m", "90", "n", "", "n", "", "", "", "1", "n", "n"]
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers)
    assert code == 0
    assert any("Replace the Microsoft application credentials already configured?" in prompt for prompt in scripted.prompts)
    assert 'MS_APP_CLIENT_ID="stored-id"' in wizard_paths["env"].read_text(encoding="utf-8")
