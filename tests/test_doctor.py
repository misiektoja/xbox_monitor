"""Tests for --doctor: the report contract, every section it prints and the exit code it returns.

The output contract lives in the seam between the functions, not inside any one of them, so the contract tests
drive the whole run and read the transcript a user sees.
"""

import inspect
import re
from unittest.mock import Mock

import pytest

import xbox_monitor as monitor

GAMERTAG = "misiektoja"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"

# The four shared markers. A fifth is the drift these tests exist to catch
MARKERS = ("PASS", "WARN", "FAIL", "SKIP")

MARKER_RE = re.compile(r"^\[([A-Z -]+)\]")


# Builds the minimal advice a WARN or FAIL row is required to carry
def actionable_advice():
    return monitor.make_recovery_advice("unknown", "a summary", "do the thing", False)


# Captured before the autouse fixture below replaces the name with an offline stub
REAL_CONNECTIVITY_CHECK = monitor.doctor_check_connectivity


# Fails the test if the doctor tries to sign in on a path that must never reach the network
def _unreachable_smtp(*args, **kwargs):
    raise AssertionError("Doctor must not open an SMTP connection when the sign-in cannot be attempted")


# Fails the test if the doctor publishes a webhook the user declined
def _unreachable_webhook(*args, **kwargs):
    raise AssertionError("Doctor must not publish a webhook without approval")


# Stands in for the signed session, which the checks close whether or not they got that far
class _FakeClosableSession:
    async def aclose(self):
        pass


# Stands in for an interactive terminal, collecting print output and progress writes in one buffer
class FakeTerminal:
    def __init__(self, interactive=True):
        self.interactive = interactive
        self.chunks = []

    def isatty(self):
        return self.interactive

    def write(self, text):
        self.chunks.append(text)
        return len(text)

    def flush(self):
        pass

    @property
    def text(self):
        return "".join(self.chunks)


# Replays one line's carriage returns, so a write hides only the columns it actually covers
def replay_overwrites(line):
    rendered = ""
    for segment in line.split("\r"):
        rendered = segment + rendered[len(segment):]
    return rendered


# Collapses carriage-return overwrites the way a terminal does, so cleared progress does not read as content
def as_displayed(raw):
    return "\n".join(replay_overwrites(line).rstrip() for line in raw.split("\n"))


@pytest.fixture
# Runs the doctor against a fake interactive terminal and returns what the user would see
def doctor_run(monkeypatch):
    def run(interactive=True, **kwargs):
        terminal = FakeTerminal(interactive)
        monkeypatch.setattr(monitor.sys, "stdout", terminal)
        monkeypatch.setattr(monitor.sys, "stdin", terminal)
        code = monitor.run_doctor(**kwargs)
        return code, terminal.text
    return run


@pytest.fixture(autouse=True)
# Keeps every run offline and away from any config or dotenv file the developer happens to have
def offline_doctor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "MS_AUTH_TOKENS_FILE", str(tmp_path / "xbox_tokens.json"))
    monkeypatch.setattr(monitor, "doctor_check_connectivity", lambda: [monitor.make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable")])
    monkeypatch.setattr(monitor.smtplib, "SMTP", _unreachable_smtp)


@pytest.fixture
# Signs the doctor in to Xbox Live without a network call, returning the profile the target lookup then reports
def xbox_session(monkeypatch):
    def install(gamertag=GAMERTAG, xuid=2535428504476914, refresh_error=None, lookup_error=None):
        monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "client-id-value")
        monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "client-secret-value")
        tokens = monitor.Path(monitor.MS_AUTH_TOKENS_FILE)
        tokens.write_text("{}", encoding="utf-8")
        tokens.chmod(0o600)

        async def fake_refresh(auth_mgr):
            if refresh_error is not None:
                raise refresh_error

        async def fake_target(auth_mgr, xbox_gamertag, progress=None):
            if lookup_error is not None:
                advice = monitor.classify_recovery_error(lookup_error, context="target", detail=f"Looking up the gamertag '{xbox_gamertag}' failed: {lookup_error}")
                return [monitor.make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
            return [monitor.make_doctor_check("Target", "PASS", f"Gamertag {gamertag} was found", f"XUID: {xuid}")]

        monkeypatch.setattr(monitor, "create_signed_session", lambda: _FakeClosableSession())
        monkeypatch.setattr(monitor, "AuthenticationManager", lambda *args: object())
        monkeypatch.setattr(monitor, "doctor_refresh_tokens", fake_refresh)
        monkeypatch.setattr(monitor, "doctor_check_target", fake_target)
    return install


@pytest.fixture
# Lets the passive sign-in succeed without contacting a server, for the tests that need a ready email channel
def smtp_sign_in_ok(monkeypatch):
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: monitor.SMTP_USER)


# Turns on every email setting the notification check needs before it will attempt a sign-in
def enable_email(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_USER", "sender@example.com")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "smtp-password-value")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.com")
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", True)


# Turns on a working Discord destination, so the webhook check reaches the settings it validates
def enable_webhook(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)


# Returns every check the doctor produced for one section
def checks_in(report, section):
    return [check for check in report.checks if check.section == section]


# Returns the first check whose label starts with the given text
def check_labelled(report, prefix):
    return next(check for check in report.checks if check.label.startswith(prefix))


# Verifies the preflight notice, the progress line and the heading arrive in the documented order
def test_the_report_is_printed_in_the_documented_order(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    notice = raw.index("Running preflight checks")
    progress = raw.index("* Checking environment ...")
    # The heading is written straight after the progress line is erased, so there is no newline before it
    heading = raw.index("Doctor\nDetected install method:")
    assert notice < progress < heading < raw.index("\nSummary\n")


# Verifies the preflight notice names both channels the delivery tests can offer, so neither is a surprise
def test_the_preflight_notice_names_both_delivery_channels(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    assert "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval." in raw


# The transient progress line must not survive into the report a user reads or pastes into an issue
def test_the_progress_line_is_cleared_before_the_report(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    assert "* Checking" in raw
    assert "* Checking" not in as_displayed(raw)


# A carriage return with nothing written after it moves the cursor only, so the line must survive intact
def test_a_trailing_carriage_return_keeps_the_line():
    assert as_displayed("Target\r\n[WARN] No profile") == "Target\n[WARN] No profile"


# A shorter write hides only the columns it covers, the way a terminal redraws a line
def test_an_overwrite_replaces_only_the_columns_it_covers():
    assert replay_overwrites("* Checking configuration ...\rDoctor") == "Doctor" + "* Checking configuration ..."[6:]
    # A progress line erased by exactly its own width leaves nothing behind
    assert replay_overwrites("\r* Checking environment ...\r" + " " * 26 + "\r").strip() == ""


# A redirected run has nothing to overwrite, so writing progress there would corrupt the saved report
def test_no_progress_is_written_when_the_output_is_not_a_terminal(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(interactive=False, xbox_gamertag=GAMERTAG)
    assert "* Checking" not in raw
    assert "\r" not in raw


# Blank-line drift is what makes one tool's report look different from another's
def test_the_report_never_prints_two_blank_lines_in_a_row(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    assert "\n\n\n" not in as_displayed(raw).strip()


# A fifth marker would silently change what a status means across the whole family
def test_only_the_four_shared_markers_are_used(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    found = {match.group(1) for line in as_displayed(raw).splitlines() if (match := MARKER_RE.match(line))}
    assert found
    assert found <= set(MARKERS)


# The guard has to reject an unsupported marker at the point it is created, not when it is printed
def test_an_unsupported_marker_is_refused():
    with pytest.raises(ValueError):
        monitor.make_doctor_check("Environment", "OK", "Anything")


# A detail that repeats its own label reads as two separate problems
def test_a_detail_that_repeats_the_label_is_dropped():
    check = monitor.make_doctor_check("Environment", "FAIL", "Something broke", "Something broke", actionable_advice())
    assert check.detail == ""


# Sections in a fixed order let a reader compare two reports line by line
def test_sections_appear_in_the_fixed_order(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    displayed = as_displayed(raw)
    positions = [displayed.index(f"\n{section}\n") for section in monitor.DOCTOR_SECTIONS if f"\n{section}\n" in displayed]
    assert len(positions) == len(monitor.DOCTOR_SECTIONS)
    assert positions == sorted(positions)


# A fix line under a passing row is noise and a missing one under a failure leaves the user stuck
def test_only_the_rows_that_are_not_a_pass_carry_a_fix(xbox_session, doctor_run, monkeypatch):
    xbox_session()
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", 5)
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    lines = as_displayed(raw).splitlines()
    fixes = [index for index, line in enumerate(lines) if line.startswith("  To fix: ")]
    assert fixes
    for index in fixes:
        preceding = next(MARKER_RE.match(line) for line in reversed(lines[:index]) if MARKER_RE.match(line))
        assert preceding is not None and preceding.group(1) in ("WARN", "FAIL")


# One sentence and one link is the whole contract for the end of the report
def test_the_report_ends_with_one_summary_sentence_and_the_guide(xbox_session, doctor_run):
    xbox_session()
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    tail = [line for line in as_displayed(raw).strip().splitlines() if line.strip()]
    assert tail[-1].startswith("Guide: ")
    assert monitor.DOCTOR_GUIDE_URL in tail[-1]


@pytest.mark.parametrize("failures, warnings, sentence", [
    (0, 0, "All checks passed. You are good to go!"),
    (0, 2, "All critical checks passed with 2 warning(s). Review the warnings above."),
    (1, 0, "1 check(s) failed, 0 warning(s). Fix the failures above before relying on the tool."),
])
# The summary sentence is what a user reads first, so each count has to say what it means
def test_the_summary_says_what_the_counts_mean(failures, warnings, sentence):
    checks = [monitor.make_doctor_check("Environment", "FAIL", "f", "", actionable_advice())] * failures + [monitor.make_doctor_check("Environment", "WARN", "w", "", actionable_advice())] * warnings
    assert sentence in monitor.render_doctor_summary(checks)


# The whole promise of the preflight notice is that a diagnosis costs the user nothing
def test_the_doctor_writes_no_files(xbox_session, doctor_run, tmp_path):
    xbox_session()
    before = {path.name for path in tmp_path.iterdir()}
    doctor_run(xbox_gamertag=GAMERTAG)
    assert {path.name for path in tmp_path.iterdir()} == before


# The gate that stops the tool at startup and the row the report prints must use the same minimum
def test_an_unsupported_python_version_fails_against_the_shared_minimum():
    below = (monitor.MINIMUM_PYTHON_VERSION[0], monitor.MINIMUM_PYTHON_VERSION[1] - 1, 0)
    check = monitor.doctor_check_environment(version_info=below)[0]
    assert check.status == "FAIL"
    assert monitor.MINIMUM_PYTHON_VERSION_TEXT in check.detail


# A dependency the tool imports without a guard cannot be missing and still be a working install
def test_a_missing_required_dependency_fails():
    checks = monitor.doctor_check_environment(spec_finder=lambda name: None)
    required = [check for check in checks if "Required dependency" in check.label]
    assert len(required) == len(monitor.DOCTOR_REQUIRED_DEPENDENCIES)
    assert all(check.status == "FAIL" for check in required)
    assert all("pip" in check.advice.fix for check in required)


# A guarded import only removes one feature, so the row has to say which one rather than look like a failure
def test_a_missing_optional_dependency_warns_and_says_what_breaks(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")
    checks = monitor.doctor_check_environment(spec_finder=lambda name: None)
    optional = [check for check in checks if "Optional dependency" in check.label]
    assert len(optional) == len(monitor.DOCTOR_OPTIONAL_DEPENDENCIES)
    assert all(check.status == "WARN" for check in optional)
    assert all("Every other feature is unaffected" in check.detail for check in optional)


# A warning about a library that cannot affect this machine is noise the reader has to learn to ignore
@pytest.mark.parametrize("system, reported", [("Windows", True), ("Linux", False), ("Darwin", False)])
def test_a_platform_specific_dependency_is_only_reported_where_it_applies(monkeypatch, system, reported):
    monkeypatch.setattr(monitor.platform, "system", lambda: system)
    checks = monitor.doctor_check_environment(spec_finder=lambda name: None)
    assert any("colorama" in check.label for check in checks) is reported


# Every command the report prints has to match how this copy was installed
def test_the_install_method_is_stated_under_the_heading(monkeypatch):
    monkeypatch.setattr(monitor, "detect_install_method", lambda: "pipx")
    rendered = monitor.render_doctor_sections(monitor.DoctorReport())
    assert rendered.splitlines()[1] == "Detected install method: pipx"


# The most common support question is which files a run is actually reading
def test_the_configuration_and_dotenv_files_in_use_are_named(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")
    checks = monitor.doctor_check_configuration(config_path="/tmp/xbox.conf", env_path=str(env_path))
    assert "Path: /tmp/xbox.conf" in checks[0].detail
    assert checks[1].label == "Dotenv file loaded"
    assert f"Path: {env_path}" in checks[1].detail


# Verifies an explicitly selected missing dotenv file is reported as missing rather than loaded
def test_a_missing_dotenv_file_is_a_warning(tmp_path):
    missing = tmp_path / "missing.env"

    checks = monitor.doctor_check_configuration(env_path=str(missing))
    missing_check = next(check for check in checks if check.label == "The requested dotenv file was not found")

    assert missing_check.status == "WARN"
    assert missing_check.detail == f"Path: {missing}"
    assert missing_check.advice is not None
    assert "--env-file" in missing_check.advice.fix
    assert not any(check.label == "Dotenv file loaded" for check in checks)


# Running with no config file at all is a supported setup, not a problem to report
def test_no_configuration_file_is_a_working_setup():
    checks = monitor.doctor_check_configuration()
    assert checks[0].status == "PASS"
    assert checks[0].label == "No configuration file selected"


# Naming the source is what turns "it still uses the old key" into a one-line answer
def test_secrets_are_reported_by_name_and_source(monkeypatch):
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "client-id-value")
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "client-secret-value")
    monkeypatch.setitem(monitor.SECRET_SOURCES, "MS_APP_CLIENT_ID", "dotenv file")
    monkeypatch.setitem(monitor.SECRET_SOURCES, "MS_APP_CLIENT_SECRET", "environment")
    checks = monitor.doctor_secret_checks()
    reported = {check.label: check.detail for check in checks}
    assert reported["Secrets loaded from the dotenv file"] == "MS_APP_CLIENT_ID"
    assert reported["Secrets loaded from the environment"] == "MS_APP_CLIENT_SECRET"


# The value itself must never reach the report, however the secret was supplied
def test_a_secret_value_never_appears_in_the_report(monkeypatch):
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "a-very-secret-value")
    monkeypatch.setitem(monitor.SECRET_SOURCES, "MS_APP_CLIENT_SECRET", "dotenv file")
    rendered = "\n".join(check.label + check.detail for check in monitor.doctor_secret_checks())
    assert "a-very-secret-value" not in rendered
    assert "MS_APP_CLIENT_SECRET" in rendered


# A fresh install has no secrets and saying so is more useful than printing nothing
def test_a_run_with_no_secrets_says_so(monkeypatch):
    for key in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, key, "")
    checks = monitor.doctor_secret_checks()
    assert len(checks) == 1
    assert checks[0].label == "No secrets loaded"


# An interval below the safe floor gets the account rate limited, which looks like the tool being broken
def test_a_rate_limiting_interval_is_warned_about(monkeypatch):
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", 5)
    check = check_labelled(monitor.DoctorReport(checks=monitor.doctor_check_configuration()), "Check intervals are short")
    assert check.status == "WARN"
    assert str(monitor.DOCTOR_MIN_SAFE_ACTIVE_INTERVAL) in check.advice.fix


# Turning verification off is a deliberate choice for one network and it must never pass unremarked
def test_disabled_tls_verification_is_warned_about(monkeypatch):
    monkeypatch.setattr(monitor, "VERIFY_SSL", False)
    check = check_labelled(monitor.DoctorReport(checks=monitor.doctor_check_configuration()), "TLS certificate verification is off")
    assert check.status == "WARN"
    assert check.advice.code == "config.insecure"


# A file the tool cannot write is a failure the user should learn about before a status change is lost
def test_an_unwritable_csv_path_fails_with_its_path(monkeypatch, tmp_path):
    blocked = tmp_path / "missing-directory" / "history.csv"
    monkeypatch.setattr(monitor, "CSV_FILE", str(blocked))
    check = check_labelled(monitor.DoctorReport(checks=monitor.doctor_check_configuration()), "CSV destination")
    assert check.status == "FAIL"
    assert str(blocked) in check.label


# The status file is how a restart resumes, so the report has to name the exact path it would use
def test_the_report_names_the_status_file(monkeypatch, tmp_path):
    checks = monitor.doctor_check_configuration(xbox_gamertag=GAMERTAG)
    check = check_labelled(monitor.DoctorReport(checks=checks), "Status destination appears writable")
    assert monitor.resolve_status_file(GAMERTAG) in check.detail


# Without application credentials there is nothing to sign in with, so no call should be attempted
def test_missing_credentials_are_reported_before_any_call(monkeypatch):
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "")
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "")
    monkeypatch.setattr(monitor, "create_signed_session", _unreachable_smtp)
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), GAMERTAG))
    auth = checks_in(monitor.DoctorReport(checks=checks), "Authentication")
    assert [check.status for check in auth] == ["FAIL"]
    assert auth[0].advice.code == "secret.missing"


# A first run has no token cache yet, which is a normal state the sign-in flow fixes rather than a failure
def test_a_missing_token_cache_warns_with_the_command_that_creates_it(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "client-id-value")
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "client-secret-value")
    monkeypatch.setattr(monitor, "create_signed_session", _unreachable_smtp)
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), GAMERTAG))
    check = check_labelled(monitor.DoctorReport(checks=checks), "No saved Xbox tokens were found")
    assert check.status == "WARN"
    assert check.advice.code == "auth.token_cache"


# A cache other accounts can read holds a live refresh token, so it must be called out with its own fix
@pytest.mark.skipif(monitor.os.name != "posix", reason="File modes are only meaningful on POSIX")
def test_a_world_readable_token_cache_is_warned_about(xbox_session, monkeypatch):
    xbox_session()
    monitor.Path(monitor.MS_AUTH_TOKENS_FILE).chmod(0o644)
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), GAMERTAG))
    check = check_labelled(monitor.DoctorReport(checks=checks), "The Xbox token cache is readable by other accounts")
    assert check.status == "WARN"
    assert "chmod 600" in check.advice.fix


# A real run answers an unreadable cache by starting an interactive sign-in, which the doctor must never do
def test_an_unreadable_token_cache_is_diagnosed_rather_than_reauthorized(xbox_session, monkeypatch):
    xbox_session()
    # The session fixture stubs the refresh, so the real one is put back to exercise the parse it performs
    monkeypatch.undo()
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "client-id-value")
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_SECRET", "client-secret-value")
    monitor.Path(monitor.MS_AUTH_TOKENS_FILE).write_text("not a token response", encoding="utf-8")
    monkeypatch.setattr(monitor, "create_signed_session", lambda: _FakeClosableSession())
    monkeypatch.setattr(monitor, "AuthenticationManager", lambda *args: object())
    monkeypatch.setattr(monitor, "oauth_interactive_auth", _unreachable_smtp)
    monkeypatch.setattr(monitor, "refresh_tokens_with_retry", _unreachable_smtp)
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), GAMERTAG))
    check = check_labelled(monitor.DoctorReport(checks=checks), "The Xbox token cache '")
    assert check.status == "FAIL"
    assert check.advice.code == "auth.token_cache"


# Expired credentials are the single most common cause of a run that stops reporting
def test_a_rejected_refresh_is_reported_with_its_fix(xbox_session):
    xbox_session(refresh_error=monitor.httpx.HTTPStatusError("invalid_grant", request=monitor.httpx.Request("POST", "https://login.live.com/"), response=monitor.httpx.Response(400)))
    report = monitor.DoctorReport()
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(report, GAMERTAG))
    check = check_labelled(monitor.DoctorReport(checks=checks), "The Microsoft sign-in endpoint")
    assert check.status == "FAIL"
    assert report.authenticated is False


# A working sign-in has to say that nothing was written, because that is the promise the notice made
def test_a_working_sign_in_reports_that_nothing_was_written(xbox_session):
    xbox_session()
    report = monitor.DoctorReport()
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(report, GAMERTAG))
    check = check_labelled(monitor.DoctorReport(checks=checks), "Xbox Live accepted the saved tokens")
    assert report.authenticated is True
    assert "nothing was written" in check.detail


# Reporting the target as broken when the sign-in never happened turns one problem into two
def test_the_target_is_skipped_when_authentication_failed(xbox_session):
    xbox_session(refresh_error=RuntimeError("no"))
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), GAMERTAG))
    target = checks_in(monitor.DoctorReport(checks=checks), "Target")
    assert [check.status for check in target] == ["SKIP"]


# A doctor run with no gamertag warns rather than fails, so a credentials-only run still exits clean
def test_a_missing_gamertag_warns_on_the_target(xbox_session):
    xbox_session()
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), None))
    target = checks_in(monitor.DoctorReport(checks=checks), "Target")
    assert [check.status for check in target] == ["WARN"]
    assert target[0].detail == "Nothing will be monitored until one is given"
    assert target[0].advice.code == "target.missing"
    assert monitor.XBOX_TARGET_FORMS in target[0].advice.fix


# A profile that hides its activity is a privacy setting on the monitored account, not a broken setup
def test_a_hidden_profile_is_reported_with_the_privacy_steps(xbox_session):
    xbox_session(lookup_error=monitor.httpx.HTTPStatusError("forbidden", request=monitor.httpx.Request("GET", "https://profile.xboxlive.com/"), response=monitor.httpx.Response(403)))
    checks = monitor.asyncio.run(monitor.doctor_check_xbox_live(monitor.DoctorReport(), GAMERTAG))
    target = checks_in(monitor.DoctorReport(checks=checks), "Target")
    assert target[0].status == "FAIL"
    assert target[0].advice.code == "target.not_visible"


# A fresh install has no SMTP settings and an error alert alone must not make it look configured
def test_a_fresh_install_reports_email_as_disabled(monkeypatch):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    checks = monitor.doctor_check_email_notifications(monitor.DoctorReport())
    assert [check.status for check in checks] == ["PASS"]
    assert checks[0].label == "Email notifications are disabled"
    assert checks[0].detail == "No SMTP connection was attempted and no email was sent"


# Alerts that are on but cannot be delivered are the failure mode a user never notices on their own
def test_enabled_alerts_with_broken_settings_warn(monkeypatch):
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SMTP_HOST", "not a host")
    checks = monitor.doctor_check_email_notifications(monitor.DoctorReport())
    assert checks[0].status == "WARN"
    assert checks[0].advice is not None
    assert checks[0].advice.code == "smtp.invalid"


# Reporting the channel ready without signing in would pass a setup that cannot deliver anything
def test_the_email_check_signs_in_before_reporting_ready(monkeypatch):
    enable_email(monkeypatch)
    attempts = []
    monkeypatch.setattr(monitor, "smtp_sign_in", lambda password, timeout=15: attempts.append(timeout) or monitor.SMTP_USER)
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_email_notifications(report)
    assert attempts == [monitor.DOCTOR_SMTP_TIMEOUT]
    assert checks[0].status == "PASS"
    assert checks[0].label == monitor.SMTP_READY_CHECK_LABEL
    assert report.email_ready is True


# A rejected login is a credential problem with its own fix, not a generic connection failure
def test_a_rejected_sign_in_fails_the_email_row(monkeypatch):
    enable_email(monkeypatch)

    def reject(password, timeout=15):
        raise monitor.RecoveryError(monitor.classify_recovery_error(monitor.smtplib.SMTPAuthenticationError(535, b"bad"), context="smtp", detail="rejected"))

    monkeypatch.setattr(monitor, "smtp_sign_in", reject)
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_email_notifications(report)
    assert checks[0].status == "FAIL"
    assert checks[0].advice is not None
    assert checks[0].advice.code == "smtp.authentication"
    assert report.email_ready is False


# A password that is still the shipped placeholder cannot sign in, so opening a connection would only stall
def test_missing_smtp_credentials_warn_without_connecting(monkeypatch):
    enable_email(monkeypatch)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "your_smtp_password")
    monkeypatch.setattr(monitor, "smtp_sign_in", _unreachable_smtp)
    checks = monitor.doctor_check_email_notifications(monitor.DoctorReport())
    assert checks[0].status == "WARN"
    assert checks[0].label == monitor.EMAIL_UNUSABLE_CHECK_LABEL
    assert checks[0].detail == "SMTP_PASSWORD is empty or still set to its placeholder"
    assert checks[0].advice is not None
    assert "Set SMTP_PASSWORD with" in checks[0].advice.fix
    assert monitor.SMTP_GUIDE_URL in checks[0].advice.fix


# The report has to say what it found before any real message is offered, let alone sent
def test_delivery_tests_are_offered_after_the_report_and_before_the_summary(xbox_session, doctor_run, monkeypatch, smtp_sign_in_ok):
    xbox_session()
    enable_email(monkeypatch)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "n")
    _, raw = doctor_run(xbox_gamertag=GAMERTAG)
    displayed = as_displayed(raw)
    assert displayed.index("Doctor\nDetected install method:") < displayed.index(monitor.DOCTOR_DELIVERY_SECTION)
    assert displayed.index(monitor.DOCTOR_DELIVERY_SECTION) < displayed.index("\nSummary\n")


# Declining has to mean nothing is sent or the approval prompt is not an approval
def test_a_declined_delivery_test_sends_nothing(monkeypatch, smtp_sign_in_ok):
    enable_email(monkeypatch)
    monkeypatch.setattr(monitor, "send_email", _unreachable_smtp)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "n")
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(monitor.sys, "stdout", FakeTerminal())
    offered = monitor.offer_doctor_delivery_tests(monitor.DoctorReport(email_ready=True))
    assert [check.status for check in offered] == ["SKIP"]


# One approval must send exactly one message and its result has to reach the summary
def test_an_approved_delivery_test_sends_one_message(monkeypatch, smtp_sign_in_ok):
    enable_email(monkeypatch)
    sent = []
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: sent.append(args[0]) or 0)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "y")
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(monitor.sys, "stdout", FakeTerminal())
    report = monitor.DoctorReport(email_ready=True)
    offered = monitor.offer_doctor_delivery_tests(report)
    assert len(sent) == 1
    assert [check.status for check in offered] == ["PASS"]
    assert offered[0] in report.checks


# The delivery rows have to print the same label and detail the sibling tools print or the wording has drifted
def test_the_delivery_rows_print_the_shared_label_and_detail(monkeypatch, smtp_sign_in_ok):
    enable_email(monkeypatch)
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "send_webhook", _unreachable_webhook)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "n" if "webhook" in prompt else "y")
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal())
    stdout = FakeTerminal()
    monkeypatch.setattr(monitor.sys, "stdout", stdout)

    monitor.offer_doctor_delivery_tests(monitor.DoctorReport(email_ready=True, webhook_ready=True))
    output = "".join(stdout.chunks)
    provider = monitor.webhook_provider_display_name()

    assert monitor.DOCTOR_DELIVERY_SECTION in output
    assert "[PASS] Doctor test email delivered" in output
    assert "  One real test email was sent after confirmation" in output
    assert f"[SKIP] Test webhook through {provider} was not sent" in output
    assert "  You declined the real delivery test. Run doctor again and approve the webhook test when ready" in output


# A fresh install has no webhook destination and an error alert alone must not make it look configured
def test_a_fresh_install_reports_webhooks_as_disabled(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    checks = monitor.doctor_check_webhook_notifications(monitor.DoctorReport())
    assert [check.status for check in checks] == ["PASS"]
    assert checks[0].label == "Webhook alerts are disabled"
    # The label says everything, so the row carries no detail that only repeats it
    assert checks[0].detail == ""


# Alerts chosen while the channel is off would never be delivered, which nothing else in the report would say
def test_selected_webhook_alerts_with_the_channel_off_warn(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    checks = monitor.doctor_check_webhook_notifications(monitor.DoctorReport())
    assert checks[0].status == "WARN"
    assert checks[0].advice is not None
    assert checks[0].advice.code == "webhook.invalid"


# A channel with no alert type selected is switched on but silent
def test_a_webhook_channel_with_no_alert_selected_warns(monkeypatch):
    enable_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", False)
    checks = monitor.doctor_check_webhook_notifications(monitor.DoctorReport())
    assert checks[0].status == "WARN"
    assert checks[0].label == "Webhook alerts are on but no alert types are selected"


# Each unusable setting has to be named on its own, since the user can only correct the one that is wrong
@pytest.mark.parametrize("setting, value", [
    ("WEBHOOK_PROVIDER", "slack"),
    ("WEBHOOK_URL", "your_webhook_url"),
    ("WEBHOOK_AVATAR_URL", "not-a-url"),
    ("WEBHOOK_HEADERS", {"Bad Header": "value"}),
])
def test_an_unusable_webhook_setting_fails_with_its_fix(monkeypatch, setting, value):
    enable_webhook(monkeypatch)
    monkeypatch.setattr(monitor, setting, value)
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_webhook_notifications(report)
    assert checks[0].status == "FAIL"
    assert checks[0].advice is not None
    assert checks[0].advice.code.startswith("webhook.")
    assert report.webhook_ready is False


# A passive check must not publish anything and must not print the private destination it validated
def test_the_webhook_check_sends_nothing_and_hides_the_link(monkeypatch):
    enable_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "send_webhook", _unreachable_smtp)
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_webhook_notifications(report)
    assert checks[0].status == "PASS"
    assert checks[0].label.startswith(monitor.WEBHOOK_READY_CHECK_LABEL)
    assert report.webhook_ready is True
    assert WEBHOOK_URL not in f"{checks[0].label} {checks[0].detail}"


# One approval must publish exactly one notification and its result has to reach the summary
def test_an_approved_webhook_test_sends_one_notification(monkeypatch):
    enable_webhook(monkeypatch)
    sent = []
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: sent.append(args[0]) or 0)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "y")
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(monitor.sys, "stdout", FakeTerminal())
    report = monitor.DoctorReport(webhook_ready=True)
    offered = monitor.offer_doctor_delivery_tests(report)
    assert len(sent) == 1
    assert [check.status for check in offered] == ["PASS"]
    assert offered[0] in report.checks


# Declining has to mean nothing is published or the approval prompt is not an approval
def test_a_declined_webhook_test_publishes_nothing(monkeypatch):
    enable_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "send_webhook", _unreachable_smtp)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "n")
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(monitor.sys, "stdout", FakeTerminal())
    offered = monitor.offer_doctor_delivery_tests(monitor.DoctorReport(webhook_ready=True))
    assert [check.status for check in offered] == ["SKIP"]


# There is nobody to approve a real message on a redirected run
def test_no_delivery_test_is_offered_without_a_terminal(monkeypatch):
    monkeypatch.setattr(monitor, "send_email", _unreachable_smtp)
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal(interactive=False))
    monkeypatch.setattr(monitor.sys, "stdout", FakeTerminal(interactive=False))
    assert monitor.offer_doctor_delivery_tests(monitor.DoctorReport(email_ready=True)) == []


# A healthy setup has to exit zero or the doctor cannot be used in a script
def test_a_healthy_setup_exits_zero(xbox_session, doctor_run):
    xbox_session()
    code, raw = doctor_run(xbox_gamertag=GAMERTAG)
    assert code == 0
    assert "All checks passed" in as_displayed(raw)


# Warnings describe a working setup, so only a real failure may change the exit code
def test_only_a_failure_changes_the_exit_code(xbox_session, doctor_run, monkeypatch):
    xbox_session()
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", 5)
    warned, raw = doctor_run(xbox_gamertag=GAMERTAG)
    assert warned == 0
    assert "All critical checks passed" in as_displayed(raw)
    monkeypatch.setattr(monitor, "CSV_FILE", "/no-such-directory/history.csv")
    failed, _ = doctor_run(xbox_gamertag=GAMERTAG)
    assert failed == 1


# Runs main() with the given arguments and returns the exit code it chose
def run_main(monkeypatch, arguments):
    monkeypatch.setattr(monitor.sys, "argv", ["xbox_monitor", *map(str, arguments)])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)
    with pytest.raises(SystemExit) as exit_info:
        monitor.main()
    return exit_info.value.code


# A configuration file that cannot be loaded is the problem the report exists to name, not a reason to stop
def test_a_broken_configuration_file_is_reported_not_fatal(xbox_session, monkeypatch, capsys, tmp_path):
    xbox_session()
    broken = tmp_path / "broken.conf"
    broken.write_text("XBOX_CHECK_INTERVAL = os.system('id')\n", encoding="utf-8")
    code = run_main(monkeypatch, [GAMERTAG, "--doctor", "--config-file", str(broken), "--env-file", "none"])
    output = capsys.readouterr().out
    assert code == 1
    assert "[FAIL] Config file" in output
    # The rest of the report still ran, which is the point of not exiting on the first problem
    assert "Authentication" in output and "Summary" in output


# The report still has to stamp its own timestamps, so a bad timezone becomes a row and a fallback
def test_an_invalid_timezone_is_reported_not_fatal(xbox_session, monkeypatch, capsys):
    xbox_session()
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")
    code = run_main(monkeypatch, [GAMERTAG, "--doctor", "--env-file", "none"])
    output = capsys.readouterr().out
    assert code == 1
    assert "[FAIL] Local timezone is invalid\n  Time zone: Mars/Olympus_Mons" in output
    assert "Notifications" in output


# Monitoring cannot timestamp anything without a valid timezone, so a normal run still stops
def test_an_invalid_timezone_still_stops_a_normal_run(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")
    code = run_main(monkeypatch, [GAMERTAG, "--env-file", "none"])
    assert code == 1
    assert "is not valid" in capsys.readouterr().out


# Doctor is the one path that must not open a connection before it has reported what it found
def test_the_doctor_never_reaches_the_connectivity_gate_that_stops_a_normal_run(xbox_session, monkeypatch, capsys):
    xbox_session()

    def refuse(*args, **kwargs):
        raise AssertionError("Doctor must run its own connectivity check, not the startup gate")

    monkeypatch.setattr(monitor.sys, "argv", ["xbox_monitor", GAMERTAG, "--doctor", "--env-file", "none"])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: None)
    monkeypatch.setattr(monitor, "check_internet", refuse)
    with pytest.raises(SystemExit):
        monitor.main()
    assert "Summary" in capsys.readouterr().out


# Verifies the Python row states the minimum it was judged against, whichever way the judgement went
def test_the_python_row_names_the_minimum_supported_version():
    below = (monitor.MINIMUM_PYTHON_VERSION[0], monitor.MINIMUM_PYTHON_VERSION[1] - 1, 0)

    supported = monitor.doctor_check_environment()[0]
    unsupported = monitor.doctor_check_environment(version_info=below)[0]

    assert supported.detail == f"Minimum supported version: {monitor.MINIMUM_PYTHON_VERSION_TEXT}"
    assert unsupported.detail == supported.detail


# Verifies settings that are merely valid take no row, since a value that is fine is not a finding
def test_valid_intervals_and_separators_take_no_row():
    labels = [check.label for check in monitor.doctor_check_configuration()]

    assert "Check intervals are set" not in labels
    assert not any(label.startswith("ASCII log separators") for label in labels)


# Verifies every doctor detail keeps to the agreed shapes: it never repeats its label, gives an instruction or joins values with a pipe
def test_doctor_details_keep_to_the_agreed_shapes():
    import ast
    import inspect

    # Renders one detail argument as text, standing in {} for the parts an f-string fills at runtime
    def detail_text(node):
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return "".join(part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}" for part in node.values)
        return None

    offenders = []
    for node in ast.walk(ast.parse(inspect.getsource(monitor))):
        if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"make_doctor_check", "report.add"} or len(node.args) < 4:
            continue
        label, text = node.args[2], detail_text(node.args[3])
        if text is None:
            continue
        if isinstance(label, ast.Constant) and text == label.value:
            offenders.append(f"{node.lineno}: the detail repeats its label")
        if text.startswith(("Use ", "Set ", "Run ")):
            offenders.append(f"{node.lineno}: the detail gives an instruction, which belongs in the fix line")
        if " | " in text:
            offenders.append(f"{node.lineno}: the detail joins two values with a pipe")
        if text.endswith("."):
            offenders.append(f"{node.lineno}: the detail ends with a full stop")

    assert not offenders, "doctor details outside the agreed shapes:\n" + "\n".join(offenders)


# Verifies the resolved time zone is reported as a named value rather than a bare string
def test_the_timezone_row_names_the_value(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Europe/Warsaw")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE_STATE", "config")

    checks = monitor.doctor_check_configuration()

    check = next(item for item in checks if item.label == monitor.TIMEZONE_CHECK_LABELS["config"])
    assert check.detail == "Time zone: Europe/Warsaw"


# Verifies the constructor drops a detail that only repeats its label, so no row says the same thing twice
def test_a_detail_that_repeats_its_label_is_dropped():
    check = monitor.make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Output logging is disabled")

    assert check.detail == ""


# Verifies only the four shared markers can reach a report
def test_an_actionable_row_is_rejected_without_a_fix():
    for status in ("WARN", "FAIL"):
        with pytest.raises(ValueError):
            monitor.make_doctor_check("Configuration", status, "a label", "some detail")

    assert monitor.make_doctor_check("Configuration", "SKIP", "a label").status == "SKIP"


# Verifies only the four shared markers can reach a report
def test_only_the_four_shared_markers_are_accepted():
    assert monitor.DOCTOR_STATUSES == MARKERS
    assert [monitor.make_doctor_check("Configuration", status, "a label", "", actionable_advice()).status for status in MARKERS] == list(MARKERS)

    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "INFO", "a label")


# Verifies one row reads as one block: the action lines sit under the marker at the detail indent while a pass row has none
def test_the_action_lines_sit_indented_under_their_marker(monkeypatch):
    monkeypatch.setattr(monitor, "colorize", lambda theme, text: text)
    advice = monitor.make_recovery_advice("unknown", "a summary", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), True)
    report = monitor.DoctorReport([
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice),
        monitor.make_doctor_check("Configuration", "PASS", "a passing row", "", advice),
    ])

    lines = monitor.render_doctor_sections(report).splitlines()
    rows = lines[lines.index("[WARN] a warning row"):]

    assert rows[:5] == ["[WARN] a warning row", "  a detail worth keeping", "  To fix: do the thing", f"  Guide: {monitor.DOCTOR_GUIDE_URL}", "[PASS] a passing row"]


# Verifies an approved delivery test that failed reaches the summary, so a failing run cannot report a clean one
def test_a_failed_delivery_test_reaches_the_summary(monkeypatch):
    terminal = FakeTerminal(True)
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    monkeypatch.setattr(monitor.sys, "stdin", terminal)
    monkeypatch.setattr(monitor, "ask_yes_no", lambda question: True)
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 1)
    report = monitor.DoctorReport(email_ready=True)

    monitor.offer_doctor_delivery_tests(report)

    assert [(check.section, check.status, check.label) for check in report.checks] == [(monitor.DOCTOR_DELIVERY_SECTION, "FAIL", "Doctor test email delivery failed")]
    assert "1 check(s) failed, 0 warning(s)." in monitor.render_doctor_summary(report.checks)


# Verifies a failed delivery test fails the whole run, so the exit code and the last sentence agree
def test_a_failed_delivery_test_changes_the_exit_code(xbox_session, doctor_run, monkeypatch, smtp_sign_in_ok):
    xbox_session()
    enable_email(monkeypatch)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: "y")
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 1)

    code, raw = doctor_run(xbox_gamertag=GAMERTAG)

    displayed = as_displayed(raw)
    assert code == 1
    assert "[FAIL] Doctor test email delivery failed" in displayed
    assert "1 check(s) failed" in displayed
    assert "All checks passed" not in displayed


# Verifies every doctor entry point renders its summary after the delivery tests, so the sentence and the exit code describe one run
def test_the_summary_is_rendered_after_the_delivery_tests():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(monitor))
    checked = 0
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        calls = [(call.lineno, ast.unparse(call.func)) for call in ast.walk(function) if isinstance(call, ast.Call)]
        offers = [lineno for lineno, name in calls if name.endswith("offer_doctor_delivery_tests")]
        summaries = [lineno for lineno, name in calls if name.endswith("render_doctor_summary")]
        if not offers or not summaries:
            continue
        checked += 1
        assert max(offers) < min(summaries), f"{function.name} renders the summary before the delivery tests"

    assert checked, "no doctor entry point runs the delivery tests and then the summary"


# Verifies the connectivity row carries the label and the endpoint detail shared with the sibling monitors
def test_the_connectivity_row_names_the_shared_endpoint(monkeypatch):
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://probe.example/ping")

    class FakeClient:
        def __init__(self, fails):
            self.fails = fails

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            if self.fails:
                raise monitor.httpx.ConnectError("offline for doctor")

    monkeypatch.setattr(monitor.httpx, "Client", lambda **kwargs: FakeClient(False))
    passing = REAL_CONNECTIVITY_CHECK()[0]
    monkeypatch.setattr(monitor.httpx, "Client", lambda **kwargs: FakeClient(True))
    failing = REAL_CONNECTIVITY_CHECK()[0]

    assert (passing.status, passing.label, passing.detail) == ("PASS", "The connectivity endpoint is reachable", "Endpoint: https://probe.example/ping")
    assert (failing.status, failing.label, failing.detail) == ("FAIL", "The connectivity endpoint could not be reached", "Endpoint: https://probe.example/ping")
    # The row carries no guide, because no page covers this check and the report ends with the doctor link
    assert failing.advice is not None and failing.advice.fix == "Check network, DNS, proxy and CHECK_INTERNET_URL settings"


# Verifies the output rows wait for the target instead of checking a placeholder path that is never written
def test_the_output_rows_wait_for_a_target(doctor_run, monkeypatch):
    monkeypatch.setattr(monitor, "XBOX_STATUS_FILE", "")
    monkeypatch.setattr(monitor, "XBOX_LOGFILE", "xbox_monitor")
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)

    _, without_target = doctor_run()
    _, with_target = doctor_run(xbox_gamertag=GAMERTAG)

    assert "[PASS] Status file will be finalized after a target is selected" in without_target
    assert "[PASS] Log destination will be finalized after a target is selected" in without_target
    assert "Path: xbox_<xbox_gamertag>_last_status.json" not in without_target
    assert "Path: xbox_monitor_<xbox_gamertag>.log" not in without_target
    assert "[PASS] Status destination appears writable" in with_target
    assert "[PASS] Log destination appears writable" in with_target


# Verifies a report read on its own ends with the command that starts monitoring, carrying this run's files
def test_the_report_ends_with_the_command_that_starts_monitoring(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/xbox.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/xbox.env")

    monitor.print_doctor_next_steps(doctor_exit=0)

    transcript = capsys.readouterr().out
    assert "Next steps" in transcript
    assert "Start monitoring:" in transcript
    # Nothing supplies a target here, so the command keeps the placeholder rather than printing one that cannot run
    assert "xbox_monitor.py <xbox_gamertag> --config-file /etc/xbox.conf --env-file /etc/xbox.env" in transcript
    assert transcript.rstrip().endswith(monitor.QUICK_START_GUIDE_URL)


# Verifies a failing report names the order to work in, rather than inviting a run that cannot succeed yet
def test_a_failing_report_asks_for_the_failures_first(capsys):
    monitor.print_doctor_next_steps(doctor_exit=1)

    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies a target the command line named is carried, so the printed command watches the account just checked
def test_a_command_line_target_is_carried_into_the_command(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")

    monitor.print_doctor_next_steps("someone", doctor_exit=0)

    assert "xbox_monitor.py someone" in capsys.readouterr().out


# Verifies the row names the state the shared resolver settled on, so it says what a restart would say
def test_the_timezone_row_follows_the_shared_resolver(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE_STATE", "config")

    advice = monitor.resolve_local_timezone()

    assert monitor.LOCAL_TIMEZONE_STATE == "invalid"
    row = next(item for item in monitor.doctor_check_configuration(timezone_advice=advice) if item.label in monitor.TIMEZONE_CHECK_LABELS.values())
    assert (row.status, row.label, row.detail) == ("FAIL", "Local timezone is invalid", "Time zone: Mars/Olympus_Mons")


# Verifies Ctrl+C at a delivery prompt ends the run instead of declining one test and asking the next
def test_a_delivery_prompt_interrupt_ends_the_run(monkeypatch):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    # The handler restores the saved stream, so it is pointed at the one this test captures
    monkeypatch.setattr(monitor, "stdout_bck", monitor.sys.stdout)
    monkeypatch.setattr("builtins.input", interrupt)

    with pytest.raises(SystemExit) as raised:
        monitor.ask_yes_no("Send one test")

    assert raised.value.code == 0


# Verifies a closed input at a delivery prompt says the test was skipped rather than ending on a bare newline
def test_a_closed_delivery_prompt_says_the_test_was_skipped(monkeypatch, capsys):
    def closed(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", closed)

    assert monitor.ask_yes_no("Send one test") is False
    assert "Delivery test skipped." in capsys.readouterr().out


# Verifies every unusable timing or count setting is named in one row, so a fix does not need one run per setting
def test_invalid_numeric_settings_are_reported_in_one_row(monkeypatch):
    monkeypatch.setattr(monitor, "XBOX_CHECK_INTERVAL", 0)
    monkeypatch.setattr(monitor, "TOKEN_REFRESH_RETRIES", 0)
    monkeypatch.setattr(monitor, "SMTP_PORT", 70000)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "One or more numeric settings are invalid"]

    assert [item.status for item in rows] == ["FAIL"]
    assert all(name in rows[0].detail for name in ("XBOX_CHECK_INTERVAL", "TOKEN_REFRESH_RETRIES", "SMTP_PORT"))


# Verifies a quoted interval is reported as an unusable setting, since comparing it against the safe floor used to raise
def test_an_interval_that_is_not_a_number_is_reported_rather_than_raised(monkeypatch):
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", "3600")

    labels = [item.label for item in monitor.doctor_check_configuration()]

    assert "One or more numeric settings are invalid" in labels
    assert "Check intervals are short" not in labels


# Verifies configured mail settings with no alert types selected warn, since nothing would ever be emailed
def test_email_configured_but_nothing_selected_warns(monkeypatch):
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "GAME_CHANGE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "STATUS_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "private-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "monitor@example.test")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "alerts@example.test")
    monkeypatch.setattr(monitor, "smtp_sign_in", Mock(side_effect=AssertionError("SMTP was contacted")))
    report = monitor.DoctorReport()

    check = monitor.doctor_check_email_notifications(report)[0]

    assert (check.status, check.label) == ("WARN", "Email is configured but no alert types are selected")
    assert check.detail == "Nothing would ever be emailed"
    assert check.advice is not None and check.advice.code == "smtp.invalid"
    assert report.email_ready is False


# Verifies webhook alert types selected while the channel is off warn with the wording every sibling uses
def test_webhook_alerts_selected_but_switched_off_warn(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)

    check = monitor.doctor_check_webhook_notifications(monitor.DoctorReport())[0]

    assert (check.status, check.label) == ("WARN", "Webhook alert types are selected but webhooks are switched off")
    assert check.advice is not None and "WEBHOOK_ENABLED" in check.advice.fix


# The sanitizing terminal wrapper strips a bare carriage return, so progress has to reach the real terminal beneath it
def test_the_progress_line_reaches_the_terminal_under_the_sanitizing_wrapper(monkeypatch):
    terminal = FakeTerminal()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(terminal))
    monkeypatch.setattr(monitor, "DOCTOR_PROGRESS_WIDTH", 0)

    monitor.doctor_progress("environment")

    assert "".join(terminal.chunks) == "\r* Checking environment ..."


# Two results printed after the last question read as one block that answers neither, so each sits under its own
def test_a_delivery_result_is_printed_under_its_own_question(monkeypatch, smtp_sign_in_ok):
    enable_email(monkeypatch)
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal())
    stdout = FakeTerminal()
    monkeypatch.setattr(monitor.sys, "stdout", stdout)
    monkeypatch.setattr(monitor, "read_interactively", lambda prompt_fn, prompt: stdout.write(prompt) and "y")

    monitor.offer_doctor_delivery_tests(monitor.DoctorReport(email_ready=True, webhook_ready=True))
    output = "".join(stdout.chunks)

    assert output.index("[PASS] Doctor test email delivered") < output.index("Send one test webhook")


# Two labelled values crammed into one detail read as one value, and the handle rule coloured the whole run
def test_the_target_row_separates_the_gamertag_from_the_xuid(monkeypatch, tmp_path):
    from test_xbox_boundary_flows import setup_xbox_transport
    setup_xbox_transport(monkeypatch, tmp_path, "normal")

    # Builds the target row through real authentication and profile models
    async def check_target():
        async with monitor.create_signed_session() as session:
            auth = monitor.AuthenticationManager(session, monitor.MS_APP_CLIENT_ID, monitor.MS_APP_CLIENT_SECRET, "")
            await monitor.doctor_refresh_tokens(auth)
            return (await monitor.doctor_check_target(auth, GAMERTAG))[0]

    check = monitor.asyncio.run(check_target())
    assert (check.status, check.label, check.detail) == ("PASS", f"Gamertag {GAMERTAG} was found and activity is accessible", "XUID: 1234")


# One row shape and one advice shape across the family: the advice rides on the row and its fix carries the
# guide, so a row or an advice copied from a sibling means the same thing here
def test_the_doctor_row_and_its_advice_share_one_contract():
    row_parameters = list(inspect.signature(monitor.make_doctor_check).parameters.values())
    advice_parameters = list(inspect.signature(monitor.make_recovery_advice).parameters.values())

    assert [parameter.name for parameter in row_parameters] == ["section", "status", "label", "detail", "advice"]
    assert [parameter.default for parameter in row_parameters[3:]] == ["", None]
    assert [parameter.name for parameter in advice_parameters] == ["code", "summary", "fix", "retryable", "detail"]
    assert monitor.recovery_fix_with_guide("do the thing", "https://example.invalid/page") == "do the thing\nGuide: https://example.invalid/page"


# A non-pass row is refused without advice and keeps the advice it was given, which is where its fix and guide live
def test_a_row_carries_its_advice_and_refuses_to_go_without():
    advice = monitor.make_recovery_advice("config.invalid", "a warning row", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), False)

    row = monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice)

    assert row.advice is advice
    assert not hasattr(advice, "guide_url")
    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping")


# A string such as "false" counts as on, so an on/off setting holding anything but True or False is named in one row
def test_invalid_boolean_settings_are_reported_in_one_row(monkeypatch):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", "false", raising=False)
    monkeypatch.setattr(monitor, "SMTP_SSL", 1, raising=False)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "One or more on/off settings are invalid"]

    assert [item.status for item in rows] == ["FAIL"]
    assert "ERROR_NOTIFICATION must be True or False, not 'false'" in rows[0].detail
    assert "SMTP_SSL must be True or False, not 1" in rows[0].detail
    assert rows[0].advice.fix.startswith("Set the reported settings to True or False")


# An on/off setting written as 0 or 1 was accepted before the values were checked, so it still reads as off and on
def test_a_numeric_on_off_setting_is_read_as_a_boolean():
    parsed = monitor.parse_config_content("VERIFY_SSL = 0\nDISABLE_LOGGING = 1\n")

    assert parsed == {"VERIFY_SSL": False, "DISABLE_LOGGING": True}
    assert all(isinstance(value, bool) for value in parsed.values())


# The shipped defaults are all real booleans, so a run with nothing overridden never sees the on/off row
def test_the_shipped_defaults_pass_the_boolean_check():
    assert monitor.runtime_boolean_errors() == []


# Doctor runs before the summary reports an unavailable selected channel
def test_the_unusable_webhook_gate_runs_after_doctor_in_the_family_wording():
    source = inspect.getsource(monitor)
    assert source.index("if doctor_mode:") < source.index("emit_startup_summary(build_startup_summary(")
