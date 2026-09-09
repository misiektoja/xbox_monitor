"""Tests for the recovery taxonomy: which category a failure lands in and what the user is told to do next.

The category decides the fix paragraph, whether a retry is worth waiting for and whether an error email fires,
so each test pins one failure a user can actually hit.
"""

import ast
import re
import smtplib
import socket
import ssl
from pathlib import Path

import pytest

import xbox_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "xbox_monitor.py").read_text(encoding="utf-8")


# Builds an httpx error carrying the given status, the shape every Xbox Live and Microsoft failure arrives in
def http_error(status, url="https://profile.xboxlive.com/users"):
    request = monitor.httpx.Request("GET", url)
    return monitor.httpx.HTTPStatusError(f"{status}", request=request, response=monitor.httpx.Response(status, request=request))


# A code outside the taxonomy is drift and it has to be refused where the advice is built
def test_an_unsupported_code_is_refused():
    with pytest.raises(ValueError):
        monitor.make_recovery_advice("auth.something_new", "s", "f", False)


# Returns every string literal in an expression, so a code chosen by a conditional is still collected
def _string_literals(node):
    return {item.value for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)}


# Collects every code that reaches the first argument of make_recovery_advice, following a local variable once
def produced_recovery_codes(source):
    tree = ast.parse(source)
    scopes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module))]
    codes = set()
    for scope in scopes:
        assigned = {target.id: node.value for node in ast.walk(scope) if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)}
        for node in ast.walk(scope):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "make_recovery_advice" and node.args):
                continue
            first = node.args[0]
            codes |= _string_literals(assigned[first.id]) if isinstance(first, ast.Name) and first.id in assigned else _string_literals(first)
    return codes


# Every code the taxonomy declares has to be produced somewhere or it is documentation of nothing
def test_every_declared_code_is_produced_somewhere():
    assert produced_recovery_codes(SOURCE) == set(monitor.RECOVERY_CODES)


# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the pytz library": "raised at import, while a dependency the classifier itself needs is missing",
    "Couldn't find the Python-Xbox library": "raised at import, while a dependency the classifier itself needs is missing",
    "sanitize_error_text(message)": "the debug printer, whose content the redactor guard covers",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Token refresh attempt": "reports a retry in progress, with the classified advice printed if every attempt fails",
    "so this run will ask you to authorize once": "the expected first-run state, answered by the sign-in that follows",
    "Re-authorization is required": "reports the recovery action taken, printed under the classified advice",
    "Email notifications:": "the startup summary, where the word error names a switched-on alert",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be", re.IGNORECASE)


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = []
    for node in ast.walk(ast.parse(SOURCE)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        segment = ast.get_source_segment(SOURCE, node) or ""
        if TROUBLE_WORDS.search(segment) and not any(marker in segment for marker in CLASSIFIER_EXEMPTIONS):
            unexplained.append(f"line {node.lineno}: {' '.join(segment.split())[:120]}")
    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    inspected = [node for node in ast.walk(ast.parse(SOURCE)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]
    assert len(inspected) > 100
    assert all(marker in SOURCE for marker in CLASSIFIER_EXEMPTIONS)


# Every fix has to end with the guide line, since the fix paragraph is where a reader looks for the next step
def test_every_fix_carries_a_guide_link():
    advice = [
        monitor.classify_recovery_error(context="config.missing"),
        monitor.classify_recovery_error(context="secret.missing"),
        monitor.classify_recovery_error(context="target.missing"),
        monitor.classify_recovery_error(http_error(429), context="monitor"),
        monitor.classify_recovery_error(http_error(500), context="monitor"),
        monitor.classify_recovery_error(socket.timeout(), context="connectivity"),
    ]
    assert all("\nGuide: https://" in item.fix for item in advice)


@pytest.mark.parametrize("status, code", [
    (429, "xbox.rate_limited"),
    (404, "target.not_found"),
    (500, "xbox.unavailable"),
    (503, "xbox.unavailable"),
])
# The status Xbox Live returns is the most reliable signal available, so each one has to reach its own category
def test_a_status_response_lands_in_its_own_category(status, code):
    assert monitor.classify_recovery_error(http_error(status), context="monitor").code == code


# A 403 while reading a profile is a privacy setting on the monitored account, not a credential problem
def test_a_forbidden_profile_is_a_privacy_problem():
    advice = monitor.classify_recovery_error(http_error(403), context="target")
    assert advice.code == "target.not_visible"
    assert monitor.PRIVACY_GUIDE_URL in advice.fix


# The same status during a sign-in is a credential problem and telling the user to check privacy would misdirect
def test_the_same_status_during_authentication_is_a_credential_problem():
    advice = monitor.classify_recovery_error(http_error(401, "https://login.live.com/oauth20_token.srf"), context="auth")
    assert advice.code == "auth.credentials_invalid"
    assert monitor.CREDENTIALS_GUIDE_URL in advice.fix


# An expired refresh token is the most common cause of a run that quietly stops reporting
def test_an_expired_refresh_token_is_reported_as_expired():
    advice = monitor.classify_recovery_error(ValueError("invalid_grant: token expired"), context="monitor")
    assert advice.code == "auth.token_expired"
    assert advice.retryable is False


# A rate limit and an outage both clear on their own, so both have to be marked worth retrying
@pytest.mark.parametrize("status", [429, 500, 503])
def test_a_transient_failure_is_marked_retryable(status):
    assert monitor.classify_recovery_error(http_error(status), context="monitor").retryable is True


@pytest.mark.parametrize("error, code", [
    (monitor.httpx.ConnectError("no route"), "network.unavailable"),
    (monitor.httpx.ReadTimeout("slow"), "network.timeout"),
    (socket.timeout(), "network.timeout"),
])
# A network that is down and a network that is slow need different advice, so they are told apart
def test_a_network_failure_is_told_apart_from_a_timeout(error, code):
    assert monitor.classify_recovery_error(error, context="monitor").code == code


# Running out of descriptors is a local limit and blaming Xbox Live for it sends the user to the wrong place
def test_an_exhausted_descriptor_limit_is_reported_as_a_local_limit():
    advice = monitor.classify_recovery_error(OSError(24, "Too many open files"), context="monitor")
    assert advice.code == "resource.exhausted"
    assert "ulimit" in advice.fix


@pytest.mark.parametrize("error, code", [
    (smtplib.SMTPAuthenticationError(535, b"bad"), "smtp.authentication"),
    (smtplib.SMTPConnectError(421, b"busy"), "smtp.connection"),
    (ssl.SSLError("handshake"), "smtp.connection"),
])
# A rejected password and an unreachable server look the same to the user but need opposite fixes
def test_an_smtp_failure_is_split_by_cause(error, code):
    assert monitor.classify_recovery_error(error, context="smtp").code == code


# An unrecognised failure still has to say what to do or the user is left with a stack trace and no next step
def test_an_unrecognised_failure_still_names_a_next_step():
    advice = monitor.classify_recovery_error(RuntimeError("something odd"), context="monitor")
    assert advice.code == "unknown"
    assert "--debug" in advice.fix


# Advice already classified upstream must survive being reclassified or the specific fix is replaced by a guess
def test_an_already_classified_failure_is_not_reclassified():
    original = monitor.make_recovery_advice("auth.oauth_code", "s", "f", False)
    assert monitor.classify_recovery_error(monitor.RecoveryError(original), context="monitor") is original


# The fix has to name the command for how this copy was installed or it cannot be pasted into a shell
def test_the_fix_is_written_for_the_detected_install_method(monkeypatch):
    monkeypatch.setattr(monitor, "detect_install_method", lambda: "pip")
    assert "xbox_monitor --generate-config" in monitor.classify_recovery_error(context="config.missing").fix
    monkeypatch.setattr(monitor, "detect_install_method", lambda: "manual")
    assert "xbox_monitor.py --generate-config" in monitor.classify_recovery_error(context="config.missing").fix


# Naming the default path in the advice sends a reader to edit a file that a different flag chose
def test_the_broken_config_advice_does_not_name_the_default_path():
    assert monitor.DEFAULT_CONFIG_FILENAME not in monitor.classify_recovery_error(context="config.invalid", detail="bad line").fix


# The technical detail is for a bug report, so it stays out of the way until debug mode asks for it
@pytest.mark.parametrize("debug, shown", [(True, True), (False, False)])
def test_the_technical_detail_appears_only_in_debug_mode(debug, shown):
    advice = monitor.make_recovery_advice("unknown", "Broke", "Retry", True, "the raw library message")
    rendered = monitor.render_recovery_advice(advice, debug=debug)
    assert ("the raw library message" in rendered) is shown
    assert "To fix: Retry" in rendered


# Repeating the same fix paragraph every cycle buries the timestamps that show the tool is still alive
def test_a_repeated_failure_prints_its_fix_once():
    tracker = monitor.RecoveryHintTracker()
    advice = monitor.classify_recovery_error(http_error(503), context="monitor")
    assert tracker.should_render(advice) is True
    assert tracker.should_render(advice) is False


# A different failure is new information, so its fix has to be printed even while another is being suppressed
def test_a_different_failure_prints_its_own_fix():
    tracker = monitor.RecoveryHintTracker()
    tracker.should_render(monitor.classify_recovery_error(http_error(503), context="monitor"))
    assert tracker.should_render(monitor.classify_recovery_error(http_error(429), context="monitor")) is True


# After a poll succeeds the next failure is a fresh event, so the fix has to be shown in full again
def test_a_successful_poll_restores_the_full_fix():
    tracker = monitor.RecoveryHintTracker()
    advice = monitor.classify_recovery_error(http_error(503), context="monitor")
    tracker.should_render(advice)
    tracker.reset()
    assert tracker.should_render(advice) is True


# Only a credential failure is worth an email, since every other category clears on its own
def test_only_a_credential_failure_is_worth_an_error_email():
    assert monitor.classify_recovery_error(ValueError("invalid_grant"), context="monitor").code in monitor.AUTH_RECOVERY_CODES
    assert monitor.classify_recovery_error(http_error(503), context="monitor").code not in monitor.AUTH_RECOVERY_CODES
    assert monitor.AUTH_RECOVERY_CODES <= monitor.RECOVERY_CODES


# Returns the monitoring loop as a parsed tree, so its failure policy can be inspected without running it
def monitoring_loop_tree():
    for node in ast.walk(ast.parse(SOURCE)):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "xbox_monitor_user":
            return node
    raise AssertionError("the monitoring loop was not found")


# The subject is the whole alert for anyone reading it on a phone, so it has to name what actually failed
def test_the_alert_subject_names_the_failure_and_the_account():
    advice = monitor.classify_recovery_error(http_error(401), context="monitor")

    subject = monitor.recovery_email_subject(advice, "SomeTag")

    assert subject.startswith("xbox_monitor: ")
    assert advice.summary in subject
    assert "(user: SomeTag)" in subject


# The body repeats the fix, since the operator reading the alert is not looking at the terminal
def test_the_alert_body_carries_the_fix_and_the_streak(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    advice = monitor.make_recovery_advice("network.timeout", "Xbox Live did not answer", "Check the connection", True, "detail text")

    body = monitor.recovery_email_body(advice, error_streak=7)

    assert "To fix: Check the connection" in body
    assert "Failed checks in a row: 7" in body
    assert "Technical detail: detail text" in body
    assert "Timestamp: " in body


# A single failed check is not worth an alert, so the streak count only appears once it means something
def test_a_single_failure_body_omits_the_streak(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    advice = monitor.make_recovery_advice("network.timeout", "Xbox Live did not answer", "Check the connection", True)

    assert "Failed checks in a row" not in monitor.recovery_email_body(advice, error_streak=1)


# A blip must not mail anyone and a failure nothing can retry away must not wait for a streak that never comes
def test_the_loop_alerts_at_once_only_for_a_failure_that_cannot_clear_itself():
    loop = monitoring_loop_tree()
    assignments = [node for node in ast.walk(loop) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "alert_after"]

    assert len(assignments) == 1
    assert ast.unparse(assignments[0].value) == "MONITOR_TRANSIENT_ALERT_AFTER if advice.retryable else 1"
    assert monitor.MONITOR_TRANSIENT_ALERT_AFTER > 1


# Retrying a local file descriptor limit forever would spin without ever recovering, so the loop has to stop
def test_the_loop_exits_on_a_limit_it_cannot_retry_away():
    loop = monitoring_loop_tree()
    guards = [ast.unparse(node.test) for node in ast.walk(loop) if isinstance(node, ast.If) and any(isinstance(inner, ast.Call) and ast.unparse(inner.func) == "sys.exit" for inner in ast.walk(node))]

    assert "exhausted" in guards
    assert monitor.classify_recovery_error(OSError(24, "Too many open files"), context="monitor").code == "resource.exhausted"
