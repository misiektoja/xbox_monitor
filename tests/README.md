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

CI runs all three on every push and pull request, across Python 3.11 through 3.14
and again before anything is published to PyPI.

## Layout

| File | Area under test |
| --- | --- |
| `test_notification_receipts.py` | SMTP acceptance despite cleanup failures, receipt controls and unchanged notification content |
| `test_configuration_notification_boundaries.py` | Invalid output settings, CLI precedence and strict webhook fields with legacy JSON support |
| `test_boundary_regressions.py` | Real notification transports, literal secret resolution and malformed startup paths |
| `test_xbox_boundary_flows.py` | Real Xbox authentication, Doctor presence access, token paths and activity classification |
| `test_release_boundaries.py` | Real HTTP retries, Discord mention safety, unrenderable templates, SMTP password round trips, split terminal writes and the width cap without wcwidth |
| `test_compact_commands.py` | Literal short command prefixes, real help output and dependency hints |
| `test_release_safety.py` | Credential preservation, private error rendering, runtime timing validation and saved-state compatibility |
| `test_recovery_safety.py` | Real dotenv reloads, setup backups, oversized counts and provider-error privacy |
| `test_secret_policy.py` | Shared credential priority, reload ownership and setup destination conflicts |
| `test_smtp_error_privacy.py` | Short and escaped passwords in rejected SMTP sign-ins through commands, setup, Doctor and delivery |
| `test_setup_resolution_regressions.py` | Saved dotenv destinations, empty secrets, export precedence and recovery paths |
| `test_dotenv_quoted_keys.py` | Quoted dotenv keys, export prefixes, multiline values and duplicate removal |
| `test_documentation_layout.py` | Unique anchors, main screenshot placement and matching entry-page feature summaries |
| `conftest.py` | Shared fixtures: module globals, exported secrets and signal handlers are reset between tests |
| `data/config_templates/` | The configuration template every released version shipped, replayed by `test_config_loading.py` |
| `test_auth_retry.py` | Transient error classification, refresh retry and give-up behavior, no interactive auth on timeout |
| `test_cli_startup.py` | Real startup through `main()`: `--debug` precedence over the config file, secret source attribution, placeholder gates for credentials and email, install method commands, the `--generate-config` replacement guard and the webhook flags |
| `test_config_loading.py` | Config files are parsed as data, rejected content, retired settings and every released template still loading |
| `test_config_writing.py` | Timestamped backups, atomic replacement, private token cache writes and the guard on writing a generated config |
| `test_diagnostic_grammar.py` | Every debug line following one `Operation: key=value` shape with a closed outcome vocabulary |
| `test_diagnostic_modes.py` | What `--verbose` and `--debug` each report and that neither leaks a secret value |
| `test_doctor.py` | `--doctor`: the shared report contract, every section, the delivery test approval and the exit code |
| `test_documentation.py` | The documentation site: guide links, navigation, page structure and the flags and settings it names |
| `test_email_html.py` | HTML notification bodies: escaping, the Discord markdown form and the plain-text match |
| `test_help_screen.py` | The `--help` screen: the option groups, the worked examples and the version banner |
| `test_output_safety.py` | Redaction of secrets and upstream text that cannot drive the terminal, the log, the CSV file or an email |
| `test_presence_titles.py` | Which presence titles count as a game: Xbox system surfaces are filtered and zero-width characters are stripped |
| `test_recovery_errors.py` | The recovery taxonomy, which category each failure lands in and the classifier coverage guard |
| `test_missed_alert_recovery.py` | The recovery alert sent to a channel that never received the failure alert |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Citation, funding, line endings, the declared editor style, the pinned linter, release integrity and the version sites |
| `test_secret_commands.py` | The one-shot commands that write a secret: what each validates, writes and refuses to write |
| `test_secret_reload.py` | `SIGHUP` reload bumping the authentication refresh version and following a replaced webhook destination |
| `test_setup_wizard.py` | `--setup` driven end to end: what it asks, what it writes and what it leaves untouched |
| `test_partial_setup_save.py` | Real wizard inputs and filesystem failures after configuration replacement |
| `test_shared_wording.py` | The prompts, labels and headings this tool shares word for word with the sibling monitors |
| `test_startup_summary.py` | The startup summary rows, their order and the concise and verbose views |
| `test_startup_summary_channels.py` | Summary rows naming the webhook provider, the mail server, the masked recipient, the delivery confirmations and the runtime |
| `test_terminal_color.py` | The colour engine, the theme in both directions and which values are coloured |
| `test_terminal_transcripts.py` | Real pty runs: what a terminal actually receives, with and without `--no-color` |
| `test_tls_verification.py` | Every connection honouring `VERIFY_SSL` and the single shared TLS context builder |
| `test_webhook_notifications.py` | Webhook delivery: the destination, the request each provider gets, the bounded retry and the loop's call sites |
| `test_moved_private_settings.py` | Kept credentials across dotenv destination changes and startup error handling |

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
