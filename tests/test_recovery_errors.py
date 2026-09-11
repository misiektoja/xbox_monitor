"""Tests for the recovery taxonomy: which category a failure lands in and what the user is told to do next.

The category decides the fix paragraph, whether a retry is worth waiting for and whether an error email fires,
so each test pins one failure a user can actually hit.
"""

import ast
import inspect
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
# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the pytz library": "raised at import, while a dependency the classifier itself needs is missing",
    "Couldn't find the Python-Xbox library": "raised at import, while a dependency the classifier itself needs is missing",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Token refresh attempt": "reports a retry in progress, with the classified advice printed if every attempt fails",
    "Setup needs a writable dotenv file": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems(SOURCE) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    source = SOURCE
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]
    problems = reported_problems(source)

    assert len(inspected) > 200
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


# A fix ends with the guide line wherever a page covers the failure, since that is where a reader looks next
def test_every_fix_carries_a_guide_link():
    advice = [
        monitor.classify_recovery_error(context="config.missing"),
        monitor.classify_recovery_error(context="secret.missing"),
        monitor.classify_recovery_error(context="target.missing"),
        monitor.classify_recovery_error(http_error(429), context="monitor"),
        monitor.classify_recovery_error(http_error(500), context="monitor"),
    ]
    assert all("\nGuide: https://" in item.fix for item in advice)


# The connectivity check has no page of its own, and its fix already names the setting to look at
def test_the_connectivity_fix_carries_no_guide_link():
    advice = monitor.classify_recovery_error(socket.timeout(), context="connectivity")

    assert advice.fix == "Check network, DNS, proxy and CHECK_INTERNET_URL settings"


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


# Verifies the descriptor limit is matched as a whole errno, so errno 240 or 241 in a message is not mistaken for it
def test_a_neighbouring_errno_is_not_a_file_descriptor_limit():
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 24] Too many open files")) is True
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 240] something else")) is False
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 241] something else")) is False


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


# A blip must not mail anyone and a failure nothing can retry away must not wait for an outage that never lasts
def test_the_loop_alerts_at_once_only_for_a_failure_that_cannot_clear_itself():
    loop = monitoring_loop_tree()
    assignments = [node for node in ast.walk(loop) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "alert_due"]

    assert len(assignments) == 1
    assert ast.unparse(assignments[0].value) == "not advice.retryable or int(time.time()) - outage.since >= ERROR_ALERT_AFTER_SECONDS"
    assert monitor.ERROR_ALERT_AFTER_SECONDS > 0


# Retrying a local file descriptor limit forever would spin without ever recovering, so the loop has to stop
def test_the_loop_exits_on_a_limit_it_cannot_retry_away():
    loop = monitoring_loop_tree()
    guards = [ast.unparse(node.test) for node in ast.walk(loop) if isinstance(node, ast.If) and any(isinstance(inner, ast.Call) and ast.unparse(inner.func) == "sys.exit" for inner in ast.walk(node))]

    assert "exhausted" in guards
    assert monitor.classify_recovery_error(OSError(24, "Too many open files"), context="monitor").code == "resource.exhausted"


# Verifies added context does not replace the error text the rules read, which used to make every such failure unknown
@pytest.mark.parametrize("message, expected", [("429 rate limit exceeded", "xbox.rate_limited"), ("Connection timed out", "network.timeout")])
def test_a_caller_supplied_detail_does_not_hide_the_error(message, expected):
    advice = monitor.classify_recovery_error(Exception(message), detail="Cannot read the Xbox profile")

    assert advice.code == expected
    assert "Cannot read the Xbox profile" in advice.detail


# The only advice that names no page, and the reason no page covers it
GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page():
    source = SOURCE
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source():
    source = SOURCE
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 40
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"


# One concept carried three names across this family: a renderer taking a built advice, a renderer taking the
# failure itself, and a third pair that classified and printed under a name of its own. Pinned here so a call
# copied from a sibling cannot quietly mean something else
def test_the_recovery_printers_share_one_contract():
    advice_first = ("advice", "debug", "retry_note", "with_fix", "label")
    error_first = ("error", "context", "debug", "detail", "retry_note", "with_fix", "label")

    assert tuple(inspect.signature(monitor.render_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(monitor.render_recovery_error).parameters) == error_first
    # The hint tracker follows the shared parameters, so a call written for a sibling without one still means the same thing
    assert tuple(inspect.signature(monitor.print_recovery_advice).parameters) == advice_first + ("tracker",)
    assert tuple(inspect.signature(monitor.print_recovery_error).parameters) == error_first + ("tracker",)


# The advice pair prints what the caller built, so a summary the classifier would never produce survives the trip
def test_the_advice_printer_does_not_reclassify(capsys):
    monitor.DEBUG_MODE = False
    advice = monitor.make_recovery_advice("network.timeout", "a summary no rule produces", "a fix of its own", True)

    returned = monitor.print_recovery_advice(advice)

    assert capsys.readouterr().out == "* Error: a summary no rule produces\nTo fix: a fix of its own\n"
    assert returned is advice


# The error pair classifies what the caller hands it, which is the difference between the two front doors
def test_the_error_printer_classifies_what_it_was_given(capsys):
    monitor.DEBUG_MODE = False

    returned = monitor.print_recovery_error(socket.timeout("timed out"), context="runtime")

    assert returned.code != "unknown"
    assert capsys.readouterr().out.startswith(f"* Error: {returned.summary}\n")


# Both front doors reach the same renderer, so the retry note, the label and a suppressed fix behave the same way
def test_both_front_doors_render_the_same_line():
    monitor.DEBUG_MODE = False
    error = socket.timeout("timed out")
    advice = monitor.classify_recovery_error(error, "runtime")

    through_advice = monitor.render_recovery_advice(advice, retry_note="retrying in 5 minutes", with_fix=False, label="Warning")
    through_error = monitor.render_recovery_error(error, "runtime", retry_note="retrying in 5 minutes", with_fix=False, label="Warning")

    assert through_advice == through_error
    assert through_advice == f"* Warning: {advice.summary} (retrying in 5 minutes)"


# The tracker decides only whether the fix repeats, and it does that after the caller has already allowed it
def test_the_tracker_suppresses_only_the_repeated_fix(capsys):
    monitor.DEBUG_MODE = False
    tracker = monitor.RecoveryHintTracker()

    monitor.print_recovery_error(socket.timeout("timed out"), "runtime", tracker=tracker)
    monitor.print_recovery_error(socket.timeout("timed out"), "runtime", tracker=tracker)

    printed = capsys.readouterr().out
    assert printed.count("* Error: ") == 2
    assert printed.count("To fix: ") == 1


# A detail that only repeats the summary spends a line saying nothing, so the block drops it and keeps a real one
def test_a_detail_repeating_the_summary_is_dropped():
    repeated = monitor.make_recovery_advice("unknown", "the same sentence twice", "a fix", False, "the same sentence twice")
    differing = monitor.make_recovery_advice("unknown", "the summary", "a fix", False, "the raw cause")

    assert "Technical detail:" not in monitor.render_recovery_advice(repeated, debug=True)
    assert "Technical detail: the raw cause" in monitor.render_recovery_advice(differing, debug=True)


# A run that already prints the technical cause cannot be told to re-run for it
def test_the_unrecognized_failure_fix_follows_the_diagnostic_mode(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    plain = monitor.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    debugging = monitor.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix

    assert "--debug" in plain
    assert "--debug" not in debugging
