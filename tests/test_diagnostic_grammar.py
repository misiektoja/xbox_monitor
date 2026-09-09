"""Tests that every diagnostic line follows the one grammar the tool family shares.

A trace is only worth having if it can be scanned. The rules are mechanical, so they are checked
mechanically: the shape drifts back one call site at a time and nothing else notices.
"""

import ast
import re
from pathlib import Path

import xbox_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "xbox_monitor.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

# Reserved so that grepping outcome=failed stays meaningful across every tool in the family
DIAGNOSTIC_OUTCOMES = ("OK", "failed", "degraded", "skipped")


# Returns every debug_print call in the source, excluding the definition itself
def debug_calls():
    return [node for node in ast.walk(TREE) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "debug_print"]


# Returns the literal operation of one call, or None when it is built at runtime
def operation_of(node):
    first = node.args[0] if node.args else None
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


# The source has to contain enough calls for these rules to be worth checking at all
def test_the_grammar_check_still_inspects_the_source():
    assert len(debug_calls()) > 40


# A runtime-built operation cannot be read as a stable label, so every call names one outright
def test_every_operation_is_a_literal():
    unnamed = [f"line {node.lineno}" for node in debug_calls() if operation_of(node) is None]
    assert unnamed == [], f"debug_print calls whose operation is not a literal: {unnamed}"


# The detail belongs in named fields, so nothing is interpolated into the label
def test_no_value_is_interpolated_into_the_operation():
    interpolated = [f"line {node.lineno}" for node in debug_calls() if node.args and isinstance(node.args[0], ast.JoinedStr)]
    assert interpolated == [], f"debug_print calls with an f-string operation: {interpolated}"


# An equals sign in the label is the old prose line wearing the new format
def test_no_operation_carries_its_own_fields():
    offenders = [f"line {node.lineno}: {operation_of(node)}" for node in debug_calls() if "=" in (operation_of(node) or "")]
    assert offenders == [], f"debug_print operations carrying key=value text: {offenders}"


# A label cut off mid-clause is what converting prose mechanically leaves behind
def test_no_operation_ends_in_a_preposition_or_punctuation():
    trailing = re.compile(r"(?:[:,.]|\b(?:for|of|in|to|with|from|at|on|by)\s*)$", re.IGNORECASE)
    offenders = [f"line {node.lineno}: {operation_of(node)}" for node in debug_calls() if trailing.search(operation_of(node) or "")]
    assert offenders == [], f"debug_print operations ending mid-clause: {offenders}"


# Every detail is passed as a named field rather than packed into the label
def test_every_call_passes_its_detail_as_fields():
    positional = [f"line {node.lineno}" for node in debug_calls() if len(node.args) > 1]
    assert positional == [], f"debug_print calls passing more than the operation positionally: {positional}"


# Reserving the token is the practical reason the vocabulary is closed
def test_the_outcome_vocabulary_is_closed():
    offenders = []
    for node in debug_calls():
        for keyword in node.keywords:
            if keyword.arg != "outcome":
                continue
            if not isinstance(keyword.value, ast.Constant) or keyword.value.value not in DIAGNOSTIC_OUTCOMES:
                offenders.append(f"line {node.lineno}")
    assert offenders == [], f"debug_print calls using an outcome outside {DIAGNOSTIC_OUTCOMES}: {offenders}"


# The operation says what was attempted and the field says how it went, so neither repeats the other
def test_the_operation_does_not_repeat_its_outcome():
    words = ("failed", "failure", "succeeded", "success", "skipped", "degraded")
    offenders = []
    for node in debug_calls():
        operation = (operation_of(node) or "").casefold()
        if any(keyword.arg == "outcome" for keyword in node.keywords) and any(word in operation for word in words):
            offenders.append(f"line {node.lineno}: {operation_of(node)}")
    assert offenders == [], f"debug_print operations restating their own outcome: {offenders}"


# A failure the reader cannot identify is a line that only says something went wrong
def test_every_failed_outcome_carries_its_error():
    offenders = []
    for node in debug_calls():
        outcomes = [keyword.value.value for keyword in node.keywords if keyword.arg == "outcome" and isinstance(keyword.value, ast.Constant)]
        if "failed" in outcomes and not any(keyword.arg in ("error", "reason") for keyword in node.keywords):
            offenders.append(f"line {node.lineno}: {operation_of(node)}")
    assert offenders == [], f"debug_print failures with neither an error nor a reason: {offenders}"


# A field holding several details wearing one name gives up everything fields were for
def test_no_field_packs_several_details():
    offenders = []
    for node in debug_calls():
        for keyword in node.keywords:
            if not isinstance(keyword.value, ast.JoinedStr):
                continue
            literal = "".join(str(part.value) for part in keyword.value.values if isinstance(part, ast.Constant))
            if any(character in literal for character in "=(") or literal.count(":") > 1:
                offenders.append(f"line {node.lineno}: {keyword.arg}")
    assert offenders == [], f"debug_print fields packing several details: {offenders}"


# An unset field is dropped, so a call site can pass an optional detail without branching around it
def test_an_unset_field_is_dropped():
    assert monitor.format_diagnostic_line("Thing", {"a": 1, "b": None, "c": "x"}) == "Thing: a=1, c=x"


# An operation with no fields is still a line worth printing
def test_an_operation_without_fields_renders_alone():
    assert monitor.format_diagnostic_line("Thing", {}) == "Thing"
