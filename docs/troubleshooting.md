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

## Debug Output

To print full technical logging for authentication, presence tracking and activity detection, use `--debug`:

```sh
xbox_monitor <xbox_gamer_tag> --debug
```

Set `DEBUG_MODE` to `True` in the configuration file to keep it on.

`--debug` applies before the configuration file is read, so a saved `DEBUG_MODE = False` cannot switch off what the command line asked for. The terminal is not cleared while debug mode is on, so nothing scrolls away before you can read it.

Debug output is redacted. Known secret values, credential-shaped strings, authorization headers and tokens in URLs are replaced before anything is printed, so the output can be pasted into a public bug report. The technical detail behind an error is printed only in debug mode.
