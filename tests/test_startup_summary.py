"""Tests for the startup summary rows and where each one is shown."""

import pytest

import xbox_monitor as monitor


# Collects what the terminal and the log file were each given, the way the real Logger splits them
class RoutedStream:
    def __init__(self):
        self.terminal = []
        self.log = []

    # Records text meant only for the reader at the terminal
    def terminal_only(self, message):
        self.terminal.append(message)

    # Records text meant only for the log file
    def log_only(self, message):
        self.log.append(message)

    # Present because every stream the tool writes to has one
    def flush(self):
        pass

    # Returns what the terminal was shown
    def terminal_text(self):
        return "".join(self.terminal)

    # Returns what the log file kept
    def log_text(self):
        return "".join(self.log)


@pytest.fixture
# Builds the summary rows with settings that make every optional feature visible and predictable
def summary_rows(monkeypatch):
    monkeypatch.setattr(monitor, "XBOX_CHECK_INTERVAL", 600)
    monkeypatch.setattr(monitor, "XBOX_ACTIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", 43200)
    monkeypatch.setattr(monitor, "CSV_FILE", "history.csv")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    return monitor.build_startup_summary("misiektoja", "xbox_monitor.conf", ".env", "xbox_monitor_misiektoja.log")


# Returns the row with the given label, failing the test when the summary has no such row
def row_named(rows, label):
    matched = [row for row in rows if row.label == label]
    assert len(matched) == 1, f"expected exactly one {label!r} row, found {len(matched)}"
    return matched[0]


# Verifies a row is part of the full view and the log file unless it opts out, and stays out of the concise view
def test_a_row_is_full_view_only_until_it_opts_in():
    row = monitor.StartupSummaryRow("Some setting", "some value")

    assert row.concise is False
    assert row.full is True
    assert row.log is True


# Verifies the concise view stays short and the full view is a superset of the settings it reports
def test_the_full_view_reports_more_settings_than_the_concise_one(summary_rows):
    concise = {row.label for row in summary_rows if row.concise}
    full = {row.label for row in summary_rows if row.full}

    assert len(concise) < len(full)
    # The two rows the concise view uses to orient a new reader have a better place in the full view
    assert concise - full == {"Output", "More details"}


# Verifies the pointer at the two flags is dropped once the reader has used one of them
def test_the_flag_pointer_is_concise_view_only(summary_rows):
    pointer = row_named(summary_rows, "More details")

    assert pointer.concise is True
    assert pointer.full is False
    assert pointer.log is False


# Verifies every file the tool can be configured to write is named in the full view with its effective path
def test_the_full_view_names_every_generated_file(summary_rows):
    for label, expected in (("Output logging", "xbox_monitor_misiektoja.log"), ("Status file", "xbox_misiektoja_last_status.json"), ("CSV output", "history.csv"), ("Token cache", "xbox_tokens.json")):
        row = row_named(summary_rows, label)
        assert row.full is True
        assert expected in str(row.value)


# Verifies the log file keeps the complete summary even when the terminal was shown the concise view
def test_the_log_file_keeps_the_full_summary_whatever_the_terminal_showed(summary_rows):
    stream = RoutedStream()

    monitor.emit_startup_summary(summary_rows, show_full=False, stream=stream)

    terminal = stream.terminal_text()
    log = stream.log_text()
    assert "Install method:" not in terminal
    assert "Install method:" in log
    assert "Local timezone:" not in terminal
    assert "Local timezone:" in log


# Verifies the two orientation rows never reach the log file, which already records the same facts
def test_terminal_only_rows_are_kept_out_of_the_log(summary_rows):
    stream = RoutedStream()

    monitor.emit_startup_summary(summary_rows, show_full=True, stream=stream)

    log = stream.log_text()
    assert "* Output:" not in log
    assert "More details:" not in log
    assert "Output logging:" in log


# Verifies a plain stream that cannot route rows still gets one complete view rather than nothing
def test_an_unrouted_stream_receives_the_requested_view(summary_rows):
    class PlainStream:
        def __init__(self):
            self.text = ""

        def write(self, message):
            self.text += message

        def flush(self):
            pass

    concise, full = PlainStream(), PlainStream()

    monitor.emit_startup_summary(summary_rows, show_full=False, stream=concise)
    monitor.emit_startup_summary(summary_rows, show_full=True, stream=full)

    assert "More details:" in concise.text
    assert "Install method:" not in concise.text
    assert "Install method:" in full.text
    assert "More details:" not in full.text


# Verifies the summary ends with one blank line, so the next heading starts at the cursor
def test_the_summary_ends_with_a_single_blank_line(summary_rows):
    stream = RoutedStream()

    monitor.emit_startup_summary(summary_rows, show_full=False, stream=stream)

    assert stream.terminal_text().endswith("\n\n")
    assert not stream.terminal_text().endswith("\n\n\n")


# Verifies every value starts in the same column, so the summary reads as a table
def test_values_line_up_in_one_column(summary_rows):
    rendered = [monitor.format_startup_summary_row(row) for row in summary_rows]

    columns = {line.index(str(row.value).split(" ")[0]) for row, line in zip(summary_rows, rendered, strict=True) if row.value}
    assert len(columns) == 1


# Verifies the email rollup names what is switched on instead of printing four separate booleans
def test_the_notification_row_names_what_is_enabled(monkeypatch):
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "GAME_CHANGE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "STATUS_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)

    assert monitor.startup_notification_state() == "On (status changes, errors)"


# Verifies the rollup says so plainly when no email alert can fire
def test_the_notification_row_reports_when_everything_is_off(monkeypatch):
    for name in ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "STATUS_NOTIFICATION", "ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, name, False)

    assert monitor.startup_notification_state() == "Off"


# Verifies a long email rollup wraps under its own label instead of running past the column
def test_a_long_notification_rollup_wraps_under_its_label():
    row = monitor.StartupSummaryRow("Notifications (email)", "On (" + ", ".join(["a long alert name"] * 8) + ")", concise=True)

    lines = monitor.format_startup_summary_row(row).splitlines()

    assert len(lines) > 1
    assert all(len(line) <= 100 for line in lines)
    assert lines[1].startswith(" " * 32)


# Verifies disabled logging is reported as such rather than leaving the reader guessing where output went
def test_disabled_logging_is_named_in_both_views(monkeypatch):
    monkeypatch.setattr(monitor, "CSV_FILE", None)
    rows = monitor.build_startup_summary("misiektoja", None, None, None)

    assert row_named(rows, "Output").value == "Terminal only (logging disabled)"
    assert row_named(rows, "Output logging").value == "Disabled"
    assert row_named(rows, "CSV output").value == "Disabled"


# Verifies either diagnostic flag asks for the full view, since both of them report settings
@pytest.mark.parametrize("verbose, debug, expected", [(False, False, False), (True, False, True), (False, True, True), (True, True, True)])
def test_either_flag_asks_for_the_full_view(monkeypatch, verbose, debug, expected):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", verbose)
    monkeypatch.setattr(monitor, "DEBUG_MODE", debug)

    assert monitor.full_startup_summary_enabled() is expected


# Verifies the real logger writes the full summary to the file while the terminal keeps the concise view
def test_the_real_logger_splits_the_summary(tmp_path, summary_rows, capsys):
    log_file = tmp_path / "xbox_monitor.log"
    logger = monitor.Logger(str(log_file))

    monitor.emit_startup_summary(summary_rows, show_full=False, stream=logger)
    logger.flush()

    saved = log_file.read_text(encoding="utf-8")
    shown = capsys.readouterr().out
    assert "Install method:" in saved
    assert "Install method:" not in shown
    assert "Polling intervals:" in saved
    assert "Polling intervals:" in shown
    # The log file stays plain text, whichever writer put the line there
    assert "\x1b" not in saved
    assert "\t" not in saved


# Verifies each source that can supply a secret gets its own row, so none of them is filed under another
@pytest.mark.parametrize("source, label", [("dotenv file", "Secrets from dotenv"), ("environment", "Secrets from environment"), ("configuration file", "Secrets from config file"), ("command line", "Secrets from command line")])
def test_each_secret_source_is_reported_under_its_own_row(monkeypatch, source, label):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"MS_APP_CLIENT_ID": source})
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "client-id-value")

    rows = monitor.build_startup_summary("misiektoja")

    assert row_named(rows, label).value == "MS_APP_CLIENT_ID"
    for other in ("Secrets from dotenv", "Secrets from environment", "Secrets from config file", "Secrets from command line"):
        if other != label:
            assert row_named(rows, other).value == "None"


# Verifies an unedited placeholder is never reported as a loaded secret, whichever layer recorded it
def test_placeholder_secrets_are_not_reported_as_loaded(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"MS_APP_CLIENT_ID": "dotenv file", "SMTP_PASSWORD": "configuration file"})
    monkeypatch.setattr(monitor, "MS_APP_CLIENT_ID", "your_ms_application_client_id")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "your_smtp_password")

    reported = [name for names in monitor.doctor_secret_sources().values() for name in names]

    assert "MS_APP_CLIENT_ID" not in reported
    assert "SMTP_PASSWORD" not in reported


# The rows shared with the sibling monitors, in the order every one of them prints
SHARED_ROW_ORDER = ("Target", "Polling intervals", "Notifications (email)", "Notifications (webhook)", "Output", "Output logging", "Config", "Dotenv", "Liveness output", "CSV output", "Local timezone", "Install method", "Secrets from dotenv", "Secrets from environment", "Secrets from config file", "Secrets from command line", "TLS verification", "ASCII log separators", "Verbose mode", "Debug mode", "More details")


# Verifies the shared rows keep the order and the label column width every sibling monitor prints
def test_the_shared_summary_rows_match_the_sibling_tools(summary_rows):
    assert [row.label for row in summary_rows if row.label in SHARED_ROW_ORDER] == list(SHARED_ROW_ORDER)
    # The renderer pads "<label>:" into a 30-character column, so a longer label swallows the separating space
    assert max(len(row.label) for row in summary_rows) <= 28


# Verifies an optional feature that is switched off stays out of the concise view
@pytest.mark.parametrize("label, setting, value", [("Liveness output", "LIVENESS_CHECK_INTERVAL", 0), ("CSV output", "CSV_FILE", ""), ("TLS verification", "VERIFY_SSL", True)])
def test_an_inactive_optional_feature_is_kept_out_of_the_concise_view(monkeypatch, label, setting, value):
    monkeypatch.setattr(monitor, setting, value)

    rows = monitor.build_startup_summary("misiektoja")

    assert row_named(rows, label).concise is False


# Verifies the same features earn a concise row as soon as they are switched on
@pytest.mark.parametrize("label, setting, value", [("Liveness output", "LIVENESS_CHECK_INTERVAL", 43200), ("CSV output", "CSV_FILE", "history.csv"), ("TLS verification", "VERIFY_SSL", False)])
def test_an_active_optional_feature_earns_a_concise_row(monkeypatch, label, setting, value):
    monkeypatch.setattr(monitor, setting, value)

    rows = monitor.build_startup_summary("misiektoja")

    assert row_named(rows, label).concise is True


# Verifies a row can be shown in the full view and still be kept out of the log, which is a separate decision
def test_the_log_flag_is_independent_of_the_view_flags():
    stream = RoutedStream()
    rows = [monitor.StartupSummaryRow("Shown but not logged", "value", concise=True, full=True, log=False), monitor.StartupSummaryRow("Shown and logged", "value", concise=True, full=True, log=True)]

    monitor.emit_startup_summary(rows, show_full=True, stream=stream)

    assert "Shown but not logged:" in stream.terminal_text()
    assert "Shown but not logged:" not in stream.log_text()
    assert "Shown and logged:" in stream.log_text()
