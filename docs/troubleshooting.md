# Troubleshooting

## Doctor Preflight

`--doctor` checks the whole setup and exits. It writes no files, so running it costs nothing:

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

Each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`, colour-coded by status when colour output is on. Every `[WARN]` and `[FAIL]` row carries an indented `To fix:` line under its marker, plus a `Guide:` link when a documentation page covers that row. A `[SKIP]` row names a check that could not run and says why. An explicitly selected dotenv path that does not exist is reported as a warning with the path and recovery command. A warning describes a working setup worth reviewing. Only a failure changes the exit code, which is 1 when anything failed and 0 otherwise, so the report can be used in a script.

When both the input and the output are a terminal and a channel passed, the report offers one real test message for that channel. Nothing is sent without a separate yes and the result is counted in the summary. The webhook check validates the settings without contacting Discord or ntfy, so nothing is published until you approve the test.

Doctor never starts the interactive sign-in, because that writes a token file. A missing token cache is reported as a warning naming the command that creates one, which is `--setup` or the first monitoring run.

The report ends with a **Next steps** block naming the command that starts monitoring, carrying the same `--config-file` and `--env-file` this run checked. It carries the target this run used, leaves it out when the configuration file already supplies one and otherwise shows `<xbox_gamertag>` for you to replace. While a check is failing it asks for the failures first.

## Setup and Secret Commands

`--setup`, `--set-ms-app-credentials`, `--set-smtp-password` and `--set-webhook-url` need an interactive terminal, since the values they collect must stay hidden. Run outside one they explain that and exit non-zero rather than reading a secret from a pipe.

Ctrl+C is safe at every question. During `--setup` it reports that the destination files were not changed. During a secret command it says the entry was cancelled, names the command that resumes it and leaves the dotenv file unchanged. Answering `n` at a replace question instead says the saved values were left as they are. After `--setup` has saved, Ctrl+C only skips the optional doctor run or the offer to start monitoring. At the doctor's own optional delivery prompts it ends the run instead, since nothing is waiting to be written there.

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

The banner that says nothing changed prints in any mode: `* Monitoring healthy for <xbox_gamertag>` with what was checked, followed by `Liveness check, timestamp:`. It is timed rather than counted in checks, so it appears once per `LIVENESS_CHECK_INTERVAL` of quiet, measured from the last thing the run printed. A monitoring failure is reported as `* Error: <what failed> (retrying in <time>)`, with the `To fix:` paragraph under it the first time that category appears. Every monitor in this family prints that same line. During a long outage the failure is reported in full once, then the tool stays quiet and reminds you once an hour with `* Monitoring degraded for <xbox_gamertag>`, the summary of what is still failing, when it started and how many checks have failed so far, so a two-day outage is a handful of lines rather than one block per check. The reminder has its own clock and does not depend on `LIVENESS_CHECK_INTERVAL`, so it keeps coming when the banner is off. When the failure clears, `* Monitoring recovered for <xbox_gamertag>` reports how long it lasted. An outage that starts failing differently is still one outage: a lost connection that reads as a timeout on one check and as an unreachable host on the next prints nothing new, a change to another kind of failure that clears on its own is one line, `* Monitoring failure changed for <xbox_gamertag>. <what fails now>`, and a change to a failure that needs you is reported in full.

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

Every outbound call reports `outcome=OK` or `outcome=failed` with an `error=` field. Both modes redact every secret, including your Microsoft application client ID and secret, the Xbox tokens, your SMTP password and your webhook URL. A secret is reported by name and source rather than by value. A webhook delivery is traced by destination host only, never by its private path. The client ID and secret also report their length, because a value truncated while copying is a common reason sign-in stops working. Your SMTP password reports only that it is set.

Both flags take effect before the configuration file is read, so they still work when the problem you are chasing is the configuration file itself. A flag you type always wins over `VERBOSE_MODE` or `DEBUG_MODE` in the configuration file.
