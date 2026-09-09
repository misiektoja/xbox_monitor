"""Tests for backups, atomic replacement and the guard on writing a generated config."""

import json
import os
import stat
from pathlib import Path

import pytest

import xbox_monitor as monitor


# Verifies a backup keeps the previous bytes, is private to the owner and is named for the file it copies
def test_a_backup_keeps_the_previous_content_privately(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(destination)

    assert backup_path is not None
    backup = Path(backup_path)
    assert backup.parent == tmp_path
    assert backup.name.startswith("xbox_monitor.conf.") and backup.name.endswith(".bak")
    assert backup.read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"
    if os.name == "posix":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600


# Verifies a second backup in the same second gets its own name instead of overwriting the first
def test_backups_never_overwrite_each_other(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(destination)
    destination.write_text("second\n", encoding="utf-8")

    second = monitor.create_timestamped_backup(destination)

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies nothing is backed up when there is nothing to lose
def test_a_missing_file_produces_no_backup(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None
    assert list(tmp_path.iterdir()) == []


# Verifies a backup that cannot get a unique name fails loudly instead of silently skipping
def test_an_exhausted_backup_name_space_raises(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("content\n", encoding="utf-8")
    monitor.create_timestamped_backup(destination, attempts=1)

    with pytest.raises(OSError):
        monitor.create_timestamped_backup(destination, attempts=1)


# Verifies a write leaves either the old file or the new one, never a temporary file beside them
def test_an_atomic_write_leaves_no_temporary_file(tmp_path):
    destination = tmp_path / "state.json"
    destination.write_text("old", encoding="utf-8")

    monitor.write_file_atomically(destination, "new")

    assert destination.read_text(encoding="utf-8") == "new"
    assert [entry.name for entry in tmp_path.iterdir()] == ["state.json"]


# Verifies a failed write is cleaned up rather than left behind as a half-written temporary file
def test_a_failed_atomic_write_cleans_up_after_itself(tmp_path, monkeypatch):
    destination = tmp_path / "state.json"
    destination.write_text("old", encoding="utf-8")

    def refuse_replace(_source, _target):
        raise OSError("disk full")

    monkeypatch.setattr(monitor.os, "replace", refuse_replace)

    with pytest.raises(OSError):
        monitor.write_file_atomically(destination, "new")

    assert destination.read_text(encoding="utf-8") == "old"
    assert [entry.name for entry in tmp_path.iterdir()] == ["state.json"]


# Verifies the parent directory is created rather than the write failing on a fresh install
def test_an_atomic_write_creates_its_directory(tmp_path):
    destination = tmp_path / "nested" / "deeper" / "state.json"

    monitor.write_file_atomically(destination, "content")

    assert destination.read_text(encoding="utf-8") == "content"


# Verifies a file written with a mode is private to the owner even when it replaces a world-readable one
@pytest.mark.skipif(os.name != "posix", reason="file modes are a POSIX property")
def test_a_private_write_replaces_a_readable_file_with_a_private_one(tmp_path):
    destination = tmp_path / "xbox_tokens.json"
    destination.write_text("{}", encoding="utf-8")
    destination.chmod(0o644)

    monitor.write_file_atomically(destination, '{"refresh_token": "x"}', mode=0o600)

    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert destination.read_text(encoding="utf-8") == '{"refresh_token": "x"}'


# Verifies the last status file is written atomically and reads back as the pair the monitor saved
def test_the_saved_status_is_written_atomically(tmp_path):
    status_file = tmp_path / "xbox_someone_last_status.json"

    monitor.save_last_status(status_file, 1767222000, "online")

    assert json.loads(status_file.read_text(encoding="utf-8")) == [1767222000, "online"]
    assert [entry.name for entry in tmp_path.iterdir()] == ["xbox_someone_last_status.json"]


# Verifies writing a config where nothing exists yet asks nobody anything
def test_writing_a_new_config_needs_no_confirmation(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"

    def refuse_to_ask(prompt):
        raise AssertionError(f"should not have prompted: {prompt}")

    backup_path, written = monitor.write_generated_config(destination, "XBOX_CHECK_INTERVAL = 180\n", input_func=refuse_to_ask, interactive=True)

    assert (backup_path, written) == (None, True)
    assert destination.read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 180\n"


# Verifies replacing an existing config outside a terminal refuses and leaves the file alone
def test_replacing_a_config_outside_a_terminal_refuses(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")

    with pytest.raises(FileExistsError) as raised:
        monitor.write_generated_config(destination, "template\n", interactive=False)

    assert "already exists" in str(raised.value)
    assert destination.read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"


# Verifies a declined prompt leaves the existing config exactly as it was
def test_a_declined_replacement_changes_nothing(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=lambda prompt: "n")

    assert (backup_path, written) == (None, False)
    assert destination.read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"
    assert [entry.name for entry in tmp_path.iterdir()] == ["xbox_monitor.conf"]


@pytest.mark.parametrize("answer", ["y", "yes", "YES"])
# Verifies an accepted prompt replaces the config and keeps the previous one as a backup
def test_an_accepted_replacement_backs_up_first(tmp_path, answer):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=lambda prompt: answer)

    assert written is True
    assert backup_path is not None
    assert destination.read_text(encoding="utf-8") == "template\n"
    assert Path(backup_path).read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"


# Verifies --force replaces an existing config without asking, still keeping a backup
def test_force_replaces_without_asking(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")

    def refuse_to_ask(prompt):
        raise AssertionError(f"should not have prompted: {prompt}")

    backup_path, written = monitor.write_generated_config(destination, "template\n", force=True, interactive=False, input_func=refuse_to_ask)

    assert written is True
    assert backup_path is not None
    assert destination.read_text(encoding="utf-8") == "template\n"
    assert Path(backup_path).read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"


# Verifies an interrupted prompt counts as a refusal rather than a traceback
def test_an_interrupted_prompt_declines(tmp_path):
    destination = tmp_path / "xbox_monitor.conf"
    destination.write_text("XBOX_CHECK_INTERVAL = 999\n", encoding="utf-8")

    def interrupt(prompt):
        raise KeyboardInterrupt

    backup_path, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=interrupt)

    assert (backup_path, written) == (None, False)
    assert destination.read_text(encoding="utf-8") == "XBOX_CHECK_INTERVAL = 999\n"


# Verifies the generated template is written where it was asked for and still loads through the parser
def test_the_generated_template_is_written_to_the_named_path(tmp_path):
    destination = tmp_path / "nested" / "xbox_monitor.conf"

    monitor.write_generated_config(destination, monitor.CONFIG_BLOCK.strip("\n") + "\n", interactive=True, input_func=lambda prompt: "y")

    assert destination.is_file()
    assert monitor.parse_config_content(destination.read_text(encoding="utf-8"), str(destination))


# Verifies the token cache written after a refresh is private to the owner and replaces a readable one
@pytest.mark.skipif(os.name != "posix", reason="file modes are a POSIX property")
def test_the_token_cache_is_written_privately(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    token_file = tmp_path / "xbox_tokens.json"
    token_file.write_text('{"stale": true}', encoding="utf-8")
    token_file.chmod(0o644)
    cached = SimpleNamespace(model_dump_json=lambda: '{"refresh_token": "fresh"}')

    class FakeTokenResponse:
        @staticmethod
        def model_validate_json(_text):
            return cached

    class FakeAuthManager:
        oauth = None

        async def refresh_tokens(self):
            return None

    monkeypatch.setattr(monitor, "MS_AUTH_TOKENS_FILE", str(token_file))
    monkeypatch.setattr(monitor, "OAuth2TokenResponse", FakeTokenResponse)

    asyncio.run(monitor.authenticate_and_refresh_tokens(FakeAuthManager()))

    assert token_file.read_text(encoding="utf-8") == '{"refresh_token": "fresh"}'
    assert stat.S_IMODE(token_file.stat().st_mode) == 0o600
    assert [entry.name for entry in tmp_path.iterdir()] == ["xbox_tokens.json"]
