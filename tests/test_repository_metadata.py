"""Tests for repository metadata: governance files, citation, funding, whitespace rules and release integrity."""

import configparser
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Reads one repository asset as UTF-8
def read_asset(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Reads and parses one repository YAML asset
def read_yaml_asset(relative_path: str):
    return yaml.safe_load(read_asset(relative_path))


# Verifies the documents contributors are pointed to are present and not placeholders
def test_repository_governance_documents_exist():
    for relative_path in ("SUPPORT.md", "LICENSE", "README.md", "RELEASE_NOTES.md"):
        asset = PROJECT_ROOT / relative_path
        assert asset.is_file(), relative_path
        assert asset.stat().st_size > 200, relative_path


# Verifies the citation metadata GitHub renders stays parseable and describes this project
def test_citation_metadata_describes_this_project():
    citation = read_yaml_asset("CITATION.cff")
    assert citation["cff-version"] == "1.2.0"
    assert citation["type"] == "software"
    assert citation["title"] == "xbox_monitor"
    assert citation["message"]
    assert citation["license"] == "GPL-3.0-or-later"
    assert citation["repository-code"] == "https://github.com/misiektoja/xbox_monitor"
    assert citation["date-released"].isoformat() == str(citation["date-released"])

    author = citation["authors"][0]
    assert author["given-names"] and author["family-names"] and author["alias"] == "misiektoja"


# Verifies every place that states the version agrees, so a release cannot ship with --version naming the last one
def test_every_version_site_states_the_same_version():
    source = read_asset("xbox_monitor.py")
    module_version = re.search(r'^VERSION = "([^"]+)"', source, re.M)
    docstring_version = re.search(r"^v([\d.]+)$", source, re.M)
    packaged_version = re.search(r'^version = "([^"]+)"', read_asset("pyproject.toml"), re.M)
    newest_notes = re.search(r"^# Changes in ([\d.]+) ", read_asset("RELEASE_NOTES.md"), re.M)

    assert module_version is not None and docstring_version is not None and packaged_version is not None and newest_notes is not None
    assert docstring_version.group(1) == module_version.group(1)
    assert packaged_version.group(1) == module_version.group(1)
    assert newest_notes.group(1) == module_version.group(1)


# Verifies the citation names a version somebody can cite, so it tracks the newest dated release notes section
def test_citation_tracks_the_newest_released_version():
    released = re.search(r"^# Changes in ([\d.]+) \((\d{1,2} \w{3} \d{4})\)", read_asset("RELEASE_NOTES.md"), re.M)
    citation = read_asset("CITATION.cff")
    cited_version = re.search(r'^version: "([^"]+)"', citation, re.M)
    cited_date = re.search(r"^date-released: (\d{4}-\d{2}-\d{2})", citation, re.M)

    assert released is not None and cited_version is not None and cited_date is not None
    assert cited_version.group(1) == released.group(1)
    assert cited_date.group(1) == datetime.strptime(released.group(2), "%d %b %Y").strftime("%Y-%m-%d")


# Verifies the sponsor button keeps a target, since an empty file hides it without failing any check
def test_funding_configuration_declares_a_sponsor_target():
    funding = read_yaml_asset(".github/FUNDING.yml")
    assert funding["github"] == "misiektoja"
    assert funding["buy_me_a_coffee"] == "misiektoja"


# Verifies the shared editor settings still declare the style the repository is written in
def test_editor_configuration_declares_the_repository_style():
    settings = configparser.ConfigParser()
    settings.read_string("[editorconfig]\n" + read_asset(".editorconfig"))

    assert settings["editorconfig"]["root"] == "true"
    assert settings["*"]["charset"] == "utf-8"
    assert settings["*"]["end_of_line"] == "lf"
    assert settings["*"]["indent_style"] == "space"
    assert settings["*"]["indent_size"] == "4"
    assert settings["*"]["insert_final_newline"] == "true"
    assert settings["*"]["trim_trailing_whitespace"] == "true"
    assert settings["*.py"]["indent_size"] == "4"
    assert settings["*.{yml,yaml}"]["indent_size"] == "2"
    assert settings["*.toml"]["indent_size"] == "2"
    # Two trailing spaces are a Markdown line break, so they must stay exempt from trimming
    assert settings["*.md"]["trim_trailing_whitespace"] == "false"
    # LICENSE is verbatim upstream text, so an editor must leave its ending and its spacing alone
    assert settings["LICENSE"]["insert_final_newline"] == "unset"
    assert settings["LICENSE"]["trim_trailing_whitespace"] == "unset"


# Verifies tracked text files obey those rules, since an editor setting only warns on the machine that has it
def test_tracked_text_files_obey_the_declared_whitespace_rules():
    listing = subprocess.run(["git", "ls-files"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    if listing.returncode != 0:
        pytest.skip("not a git checkout")

    # The binary types are declared once in .gitattributes, so this list cannot drift away from that one
    binary_suffixes = {suffix.casefold() for suffix in re.findall(r"^\*(\.[A-Za-z0-9]+)\s+binary\b", read_asset(".gitattributes"), re.M)}
    assert binary_suffixes

    offenders = []
    for name in listing.stdout.split():
        asset = PROJECT_ROOT / name
        if not asset.is_file() or asset.suffix.casefold() in binary_suffixes:
            continue
        content = asset.read_bytes()
        if b"\r\n" in content:
            offenders.append(f"{name}: CRLF line ending")
        if content and not content.endswith(b"\n"):
            offenders.append(f"{name}: missing final newline")
        # LICENSE is verbatim upstream text and Markdown keeps meaningful trailing spaces
        if name != "LICENSE" and asset.suffix.casefold() != ".md" and re.search(rb"[ \t]+\n", content):
            offenders.append(f"{name}: trailing whitespace")
    assert offenders == []


# Verifies Git normalizes line endings, since one CRLF commit from a Windows contributor rewrites whole files
def test_line_ending_policy_is_declared():
    attributes = read_asset(".gitattributes")
    assert "* text=auto eol=lf" in attributes
    for pattern in ("*.png binary", "*.jpg binary", "*.gif binary"):
        assert pattern in attributes


# Verifies the support document routes each request to a channel that exists
def test_support_document_routes_every_request_type():
    support = read_asset("SUPPORT.md")
    for destination in ("https://github.com/misiektoja/xbox_monitor/discussions", "https://github.com/misiektoja/xbox_monitor/security/advisories/new", "https://github.com/misiektoja/xbox_monitor/issues/new"):
        assert destination in support
    assert "xbox_monitor --version" in support
    for concept in ("client ID or client secret", "SMTP passwords", "webhook URLs", "--debug",):
        assert concept in support


# Verifies the optional local hooks run the ruff the pinned extra installs, since a second pin here would drift
# apart from it every time one side is bumped and a locally clean commit would still fail CI
def test_local_hooks_run_the_pinned_linter():
    assert re.search(r'lint = \["ruff==([^"]+)"\]', read_asset("pyproject.toml")) is not None

    repos = read_yaml_asset(".pre-commit-config.yaml")["repos"]
    assert not any("ruff" in entry["repo"] for entry in repos), "ruff must not be pinned a second time in the hook configuration"

    ruff_hook = next(hook for entry in repos if entry["repo"] == "local" for hook in entry["hooks"] if hook["id"] == "ruff-check")
    assert ruff_hook["language"] == "system"
    assert ruff_hook["entry"].split() == ["ruff", "check"]

    lint_steps = read_yaml_asset(".github/workflows/tests.yml")["jobs"]["lint"]["steps"]
    assert any("[lint]" in step.get("run", "") for step in lint_steps)
    lint_command = next(step["run"] for step in lint_steps if "ruff check" in step.get("run", ""))

    # Both sides must also reach the same files, or the hook stays quiet about code CI rejects
    covered = re.compile(ruff_hook["files"])
    assert covered.match("xbox_monitor.py")
    assert covered.match("tests/test_repository_metadata.py")
    assert "xbox_monitor.py tests" in lint_command


# Verifies published archives stay verifiable, since an unsigned download cannot be told apart from a tampered one
def test_release_archives_ship_checksums_and_provenance():
    job = read_yaml_asset(".github/workflows/release-assets.yml")["jobs"]["build-and-upload-assets"]
    assert job["permissions"]["attestations"] == "write"
    assert job["permissions"]["id-token"] == "write"

    assert any("sha256sum" in step.get("run", "") for step in job["steps"])
    assert any("attest-build-provenance" in step.get("uses", "") for step in job["steps"])

    attest = next(step for step in job["steps"] if "attest-build-provenance" in step.get("uses", ""))
    stage = next(step for step in job["steps"] if ".intoto.jsonl" in step.get("run", ""))
    assert f"steps.{attest['id']}.outputs.bundle-path" in stage["env"]["BUNDLE_PATH"]

    upload = next(step for step in job["steps"] if "action-gh-release" in step.get("uses", ""))
    assert "_SHA256SUMS.txt" in upload["with"]["files"]
    # Offline verifiers need the bundle as an asset, since the attestations API may be unreachable
    assert ".intoto.jsonl" in upload["with"]["files"]


# Verifies the minimum supported Python version is declared once and matches the packaging metadata, CI and the README
def test_the_minimum_python_version_is_declared_once():
    import xbox_monitor as monitor

    pyproject = read_asset("pyproject.toml")
    minimum_text = monitor.MINIMUM_PYTHON_VERSION_TEXT

    assert minimum_text == ".".join(str(part) for part in monitor.MINIMUM_PYTHON_VERSION)
    assert f'requires-python = ">={minimum_text}"' in pyproject
    assert f"Programming Language :: Python :: {minimum_text}" in pyproject
    classifiers = re.findall(r"Programming Language :: Python :: (\d+\.\d+)", pyproject)
    assert min(tuple(int(part) for part in version.split(".")) for version in classifiers) == monitor.MINIMUM_PYTHON_VERSION
    matrix = read_yaml_asset(".github/workflows/tests.yml")["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    assert min(tuple(int(part) for part in str(version).split(".")) for version in matrix) == monitor.MINIMUM_PYTHON_VERSION
    # The requirements moved to the documentation site and the README keeps only the badge
    assert f"Python {minimum_text} or higher" in read_asset("docs/installation.md")
    assert f"python-{minimum_text}+" in read_asset("README.md")


# Prose files this repository writes and keeps to one editorial style
PROSE_ASSETS = ("README.md", "SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md", "tests/README.md", ".github/pull_request_template.md")


# Verifies the house style holds, since a comma before "and" or "or" creeps back one edit at a time
def test_prose_carries_no_comma_before_a_conjunction():
    offenders = []
    documents = [PROJECT_ROOT / name for name in PROSE_ASSETS] + sorted((PROJECT_ROOT / "docs").glob("*.md"))
    for path in documents:
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if re.search(r",\s+(?:and|or)\b", line):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{number}")
    # Released sections are historical text, so only the version being prepared is held to the current style
    notes = read_asset("RELEASE_NOTES.md")
    unreleased = notes[:notes.index("# Changes in 1.9.3")]
    for number, line in enumerate(unreleased.split("\n"), 1):
        if re.search(r",\s+(?:and|or)\b", line):
            offenders.append(f"RELEASE_NOTES.md:{number}")

    assert offenders == []
