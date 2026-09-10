"""Tests that drive the setup wizard end to end and assert on what it writes and what it refuses to write."""

import types

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
    hidden = list(secrets) if not callable(secrets) else []
    monkeypatch.setattr(monitor, "_wizard_request_tokens", authorizer or TokenAuthorizer())
    code = monitor.run_setup_wizard(
        initial_target=initial_target,
        config_file=str(paths["config"]),
        env_file=str(paths["env"]),
        input_func=scripted,
        getpass_func=secrets if callable(secrets) else (lambda prompt="": hidden.pop(0) if hidden else ""),
        interactive=True,
    )
    return code, scripted


# The answers for a complete run that saves, declines email, declines doctor and declines the launch offer
BASIC_ANSWERS = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "1", "n", "n"]


# Verifies a complete run writes the config, the secrets and the token cache and reports each destination
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


# Verifies the summary names the status file the run will use, built from the target when no path was given
def test_the_summary_names_the_default_status_file(monkeypatch, wizard_paths, capsys):
    code, _ = run_wizard(monkeypatch, wizard_paths, BASIC_ANSWERS)

    summary = capsys.readouterr().out.rsplit("Setup summary", 1)[1]
    assert code == 0
    assert "Status file:                    xbox_SomeTag_last_status.json" in summary


# Verifies a declined email section clears the mail server, so the written config cannot contradict the summary
def test_a_declined_email_section_clears_the_mail_server(monkeypatch, wizard_paths):
    code, _ = run_wizard(monkeypatch, wizard_paths, BASIC_ANSWERS)

    assert code == 0
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "smtp.example.com" not in written
    assert "someone@example.com" not in written


# Verifies a CSV answer without an extension is saved as a .csv file while an explicit extension is left alone
def test_the_csv_answer_gains_a_csv_extension_when_it_has_none(tmp_path):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_output_section(state, input_func=ScriptedAnswers(["y", str(tmp_path / "activity"), ""]))
    assert state.config_values["CSV_FILE"] == str(tmp_path / "activity.csv")

    monitor._wizard_collect_output_section(state, input_func=ScriptedAnswers(["y", str(tmp_path / "activity.txt"), ""]))
    assert state.config_values["CSV_FILE"] == str(tmp_path / "activity.txt")


# Verifies the status file question names the working directory, since the default is relative to where the tool runs
def test_the_status_file_question_names_the_working_directory(tmp_path):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return ""

    monitor._wizard_collect_output_section(state, input_func=answer)
    assert any("Optional status file path (blank uses the default name in the working directory)" in prompt for prompt in prompts)


# Verifies a status file answer without an extension is saved as a .json file while an explicit extension is left alone
def test_the_status_file_answer_gains_a_json_extension_when_it_has_none(tmp_path):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_output_section(state, input_func=ScriptedAnswers(["y", "", str(tmp_path / "profile")]))
    assert state.config_values["XBOX_STATUS_FILE"] == str(tmp_path / "profile.json")

    monitor._wizard_collect_output_section(state, input_func=ScriptedAnswers(["y", "", str(tmp_path / "profile.txt")]))
    assert state.config_values["XBOX_STATUS_FILE"] == str(tmp_path / "profile.txt")


# Verifies the durations people type reach the config as whole seconds
def test_a_typed_duration_reaches_the_config_as_seconds(monkeypatch, wizard_paths):
    answers = ["SomeTag", "", "1h 30m", "2m", "", "n", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "XBOX_CHECK_INTERVAL = 5400" in written
    assert "XBOX_ACTIVE_CHECK_INTERVAL = 120" in written


# Verifies a target the user declines to persist is left out of the config but still drives the printed commands
def test_a_target_the_user_declines_to_persist_stays_out_of_the_config(monkeypatch, wizard_paths, capsys):
    answers = ["SomeTag", "n", "5m", "90", "", "n", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    out = capsys.readouterr().out
    assert "XBOX_GAMERTAG = ''" in wizard_paths["config"].read_text(encoding="utf-8")
    assert "--doctor SomeTag" in out


# Verifies a gamertag copied out of a profile link is accepted and an e-mail address is rejected by name
def test_the_target_question_accepts_a_link_and_rejects_an_email(monkeypatch, wizard_paths, capsys):
    # the rejected e-mail address is followed by the retry offer, which the blank answer accepts
    answers = ["someone@example.com", "", "https://www.xbox.com/play/user/SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers)
    out = capsys.readouterr().out
    assert "e-mail address" in out
    assert "XBOX_GAMERTAG = 'SomeTag'" in wizard_paths["config"].read_text(encoding="utf-8")


# Verifies discarding the answers leaves every destination file untouched
def test_discarding_the_answers_writes_nothing(monkeypatch, wizard_paths, capsys):
    answers = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "3", "y"]
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


# Verifies a failing sign-in can be escaped and that escaping it keeps the credentials the user entered
def test_a_failing_sign_in_can_be_escaped_without_losing_the_credentials(monkeypatch, wizard_paths, capsys):
    failing = TokenAuthorizer(error=RuntimeError("network down"))
    answers = ["SomeTag", "", "5m", "90", "", "y", "n", "n", "", "", "", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, authorizer=failing)
    out = capsys.readouterr().out
    assert code == 0
    assert not wizard_paths["tokens"].exists()
    assert 'MS_APP_CLIENT_ID="client-id"' in wizard_paths["env"].read_text(encoding="utf-8")
    assert "Microsoft sign-in:" in out and "not done yet" in out


# Verifies the credentials question can be abandoned, which the summary then reports as incomplete
def test_abandoning_the_credentials_is_reported_as_incomplete(monkeypatch, wizard_paths, capsys):
    answers = ["SomeTag", "", "5m", "90", "y", "n", "n", "", "", "", "1", "n"]
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
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "n", "n", "", "", "", "1", "n", "n"]
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
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "n", "1", "n", "", "", "", "1", "n", "n"]
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
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "1", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "smtp-password"])
    written = wizard_paths["config"].read_text(encoding="utf-8")
    assert "ACTIVE_INACTIVE_NOTIFICATION = True" in written
    assert "GAME_CHANGE_NOTIFICATION = True" in written
    assert "STATUS_NOTIFICATION = False" in written
    assert "ERROR_NOTIFICATION = True" in written


# Verifies re-entering one section reverts only the keys that section owns
def test_editing_one_section_leaves_the_other_answers_alone(monkeypatch, wizard_paths):
    answers = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "2", "2", "10m", "3m", "1", "n", "n"]
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


# Echoes each prompt the way a terminal does, so the transcript is what the reader actually sees
class EchoingAnswers(ScriptedAnswers):
    def __call__(self, prompt=""):
        typed = super().__call__(prompt)
        print(f"{prompt}{typed}")
        return typed


# Verifies the wizard leaves no double blank line, including where a destination had nothing to ask about
@pytest.mark.parametrize("existing", [False, True])
def test_the_wizard_output_has_no_double_blank_lines(monkeypatch, wizard_paths, capsys, existing):
    if existing:
        wizard_paths["config"].write_text("# earlier config\n", encoding="utf-8")
    scripted = EchoingAnswers(["y", *BASIC_ANSWERS] if existing else BASIC_ANSWERS)
    monkeypatch.setattr(monitor, "_wizard_request_tokens", TokenAuthorizer())
    hidden = ["client-id", "client-secret"]
    code = monitor.run_setup_wizard(config_file=str(wizard_paths["config"]), env_file=str(wizard_paths["env"]), input_func=scripted, getpass_func=lambda prompt="": hidden.pop(0) if hidden else "", interactive=True)

    assert code == 0
    assert "\n\n\n" not in capsys.readouterr().out


# Verifies a target already known from the command line is offered as the default rather than asked for again
def test_a_target_given_on_the_command_line_is_the_offered_default(monkeypatch, wizard_paths):
    answers = ["", "", "5m", "90", "", "n", "n", "", "", "", "1", "n", "n"]
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers, initial_target="SomeTag")
    assert code == 0
    assert any("[SomeTag]" in prompt for prompt in scripted.prompts)
    assert "XBOX_GAMERTAG = 'SomeTag'" in wizard_paths["config"].read_text(encoding="utf-8")


# Verifies no secret the user typed is ever echoed back to the terminal
def test_no_entered_secret_reaches_the_screen(monkeypatch, wizard_paths, capsys):
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "1", "n", "", "", "", "1", "n", "n"]
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


# Verifies the wizard offers to launch monitoring only once a target is set and the doctor run passed
def test_the_launch_offer_needs_a_target_and_a_passed_doctor_run(monkeypatch, wizard_paths, capsys):
    launched = []
    monkeypatch.setattr(monitor, "run_doctor", lambda **kwargs: 0)
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)
    answers = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "1", "y", "y"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers)
    assert code == 0
    assert len(launched) == 1
    assert str(wizard_paths["config"]) in [str(argument) for argument in launched[0]]


# Verifies a declined doctor ends at the printed commands, so nothing is launched unchecked
def test_declining_the_doctor_removes_the_launch_offer(monkeypatch, wizard_paths):
    launched = []
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)
    answers = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "1", "n", "y"]
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers)
    assert code == 0
    assert launched == []
    assert not any("Start monitoring now?" in prompt for prompt in scripted.prompts)


# Verifies a doctor run that failed keeps the launch offer away and labels the command to run after the fix
def test_a_failed_doctor_run_removes_the_launch_offer(monkeypatch, wizard_paths, capsys):
    launched = []
    monkeypatch.setattr(monitor, "run_doctor", lambda **kwargs: 1)
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)
    answers = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "1", "y", "y"]
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers)
    assert code == 0
    assert launched == []
    assert not any("Start monitoring now?" in prompt for prompt in scripted.prompts)
    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies the doctor offer runs against the files setup just wrote rather than the state it started from
def test_the_doctor_offer_checks_the_saved_files(monkeypatch, wizard_paths):
    seen = {}

    def fake_doctor(xbox_gamertag=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None):
        seen.update({"target": xbox_gamertag, "config": config_path, "env": env_path, "client_id": monitor.MS_APP_CLIENT_ID})
        return 0

    monkeypatch.setattr(monitor, "run_doctor", fake_doctor)
    answers = ["SomeTag", "", "5m", "90", "", "n", "n", "", "", "", "1", "y", "n"]
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
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "n", "1", "n", "", "", "", "1", "n", "n"]
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "typed-password"])
    written = wizard_paths["env"].read_text(encoding="utf-8")
    assert code == 0
    assert 'SMTP_PASSWORD="original"' in written
    assert "typed-password" not in written


# Verifies a confirmed replacement does reach the dotenv file
def test_a_confirmed_dotenv_secret_replacement_is_written(monkeypatch, wizard_paths):
    wizard_paths["env"].write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    answers = ["SomeTag", "", "5m", "90", "", "y", "smtp.example.com", "587", "", "someone@example.com", "from@example.com", "to@example.com", "y", "1", "n", "", "", "", "1", "n", "n"]
    run_wizard(monkeypatch, wizard_paths, answers, secrets=["client-id", "client-secret", "typed-password"])
    assert 'SMTP_PASSWORD="typed-password"' in wizard_paths["env"].read_text(encoding="utf-8")


# Verifies credentials already in the dotenv file are noticed even when this run did not load them
def test_credentials_in_the_dotenv_file_prompt_before_being_replaced(monkeypatch, wizard_paths):
    wizard_paths["env"].write_text('MS_APP_CLIENT_ID="stored-id"\nMS_APP_CLIENT_SECRET="stored-secret"\n', encoding="utf-8")
    answers = ["SomeTag", "", "5m", "90", "n", "n", "n", "n", "", "", "", "1", "n", "n"]
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers)
    assert code == 0
    assert any("Replace the Microsoft application credentials already configured?" in prompt for prompt in scripted.prompts)
    assert 'MS_APP_CLIENT_ID="stored-id"' in wizard_paths["env"].read_text(encoding="utf-8")


DISCORD_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


# Returns the answers up to and including the declined email section, which every webhook run shares
def before_webhook_section():
    return ["SomeTag", "", "5m", "90", "", "n"]


# Returns the answers that follow the webhook section, ending with a saved run
def after_webhook_section():
    return ["", "", "", "1", "n", "n"]


# Answers each hidden prompt with the value that prompt asks for
def secrets_for(webhook_value, token_value=""):
    def answer(prompt=""):
        lowered = str(prompt).casefold()
        if "access token" in lowered:
            return token_value
        if "webhook url" in lowered or "topic" in lowered:
            return webhook_value
        return "client-secret" if "secret" in lowered else "client-id"

    return answer


# Verifies a configured Discord webhook writes its settings to the config and its URL to the dotenv file
def test_a_configured_webhook_is_saved(monkeypatch, wizard_paths):
    answers = before_webhook_section() + ["y", "1", "1"] + after_webhook_section()
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for(DISCORD_URL))
    values = monitor.parse_config_content(wizard_paths["config"].read_text(encoding="utf-8"), "xbox_monitor.conf")
    assert code == 0
    assert values["WEBHOOK_ENABLED"] is True
    assert values["WEBHOOK_PROVIDER"] == "discord"
    assert values["WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION"] is True
    assert values["WEBHOOK_STATUS_NOTIFICATION"] is False
    assert f'WEBHOOK_URL="{DISCORD_URL}"' in wizard_paths["env"].read_text(encoding="utf-8")


# Verifies the private destination is never displayed, in the prompts or in the summary that lists everything else
def test_the_webhook_url_is_never_displayed(monkeypatch, wizard_paths, capsys):
    answers = before_webhook_section() + ["y", "1", "1"] + after_webhook_section()
    run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for(DISCORD_URL))
    out = capsys.readouterr().out
    assert DISCORD_URL not in out
    assert "Webhook:" in out
    assert "Webhook alerts:" in out


# Verifies an ntfy topic name is expanded before it is written, so the saved value is a complete URL
def test_an_ntfy_topic_name_is_saved_as_a_url(monkeypatch, wizard_paths):
    # The ntfy branch asks one extra question, whether the topic needs its own access token
    answers = before_webhook_section() + ["y", "2", "n", "1"] + after_webhook_section()
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for("private-topic"))
    assert code == 0
    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in wizard_paths["env"].read_text(encoding="utf-8")


# Verifies an ntfy access token is written only when one was asked for
def test_an_ntfy_access_token_is_saved_when_offered(monkeypatch, wizard_paths):
    answers = before_webhook_section() + ["y", "2", "y", "1"] + after_webhook_section()
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for("private-topic", "tk_a_real_looking_token"))
    assert code == 0
    assert 'NTFY_ACCESS_TOKEN="tk_a_real_looking_token"' in wizard_paths["env"].read_text(encoding="utf-8")


# Verifies a token pasted with its authorization scheme can be given up on without losing the topic already entered
def test_a_pasted_ntfy_authorization_scheme_can_be_abandoned(monkeypatch, wizard_paths):
    # The "n" declines entering the token again, leaving the topic URL that was already accepted
    answers = before_webhook_section() + ["y", "2", "y", "n", "1"] + after_webhook_section()
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for("private-topic", "Bearer tk_a_real_looking_token"))
    written = wizard_paths["env"].read_text(encoding="utf-8")
    assert code == 0
    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in written
    assert "NTFY_ACCESS_TOKEN" not in written


# Verifies declining the webhook section leaves the channel and every alert it owns switched off
def test_declining_webhooks_turns_every_alert_off(monkeypatch, wizard_paths):
    # The error alert ships on, so declining has to switch it off rather than carry the shipped default through
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    run_wizard(monkeypatch, wizard_paths, BASIC_ANSWERS)
    values = monitor.parse_config_content(wizard_paths["config"].read_text(encoding="utf-8"), "xbox_monitor.conf")
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert values["WEBHOOK_GAME_CHANGE_NOTIFICATION"] is False


# Verifies an unusable destination is asked again and that giving up leaves the channel off rather than looping
def test_an_unusable_webhook_url_can_be_abandoned(monkeypatch, wizard_paths, capsys):
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    answers = before_webhook_section() + ["y", "1", "n"] + after_webhook_section()
    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for("not-a-url"))
    values = monitor.parse_config_content(wizard_paths["config"].read_text(encoding="utf-8"), "xbox_monitor.conf")
    assert code == 0
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert "complete HTTPS webhook URL" in capsys.readouterr().out
    assert "WEBHOOK_URL" not in wizard_paths["env"].read_text(encoding="utf-8")


# Verifies a blank destination is told apart from a malformed one and that skipping it leaves the channel off
def test_a_blank_webhook_url_is_worded_as_a_blank_one(monkeypatch, wizard_paths, capsys):
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    # The final "y" accepts continuing without a URL, which is what the blank wording offers
    answers = before_webhook_section() + ["y", "1", "y"] + after_webhook_section()
    code, scripted = run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for(""))
    values = monitor.parse_config_content(wizard_paths["config"].read_text(encoding="utf-8"), "xbox_monitor.conf")
    assert code == 0
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert any("Continue without the webhook URL?" in prompt for prompt in scripted.prompts)
    assert "complete HTTPS webhook URL" not in capsys.readouterr().out


# Verifies the custom preset asks about each webhook alert separately and writes exactly what was chosen
def test_the_custom_webhook_preset_writes_each_answer(monkeypatch, wizard_paths):
    answers = before_webhook_section() + ["y", "1", "3", "y", "n", "y", "n"] + after_webhook_section()
    run_wizard(monkeypatch, wizard_paths, answers, secrets=secrets_for(DISCORD_URL))
    values = monitor.parse_config_content(wizard_paths["config"].read_text(encoding="utf-8"), "xbox_monitor.conf")
    assert values["WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION"] is True
    assert values["WEBHOOK_GAME_CHANGE_NOTIFICATION"] is False
    assert values["WEBHOOK_STATUS_NOTIFICATION"] is True
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False


# Verifies every wizard prompt, visible or hidden, is coloured the same way
def test_wizard_prompts_are_colorized_visible_and_hidden_alike(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    prompts = []

    assert monitor._wizard_ask_secret("Client secret value", getpass_func=lambda prompt: prompts.append(prompt) or "secret") == "secret"
    assert monitor._wizard_input("Xbox gamertag to monitor: ", input_func=lambda prompt: prompts.append(prompt) or "") == ""

    hidden_prompt, visible_prompt = prompts
    assert hidden_prompt == monitor.colorize("info", "Client secret value: ")
    assert visible_prompt == monitor.colorize("info", "Xbox gamertag to monitor: ")
    assert hidden_prompt.endswith(monitor.ANSI_RESET)


# Verifies debug output is off while a hidden wizard answer is read and restored afterwards
def test_a_hidden_wizard_answer_is_read_with_debug_output_off(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    seen = []

    answer = monitor._wizard_ask_secret("Client secret value", getpass_func=lambda prompt: seen.append(monitor.DEBUG_MODE) or "secret")

    assert answer == "secret"
    assert seen == [False]
    assert monitor.DEBUG_MODE is True


# Replays scripted answers the way a terminal does, echoing each prompt so the transcript is what a user sees
class EchoingAnswers(ScriptedAnswers):
    def __call__(self, prompt=""):
        typed = super().__call__(prompt)
        print(f"{prompt}{typed}")
        return typed


# Verifies the destination block states the raw install method key in the column the siblings print
def test_the_setup_header_uses_the_shared_destination_column(capsys):
    monitor._wizard_print_setup_destinations("xbox_monitor.conf", ".env")

    assert capsys.readouterr().out == f"Detected install method: {monitor.detect_install_method()}\nConfiguration:          xbox_monitor.conf\nDotenv:                 .env\n\n"


# Verifies the credential guidance and both channel questions each open their own group
def test_every_question_group_opens_with_one_blank_line(monkeypatch, wizard_paths, capsys):
    hidden = ["client-id", "client-secret"]
    monkeypatch.setattr(monitor, "_wizard_request_tokens", TokenAuthorizer())

    monitor.run_setup_wizard(config_file=str(wizard_paths["config"]), env_file=str(wizard_paths["env"]), input_func=EchoingAnswers(BASIC_ANSWERS), getpass_func=lambda prompt="": hidden.pop(0) if hidden else "", interactive=True)

    transcript = capsys.readouterr().out
    assert f"\n\nRegister an application at {monitor.ENTRA_PORTAL_URL}\n" in transcript
    assert "* Register an application at" not in transcript
    assert "\n\nConfigure email notifications?" in transcript
    assert "\n\nSet up webhook alerts (Discord, ntfy etc.)?" in transcript


# Verifies the doctor setup runs reports the source a restart would report, not the fallback label
def test_saved_secrets_are_credited_to_the_dotenv_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("MS_APP_CLIENT_ID=a-saved-client-id\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "")
    state = types.SimpleNamespace(config_values={}, secret_updates={"MS_APP_CLIENT_ID": "a-saved-client-id"})

    monitor._wizard_apply_saved_values(state, env_path=env_path)

    assert monitor.SECRET_SOURCES["MS_APP_CLIENT_ID"] == "dotenv file"


# Verifies an exported secret keeps its own source after setup, since the export still wins at the next start
def test_an_exported_secret_is_not_credited_to_the_dotenv_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("MS_APP_CLIENT_ID=a-saved-client-id\n", encoding="utf-8")
    monkeypatch.setenv("MS_APP_CLIENT_ID", "a-saved-client-id")
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", frozenset({"MS_APP_CLIENT_ID"}))
    state = types.SimpleNamespace(config_values={}, secret_updates={})

    monitor._wizard_apply_saved_values(state, env_path=env_path)

    assert monitor.SECRET_SOURCES["MS_APP_CLIENT_ID"] == "environment"


# Verifies an Auto zone in the saved config is resolved before doctor reads it, as it is on a normal start
def test_the_saved_timezone_is_resolved_before_doctor_reads_it(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Europe/Warsaw")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE_STATE", "config")
    monkeypatch.setattr(monitor, "get_localzone", lambda: "Europe/Warsaw")
    state = types.SimpleNamespace(config_values={"LOCAL_TIMEZONE": "Auto"}, secret_updates={})

    advice = monitor._wizard_apply_saved_values(state, env_path=None)

    assert advice is None
    assert monitor.LOCAL_TIMEZONE == "Europe/Warsaw"
    assert monitor.TIMEZONE_CHECK_LABELS[monitor.LOCAL_TIMEZONE_STATE] == "Local timezone can be detected"


# Stands in for the Xbox authentication manager, so the real token exchange is never contacted
class FakeAuthManager:
    def __init__(self, session, client_id, client_secret, redirect_uri):
        self.oauth = types.SimpleNamespace(model_dump_json=lambda: '{"access_token": "test"}')

    def generate_authorization_url(self):
        return "https://login.example.test/authorize"

    async def request_oauth_token(self, code):
        return self.oauth

    async def refresh_tokens(self):
        return None


# Verifies the token exchange announces itself, since it blocks after the code is pasted with no output
def test_the_token_exchange_announces_the_check(monkeypatch, capsys):
    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(monitor, "create_signed_session", lambda: FakeSession())
    monkeypatch.setattr(monitor, "AuthenticationManager", FakeAuthManager)

    tokens = monitor.asyncio.run(monitor._wizard_request_tokens("client", "secret", input_func=lambda _prompt="": "auth-code"))

    assert tokens == '{"access_token": "test"}'
    lines = capsys.readouterr().out.splitlines()
    assert "  Checking the sign-in with Microsoft ..." in lines


# Verifies a blank authorization code returns before any check is announced, since nothing is exchanged
def test_a_blank_authorization_code_announces_nothing(monkeypatch, capsys):
    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(monitor, "create_signed_session", lambda: FakeSession())
    monkeypatch.setattr(monitor, "AuthenticationManager", FakeAuthManager)

    assert monitor.asyncio.run(monitor._wizard_request_tokens("client", "secret", input_func=lambda _prompt="": "")) == ""
    assert "Checking the sign-in with Microsoft" not in capsys.readouterr().out


# Verifies a saved webhook URL and ntfy token are offered by name instead of the generic replace question
def test_saved_webhook_secrets_are_offered_as_named_choices(tmp_path, capsys):
    env_path = tmp_path / ".env"
    env_path.write_text('WEBHOOK_URL="https://ntfy.sh/old-topic"\nNTFY_ACCESS_TOKEN="tk_saved_token"\n', encoding="utf-8")
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", env_path, dict(vars(monitor)))

    monitor._wizard_collect_webhook_section(state, input_func=ScriptedAnswers(["y", "2", "1", "3", "1"]), getpass_func=lambda prompt="": "")

    transcript = capsys.readouterr().out
    assert "Which webhook URL should be used?" in transcript
    assert "Which ntfy authentication should be used?" in transcript
    # Keeping the saved URL queues nothing, so the value already in the file is never rewritten
    assert "WEBHOOK_URL" not in state.secret_updates
    assert state.secret_updates["NTFY_ACCESS_TOKEN"] == ""


# Verifies the review can move the configuration file, since the summary shows a destination it could not change
def test_the_destination_section_moves_the_configuration_file(tmp_path):
    moved = tmp_path / "elsewhere"
    moved.mkdir()
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_destination_section(state, input_func=ScriptedAnswers([str(moved / "xbox_monitor.conf"), ""]))

    assert state.config_path == moved / "xbox_monitor.conf"
    assert state.env_path == tmp_path / ".env"
    assert state.config_values["DOTENV_FILE"] == str(tmp_path / ".env")


# Verifies moving the dotenv re-asks every section holding a secret, since a kept secret was never queued
def test_moving_the_dotenv_destination_re_asks_the_secret_sections(tmp_path, monkeypatch, capsys):
    asked = []
    for name in ("_wizard_collect_auth_section", "_wizard_collect_email_section", "_wizard_collect_webhook_section"):
        monkeypatch.setattr(monitor, name, lambda state, section=name, **kwargs: asked.append(section))
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_destination_section(state, input_func=ScriptedAnswers(["", str(tmp_path / ".env-moved")]))

    assert state.env_path == tmp_path / ".env-moved"
    assert state.config_values["DOTENV_FILE"] == str(tmp_path / ".env-moved")
    assert asked == ["_wizard_collect_auth_section", "_wizard_collect_email_section", "_wizard_collect_webhook_section"]
    assert "The dotenv destination changed" in capsys.readouterr().out


# Verifies one file cannot hold both, since saving the configuration would overwrite the secrets beside it
def test_the_dotenv_destination_cannot_be_the_configuration_file(tmp_path, capsys):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_destination_section(state, input_func=ScriptedAnswers(["", str(tmp_path / "xbox_monitor.conf"), ""]))

    assert state.env_path == tmp_path / ".env"
    assert "has to be a different file" in capsys.readouterr().out


# Verifies the port question rejects a number no TCP port can be, instead of saving it for the doctor to reject
def test_the_smtp_port_question_rejects_a_number_above_the_port_range(capsys):
    answers = iter(["70000", "2525"])

    chosen = monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=lambda _prompt: next(answers))

    assert chosen == 2525
    assert "  Enter a whole number from 1 through 65535." in capsys.readouterr().out


# Verifies declining the retry offer keeps the saved value rather than asking the same question forever
def test_declining_the_retry_offer_keeps_the_saved_number(capsys):
    answers = iter(["", "n"])

    assert monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=lambda _prompt: next(answers)) == 587


# Verifies a rerun that keeps the loaded secrets leaves every one of them out of the rebuilt configuration file
def test_a_rerun_keeps_loaded_secrets_out_of_the_configuration(monkeypatch, wizard_paths):
    loaded = {"MS_APP_CLIENT_ID": "loaded-client-id", "MS_APP_CLIENT_SECRET": "loaded-client-secret", "SMTP_PASSWORD": "mail-secret-value", "WEBHOOK_URL": "https://discord.com/api/webhooks/1/loaded-hook-value", "NTFY_ACCESS_TOKEN": "ntfy-secret-value"}
    for name, value in loaded.items():
        monkeypatch.setattr(monitor, name, value)
    wizard_paths["config"].write_text("# earlier config\n", encoding="utf-8")
    # rebuild, target, persist, both intervals, keep both credentials, no email, no webhook, output files, save, decline doctor and monitoring
    answers = ["y", "SomeTag", "", "5m", "90", "n", "n", "n", "n", "", "", "", "1", "n", "n"]

    code, _ = run_wizard(monkeypatch, wizard_paths, answers, secrets=())

    assert code == 0
    written = wizard_paths["config"].read_text(encoding="utf-8")
    for value in loaded.values():
        assert value not in written


# Verifies the configuration renderer keeps the template placeholder for every secret whatever the values hold
def test_the_configuration_renderer_never_writes_a_secret():
    values = {name: f"real-{name.lower()}" for name in monitor.SECRET_KEYS}
    values["XBOX_CHECK_INTERVAL"] = 4321

    rendered = monitor.generate_config_with_current_values(values)

    assert "XBOX_CHECK_INTERVAL = 4321" in rendered
    assert not any(value in rendered for value in values.values() if isinstance(value, str))


# Verifies a blank target answer whose retry is declined ends the section instead of asking the same question forever
def test_declining_the_target_retry_ends_the_section_without_a_target(tmp_path, capsys):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", {})
    scripted = ScriptedAnswers(["", "n"])

    monitor._wizard_collect_target_section(state, input_func=scripted)

    assert state.target == ""
    assert state.config_values["XBOX_GAMERTAG"] == ""
    assert not any(prompt.startswith("Persist this target") for prompt in scripted.prompts)
    assert "No target selected. Nothing can be monitored until one is set." in capsys.readouterr().out


# Verifies a rejected target answer offers another attempt and declining it keeps the target already given
def test_a_rejected_target_answer_offers_a_retry_and_keeps_the_previous_target(tmp_path):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", {})
    state.target = "SomeTag"
    scripted = ScriptedAnswers(["someone@example.com", "n", "y"])

    monitor._wizard_collect_target_section(state, input_func=scripted)

    assert state.target == "SomeTag"
    assert any(prompt.startswith("Try entering the Xbox gamertag to monitor again?") for prompt in scripted.prompts)
    assert any(prompt.startswith("Persist this target") for prompt in scripted.prompts)


# Verifies the email question defaults to the saved alerts, so a rerun over configured email proposes keeping it
def test_the_email_question_defaults_to_the_saved_alerts(tmp_path, monkeypatch):
    state = monitor.WizardSetupState(tmp_path / "xbox_monitor.conf", tmp_path / ".env", dict(vars(monitor)))
    seen = []
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=False, **kwargs: seen.append((question, default)) or False)

    state.config_values.update({key: False for key in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS})
    state.config_values.update({"ERROR_NOTIFICATION": True, "SMTP_HOST": "your_smtp_server_ssl"})
    monitor._wizard_collect_email_section(state)
    assert seen == [("Configure email notifications?", False)]

    # A declined answer clears the section, so each case seeds the settings it needs again
    state.config_values.update({"ERROR_NOTIFICATION": True, "SMTP_HOST": "smtp.example.test"})
    monitor._wizard_collect_email_section(state)
    assert seen[-1] == ("Configure email notifications?", True)

    state.config_values.update({"ERROR_NOTIFICATION": False, "SMTP_HOST": "your_smtp_server_ssl", "GAME_CHANGE_NOTIFICATION": True})
    monitor._wizard_collect_email_section(state)
    assert seen[-1] == ("Configure email notifications?", True)
