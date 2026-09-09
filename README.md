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

**Full documentation: [misiektoja.github.io/xbox_monitor](https://misiektoja.github.io/xbox_monitor/)**

### 🚀 Quick Install

```sh
pip install xbox_monitor
```

Check the setup before relying on it. The preflight report writes nothing and exits non-zero when something is wrong:

```sh
xbox_monitor --doctor <xbox_gamer_tag>
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="85%"/>
</p>

## Features

- **Real-time tracking** of Xbox Live users' gaming activity, including when a user gets online or offline and which games they play
- **Basic statistics for user activity**: duration in different states, time spent playing a game, overall time and number of games played in a session
- **Detailed user information** display mode covering XUID, online status, platform, account tier, gamerscore, friends, recently played games and recently earned achievements
- **Activity detection for appear-offline users**, using title history to report gaming activity even when the monitored profile is set to Appear Offline
- **Email notifications** for various events, configurable per event
- **Preflight diagnostics** with `--doctor`, which checks the whole setup without writing anything
- **CSV export** of every reported activity, with **status persistence** across restarts
- **Built-in OAuth2 authentication** with manual authorization support
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/xbox_monitor/installation/) | Requirements, installing from PyPI or by hand, upgrading |
| [Setup & First Run](https://misiektoja.github.io/xbox_monitor/setup-and-first-run/) | Microsoft Entra application credentials, the first authorization, the privacy settings the monitored account needs |
| [Configuration](https://misiektoja.github.io/xbox_monitor/configuration/) | Config file, time zone, SMTP, TLS verification, check intervals, storing secrets |
| [Usage](https://misiektoja.github.io/xbox_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals |
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
