# Troubleshooting

## Doctor Preflight

`--doctor` checks the whole setup and exits. It writes no files, so running it costs nothing:

```sh
xbox_monitor --doctor <xbox_gamer_tag>
```

The report covers six sections:

| Section | What it checks |
| --- | --- |
| **Environment** | The Python version against the supported minimum, and every required and optional dependency |
| **Configuration** | The config and dotenv files in use, which secrets are loaded and from where, the time zone, the polling intervals, TLS verification and every file the tool would write |
| **Authentication** | That the application credentials are set, that the token cache is present and private, and that Xbox Live still accepts the saved tokens |
| **Connectivity** | That the connectivity endpoint answers, using the configured URL, timeout and TLS setting |
| **Target** | That the monitored gamertag resolves and shares its activity |
| **Notifications** | Whether email alerts are on and, if so, whether the SMTP server accepts the configured login |

Each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`. A row that is not a pass carries a `To fix:` line and a link. A warning describes a working setup worth reviewing. Only a failure changes the exit code, which is 1 when anything failed and 0 otherwise, so the report can be used in a script.

When both the input and the output are a terminal and the email channel passed, the report offers one real test message. Nothing is sent without a separate yes, and the result is counted in the summary.

Doctor never starts the interactive sign-in, because that writes a token file. A missing token cache is reported as a warning naming the command that creates one.

## Error Messages and Recovery

Every reported problem carries a category, a one-line summary, a `To fix:` paragraph and a link. The category decides the advice, so the same failure reads the same way wherever it surfaces.

| What you see | What it usually means |
| --- | --- |
| The configuration file could not be loaded | A line in the config file is not a plain `SETTING = value` assignment. The message names the line |
| A required credential is missing | `MS_APP_CLIENT_ID` or `MS_APP_CLIENT_SECRET` is empty or still a placeholder |
| The Microsoft sign-in endpoint rejected the saved credentials | The refresh token expired or was revoked, or the application secret in Microsoft Entra expired |
| The Xbox token cache is not a saved token response | The token file is corrupt. Delete it and authorize again |
| That Xbox profile does not share its activity | A privacy setting on the monitored account, not a problem with your credentials |
| Xbox Live is rate limiting this application | The polling intervals are too short, or several copies share one application |
| This process ran out of file descriptors | A local limit rather than an Xbox Live problem. Raise it with `ulimit -n` or `LimitNOFILE=` under systemd |
| The SMTP server rejected the login | Providers such as Gmail need an app password rather than the account password |

While the same failure repeats, the fix paragraph is printed once and then suppressed until the category changes or a check succeeds, so the timestamps that show the tool is alive stay readable.

## Verbose and Debug Output

Two flags make the tool explain what it is doing. They are independent, so you can use either or both:

```sh
xbox_monitor <xbox_gamer_tag> --verbose --debug
```

* `VERBOSE_MODE`, `--verbose`: operational events, such as email alerts switched off because their settings are still placeholders, whether an email was actually delivered, when a run recovers from failures it reported, and when a fallback such as the title history is unavailable. It prints nothing per check, so an uneventful run stays quiet. It also expands the startup summary, which is where the configuration file, dotenv file, token cache, time zone and the source of each secret are named
* `DEBUG_MODE`, `--debug`: technical diagnostics, such as every Xbox Live call, how many settings the configuration file supplied, the parsed presence and title history behind each activity decision, the classification and text of each failure, how long the tool will wait before the next check and why, every read and write of the status and CSV files and where each secret was resolved from

A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

Debug lines are prefixed with `[DEBUG HH:MM:SS]`, then name the operation and list its details as comma-separated `key=value` fields, matching the sibling monitors:

```
[DEBUG 00:03:02] Connectivity check: url=https://xbox.example/probe, outcome=OK
[DEBUG 00:03:04] Presence check: outcome=failed, error=ConnectError: connection reset by peer, recovery_code=network.unavailable, streak=1
```

Every outbound call reports `outcome=OK` or `outcome=failed` with an `error=` field. Both modes redact every secret, including your Microsoft application client ID and secret, the Xbox tokens and your SMTP password, and report a secret by name and source rather than by value. The client ID and secret also report their length, because a value truncated while copying is a common reason sign-in stops working. Your SMTP password reports only that it is set.

Both flags take effect before the configuration file is read, so they still work when the problem you are chasing is the configuration file itself. A flag you type always wins over `VERBOSE_MODE` or `DEBUG_MODE` in the configuration file.
