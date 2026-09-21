"""Tests for --verbose and --debug: what the two modes report and which setting wins.

Each coverage test drives the real code path with the failure injected rather than calling the
printers directly, so a path that was never instrumented fails the test instead of passing quietly.
"""

import asyncio
import contextlib
import time
import re
from types import SimpleNamespace

import httpx
import pytest

import xbox_monitor as monitor

GAMERTAG = "misiektoja"
XUID = 2535428504476914

# Captured before any fixture replaces it, so the connectivity test can drive the real function
REAL_CHECK_INTERNET = monitor.check_internet


# Raised by the stubbed sleep once the scripted responses are exhausted, to end the endless loop
class LoopFinished(BaseException):
    pass


# Builds the presence object the loop reads, shaped the way the Xbox Live client returns it
def presence_payload(state="offline", last_seen="2026-01-01T00:00:00Z", title="Home"):
    seen = SimpleNamespace(title_name=title, device_type="XboxSeriesX", timestamp=last_seen) if last_seen else None
    return SimpleNamespace(state=state, last_seen=seen)


@pytest.fixture(autouse=True)
# Keeps the status file, the CSV history and any generated config inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
# Keeps startup offline and away from any config or dotenv file the developer happens to have
def isolated_startup(monkeypatch):
    monkeypatch.setattr(monitor, "DEFAULT_CONFIG_FILENAME", "xbox_monitor_test_only.conf")
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    # Left at Auto the timestamped lines fail on a machine without tzlocal, which is not what these tests measure
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)


@pytest.fixture
# Turns both diagnostic modes on for tests that only care about what gets reported
def both_modes_on(monkeypatch):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)


@pytest.fixture
# Turns verbose mode on and leaves debug off, so only the rare-event lines can appear
def verbose_only(monkeypatch):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after startup
def monitor_calls(monkeypatch):
    recorded = []

    async def fake_monitor(xbox_gamertag, csv_file_name, achievements_count=5, games_count=10):
        recorded.append(xbox_gamertag)

    monkeypatch.setattr(monitor, "xbox_monitor_user", fake_monitor)
    return recorded


@pytest.fixture
# Signs the loop in without a network call and replays the scripted presence responses to it
def xbox_loop(monkeypatch):
    clock = [float(int(time.time()))]

    def install(responses):
        remaining = list(responses)
        monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
        monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "client-id-value")
        monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "client-secret-value")

        @contextlib.asynccontextmanager
        async def fake_session():
            yield SimpleNamespace()

        async def next_presence(xuid, level):
            if not remaining:
                raise LoopFinished
            answer = remaining.pop(0)
            if isinstance(answer, BaseException):
                raise answer
            return answer

        async def no_sleep(seconds):
            # Advance the fake clock, so the timed liveness reminder is deterministic
            clock[0] += seconds
            if not remaining:
                raise LoopFinished

        monkeypatch.setattr(monitor, "create_signed_session", fake_session)
        monkeypatch.setattr(monitor, "AuthenticationManager", lambda *args, **kwargs: SimpleNamespace())
        monkeypatch.setattr(monitor, "authenticate_and_refresh_tokens", lambda auth_mgr: _completed())
        monkeypatch.setattr(monitor, "get_user_info", lambda *args, **kwargs: _completed())
        monkeypatch.setattr(monitor, "xbox_get_latest_title_played_ts", lambda client, xuid, outage=None: _completed((0, "", True)))
        monkeypatch.setattr(monitor, "XboxLiveClient", lambda auth_mgr: SimpleNamespace(profile=SimpleNamespace(get_profile_by_gamertag=lambda tag: _completed(SimpleNamespace(profile_users=[SimpleNamespace(id=str(XUID))]))), presence=SimpleNamespace(get_presence=next_presence)))
        monkeypatch.setattr(monitor.asyncio, "sleep", no_sleep)
    return install


# Returns an already finished awaitable, so a synchronous stub can stand in for a coroutine
async def _completed(value=None):
    return value


# Runs the monitoring loop until the scripted responses are exhausted
def run_monitor(csv_file_name=""):
    with pytest.raises(LoopFinished):
        asyncio.run(monitor.xbox_monitor_user(GAMERTAG, csv_file_name))


# Runs main() with the supplied command line and returns the exit code it raised
def run_main(monkeypatch, argv):
    monkeypatch.setattr(monitor.sys, "argv", ["xbox_monitor", *argv])
    with pytest.raises(SystemExit) as raised:
        monitor.main()
    return raised.value.code


# Verifies a failed connectivity check names the address and the timeout it used
def test_debug_reports_the_connectivity_check(monkeypatch, both_modes_on, capsys):
    def refuse(url, timeout=None, verify=None, follow_redirects=None):
        raise httpx.ConnectError("name resolution failed")

    monkeypatch.setattr(monitor.httpx, "get", refuse)

    assert REAL_CHECK_INTERNET("https://xbox.example/probe", 7) is False

    output = capsys.readouterr().out
    assert "Connectivity check: url=https://xbox.example/probe, outcome=failed, error=ConnectError" in output


# Verifies an exception the tool swallows on purpose still leaves a trace under debug
def test_debug_reports_a_swallowed_exception(both_modes_on, capsys):
    assert monitor.convert_iso_str_to_datetime("not-a-real-timestamp") is None

    assert "Timestamp conversion to local time: outcome=failed, error=ValueError" in capsys.readouterr().out


# Verifies a file the tool cannot write is reported with the reason, not only as a generic error
def test_debug_reports_a_failed_file_write(both_modes_on, isolated_working_directory, capsys):
    unwritable = isolated_working_directory / "history-dir"
    unwritable.mkdir()

    with pytest.raises(RuntimeError):
        monitor.init_csv_file(str(unwritable))

    assert f"CSV initialization: path={unwritable}, outcome=failed, error=IsADirectoryError" in capsys.readouterr().out


# Verifies an email the tool declines to send is reported rather than disappearing
def test_debug_reports_a_skipped_email(monkeypatch, both_modes_on, capsys):
    monkeypatch.setattr(monitor, "SMTP_HOST", "your_smtp_server_ssl")

    assert monitor.send_email("subject", "body", "", False) == 1

    assert "Email delivery: outcome=skipped, reason=the SMTP settings are unusable" in capsys.readouterr().out


# Verifies a feature that quietly turns itself off says so, without needing debug mode
def test_a_degraded_feature_is_reported_in_verbose_mode(monkeypatch, verbose_only, monitor_calls, capsys):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Auto")
    monkeypatch.setattr(monitor, "get_localzone", None)

    run_main(monkeypatch, [GAMERTAG, "--verbose", "-u", "client-id-value", "-w", "client-secret-value"])

    assert "Automatic time zone detection is unavailable because the optional tzlocal library is missing" in capsys.readouterr().out


# Verifies email alerts that switch themselves off name every setting still holding a placeholder
def test_verbose_names_every_unset_smtp_setting(monkeypatch, verbose_only, monitor_calls, capsys):
    run_main(monkeypatch, [GAMERTAG, "--verbose", "-u", "client-id-value", "-w", "client-secret-value"])

    assert "Email notifications are off because SMTP_HOST, SMTP_USER and SMTP_PASSWORD are still empty or shipped placeholders" in capsys.readouterr().out


@pytest.mark.parametrize("names, expected", [(["A"], "A"), (["A", "B"], "A and B"), (["A", "B", "C"], "A, B and C"), ([], "")])
# Verifies a list of names reads as a sentence rather than repeating the conjunction
def test_names_are_joined_the_way_a_sentence_joins_them(names, expected):
    assert monitor.join_names(names) == expected


# Verifies a presence call that fails inside the monitoring loop is named along with how it was classified
def test_debug_reports_the_presence_failure_and_its_classification(xbox_loop, both_modes_on, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("connection reset by peer"), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert "recovery_code=network.unavailable" in output
    assert "Presence check: check=#1, outcome=failed, error=ConnectError: connection reset by peer" in output
    assert "streak=1" in output


# Verifies a healthy check reports that it finished and what it found, since a trace covering only failures
# makes a run that is quietly working look the same as one that is stuck
def test_debug_reports_each_completed_check_and_its_result(xbox_loop, both_modes_on, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("connection reset by peer"), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    # The first payload is the startup snapshot, so the loop sees the failure first and the second payload second
    completed = [line for line in output.splitlines() if "Completed check" in line]
    assert len(completed) == 1, output
    assert "Completed check: check=#2, user=" in completed[0]
    assert "outcome=OK, status=offline" in completed[0]


# Verifies every wait names how long it is and why, so a stalled run can be explained from the transcript
def test_debug_reports_each_sleep_with_its_reason(xbox_loop, both_modes_on, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("connection reset by peer"), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert "Sleep: seconds=" in output
    assert "reason=the presence check failed" in output


# Verifies recovering from a run of failures is reported, since a throttled failure stops printing while it lasts
def test_recovery_after_a_reported_failure_streak_is_reported(xbox_loop, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("first"), httpx.ConnectError("second"), httpx.ConnectError("third"), presence_payload(), presence_payload()])

    run_monitor()

    assert f"* Monitoring recovered for {GAMERTAG} after " in capsys.readouterr().out


# Verifies a single failure also reports its recovery, so a brief outage is not left open in the transcript
def test_a_single_reported_failure_reports_its_recovery(xbox_loop, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("only one"), presence_payload(), presence_payload()])

    run_monitor()

    assert f"* Monitoring recovered for {GAMERTAG} after " in capsys.readouterr().out


# Verifies a failure that keeps repeating is reported once and then carried by the hourly reminder with a count,
# on a clock of its own, so the liveness banner being off does not silence it or bring back a block per check
def test_a_lasting_outage_is_carried_by_the_hourly_reminder(xbox_loop, monkeypatch, capsys):
    # The screen cadence is the subject, so the alert that a lasting outage also earns is switched off
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 0)
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 2 * monitor.XBOX_CHECK_INTERVAL)
    xbox_loop([presence_payload(), *[httpx.ConnectError("down") for _ in range(8)], presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    assert output.count(f"* Monitoring degraded for {GAMERTAG}. Xbox Live could not be reached since ") == 3
    assert ", 3 failed checks\n" in output and ", 7 failed checks\n" in output
    assert output.count("Liveness check, timestamp:") == 3
    assert "Monitoring healthy" not in output


# Verifies an alert that lands on a check the outage reporter keeps quiet still ends with a timestamp
def test_a_delivery_on_a_quiet_check_ends_with_a_timestamp(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 100 * monitor.XBOX_CHECK_INTERVAL)
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda *args, **kwargs: False)
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 1)
    xbox_loop([presence_payload(), *[httpx.ConnectError("down") for _ in range(4)]])

    run_monitor()

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    deliveries = [index for index, line in enumerate(lines) if line.startswith("Sending email notification")]

    assert deliveries, lines
    for index in deliveries:
        assert any(line.startswith("Timestamp:") for line in lines[index + 1:index + 3]), lines[index:index + 3]


# Collects the subject of every email the run delivers, so an alert can be told apart from the one that closes it
def collect_email_subjects(monkeypatch):
    subjects = []
    monkeypatch.setattr(monitor, "send_email", lambda subject, *args, **kwargs: subjects.append(subject) or 0)
    return subjects


# Verifies a failure the tool can retry away is alerted only once the outage has lasted the alert delay, so a
# blip of a check reaches nobody while a real outage still does, and that the alert is closed when it clears
@pytest.mark.parametrize("failures,expected", [(1, 0), (2, 1)])
def test_a_retryable_failure_is_alerted_once_the_outage_has_lasted(xbox_loop, monkeypatch, capsys, failures, expected):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 100 * monitor.XBOX_CHECK_INTERVAL)
    subjects = collect_email_subjects(monkeypatch)
    # Five minute polls put the second failing check at the five minute delay
    xbox_loop([presence_payload(), *[httpx.ConnectError("down") for _ in range(failures)], presence_payload()])

    run_monitor()

    assert len([subject for subject in subjects if subject.startswith("Xbox Monitor error:")]) == expected
    assert len([subject for subject in subjects if subject.startswith("Xbox Monitor recovered:")]) == expected


# Verifies a failure nothing here can retry away is alerted on the first check, since waiting would change nothing
def test_a_failure_that_cannot_clear_itself_is_alerted_at_once(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    subjects = collect_email_subjects(monkeypatch)
    request = httpx.Request("GET", "https://profile.xboxlive.com/users")
    xbox_loop([presence_payload(), httpx.HTTPStatusError("401", request=request, response=httpx.Response(401, request=request)), presence_payload()])

    run_monitor()

    assert len([subject for subject in subjects if subject.startswith("Xbox Monitor error:")]) == 1


# Verifies a recovery alert only follows an outage somebody was told about, so a quiet blip stays quiet
def test_no_recovery_alert_follows_an_outage_nobody_was_told_about(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    subjects = collect_email_subjects(monkeypatch)
    xbox_loop([presence_payload(), httpx.ConnectError("down"), httpx.ConnectError("down"), presence_payload()])

    run_monitor()

    assert subjects == []
    assert f"* Monitoring recovered for {GAMERTAG} after " in capsys.readouterr().out


# Verifies the reminder follows the clock, so a run that retries faster than it polls does not remind more often
def test_the_outage_reminder_follows_the_clock_not_the_check_count(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(httpx.ConnectError("down"), context="monitor")

    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 900)
    assert reporter.failed(advice) == "full"
    outcomes = []
    for _ in range(60):
        clock[0] += 15
        outcomes.append(reporter.failed(advice))

    assert outcomes.count("reminder") == 1


# Verifies a category change mid-outage keeps the outage start, so the alert delay and the reminder still elapse
def test_an_outage_that_changes_category_keeps_its_start(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    first = monitor.classify_recovery_error(httpx.ConnectError("down"), context="monitor")
    second = monitor.classify_recovery_error(OSError(24, "Too many open files"), context="monitor")
    assert first.code != second.code

    assert reporter.failed(first) == "full"
    for index in range(60):
        clock[0] += 15
        reporter.failed(second if index % 2 else first)

    assert reporter.since == 1000000
    assert reporter.recovered() == 900


# Verifies the banner follows the clock rather than the number of checks behind it
def test_the_liveness_banner_follows_the_clock_not_the_check_count(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 3 * monitor.XBOX_CHECK_INTERVAL)
    xbox_loop([presence_payload() for _ in range(5)])

    run_monitor()

    assert capsys.readouterr().out.count("Monitoring healthy for") == 1


# Verifies a check that reported the end of an outage restarts the quiet clock, since the banner speaks for a
# check that said nothing and would otherwise contradict the recovery line above it
def test_a_check_that_reported_a_recovery_does_not_claim_it_was_quiet(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 2 * monitor.XBOX_CHECK_INTERVAL)
    failures = [httpx.ConnectError("down") for _ in range(4)]
    xbox_loop([presence_payload(), *failures, presence_payload(), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert "Monitoring recovered for" in output, "the check under test reported no recovery"
    assert "Monitoring healthy for" not in output


# Verifies a cycle with nothing rare to report prints no verbose line at all
def test_verbose_stays_quiet_through_an_uneventful_cycle(xbox_loop, verbose_only, capsys):
    xbox_loop([presence_payload(), presence_payload(), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert "Monitoring recovered for" not in output
    assert "[DEBUG " not in output


# Verifies neither mode prints anything on a run that exercises the paths both of them instrument
def test_neither_mode_prints_anything_when_both_are_off(xbox_loop, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("connection reset by peer"), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert "[DEBUG " not in output
    assert "Sleep:" not in output


# Verifies the config file and the source of every secret are reported, which is what a wrong-credential report needs
def test_debug_reports_the_config_load_and_the_secret_source(monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "custom.conf"
    config.write_text('MS_APP_CLIENT_ID = "client-id-from-config"\nXBOX_CHECK_INTERVAL = 300\n', encoding="utf-8")

    run_main(monkeypatch, ["--config-file", str(config), "--debug", "-w", "client-secret-value", GAMERTAG])

    output = capsys.readouterr().out
    assert f"Configuration applied: path={config}, settings=2, names=MS_APP_CLIENT_ID, XBOX_CHECK_INTERVAL" in output
    assert "Secret resolution: name=MS_APP_CLIENT_ID, source=configuration file" in output
    assert "Secret resolution: name=MS_APP_CLIENT_SECRET, source=command line, value=set, chars=19" in output


# Verifies a secret supplied on the command line is never printed by the line that reports it
def test_debug_never_prints_the_credential_it_reports(monkeypatch, monitor_calls, capsys):
    run_main(monkeypatch, ["--debug", "-u", "aVeryLongClientIdValue1234567890", "-w", "aVeryLongClientSecretValue123456", GAMERTAG])

    output = capsys.readouterr().out
    assert "Secret resolution: name=MS_APP_CLIENT_ID, source=command line" in output
    assert "aVeryLongClientIdValue1234567890" not in output
    assert "aVeryLongClientSecretValue123456" not in output


# Verifies debug output starts before the config file is read, so a broken config is still diagnosable
def test_the_debug_flag_applies_before_the_config_file_is_read(monkeypatch, isolated_working_directory, capsys):
    config = isolated_working_directory / "broken.conf"
    config.write_text("XBOX_CHECK_INTERVAL = = 300\n", encoding="utf-8")

    assert run_main(monkeypatch, ["--config-file", str(config), "--debug", GAMERTAG]) == 1

    assert f"Configuration load: path={config}, outcome=failed" in capsys.readouterr().out


# Verifies turning one mode on does not turn the other on
def test_the_two_modes_are_independent(monkeypatch, monitor_calls, capsys):
    run_main(monkeypatch, [GAMERTAG, "--verbose", "-u", "client-id-value", "-w", "client-secret-value"])
    verbose_output = capsys.readouterr().out

    # A real process runs main() once, so the second run starts from the shipped defaults again
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    run_main(monkeypatch, [GAMERTAG, "--debug", "-u", "client-id-value", "-w", "client-secret-value"])
    debug_output = capsys.readouterr().out

    assert "[DEBUG " not in verbose_output
    assert "[DEBUG " in debug_output
    # The startup summary reports each mode separately, so one flag must never switch the other on
    assert re.search(r"\* Verbose mode:\s+True", verbose_output) and re.search(r"\* Debug mode:\s+False", verbose_output)
    assert re.search(r"\* Verbose mode:\s+False", debug_output) and re.search(r"\* Debug mode:\s+True", debug_output)


# Verifies the startup summary points at the flags while they are off and reports them once they are on
def test_the_startup_summary_offers_the_flags_then_reports_them(monkeypatch, monitor_calls, capsys):
    run_main(monkeypatch, [GAMERTAG, "-u", "client-id-value", "-w", "client-secret-value"])
    without_flags = capsys.readouterr().out

    run_main(monkeypatch, [GAMERTAG, "--verbose", "-u", "client-id-value", "-w", "client-secret-value"])
    with_verbose = capsys.readouterr().out

    assert "use --verbose or --debug" in without_flags
    assert "* More details:" not in with_verbose
    assert "Verbose mode:" in with_verbose
    # The concise view stays short and asking for the full one is what adds the rest
    assert without_flags.count("\n* ") < with_verbose.count("\n* ")


# Verifies only debug keeps the screen, since a cleared terminal loses the run being compared against
@pytest.mark.parametrize("flag, expected", [("--debug", False), ("--verbose", True)])
def test_only_debug_mode_keeps_the_screen(monkeypatch, monitor_calls, flag, expected):
    cleared = []
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: cleared.append(bool(enabled)))
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)

    run_main(monkeypatch, [GAMERTAG, flag, "-u", "client-id-value", "-w", "client-secret-value"])

    assert cleared == [expected]


# Verifies the one-shot commands keep whatever is already on the screen, so their output stays scrollable
@pytest.mark.parametrize(("argv", "expected"), ((["xbox_monitor", "--doctor"], True), (["xbox_monitor", "--set-ms-app-credentials"], True), (["xbox_monitor", "--send-test-email"], True), (["xbox_monitor", "--help"], True), (["xbox_monitor", "test-gamertag"], False)))
def test_one_shot_commands_keep_the_terminal_history(monkeypatch, argv, expected):
    monkeypatch.setattr(monitor.sys, "argv", argv)

    assert monitor.keep_terminal_history() is expected


# Verifies a redirected stdout is never cleared, so no escape sequence or TERM warning reaches the captured output
def test_a_redirected_stdout_is_never_cleared(monkeypatch):
    commands = []
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(monitor.os, "system", lambda command: commands.append(command))

    monitor.clear_screen(True)

    assert commands == []


# Verifies a verbose notice raised before monitoring starts does not print a timestamp the run has no use for
def test_a_notice_before_monitoring_starts_carries_no_timestamp(monkeypatch, verbose_only, capsys):
    monkeypatch.setattr(monitor, "MONITORING_ACTIVE", False)

    monitor.verbose_notice("A feature turned itself off")

    output = capsys.readouterr().out
    assert "* A feature turned itself off" in output
    assert "Timestamp:" not in output


# Verifies the same notice closes its own block once monitoring is printing timestamped cycles
def test_a_notice_during_monitoring_closes_its_own_block(monkeypatch, verbose_only, capsys):
    monkeypatch.setattr(monitor, "MONITORING_ACTIVE", True)

    monitor.verbose_notice("A feature turned itself off")

    output = capsys.readouterr().out
    assert "* A feature turned itself off" in output
    assert "Timestamp:" in output


@pytest.mark.parametrize("printer", ["verbose_print", "debug_print"])
# Verifies each printer stays silent while its own mode is off, whatever the other mode is doing
def test_each_printer_is_silent_while_its_mode_is_off(monkeypatch, printer, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", printer != "verbose_print")
    monkeypatch.setattr(monitor, "DEBUG_MODE", printer != "debug_print")

    getattr(monitor, printer)("A line nobody asked for")

    assert "A line nobody asked for" not in capsys.readouterr().out


# Verifies a secret issued by Microsoft reports its length while one the user chose reports presence only
@pytest.mark.parametrize("key, value, expected", [
    ("MS_APP_CLIENT_ID", "0123456789abcdef", "set, 16 chars"),
    ("MS_APP_CLIENT_SECRET", "0123456789", "set, 10 chars"),
    ("SMTP_PASSWORD", "a-password-the-user-picked", "set"),
    ("SMTP_PASSWORD", "your_smtp_password", "not set"),
    ("MS_APP_CLIENT_ID", "", "not set"),
])
def test_a_secret_is_described_without_revealing_it(key, value, expected):
    assert monitor.secret_fingerprint(value, key) == expected
    assert value not in monitor.secret_fingerprint(value, key) or not value


# The diagnostic line is documented as comma-separated key=value fields, so the length travels as its own field
@pytest.mark.parametrize("key, value, fields", [
    ("MS_APP_CLIENT_ID", "0123456789abcdef", {"value": "set", "chars": 16}),
    ("SMTP_PASSWORD", "a-password-the-user-picked", {"value": "set", "chars": None}),
    ("MS_APP_CLIENT_ID", "", {"value": "not set", "chars": None}),
])
def test_no_secret_field_value_carries_a_comma(key, value, fields):
    assert monitor.secret_fields(value, key) == fields
    assert all("," not in str(part) for part in fields.values())


# The webhook override is applied after the resolution loop, so a webhook given on the command line still reports its source
def test_a_command_line_webhook_reports_where_it_came_from(monkeypatch, monitor_calls, capsys):
    run_main(monkeypatch, ["--debug", "--webhook-url", "https://discord.com/api/webhooks/1/" + "a" * 32, GAMERTAG])

    traces = [line for line in capsys.readouterr().out.splitlines() if "Secret resolution: name=WEBHOOK_URL" in line]
    assert traces[-1].endswith("Secret resolution: name=WEBHOOK_URL, source=command line, value=set")


# Verifies a reported failure uses the line shape shared with the sibling monitors
def test_a_reported_failure_uses_the_shared_line_shape(xbox_loop, capsys):
    xbox_loop([presence_payload(), httpx.ConnectError("connection reset by peer"), presence_payload()])

    run_monitor()

    reported = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("* Error: "))
    assert reported == f"* Error: Xbox Live could not be reached (retrying in {monitor.display_time(monitor.XBOX_CHECK_INTERVAL)})"


# Verifies the liveness banner explains itself without --verbose, so a plain run never prints a bare timestamp
def test_the_liveness_banner_explains_itself_without_diagnostics(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", monitor.XBOX_CHECK_INTERVAL)
    xbox_loop([presence_payload(), presence_payload(), presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert f"* Monitoring healthy for {GAMERTAG}. The user is offline with no activity change since the last check" in output
    assert "Liveness check, timestamp:" in output


# A secret no layer supplied takes no row, so the trace lists what is configured rather than what is not
def test_the_trace_omits_every_secret_no_layer_supplied(monkeypatch, monitor_calls, capsys):
    run_main(monkeypatch, ["--debug", "--webhook-url", "https://discord.com/api/webhooks/1/" + "a" * 32, GAMERTAG])

    output = capsys.readouterr().out
    assert "Secret resolution: name=WEBHOOK_URL, source=command line" in output
    assert "name=NTFY_ACCESS_TOKEN" not in output
    assert "source=nowhere" not in output


# The trace runs after the last layer, so one secret cannot be reported twice with opposite answers
def test_the_trace_reports_a_command_line_secret_exactly_once(monkeypatch, monitor_calls, capsys):
    run_main(monkeypatch, ["--debug", "--webhook-url", "https://discord.com/api/webhooks/1/" + "a" * 32, GAMERTAG])

    traces = [line for line in capsys.readouterr().out.splitlines() if "Secret resolution: name=WEBHOOK_URL" in line]
    assert len(traces) == 1


# A placeholder is not a value, so it earns neither a source nor a row, which is what the doctor already reports
def test_a_placeholder_earns_no_source(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "your_ms_app_client_id", raising=False)

    monitor.record_secret_source("MS_APP_CLIENT_ID", "dotenv file")

    assert monitor.SECRET_SOURCES == {}
    with pytest.raises(ValueError, match="Unsupported secret source"):
        monitor.record_secret_source("MS_APP_CLIENT_ID", "a layer that does not exist", "a real value")


# Builds the server-side error httpx raises for one rejected status
def server_error(status):
    request = httpx.Request("GET", "https://userpresence.xboxlive.com/users")
    return httpx.HTTPStatusError(str(status), request=request, response=httpx.Response(status, request=request))


# Verifies an internet outage that classifies as a timeout on one check and as unreachable on the next is one
# outage, so it is reported once rather than on every change
def test_an_internet_outage_that_flaps_is_one_outage(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    flapping = [httpx.ConnectError("down") if index % 2 else httpx.ReadTimeout("slow") for index in range(10)]
    xbox_loop([presence_payload(), *flapping, presence_payload()])

    run_monitor()

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    assert "Monitoring failure changed" not in output
    assert f"* Monitoring recovered for {GAMERTAG} after " in output


# Verifies a reported outage that starts failing differently is still one outage, so the change is one line
# rather than a second report
def test_a_second_failure_category_is_noted_in_one_line(xbox_loop, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    unavailable = monitor.classify_recovery_error(server_error(503), context="monitor")
    assert unavailable.retryable and monitor.outage_family(unavailable.code) != "network"
    xbox_loop([presence_payload(), *[httpx.ConnectError("down") for _ in range(3)], *[server_error(503) for _ in range(3)]])

    run_monitor()

    lines = capsys.readouterr().out.splitlines()
    reports = [line for line in lines if line.startswith("* Error:")]
    changes = [number for number, line in enumerate(lines) if line.startswith(f"* Monitoring failure changed for {GAMERTAG}. ")]
    assert len(reports) == 1 and "could not be reached" in reports[0]
    assert len(changes) == 1 and lines[changes[0]].endswith(unavailable.summary)
    assert lines[changes[0] + 1].startswith("Timestamp:")
    assert "\n".join(lines).count("To fix: ") == 1


# Verifies the reporter treats every network code as one outage and a change to a failure nothing can retry
# away as a new report
def test_the_outage_reporter_merges_network_codes_and_reports_a_terminal_change(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    unreachable = monitor.classify_recovery_error(httpx.ConnectError("down"), context="monitor")
    timeout = monitor.classify_recovery_error(httpx.ReadTimeout("slow"), context="monitor")
    rejected = monitor.classify_recovery_error(server_error(401), context="monitor")
    assert (monitor.outage_family(timeout.code), monitor.outage_family(unreachable.code)) == ("network", "network")
    assert not rejected.retryable

    assert reporter.failed(unreachable) == "full"
    assert reporter.failed(timeout) == ""
    assert reporter.failed(unreachable) == ""
    assert reporter.failed(rejected) == "full"
    assert reporter.since == 1000000
