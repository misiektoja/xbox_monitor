# xbox_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/xbox_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/xbox_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/xbox_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.11+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/xbox_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/xbox_monitor?style=flat-square&color=green" alt="Last Commit" />
</p>

Powerful tool for real-time monitoring of **Xbox Live players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="85%"/>
</p>

**Full documentation: [misiektoja.github.io/xbox_monitor](https://misiektoja.github.io/xbox_monitor/)**

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/xbox_monitor/installation/#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install xbox_monitor
```

Run the setup wizard:

```sh
xbox_monitor --setup
```

Review the target, credentials and alerts before saving. See [Setup & First Run](https://misiektoja.github.io/xbox_monitor/setup-and-first-run/) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/xbox_monitor/installation/).

## Features

### Activity Tracking

* **Gaming activity**: Track status, game starts, finishes and changes.
* **Appear Offline**: Detect gaming activity from title history when presence is hidden.
* **Session statistics**: Measure state and game durations, preserving statistics through short offline interruptions.

### Profile Insights

* **Profile details**: View XUID, status, platform, account tier, gamerscore and friends.
* **Games and achievements**: See recent games, playtime and earned achievements.

### Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save reported activity with timestamps.
* **Saved status**: Retain monitoring state across restarts.

### Setup and Configuration

* **Guided setup**: Configure credentials and complete OAuth2 authorization with `--setup`.
* **Preflight checks**: Check readiness with `--doctor` without writing files.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.

## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](https://misiektoja.github.io/xbox_monitor/usage/#command-format) for manual-script equivalents.

Replace the target placeholders with an Xbox gamertag, quoted when it contains spaces. Monitoring requires the [Microsoft Entra application credentials](https://misiektoja.github.io/xbox_monitor/setup-and-first-run/#microsoft-entra-application-credentials) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `xbox_monitor --setup` |
| Start monitoring with saved credentials | `xbox_monitor "<xbox_gamertag>"` |
| Check setup before monitoring | `xbox_monitor --doctor "<xbox_gamertag>"` |
| Enter or replace credentials through hidden prompts | `xbox_monitor --set-ms-app-credentials` |
| Use a specific configuration and secrets file | `xbox_monitor --config-file xbox_monitor.conf --env-file .env "<xbox_gamertag>"` |
| Show profile details once | `xbox_monitor "<xbox_gamertag>" -i` |
| List every supported command-line option | `xbox_monitor --help` |

Complete [First Authorization](https://misiektoja.github.io/xbox_monitor/setup-and-first-run/#first-authorization) before relying on Doctor. Doctor checks saved tokens and does not create them.

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/xbox_monitor/setup-and-first-run/#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](https://misiektoja.github.io/xbox_monitor/usage/). If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/xbox_monitor/troubleshooting/#doctor-preflight).

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/xbox_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/xbox_monitor/setup-and-first-run/) | The guided setup, Microsoft Entra application credentials, the first authorization, the privacy settings the monitored account needs |
| [Configuration](https://misiektoja.github.io/xbox_monitor/configuration/) | Config file, time zone, SMTP, webhooks, TLS verification, check intervals, storing secrets |
| [Usage](https://misiektoja.github.io/xbox_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals, terminal colours |
| [Troubleshooting](https://misiektoja.github.io/xbox_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/xbox_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/xbox_monitor/about/) | Change log, contributing, security, license, support |

## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/xbox_monitor/blob/main/RELEASE_NOTES.md).

## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/xbox_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/xbox_monitor/blob/main/CODE_OF_CONDUCT.md).

## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/xbox_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/xbox_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/xbox_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/xbox_monitor/blob/main/THIRD_PARTY_NOTICES.md).

## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/xbox_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
