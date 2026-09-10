"""Tests for the colour engine: what gets a colour, what must never get one and what the log file keeps."""

import ast
import io
import os
import re
import sys

import pytest

import xbox_monitor as monitor

SOURCE = monitor.Path(monitor.__file__).read_text(encoding="utf-8")
SGR = re.compile(r"\x1b\[[0-9;]*m")


# Turns colour on with the shipped defaults, the state every render test needs
@pytest.fixture
def colored(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(style)})
    return monitor


# Reports whether one piece of text was wrapped in the colour the named theme key describes
def styled_as(line, text, key):
    return f"{monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME[key])}{text}{monitor.ANSI_RESET}" in line


# Reports whether one piece of text carries no colour of its own, ignoring any style wrapped around the whole line
def uncolored(line, text):
    return text in line and not any(styled_as(line, text, key) for key in monitor.DEFAULT_COLOR_THEME)


# Collects every string constant the source mentions outside the theme definition itself
def mentioned_strings():
    tree = ast.parse(SOURCE)
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(target, "id", "") == "DEFAULT_COLOR_THEME" for target in node.targets):
            skip |= {id(inner) for inner in ast.walk(node.value)}
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip}


# Verifies the identity colours are the ones every sibling uses, so a reader learns them once
def test_the_identity_colours_match_the_shared_palette():
    assert monitor.DEFAULT_COLOR_THEME["username"] == "bright_cyan underline"
    assert monitor.DEFAULT_COLOR_THEME["id"] == "bright_magenta"
    assert monitor.DEFAULT_COLOR_THEME["link"] == "blue underline"
    assert monitor.DEFAULT_COLOR_THEME["timestamp_value"] == "cyan"


# Verifies a warning marks its opening word instead of painting the line, so the values inside stay visible
def test_a_warning_marks_its_opening_word_and_leaves_the_rest(colored):
    line = monitor._colorize_line("* Warning: the account changed status during the check")

    assert styled_as(line, "Warning:", "warning")
    assert styled_as(line, "changed status", "status_change")
    assert not line.startswith(monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["warning"]))


# Verifies a reported signal marks its own name rather than painting the line it arrives on
def test_a_signal_marks_its_own_name(colored):
    line = monitor._colorize_line("* Signal SIGUSR1 received")

    assert line == f"* Signal {monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME['signal'])}SIGUSR1{monitor.ANSI_RESET} received"


# Verifies a value colour never equals a whole-line style that can enclose it, which would hide the value
def test_block_styles_never_hide_a_name(colored):
    resolved = {name: monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME[name]) for name in monitor.BLOCK_STYLE_PARTS + monitor.NAME_STYLE_PARTS}
    for block in monitor.BLOCK_STYLE_PARTS:
        for name in monitor.NAME_STYLE_PARTS:
            assert resolved[name] != resolved[block], f"{name} is invisible inside a {block} line"


# Verifies an error still paints its whole line, so the fix that freed warnings did not free every block
def test_an_error_line_is_still_painted_end_to_end(colored):
    line = monitor._colorize_line("* Error: the account changed status during the check")

    assert line.startswith(monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["error"]))


# Verifies the liveness banner timestamp carries the timestamp colour instead of the generic date colour
def test_liveness_check_timestamp_uses_timestamp_style(colored):
    line = monitor._colorize_line("Liveness check, timestamp:\tWed 26 Aug 2026, 20:23:03")
    assert styled_as(line, "Wed 26 Aug 2026, 20:23:03", "timestamp_value")


# Verifies a gamertag is a handle everywhere it appears, so the Target row agrees with the rows under it
@pytest.mark.parametrize("line, value", [
    ("* Target:                       misiektoja", "misiektoja"),
    ("Gamertag:\t\t\tmisiektoja", "misiektoja"),
    ("Monitoring user with Xbox gamer tag misiektoja", "misiektoja"),
    ("Xbox user misiektoja changed status from ONLINE to OFFLINE", "misiektoja"),
    ("* Fetching details for Xbox user 'misiektoja'...", "misiektoja"),
])
def test_a_gamertag_is_always_a_handle(colored, line, value):
    assert styled_as(colored._colorize_line(line), value, "username")


# Verifies the XUID is an identifier rather than a handle, since it is a machine number
def test_the_xuid_is_an_identifier(colored):
    assert styled_as(colored._colorize_line("XUID:\t\t\t\t2533274812345678"), "2533274812345678", "id")


# Verifies each presence state gets the colour its own theme key describes
@pytest.mark.parametrize("status, key", [("ONLINE", "status_active"), ("AWAY", "status_away"), ("OFFLINE", "status_offline")])
def test_each_presence_state_uses_its_own_theme_key(colored, status, key):
    assert styled_as(colored._colorize_line(f"Status:\t\t\t\t{status}"), status, key)


# Verifies the three presence states really are three different colours on screen
def test_the_three_presence_states_are_three_colours():
    assert len({monitor.DEFAULT_COLOR_THEME[key] for key in ("status_active", "status_away", "status_offline")}) == 3


# Verifies a game title is coloured as content wherever it appears
@pytest.mark.parametrize("line, value", [
    ("Current game:\t\t\tHalo Infinite", "Halo Infinite"),
    ("Xbox user x started playing 'Sea of Thieves'", "Sea of Thieves"),
    ("Title name:\t\t\tForza Horizon 5", "Forza Horizon 5"),
])
def test_a_game_title_is_coloured_as_content(colored, line, value):
    assert styled_as(colored._colorize_line(line), value, "game")


# Verifies the activity verbs are coloured like the state they move to
@pytest.mark.parametrize("phrase, key", [("started playing", "status_active"), ("stopped playing", "status_inactive"), ("changed status", "status_change"), ("changed game", "status_change")])
def test_an_activity_verb_is_coloured_like_the_state_it_reports(colored, phrase, key):
    assert styled_as(colored._colorize_line(f"Xbox user x {phrase} something"), phrase, key)


# Verifies a placeholder inside a printed command stays plain, since it is not a name the user recognises
def test_a_command_placeholder_is_not_read_as_a_name(colored):
    line = colored._colorize_line("To fix: run: xbox_monitor '<xbox_gamertag>' -u '<client_id>'")
    assert uncolored(line, "<xbox_gamertag>")
    assert uncolored(line, "<client_id>")


# Verifies a quoted file path stays plain, since a log destination is not content
def test_a_quoted_file_path_is_not_read_as_a_name(colored):
    assert uncolored(colored._colorize_line("* Warning: dotenv file '/tmp/some.env' does not exist"), "/tmp/some.env")


# Verifies each doctor marker carries the colour its status means
@pytest.mark.parametrize("marker, key", [("[PASS]", "boolean_true"), ("[WARN]", "warning"), ("[FAIL]", "error"), ("[SKIP]", "info")])
def test_each_doctor_marker_is_coloured_by_status(colored, marker, key):
    assert styled_as(colored._colorize_line(f"{marker} Something was checked"), marker, key)


# Verifies the rest of a doctor row stays plain, so a long label is still readable
def test_a_doctor_row_keeps_its_label_plain(colored):
    assert colored._colorize_line("[PASS] The monitored profile was not checked").endswith(f"{monitor.ANSI_RESET} The monitored profile was not checked")


# Verifies links are coloured wherever they appear
def test_a_link_is_coloured(colored):
    assert styled_as(colored._colorize_line("Guide: https://example.com/page"), "https://example.com/page", "link")


# Verifies no colour is emitted at all while the feature is off
@pytest.mark.parametrize("line", [
    "* Target:                       misiektoja",
    "[FAIL] A required credential is missing",
    "Guide: https://example.com/page",
    "Xbox user x started playing 'Halo'",
])
def test_nothing_is_coloured_while_the_feature_is_off(monkeypatch, line):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    assert monitor._colorize_line(line) == line


# Verifies one value is never wrapped in a second span, which would end the first one early
def test_no_value_is_coloured_twice(colored):
    line = colored._colorize_line("Xbox user misiektoja changed game from 'Halo' to 'Forza' after 1 hour")
    depth = 0
    for match in SGR.finditer(line):
        depth += -1 if match.group(0) == monitor.ANSI_RESET else 1
        assert depth in (0, 1), f"nested colour span in {line!r}"
    assert depth == 0


# Verifies a block style is restored after every highlight inside its line
def test_a_block_style_returns_after_every_inner_span(colored):
    line = colored._colorize_line("* Error: token refresh failed for 'Halo Infinite'")
    assert line.startswith(monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["error"]))
    assert line.endswith(monitor.ANSI_RESET)


# Verifies a debug line keeps its own colours instead of being painted as the failure it reports
def test_a_debug_line_is_not_painted_as_an_error(colored):
    line = colored._colorize_line("[DEBUG 14:22:01] Token refresh: outcome=failed, error=HTTPStatusError")
    assert not line.startswith(monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["error"]))


# Verifies a diagnostic field that merely names a setting does not paint its line as a failure
def test_a_key_value_field_is_not_read_as_a_failure(colored):
    line = colored._colorize_line("* SMTP sign-in check: host=smtp.example.com, timeout=15")
    assert not line.startswith(monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["error"]))


# Verifies the tool has no theme key that nothing reads, since such a key is a setting with no effect
def test_the_theme_has_no_unused_key():
    assert sorted(set(monitor.DEFAULT_COLOR_THEME) - mentioned_strings()) == []


# Collects the theme keys the source names literally when it colours something
def looked_up_theme_keys():
    positions = {"colorize": 0, "_apply_style_nested": 1}
    keys = set()
    for node in ast.walk(ast.parse(SOURCE)):
        if not isinstance(node, ast.Call):
            continue
        index = positions.get(getattr(node.func, "id", ""), -1)
        if index < 0 or len(node.args) <= index:
            continue
        argument = node.args[index]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            keys.add(argument.value)
    return keys


# Verifies every key the source colours with exists in the theme, so a colorize call cannot silently do nothing
def test_every_looked_up_key_exists_in_the_theme():
    assert sorted(looked_up_theme_keys() - set(monitor.DEFAULT_COLOR_THEME)) == []


# Verifies the commented template theme still matches the built-in one, so the two cannot drift apart
def test_the_commented_template_theme_matches_the_built_in_theme():
    block = monitor.CONFIG_BLOCK.split("# COLOR_THEME = {", 1)[1].split("\n# }", 1)[0]
    uncommented = "{" + "\n".join(line.lstrip().removeprefix("#").strip() for line in block.splitlines()) + "}"
    assert ast.literal_eval(uncommented) == monitor.DEFAULT_COLOR_THEME


# Verifies a setting the template ships commented out is still accepted by the config loader
def test_a_commented_out_setting_is_still_accepted(tmp_path):
    config = tmp_path / "xbox_monitor.conf"
    config.write_text('COLOR_THEME = {"username": "red"}\n', encoding="utf-8")
    assert monitor.parse_config_content(config.read_text(encoding="utf-8"), str(config))["COLOR_THEME"] == {"username": "red"}


# Verifies a config theme is merged over the defaults rather than replacing them
def test_a_config_theme_overrides_only_what_it_names(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"username": "red"})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(io.StringIO())
    assert monitor._COLOR_STYLES["username"] == monitor._build_ansi_sequence("red")
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("bright_magenta")


# Verifies colour is off whenever the stream is not a terminal, so escapes never reach a redirected file
def test_colour_stays_off_when_the_output_is_not_a_terminal(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monitor.init_color_output(io.StringIO())
    assert monitor.COLOR_ENABLED is False
    assert monitor._COLOR_STYLES == {}


# Verifies the NO_COLOR convention is honoured even on a real terminal
def test_no_color_in_the_environment_switches_colour_off(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    stream = io.StringIO()
    monkeypatch.setattr(stream, "isatty", lambda: True, raising=False)
    assert monitor._stream_supports_color(stream) is False


# Verifies a title's own apostrophe does not end the name early, which left most of the title uncoloured
@pytest.mark.parametrize("title", ["Tom Clancy's Rainbow Six Siege", "Assassin's Creed Valhalla"])
def test_a_title_containing_an_apostrophe_is_coloured_whole(colored, title):
    assert styled_as(colored._colorize_line(f"Xbox user x started playing '{title}' after 1 hour"), title, "game")


# Verifies two quoted titles on one line stay two names, since the closing quote rule could have joined them
def test_two_quoted_titles_on_one_line_stay_separate(colored):
    line = colored._colorize_line("Xbox user x changed game from 'Halo' to 'Forza Horizon 5' after 2 hours")
    assert styled_as(line, "Halo", "game") and styled_as(line, "Forza Horizon 5", "game")


# Verifies a quoted command-line option reads as an instruction rather than a name
def test_a_quoted_option_is_not_read_as_a_name(colored):
    assert uncolored(colored._colorize_line("Replace '--env-file none' with a writable path"), "--env-file none")


# Verifies a quoted piece of a URL stays plain, since the authorization prompt points at one
@pytest.mark.parametrize("fragment", ["?code=", "&state="])
def test_a_quoted_url_fragment_is_not_read_as_a_name(colored, fragment):
    assert uncolored(colored._colorize_line(f"Enter authorization code (part after '{fragment}' in callback URL): "), fragment)


# Verifies the URL rule reads only a leading '?' or '&', so a title carrying one mid-name is still a title
@pytest.mark.parametrize("title", ["Ratchet & Clank: Rift Apart", "Rock Band: A=440 Edition"])
def test_a_title_containing_a_url_character_is_still_coloured(colored, title):
    assert styled_as(colored._colorize_line(f"Xbox user x started playing '{title}'"), title, "game")


# Verifies truncation is switched off, with a warning, when the package that measures width is missing
def test_truncation_is_disabled_when_wcwidth_is_missing(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "wcwidth", None)
    assert monitor.resolve_truncate_chars(80, 0, False) == 0
    out = capsys.readouterr().out
    assert "wcwidth" in out and "Screen truncation is disabled" in out


# Verifies the width sentinel expands to the real terminal width, the documented meaning of 999
def test_the_width_sentinel_expands_to_the_terminal_width(monkeypatch):
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", lambda: os.terminal_size((123, 40)))
    assert monitor.resolve_truncate_chars(999, 0, False) == 123


# Verifies truncation stays off while logging is disabled, since the trimmed text would then be lost for good
def test_truncation_stays_off_while_logging_is_disabled():
    assert monitor.resolve_truncate_chars(80, 0, True) == 0


# Verifies both delivery announcements are painted for their channel, so the two theme keys are not settings that do nothing
@pytest.mark.parametrize("line,part", [
    ("* Sending email notification to alerts@example.test", "email"),
    ("* Sending webhook notification", "webhook"),
])
def test_a_delivery_announcement_is_painted_for_its_channel(colored, line, part):
    assert styled_as(monitor._colorize_line(line), line, part)


# Verifies the two channels keep the values every sibling monitor ships, and that the console tag stays visible
# inside a webhook line rather than sharing its colour
def test_the_delivery_channels_keep_the_shared_colours():
    assert monitor.DEFAULT_COLOR_THEME["email"] == "bright_cyan"
    assert monitor.DEFAULT_COLOR_THEME["webhook"] == "bright_blue"
    assert monitor.DEFAULT_COLOR_THEME["platform"] != monitor.DEFAULT_COLOR_THEME["webhook"]


# Verifies the version under the banner carries a colour, the way every sibling monitor prints it
def test_the_banner_version_line_is_coloured(colored, capsys):
    monitor.print_startup_banner()

    version_line = next(line for line in capsys.readouterr().out.splitlines() if f"v{monitor.VERSION}" in line)
    assert SGR.search(version_line)


# Verifies a printed command and its hint carry the colours every sibling monitor gives them
def test_a_labelled_command_and_its_hint_are_coloured(colored, capsys):
    monitor.print_labelled_command("Easiest start (guided setup wizard):", "xbox_monitor --setup", "   (or just answer Y below)")

    output = capsys.readouterr().out
    assert styled_as(output, "xbox_monitor --setup", "section")
    assert styled_as(output, "   (or just answer Y below)", "info")
