# Troubleshooting

Examples on this page use the PyPI command `xbox_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format-by-installation-method).

<a id="doctor-preflight"></a>
## Doctor Preflight

`--doctor` checks the setup without writing files:

```sh
xbox_monitor --doctor <xbox_gamertag>
```

The report covers six sections:

| Section | What it checks |
| --- | --- |
| **Environment** | The Python version against the supported minimum, plus every required and optional dependency |
| **Configuration** | The config and dotenv files in use, which secrets are loaded and from where, the time zone, TLS verification, whether the timing and count settings hold usable values and every file the tool would write |
| **Authentication** | That the application credentials are set, that Xbox Live still accepts the saved tokens and that the token cache is present and private |
| **Connectivity** | That the connectivity endpoint answers, using the configured URL, timeout and TLS setting |
| **Target** | That the monitored gamertag resolves and shares its activity |
| **Notifications** | Whether email alerts are on and, if so, whether the SMTP server accepts the configured login. Whether the webhook destination, headers and alert choices can be used |

Results use `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`. Warnings and failures include a `To fix:` action and relevant guide links. Doctor exits `1` if anything fails and `0` otherwise.

When both the input and the output are a terminal and a channel passed, the report offers one real test message for that channel. Nothing is sent without a separate yes and the result is counted in the summary. The webhook check validates the settings without contacting Discord or ntfy, so nothing is published until you approve the test.

Doctor never starts the interactive sign-in, because that writes a token file. A missing token cache is reported as a warning naming the command that creates one, which is `--setup` or the first monitoring run.

Follow the report's **Next steps** after correcting any failed checks. The printed start command uses the configuration and dotenv files you checked.

<a id="common-problems"></a>
## Common Problems

Every failure is reported in the same three-part shape: what went wrong, a `To fix:` action and a `Guide:` link to the page that covers it. The fix command matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. `--debug` appends a `Technical detail:` line for bug reports. Secrets are redacted from all three.

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| `Xbox Live rejected authorization for this account` | The saved tokens are no longer accepted | [First Authorization](setup-and-first-run.md#first-authorization) |
| `That Xbox profile does not share its activity with this application` | A privacy setting on the monitored account | [User Privacy Settings](setup-and-first-run.md#user-privacy-settings) |
| Rate limit warnings | The polling intervals are too short | [Check Intervals](usage.md#check-intervals) |
| The run stops naming a file and a line number | A configuration line is not a plain `SETTING = value` assignment | [Configuration File](configuration.md#configuration-file) |
| Emails never arrive | Incomplete SMTP settings | [SMTP Settings](configuration.md#smtp-settings) then run `xbox_monitor --send-test-email` |
| Webhook alerts never arrive | Provider mismatch or a stale destination | [Webhook Settings](configuration.md#webhook-settings) then run `xbox_monitor --send-test-webhook` |
| `xbox_monitor` is not found after installation | The shell has not picked up the new command | [Installation and Command Problems](#installation-and-command-problems) |
| Escape sequences such as `[36m` printed as text, or no colour at all | The terminal cannot display ANSI colour, or colour was switched off | [Terminal Colours Look Wrong](#terminal-colours-look-wrong) |

A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when the [liveness reminder](usage.md#liveness-reminder) is switched off, and `* Monitoring recovered` marks recovery. Use `--verbose` to see the first failed check.

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

<a id="terminal-colours-look-wrong"></a>
## Terminal Colours Look Wrong

If escape sequences such as `[36m` appear as literal text, the terminal does not understand ANSI colour. Start the tool with `--no-color` or set `COLORED_OUTPUT = False` in the configuration file. On Windows, `pip install colorama` fixes the classic Command Prompt.

If colour is missing where you expect it, check in this order: `--no-color` on the command line, `COLORED_OUTPUT` in the configuration file, a `NO_COLOR` environment variable and whether output is redirected or piped. Colour is switched off in all of those cases and also when `TERM` is unset or set to `dumb`.

Log files never contain colour by design. To colour a saved log while reading it, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

To change which colours are used, see [Terminal Colours](configuration.md#terminal-colours).

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes, a line naming where each delivered alert went and a complete startup summary without private values. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without those delivery lines
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Delivery confirmations name the recipient or webhook provider. `DELIVERY_CONFIRMATIONS = False` hides these optional success messages. Monitoring events, send attempts and errors remain visible.

Both `--verbose` and `--debug` show the complete startup summary, including notification settings and credential sources. Use it to check which configuration is active without displaying private values.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.

<a id="verbose-and-debug-output"></a>
## Verbose and Debug Output

`--verbose` adds the decisions a run made, in the same `*` lines as the rest of the output:

```sh
xbox_monitor <xbox_gamertag> --verbose
```

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
xbox_monitor <xbox_gamertag> --debug
```

Lines with details read `Operation: key=value, key=value`. Fields depend on the operation. Some results report `outcome=OK`, `failed`, `degraded` or `skipped`.

<a id="installation-and-command-problems"></a>
## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-check-and-install).

If `xbox_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format-by-installation-method) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-xbox-monitor). Use `pipx upgrade xbox_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `xbox_monitor --doctor "<xbox_gamertag>"` to see which settings are loaded.

<a id="invalid-saved-settings-and-state"></a>
## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved status file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.

A saved timestamp more than five minutes ahead of the machine clock is not used as history, because the tool wrote that file itself and a clock moved backwards is the usual reason. Monitoring warns, keeps the saved entry and times it from the moment it starts, so the run continues. Check the system clock if the warning repeats.
