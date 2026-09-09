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
    assert "was cancelled" in raised.value.advice.detail
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
