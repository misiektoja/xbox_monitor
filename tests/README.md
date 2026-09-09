# Offline test suite

These tests cover logic in `xbox_monitor.py` that can run without network access.
Xbox Live calls are replaced with test doubles.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the
working tree instead of an installed copy of the module.

Lint the same way CI does:

```bash
pip install -e '.[lint]'
python -m ruff check xbox_monitor.py tests
```

Build the documentation the same way CI does, which fails on a broken link or a
missing page:

```bash
pip install -r docs/requirements.txt
mkdocs build --strict
```

CI runs all three on every push and pull request, across Python 3.11 through 3.14,
and again before anything is published to PyPI.

## Layout

| File | Area under test |
| --- | --- |
| `conftest.py` | Shared fixtures: module globals, exported secrets and signal handlers are reset between tests |
| `test_auth_retry.py` | Transient error classification, refresh retry and give-up behavior, no interactive auth on timeout |
| `test_cli_startup.py` | Real startup through `main()`: `--debug` precedence over the config file, secret source attribution, placeholder gates for credentials and email, install method commands, the `--generate-config` replacement guard |
| `test_config_loading.py` | Config files are parsed as data, rejected content and retired settings |
| `test_config_writing.py` | Timestamped backups, atomic replacement, private token cache writes and the guard on writing a generated config |
| `test_doctor.py` | `--doctor`: the shared report contract, every section, the delivery test approval and the exit code |
| `test_documentation.py` | The documentation site: guide links, navigation, the flags and settings it names and the CI build |
| `test_output_safety.py` | Redaction of secrets from debug output, recovery advice and the doctor report |
| `test_recovery_errors.py` | The recovery taxonomy, which category each failure lands in and the classifier coverage guard |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_secret_reload.py` | `SIGHUP` reload bumping the authentication refresh version |
| `test_tls_verification.py` | Every connection honouring `VERIFY_SSL`, and the single shared TLS context builder |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace Xbox Live calls and notification delivery with test doubles.
* Never use a real Microsoft app client ID and secret, SMTP password or webhook URL.

A change to the monitoring loop, authentication or Xbox Live data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
