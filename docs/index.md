# xbox_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/xbox_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/xbox_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/xbox_monitor?style=flat-square&color=teal)](https://pypi.org/project/xbox-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/xbox_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/xbox_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.11+-blueviolet?style=flat-square)](https://pypi.org/project/xbox-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/xbox_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/xbox_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fxbox_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/xbox_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/xbox_monitor?style=flat-square&color=green)](https://github.com/misiektoja/xbox_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/xbox_monitor)

Powerful tool for real-time monitoring of **Xbox Live players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="85%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install xbox_monitor
```

Run the setup wizard:

```sh
xbox_monitor --setup
```

The wizard asks for the target, the Microsoft Entra application credentials and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the application credentials, the first authorization and the required privacy settings.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

<a id="features"></a>
## Features

### 🔍 Activity Tracking

* **Gaming activity**: Track status, game starts, finishes and changes.
* **Appear Offline**: Detect gaming activity from title history when presence is hidden.
* **Session statistics**: Measure state and game durations, preserving statistics through short offline interruptions.

### 📊 Profile Insights

* **Profile details**: View XUID, status, platform, account tier, gamerscore and friends.
* **Games and achievements**: See recent games, playtime and earned achievements.

### 🔔 Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save reported activity with timestamps.
* **Saved status**: Retain monitoring state across restarts.

### ⚙️ Setup and Configuration

* **Guided setup**: Configure credentials and complete OAuth2 authorization with `--setup`.
* **Preflight checks**: Check readiness with `--doctor` without writing files.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.
