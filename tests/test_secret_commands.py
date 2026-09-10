"""Tests for the one-shot commands that write a secret, covering what they write and what they refuse to write."""

import pytest

import xbox_monitor as monitor


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


# Points the token cache at the temporary directory and returns the dotenv path the commands write to
@pytest.fixture
def secret_paths(tmp_path, monkeypatch):
    tokens = tmp_path / "xbox_tokens.json"
    monkeypatch.setattr(monitor, "MS_AUTH_TOKENS_FILE", str(tokens))
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_USER", "someone@example.com")
    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    return {"env": env, "tokens": tokens}


# Returns a hidden-prompt stub that hands back the given values in order
def hidden_answers(*values):
    remaining = list(values)
    return lambda prompt="": remaining.pop(0) if remaining else ""


# Verifies the credential command writes both secrets and the token cache after a real sign-in
def test_the_credential_command_writes_both_secrets_and_the_tokens(secret_paths, capsys):
    authorizer = TokenAuthorizer()
    monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("client-id", "client-secret"), authorizer=authorizer)
    written = secret_paths["env"].read_text(encoding="utf-8")
    out = capsys.readouterr().out
    assert 'MS_APP_CLIENT_ID="client-id"' in written
    assert 'MS_APP_CLIENT_SECRET="client-secret"' in written
    assert secret_paths["tokens"].read_text(encoding="utf-8") == '{"access_token": "test"}'
    assert secret_paths["tokens"].stat().st_mode & 0o077 == 0
    assert authorizer.calls == [("client-id", "client-secret")]
    assert "Microsoft accepted the sign-in" in out
    assert "--doctor" in out


# Verifies a refused sign-in leaves the dotenv file and the token cache untouched
def test_a_refused_sign_in_writes_nothing(secret_paths):
    authorizer = TokenAuthorizer(error=RuntimeError("invalid_client"))
    with pytest.raises(monitor.RecoveryError):
        monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("client-id", "client-secret"), authorizer=authorizer)
    assert secret_paths["env"].read_text(encoding="utf-8") == ""
    assert not secret_paths["tokens"].exists()


# Verifies one credential without the other is refused, since neither is usable alone
def test_one_credential_without_the_other_is_refused(secret_paths):
    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("client-id", ""), authorizer=TokenAuthorizer())
    assert "Both the client ID and the client secret" in raised.value.advice.detail
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies secrets already in the dotenv file are kept when the replacement is not confirmed
def test_existing_secrets_are_kept_unless_the_replacement_is_confirmed(secret_paths):
    secret_paths["env"].write_text('MS_APP_CLIENT_ID="old-id"\n', encoding="utf-8")
    with pytest.raises(monitor.RecoveryError):
        monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=True, input_func=lambda prompt="": "n", getpass_func=hidden_answers("client-id", "client-secret"), authorizer=TokenAuthorizer())
    assert secret_paths["env"].read_text(encoding="utf-8") == 'MS_APP_CLIENT_ID="old-id"\n'


# Verifies a confirmed replacement rewrites the assignment in place rather than appending a second one
def test_a_confirmed_replacement_rewrites_the_assignment_in_place(secret_paths):
    secret_paths["env"].write_text('# comment\nexport MS_APP_CLIENT_ID="old-id"\nOTHER=keep\n', encoding="utf-8")
    monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=True, input_func=lambda prompt="": "y", getpass_func=hidden_answers("new-id", "new-secret"), authorizer=TokenAuthorizer())
    written = secret_paths["env"].read_text(encoding="utf-8")
    assert written.count("MS_APP_CLIENT_ID") == 1
    assert 'export MS_APP_CLIENT_ID="new-id"' in written
    assert "# comment" in written and "OTHER=keep" in written


# Verifies a run without a terminal refuses rather than reading a secret from a pipe
def test_without_a_terminal_the_credential_command_refuses(secret_paths):
    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=False)
    assert "interactive terminal" in raised.value.advice.detail
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies the disabled dotenv setting is refused, since these commands exist to write one
def test_a_disabled_dotenv_is_refused(secret_paths):
    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_ms_app_credentials(env_file="none", interactive=True)
    assert "--set-ms-app-credentials" in raised.value.advice.detail


# Verifies the SMTP password is written only after the mail server has accepted it
def test_the_smtp_password_is_written_only_after_the_server_accepts_it(secret_paths, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    monitor.run_set_smtp_password(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("mail-password"))
    out = capsys.readouterr().out
    assert 'SMTP_PASSWORD="mail-password"' in secret_paths["env"].read_text(encoding="utf-8")
    assert "accepted the password for someone@example.com" in out
    assert "--send-test-email" in out


# Verifies a password the mail server rejects is not written
def test_a_rejected_smtp_password_is_not_written(secret_paths, monkeypatch):
    advice = monitor.make_recovery_advice("smtp.authentication", "The mail server rejected the sign-in", "Check the password", False)

    def refuse(password, timeout=15):
        raise monitor.RecoveryError(advice)

    monkeypatch.setattr(monitor, "smtp_sign_in", refuse)
    with pytest.raises(monitor.RecoveryError):
        monitor.run_set_smtp_password(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("wrong-password"))
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies an interrupted entry leaves the dotenv file untouched and says so
def test_an_interrupted_entry_writes_nothing(secret_paths):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(secret_paths["env"]), interactive=True, getpass_func=interrupt)
    assert "was cancelled" in raised.value.advice.summary
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies debug output is off while a secret is being typed, since it is the one place a value is printed verbatim
def test_debug_mode_is_off_while_a_secret_is_being_typed(secret_paths, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")
    seen = {}

    def hidden(prompt=""):
        seen["debug_mode"] = monitor.DEBUG_MODE
        monitor.debug_print("Secret prompt", value="mail-password")
        return "mail-password"

    monitor.run_set_smtp_password(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden)
    out = capsys.readouterr().out
    assert seen["debug_mode"] is False
    assert "mail-password" not in out
    assert monitor.DEBUG_MODE is True


# Verifies the dotenv writer refuses a key that is not one of this tool's secrets
def test_the_dotenv_writer_refuses_an_unknown_key(secret_paths):
    with pytest.raises(ValueError):
        monitor.update_dotenv_values(secret_paths["env"], {"PATH": "/tmp"})
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies a cleared secret is removed from the dotenv file rather than left behind as an empty assignment
def test_a_cleared_secret_is_removed_from_the_file(secret_paths):
    secret_paths["env"].write_text('SMTP_PASSWORD="old"\nOTHER=keep\n', encoding="utf-8")
    monitor.update_dotenv_values(secret_paths["env"], {"SMTP_PASSWORD": ""})
    written = secret_paths["env"].read_text(encoding="utf-8")
    assert "SMTP_PASSWORD" not in written
    assert "OTHER=keep" in written


# Verifies a value containing quotes and backslashes survives one write and read cycle unchanged
def test_a_quoted_value_survives_the_round_trip(secret_paths, monkeypatch):
    tricky = 'a"b\\c'
    monitor.update_dotenv_values(secret_paths["env"], {"SMTP_PASSWORD": tricky})
    from dotenv import dotenv_values

    assert dotenv_values(str(secret_paths["env"]))["SMTP_PASSWORD"] == tricky


# Verifies the dotenv file the writer creates is readable only by its owner
def test_a_written_dotenv_file_is_private(secret_paths):
    monitor.update_dotenv_values(secret_paths["env"], {"SMTP_PASSWORD": "value"})
    assert secret_paths["env"].stat().st_mode & 0o077 == 0


DISCORD_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


# Verifies the webhook command writes the destination and names the command that tests it
def test_the_webhook_command_writes_the_destination(secret_paths, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monitor.run_set_webhook_url(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers(DISCORD_URL))
    out = capsys.readouterr().out
    assert f'WEBHOOK_URL="{DISCORD_URL}"' in secret_paths["env"].read_text(encoding="utf-8")
    assert "valid Discord destination" in out
    assert "--send-test-webhook" in out
    assert DISCORD_URL not in out


# Verifies an ntfy topic name is expanded before it is written, so the saved value is a complete URL
def test_a_typed_ntfy_topic_is_written_as_a_url(secret_paths, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monitor.run_set_webhook_url(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("private-topic"))
    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in secret_paths["env"].read_text(encoding="utf-8")


# Verifies a destination that cannot be used is refused without echoing what was typed
def test_an_unusable_destination_is_refused_without_echoing_it(secret_paths, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_webhook_url(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("http://discord.com/api/webhooks/1/token"))
    assert "complete HTTPS link" in raised.value.advice.summary
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies a destination belonging to the other service is refused rather than saved against the wrong provider
def test_a_destination_for_the_other_service_is_refused(secret_paths, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_webhook_url(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers(DISCORD_URL))
    assert "WEBHOOK_PROVIDER is set to ntfy" in raised.value.advice.summary
    assert secret_paths["env"].read_text(encoding="utf-8") == ""


# Verifies an interrupted entry reports the cancel itself, with the command that resumes it
def test_an_interrupted_secret_entry_reports_the_cancel(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    def interrupt(prompt=""):
        raise KeyboardInterrupt

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(destination), interactive=True, getpass_func=interrupt)

    advice = raised.value.advice
    assert advice.summary == "SMTP password setup was cancelled and the dotenv file was not changed"
    assert "Run --set-smtp-password again when you have the value ready" in advice.fix
    assert monitor.SMTP_GUIDE_URL in advice.fix
    assert not destination.exists()


# Verifies a declined replacement reports the kept value rather than a cancelled entry
def test_a_declined_secret_replacement_reports_the_kept_value(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    destination.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(destination), interactive=True, input_func=lambda prompt="": "n", getpass_func=lambda prompt="": pytest.fail("hidden prompt used"))

    advice = raised.value.advice
    assert advice.summary == "The saved SMTP password was left as it is and the dotenv file was not changed"
    assert "answer y to replace the saved value" in advice.fix
    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="original"\n'


PROGRESS_COMMANDS = (("run_set_webhook_url", "webhook URL", "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"), ("run_set_smtp_password", "SMTP password", "mail-password"))


# Verifies each secret command announces the check the way the siblings do, naming the dotenv file rather than its path
@pytest.mark.parametrize("command_name, subject, secret", PROGRESS_COMMANDS)
def test_the_progress_line_names_the_dotenv_file_not_its_path(command_name, subject, secret, secret_paths, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: "someone@example.com")

    getattr(monitor, command_name)(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers(secret))

    line = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("* Checking the entered"))
    assert line == f"* Checking the entered {subject} before changing the dotenv file ..."


# Verifies the credential command names the dotenv file the same way, since it collects two values at once
def test_the_credential_progress_line_names_the_dotenv_file_not_its_path(secret_paths, capsys):
    monitor.run_set_ms_app_credentials(env_file=str(secret_paths["env"]), interactive=True, getpass_func=hidden_answers("client-id", "client-secret"), authorizer=TokenAuthorizer())

    line = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("* Checking the entered"))
    assert line == "* Checking the entered Microsoft application credentials before changing the dotenv file ..."


# Verifies the printed next steps carry a target this run was given and no placeholder when there is none
def test_the_next_steps_carry_the_target_the_config_does_not_supply(tmp_path, capsys):
    env_file = tmp_path / ".env"
    empty_config = tmp_path / "empty.conf"
    empty_config.write_text('XBOX_GAMERTAG = ""\n', encoding="utf-8")
    saved_config = tmp_path / "saved.conf"
    saved_config.write_text('XBOX_GAMERTAG = "someone"\n', encoding="utf-8")

    monitor.print_secret_next_steps(env_file, config_path=empty_config)
    without_target = capsys.readouterr().out
    monitor.print_secret_next_steps(env_file, config_path=empty_config, xbox_gamertag="someone")
    with_target = capsys.readouterr().out
    monitor.print_secret_next_steps(env_file, config_path=saved_config, xbox_gamertag="someone")
    already_saved = capsys.readouterr().out

    doctor_part, monitor_part = without_target.split("Once the checks pass", 1)
    assert "<xbox_gamertag>" not in doctor_part
    assert "<xbox_gamertag>" in monitor_part
    assert with_target.count("someone") == 2
    assert "someone" not in already_saved
    assert "<xbox_gamertag>" not in already_saved
