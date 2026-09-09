# Getting help

Start with the [README](README.md). [Requirements](README.md#requirements), [Installation](README.md#installation) and [Quick Start](README.md#quick-start) cover most first-run problems, and [Configuration](README.md#configuration) explains every setting the tool reads.

## Check your setup first

Confirm which version you are running and that the notification channel actually works, then include the results when you ask:

```sh
xbox_monitor --version
xbox_monitor --send-test-email
```

Most reports come down to a Microsoft Entra application whose client ID or secret the sign-in endpoint no longer accepts, an expired token cache or an SMTP server that refuses the message. Rerun the failing command with `--debug` and keep the output.

## Where to ask

| You want to | Go to |
| --- | --- |
| Ask a question or discuss an idea | [Discussions](https://github.com/misiektoja/xbox_monitor/discussions) |
| Report something broken | [Open an issue](https://github.com/misiektoja/xbox_monitor/issues/new) |
| Request a capability | [Open an issue](https://github.com/misiektoja/xbox_monitor/issues/new) |
| Report a vulnerability | [Private security advisory](https://github.com/misiektoja/xbox_monitor/security/advisories/new), never a public issue |

## Before you post

Include the version, how you installed it (PyPI or manual script), your operating system, the monitored gamertag or XUID you passed and what you expected instead. Run the failing command with `--debug` and attach the relevant part of the log, which the tool writes unless you pass `--disable-logging`.

Never post your Microsoft application client ID or client secret, the generated token file, SMTP passwords, webhook URLs or a complete configuration file. Redact monitored gamertags if they matter to you.

## What to expect

This is a project maintained in spare time, so replies are best effort with no response time attached. Only the latest release receives fixes, so reproduce the problem on the current version before reporting it.

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
