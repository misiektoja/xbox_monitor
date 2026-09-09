"""Tests that a config file is read as data and never executed."""

import pytest

import xbox_monitor as monitor


HOSTILE_CONTENT = (
    "import os\n"
    "os.environ['XBOX_CONFIG_EXEC_PROBE'] = 'yes'\n",
    "__import__('os').system('touch pwned')\n",
    "CHECK_INTERNET_TIMEOUT = __import__('os').getpid()\n",
    "def helper():\n    return 1\n",
    "for index in range(3):\n    pass\n",
)


# Returns a setting name the built-in configuration template actually defines
def first_allowed_setting():
    return sorted(monitor._config_allowed_names())[0]


@pytest.mark.parametrize("content", HOSTILE_CONTENT)
# Verifies executable content is refused without running, so a config in the working directory cannot run code
def test_executable_config_content_is_refused_without_running(tmp_path, monkeypatch, content):
    monkeypatch.delenv("XBOX_CONFIG_EXEC_PROBE", raising=False)
    config = tmp_path / "hostile.conf"
    config.write_text(content, encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is False
    assert namespace == {}

    import os

    assert os.environ.get("XBOX_CONFIG_EXEC_PROBE") is None
    assert not (tmp_path / "pwned").exists()


# Verifies a plain literal assignment still reaches the namespace
def test_literal_settings_are_applied(tmp_path):
    setting = first_allowed_setting()
    config = tmp_path / "good.conf"
    config.write_text(f"{setting} = 123\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace[setting] == 123


# Verifies one setting may reuse another, which the built-in template relies on
def test_a_setting_may_reference_another_setting(tmp_path):
    allowed = sorted(monitor._config_allowed_names())
    source, target = allowed[0], allowed[1]
    config = tmp_path / "reference.conf"
    config.write_text(f'{source} = "shared"\n{target} = {source}\n', encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace[target] == "shared"


# Verifies a setting this version does not define is named instead of silently landing in the namespace
def test_unknown_setting_is_rejected(tmp_path):
    config = tmp_path / "unknown.conf"
    config.write_text("NOT_A_REAL_SETTING = 1\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is False
    assert "NOT_A_REAL_SETTING" not in namespace


# Verifies a rejected file leaves the namespace untouched rather than applying the lines before the bad one
def test_a_rejected_config_applies_nothing(tmp_path):
    setting = first_allowed_setting()
    config = tmp_path / "partial.conf"
    config.write_text(f"{setting} = 5\nimport os\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is False
    assert namespace == {}


# Verifies the built-in template and the config the tool generates both survive the parser
def test_generated_configuration_round_trips():
    monitor.validate_config_content(monitor.CONFIG_BLOCK, "<built-in>")


# Verifies a file that is not valid UTF-8 is reported rather than raising
def test_invalid_encoding_is_reported(tmp_path):
    config = tmp_path / "binary.conf"
    config.write_bytes(b"\xff\xfe\x00bad\n")

    assert monitor.load_config_file(config, namespace={}, report_errors=False) is False


TEMPLATE_DIRECTORY = monitor.Path(__file__).parent / "data" / "config_templates"

# Every configuration template this tool has ever shipped, oldest first
HISTORICAL_TEMPLATES = sorted(TEMPLATE_DIRECTORY.glob("*.conf"), key=lambda path: tuple(int(part) for part in path.stem.split(".")))


# The repository ignores *.conf, so one missing negation would leave the replay silently running zero cases
def test_the_released_templates_are_present():
    assert len(HISTORICAL_TEMPLATES) >= 4


@pytest.mark.parametrize("template", HISTORICAL_TEMPLATES, ids=lambda path: path.stem)
# Verifies a config written by any released version still loads, so upgrading never rejects the file in place
def test_every_released_template_still_loads(tmp_path, template):
    config = tmp_path / "xbox_monitor.conf"
    config.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    namespace = {}

    monitor.load_config_file(str(config), namespace=namespace)

    assert namespace["XBOX_CHECK_INTERVAL"] > 0
    assert "SMTP_HOST" in namespace


# Verifies a setting a released version wrote is either still defined or explicitly retired, never merely dropped
def test_no_released_setting_was_dropped_without_being_retired():
    defined = monitor._config_allowed_names() | monitor.RETIRED_CONFIG_SETTINGS
    dropped = {}
    for template in HISTORICAL_TEMPLATES:
        tree = monitor.ast.parse(template.read_text(encoding="utf-8"))
        for statement in tree.body:
            if not isinstance(statement, monitor.ast.Assign) or not isinstance(statement.targets[0], monitor.ast.Name):
                continue
            if statement.targets[0].id not in defined:
                dropped.setdefault(statement.targets[0].id, []).append(template.stem)

    assert dropped == {}, f"rename these into RETIRED_CONFIG_SETTINGS: {dropped}"


# Verifies a retired setting is ignored with a note naming it, rather than failing the whole file
def test_a_retired_setting_is_ignored_and_reported(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "RETIRED_CONFIG_SETTINGS", frozenset(("TOOL_ALIVE_INTERVAL",)))
    config = tmp_path / "xbox_monitor.conf"
    config.write_text("TOOL_ALIVE_INTERVAL = 21600\nXBOX_CHECK_INTERVAL = 300\n", encoding="utf-8")
    namespace = {}

    monitor.load_config_file(str(config), namespace=namespace)
    out = capsys.readouterr().out

    assert namespace["XBOX_CHECK_INTERVAL"] == 300
    assert "TOOL_ALIVE_INTERVAL" not in namespace
    assert "no longer uses, which were ignored: TOOL_ALIVE_INTERVAL" in out
