"""Tests for which presence titles count as a game.

Xbox reports its own dashboard surfaces the same way it reports a game, and it embeds zero-width characters
in some names, so the tests use the exact strings the live API returns rather than tidy literals.
"""

import asyncio
import httpx
from types import SimpleNamespace

import pytest

import xbox_monitor as monitor

# The name the presence API returns for the Store, joiner included
STORE_TITLE = "Microsoft ‍Store"


@pytest.fixture(autouse=True)
# Startup resolves the shipped Auto placeholder, and every timestamp here goes through the same conversion
def fixed_timezone(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")


# Builds a presence object shaped like the one the client returns for a user on a console
def presence_with_titles(*titles, state="Online"):
    entries = [SimpleNamespace(name=name, placement=placement) for name, placement in titles]
    return SimpleNamespace(state=state, last_seen=None, devices=[SimpleNamespace(type="Scarlett", titles=entries)])


# Builds a title history response with one item, whose timestamp is what the appear-offline fallback needs
def history_client(title_name, played="2026-03-18T23:10:15.0000000Z"):
    history = SimpleNamespace(last_time_played=played)
    titles = [SimpleNamespace(name=title_name, title_history=history)]

    class Titlehub:
        # Matches the awaited call the fallback makes
        async def get_title_history(self, xuid, max_items=3):
            return SimpleNamespace(titles=titles)

    return SimpleNamespace(titlehub=Titlehub())


# The Store is a place to buy a game, not a game, and its joiner defeats a plain literal comparison
def test_the_store_is_not_reported_as_a_game():
    _status, _title, game_name, _platform, _ts = monitor.xbox_process_presence_class(presence_with_titles((STORE_TITLE, "Full")))
    assert game_name == ""


@pytest.mark.parametrize("system_title", sorted(monitor.XBOX_SYSTEM_TITLES))
# Every listed surface has to be filtered whatever case the API sends it in
def test_a_system_surface_is_not_reported_as_a_game(system_title):
    _status, _title, game_name, _platform, _ts = monitor.xbox_process_presence_class(presence_with_titles((system_title.title(), "Full")))
    assert game_name == ""


# Filtering must not swallow the real title sitting behind a system surface in the same list
def test_a_game_behind_a_system_surface_is_still_found():
    _status, _title, game_name, _platform, _ts = monitor.xbox_process_presence_class(presence_with_titles(("Home", "Full"), ("Halo Infinite", "Full")))
    assert game_name == "Halo Infinite"


# A zero-width character inside a real title would reach the screen, the log and the mail subject unseen
def test_a_zero_width_character_is_stripped_from_a_real_title():
    _status, _title, game_name, _platform, _ts = monitor.xbox_process_presence_class(presence_with_titles(("Forza​ Horizon 5", "Full")))
    assert game_name == "Forza Horizon 5"


# A background title is someone else's music or a suspended app, so it stays excluded
def test_a_background_title_is_still_ignored():
    _status, _title, game_name, _platform, _ts = monitor.xbox_process_presence_class(presence_with_titles(("Halo Infinite", "Background")))
    assert game_name == ""


# The last-seen row names the surface the user left, where the Store is as uninteresting as Home
def test_the_last_seen_row_drops_a_system_surface():
    presence = SimpleNamespace(state="Offline", last_seen=SimpleNamespace(title_name=STORE_TITLE, device_type="Scarlett", timestamp="2026-03-18T23:20:17.0000000Z"))
    _status, title_name, _game, _platform, lastonline_ts = monitor.xbox_process_presence_class(presence)
    assert title_name == ""
    assert lastonline_ts > 0


# Title history proves the user was active even when the name is a surface worth hiding, so only the name goes
def test_title_history_keeps_the_timestamp_but_drops_a_system_name():
    ts, game, _ = asyncio.run(monitor.xbox_get_latest_title_played_ts(history_client(STORE_TITLE), "2533274800000000"))
    assert ts > 0
    assert game == ""


# A blocked title history host used to look like a successful check, which cleared the outage the presence
# host was still in and repeated its notice on every poll, so the fallback now reports whether it answered
def test_a_blocked_title_history_is_reported_once_and_marked_as_failed(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "print_cur_ts", lambda *args, **kwargs: None)

    class Blocked:
        async def get_title_history(self, xuid, max_items=3):
            raise httpx.ConnectTimeout("")

    client = SimpleNamespace(titlehub=Blocked())
    outage = monitor.OutageReporter()
    results = [asyncio.run(monitor.xbox_get_latest_title_played_ts(client, "2533274800000000", outage)) for _ in range(4)]

    assert all(result == (0, "", False) for result in results)
    assert capsys.readouterr().out.count("The title history fallback is unavailable") == 1


# The same fallback still names a real game, which is what makes its message useful
def test_title_history_reports_a_real_game():
    ts, game, _ = asyncio.run(monitor.xbox_get_latest_title_played_ts(history_client("Sea of‍ Thieves"), "2533274800000000"))
    assert ts > 0
    assert game == "Sea of Thieves"


@pytest.mark.parametrize("raw, expected", [
    ("Microsoft ‍Store", "Microsoft Store"),
    ("  Halo  Infinite  ", "Halo Infinite"),
    ("﻿Forza", "Forza"),
    ("", ""),
    (None, ""),
])
# Normalization is the comparison key and the displayed name, so both padding and zero-width have to go
def test_a_title_name_is_normalized(raw, expected):
    assert monitor.xbox_normalize_title_name(raw) == expected
