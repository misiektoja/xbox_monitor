# Troubleshooting

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

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

## Setup and Secret Commands

`--setup`, `--set-ms-app-credentials`, `--set-smtp-password` and `--set-webhook-url` need an interactive terminal, since the values they collect must stay hidden. Run outside one they explain that and exit non-zero rather than reading a secret from a pipe.

Ctrl+C cancels setup before saving or cancels a secret prompt without changing the dotenv file. After saving, it skips the optional Doctor run or monitoring offer. At Doctor's test-message prompts, Ctrl+C ends the report.

`--setup` needs somewhere to put both files, so it refuses `--env-file none` and `--config-file none`. It reports a destination that is a directory or whose parent will not accept a write before asking anything.

## Error Messages and Recovery

Every reported problem carries a category, a one-line summary and a `To fix:` paragraph, plus a `Guide:` link when a documentation page covers it. The category decides the advice, so the same failure reads the same way wherever it surfaces. A command in the fix text matches how you installed the tool: `xbox_monitor ...` for a PyPI install and `python3 xbox_monitor.py ...` for a downloaded script. It also carries the `--config-file` or `--env-file` you started with.

| What you see | What it usually means |
| --- | --- |
| The configuration file could not be loaded | A line in the config file is not a plain `SETTING = value` assignment. The message names the line |
| A required credential is missing | `MS_APP_CLIENT_ID` or `MS_APP_CLIENT_SECRET` is empty or still a placeholder |
| The Microsoft sign-in endpoint rejected the saved credentials | The refresh token expired or was revoked. An expired application secret in Microsoft Entra reads the same way |
| The Xbox token cache is not a saved token response | The token file is corrupt. Delete it and authorize again |
| That Xbox profile does not share its activity | A privacy setting on the monitored account, not a problem with your credentials |
| Xbox Live is rate limiting this application | The polling intervals are too short or several copies share one application |
| This process ran out of file descriptors | A local limit rather than an Xbox Live problem. Raise it with `ulimit -n` or `LimitNOFILE=` under systemd. The tool exits, since no retry can recover it |
| The SMTP server rejected the login | Providers such as Gmail need an app password rather than the account password |
| The webhook settings cannot be used | A webhook setting is malformed. The message names the one to correct, then run `--send-test-webhook` |
| The webhook service refused the delivery | The webhook was deleted or the saved URL is out of date. Create a new one and run `--set-webhook-url` |
| The webhook service is rate limiting deliveries | Too many alerts for the destination. Enable fewer webhook alert types |

During quiet monitoring, `* Monitoring healthy for <xbox_gamertag>` confirms the tool is still running. `LIVENESS_CHECK_INTERVAL` defaults to 86400 seconds (24 hours). Set it to `0` to disable this reminder.

Failures show an error and a `To fix:` action. A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when liveness reminders are disabled. `* Monitoring recovered` marks recovery. Follow any new instructions if the failure changes.

## Verbose and Debug Output

Two flags make the tool explain what it is doing. They are independent, so you can use either or both:

```sh
xbox_monitor <xbox_gamertag> --verbose --debug
```

* `VERBOSE_MODE`, `--verbose`: operational events, such as email alerts switched off because their settings are still placeholders, whether an email was actually delivered and when a fallback such as the title history is unavailable. It prints nothing per check, so an uneventful run stays quiet. It also expands the startup summary, which is where the configuration file, dotenv file, token cache, time zone and the source of each secret are named
* `DEBUG_MODE`, `--debug`: technical diagnostics, such as every Xbox Live call, how many settings the configuration file supplied, the parsed presence and title history behind each activity decision, the classification and text of each failure, how long the tool will wait before the next check and why, every read and write of the status and CSV files and where each secret was resolved from

A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

Debug lines are prefixed with `[DEBUG HH:MM:SS]`, then name the operation and list its details as comma-separated `key=value` fields, matching the sibling monitors:

```
[DEBUG 00:03:02] Connectivity check: url=https://xbox.example/probe, outcome=OK
[DEBUG 00:03:04] Presence check: outcome=failed, error=ConnectError: connection reset by peer, recovery_code=network.unavailable, streak=1
```

Debug output includes HTTP status, retries and error details. Both modes redact credentials and tokens. Application credential lengths are shown to help identify an incomplete copy. Webhook traces show the destination host without its private path.

Both flags take effect before the configuration file is read, so they still work when the problem you are chasing is the configuration file itself. A flag you type always wins over `VERBOSE_MODE` or `DEBUG_MODE` in the configuration file. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without the `* Email sent to ...` and `* Webhook sent through ...` lines, which is worth doing when alerts are frequent.

Delivery confirmations name the email recipient or webhook provider without repeating the subject or message body. `DELIVERY_CONFIRMATIONS = False` hides those optional success receipts. Event output, send attempts and errors remain visible. Explicit notification tests report their result once. Generated email subjects and webhook titles use readable service names without a program-name prefix.

## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-install-everything).

If `xbox_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-xbox-monitor-after-python-check). Use `pipx upgrade xbox_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `xbox_monitor --doctor "<xbox_gamertag>"` to see which settings are loaded.

## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved status file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.

A saved timestamp more than five minutes ahead of the machine clock is not used as history, because the tool wrote that file itself and a clock moved backwards is the usual reason. Monitoring warns, keeps the saved entry and times it from the moment it starts, so the run continues. Check the system clock if the warning repeats.
