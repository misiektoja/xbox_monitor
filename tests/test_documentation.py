"""Tests that the documentation site describes what the tool actually does, so stale claims fail here."""

import re
from pathlib import Path

import pytest

import xbox_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
README = PROJECT_ROOT / "README.md"
MKDOCS = PROJECT_ROOT / "mkdocs.yml"


# Returns the text of every documentation page joined together
def all_docs_text():
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(DOCS_DIR.glob("*.md")))


# Returns the anchors one markdown file defines, from its headings and from any explicit anchor tags
def page_anchors(path):
    text = path.read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        title = line.lstrip("#").strip()
        anchors.add("".join(character for character in title.casefold().replace(" ", "-") if character.isalnum() or character in "-_"))
    return anchors


# Returns every command-line flag the parser accepts
def declared_flags():
    source = (PROJECT_ROOT / "xbox_monitor.py").read_text(encoding="utf-8")
    declaration_lines = re.findall(r'^\s*(?:"-[a-zA-Z]",\s*)?"--[a-z0-9-]+",\s*$', source, flags=re.MULTILINE)
    return {flag for line in declaration_lines for flag in re.findall(r'"(--[a-z0-9-]+)"', line)}


# Returns the page a documentation site URL points at, together with the anchor it names
def resolve_site_url(url):
    remainder = url[len(monitor.DOCS_BASE_URL):].lstrip("/")
    path_part, _, anchor = remainder.partition("#")
    slug = path_part.strip("/")
    return (DOCS_DIR / "index.md" if not slug else DOCS_DIR / f"{slug}.md"), anchor


# A fix paragraph that links at a missing page is worse than no link, because the reader stops looking
def test_every_guide_link_resolves_to_a_real_page_and_anchor():
    names = sorted(name for name in vars(monitor) if name.endswith("_GUIDE_URL"))
    assert names
    for name in names:
        url = getattr(monitor, name)
        assert url.startswith(monitor.DOCS_BASE_URL), f"{name} does not point at the documentation site"
        page, anchor = resolve_site_url(url)
        assert page.exists(), f"{name} points at a missing page: {page.name}"
        if anchor:
            assert anchor in page_anchors(page), f"{name} points at a missing anchor on {page.name}: #{anchor}"


# Debug output covers how to run the tool more loudly, so a failure pointed there finds nothing about its own cause
def test_a_failure_the_tool_retries_is_never_pointed_at_the_diagnostic_pages():
    for name in (name for name in vars(monitor) if name.endswith("_GUIDE_URL")):
        assert "/debugging/" not in getattr(monitor, name), name
    errors = (monitor.httpx.ReadTimeout("slow"), monitor.httpx.ConnectError("no route"), monitor.httpx.HTTPStatusError("503", request=monitor.httpx.Request("GET", "https://xboxlive.test"), response=monitor.httpx.Response(503)))
    for error in errors:
        fix = monitor.classify_recovery_error(error, context="monitor").fix
        assert "#verbose-and-debug-output" not in fix
        assert "#choosing-the-right-logging-level" not in fix


# A renamed file should fail here rather than in the built site
def test_every_navigation_entry_exists():
    navigation = MKDOCS.read_text(encoding="utf-8").split("nav:", 1)[1]
    for filename in re.findall(r":\s*([a-z0-9-]+\.md)\s*$", navigation, flags=re.MULTILINE):
        assert (DOCS_DIR / filename).exists(), f"the navigation lists a missing page: {filename}"


# A page nobody can navigate to may as well not exist
def test_every_page_is_reachable_from_the_navigation():
    navigation = MKDOCS.read_text(encoding="utf-8").split("nav:", 1)[1]
    listed = set(re.findall(r":\s*([a-z0-9-]+\.md)\s*$", navigation, flags=re.MULTILINE))
    orphans = sorted(path.name for path in DOCS_DIR.glob("*.md") if path.name not in listed)
    assert not orphans, f"pages not listed in the navigation: {orphans}"


# Cross-page links break silently when a heading is reworded, which is the most common docs regression
def test_every_internal_documentation_link_resolves():
    broken = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?:)([^)]+)\)", text):
            page_part, _, anchor = target.partition("#")
            target_page = path if not page_part else (DOCS_DIR / page_part)
            if page_part and not target_page.exists():
                broken.append(f"{path.name} -> {target}")
                continue
            if anchor and anchor not in page_anchors(target_page):
                broken.append(f"{path.name} -> {target}")
    assert not broken, f"broken documentation links: {broken}"


# The landing page is the first thing a reader sees, so a dead link there costs the most
def test_the_readme_links_resolve():
    broken = [url for url in re.findall(rf"{re.escape(monitor.DOCS_BASE_URL)}([^\s)]*)", README.read_text(encoding="utf-8")) if not resolve_site_url(monitor.DOCS_BASE_URL + url)[0].exists()]
    assert not broken, f"the README links at missing documentation pages: {broken}"


# Every markdown file outside the site that links into the repository and which a docs move can silently break
REPOSITORY_MARKDOWN = ("README.md", "SUPPORT.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", ".github/pull_request_template.md", "tests/README.md")


# Moving the documentation out of the README is exactly what leaves these links pointing at nothing
def test_no_repository_document_links_at_a_missing_local_target():
    broken = []
    for relative_path in REPOSITORY_MARKDOWN:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            continue
        for target in re.findall(r"\]\((?!https?:|mailto:)([^)]+)\)", path.read_text(encoding="utf-8")):
            page_part, _, anchor = target.partition("#")
            target_page = path if not page_part else (PROJECT_ROOT / page_part)
            if page_part and not target_page.exists():
                broken.append(f"{relative_path} -> {target}")
                continue
            if anchor and anchor not in page_anchors(target_page):
                broken.append(f"{relative_path} -> {target}")
    assert not broken, f"repository documents linking at missing targets: {broken}"


# An undocumented command may as well not exist
@pytest.mark.parametrize("flag", ["--doctor", "--verbose", "--debug", "--generate-config", "--send-test-email", "--env-file", "--config-file", "--force", "--disable-logging", "--info", "--friends", "--recent-achievements"])
def test_user_facing_flags_are_documented(flag):
    assert flag in all_docs_text(), f"{flag} is not documented on the site"


# A flag that was removed must not linger in the documentation as something a reader can try
def test_the_documentation_does_not_promise_removed_flags():
    documented = set(re.findall(r"`(--[a-z0-9-]+)`", all_docs_text()))
    # Flags belonging to pip, mkdocs or argparse itself are quoted in passing and are not this parser's to accept
    external = {"--help", "--upgrade", "--user", "--break-system-packages", "--strict"}
    missing = sorted(documented - declared_flags() - external)
    assert not missing, f"the documentation promises flags the tool does not accept: {missing}"


# A setting named in the documentation that the parser rejects sends the reader into a config that will not load
def test_the_documentation_does_not_promise_removed_settings():
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", all_docs_text()))
    allowed = set(monitor._config_allowed_names()) | set(monitor.SECRET_KEYS)
    # Signal names, environment variables, file names and prose emphasis are not configuration settings
    external = {"TERM", "NO_COLOR", "PATH", "HOME", "SIGHUP", "DEBUG", "README", "SUPPORT", "SECURITY", "CONTRIBUTING", "LICENSE", "IMPORTANT", "NOTE", "GRC", "PASS", "WARN", "FAIL", "SKIP"}
    missing = sorted(documented - allowed - external)
    assert not missing, f"the documentation promises settings the tool does not accept: {missing}"


# A fifth marker in the docs would mean the page and the code disagree about what a status means
def test_the_documented_doctor_markers_match_the_code():
    text = (DOCS_DIR / "troubleshooting.md").read_text(encoding="utf-8")
    for marker in monitor.DOCTOR_STATUSES:
        assert f"`[{marker}]`" in text, f"[{marker}] is not documented"


# A section the report prints and the page does not describe leaves the reader guessing what failed
def test_the_documented_doctor_sections_match_the_code():
    text = (DOCS_DIR / "troubleshooting.md").read_text(encoding="utf-8")
    for section in monitor.DOCTOR_SECTIONS:
        assert f"**{section}**" in text, f"the {section} doctor section is not documented"


# The startup gate and the documented requirement have to name the same version
def test_the_documented_python_minimum_matches_the_code():
    assert f"Python {monitor.MINIMUM_PYTHON_VERSION_TEXT}" in all_docs_text(), "the documentation states a different Python minimum"


# Every printed guide link is built from this base, so the site has to be published where it points
def test_the_site_url_matches_the_code():
    site_url = re.search(r"^site_url:\s*(\S+)\s*$", MKDOCS.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert site_url is not None
    assert site_url.group(1).rstrip("/") == monitor.DOCS_BASE_URL.rstrip("/")


# Documentation in two places drifts apart, which is why it was moved to the site
def test_the_readme_is_a_landing_page():
    text = README.read_text(encoding="utf-8")
    # The badge block is header chrome rather than documentation, so adding a badge must not eat the budget
    badges = [index for index, line in enumerate(text.splitlines()) if line.startswith("[![")]
    assert badges, "the README has no badge block"
    body = "\n".join(text.splitlines()[badges[-1] + 1:])
    assert len(body) < 13000, "the README has grown back into full documentation"
    assert monitor.DOCS_BASE_URL in text, "the README does not link to the documentation site"


# A job name that says it builds the docs is not the same as a step that does
def test_the_documentation_build_is_a_ci_gate():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    commands = [match.strip() for match in re.findall(r"^\s*run:\s*(.+)$", workflow, flags=re.MULTILINE)]
    assert any("mkdocs build --strict" in command for command in commands), "CI does not build the documentation site"
    assert any("docs/requirements.txt" in command for command in commands), "CI does not install the documentation dependencies"


# Every guide link the tool prints is dead until the site is actually published
def test_the_site_has_a_publishing_workflow():
    workflow = PROJECT_ROOT / ".github" / "workflows" / "docs.yml"
    assert workflow.exists(), "there is no workflow to publish the documentation"
    assert "mkdocs gh-deploy" in workflow.read_text(encoding="utf-8")


# Asking for the report closes the loop between the diagnostic and the support channel
def test_the_bug_report_asks_for_doctor_output():
    template = (PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text(encoding="utf-8")
    assert "--doctor" in template, "the bug report template does not ask for doctor output"


# Returns one page's markdown with fenced code blocks removed, so shell comments are not read as headings
def prose_lines(path):
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    return text.splitlines()


# A mechanical split of one long page silently leaves two titles behind
def test_each_page_has_exactly_one_title():
    for path in sorted(DOCS_DIR.glob("*.md")):
        titles = [line for line in prose_lines(path) if line.startswith("# ")]
        assert len(titles) == 1, f"{path.name} has {len(titles)} titles: {titles}"


# A reader who finds one copy of a section will not know the other exists and the two will drift
def test_no_section_is_duplicated_across_pages():
    # Navigation sections that close several pages by design, each pointing at the page that comes next
    shared = {"Next Step"}
    seen = {}
    duplicates = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        for line in prose_lines(path):
            if not line.startswith("## "):
                continue
            title = line[3:].strip()
            if title in seen and title not in shared:
                duplicates.append(f"'{title}' in both {seen[title]} and {path.name}")
            seen[title] = path.name
    assert not duplicates, f"sections documented twice: {duplicates}"


# The page set matches the sibling tools, so a reader moving between them finds the same shape
def test_the_page_set_is_deliberate():
    expected = {"index.md", "installation.md", "setup-and-first-run.md", "configuration.md", "usage.md", "troubleshooting.md", "testing.md", "about.md"}
    assert {path.name for path in DOCS_DIR.glob("*.md")} == expected


# Each install method the tool can detect needs the commands that method actually uses
def test_the_documented_install_methods_match_the_code():
    path = DOCS_DIR / "installation.md"
    install_sections = [line[4:].strip() for line in prose_lines(path) if line.startswith("### ") and line[4:].startswith(("Install from ", "Install the Manual Script"))]
    known = {monitor.install_method_display_name("pip"), monitor.install_method_display_name("manual")}
    # Read whole, since the commands each method needs live in the fenced blocks the prose reader drops
    page = path.read_text(encoding="utf-8")
    assert len(install_sections) == len(known), f"the page documents {install_sections} for {sorted(known)}"
    assert monitor.install_method_display_name("something-else") not in known
    assert "pip install xbox_monitor" in page
    assert "python3 xbox_monitor.py" in page


@pytest.mark.parametrize("section,page", [
    ("Requirements", "installation.md"),
    ("Run the setup wizard", "setup-and-first-run.md"),
    ("Microsoft Entra Application Credentials", "setup-and-first-run.md"),
    ("User Privacy Settings", "setup-and-first-run.md"),
    ("Storing Secrets", "configuration.md"),
    ("TLS Verification", "configuration.md"),
    ("Check Intervals", "usage.md"),
    ("Doctor Preflight", "troubleshooting.md"),
    ("Verbose and Debug Output", "troubleshooting.md"),
    ("Terminal Output", "usage.md"),
    ("Coloring Log Output with GRC", "usage.md"),
])
# Each section sits where a reader would look for it, matching the sibling tools
def test_sections_sit_on_the_page_a_reader_expects(section, page):
    located = [path.name for path in sorted(DOCS_DIR.glob("*.md")) if any(line.strip() == f"## {section}" for line in prose_lines(path))]
    assert located == [page], f"'{section}' is on {located}, expected {page}"


# A guide that lists the test files goes stale the moment one is added and nothing else notices
def test_the_test_suite_guide_lists_every_test_file():
    listed = set(re.findall(r"^\| `([^`]+)` \|", (PROJECT_ROOT / "tests" / "README.md").read_text(encoding="utf-8"), re.M))
    present = {path.name for path in (PROJECT_ROOT / "tests").glob("test_*.py")} | {path.name for path in (PROJECT_ROOT / "tests").glob("conftest.py")}

    assert present - listed == set(), f"test files missing from tests/README.md: {sorted(present - listed)}"
    assert {name for name in listed if name.endswith(".py")} - present == set(), f"tests/README.md names files that do not exist: {sorted({name for name in listed if name.endswith('.py')} - present)}"
