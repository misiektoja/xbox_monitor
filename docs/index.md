# xbox_monitor

Powerful tool for real-time monitoring of **Xbox Live players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="85%"/>
</p>

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install xbox_monitor
```

Run the setup wizard:

```sh
xbox_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

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

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](usage.md#command-format) for manual-script equivalents.

Replace the target placeholders with an Xbox gamertag, quoted when it contains spaces. Monitoring requires the [Microsoft Entra application credentials](setup-and-first-run.md#microsoft-entra-application-credentials) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `xbox_monitor --setup` |
| Start monitoring with saved credentials | `xbox_monitor "<xbox_gamertag>"` |
| Check setup before monitoring | `xbox_monitor --doctor "<xbox_gamertag>"` |
| Enter or replace credentials through hidden prompts | `xbox_monitor --set-ms-app-credentials` |
| Use a specific configuration and secrets file | `xbox_monitor --config-file xbox_monitor.conf --env-file .env "<xbox_gamertag>"` |
| Show profile details once | `xbox_monitor "<xbox_gamertag>" -i` |
| List every supported command-line option | `xbox_monitor --help` |

Complete [First Authorization](setup-and-first-run.md#first-authorization) before relying on Doctor. Doctor checks saved tokens and does not create them.

The monitored account must expose the activity described in [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](usage.md). If a run fails, start with [Doctor Preflight](troubleshooting.md#doctor-preflight).

## Documentation

* [Installation](installation.md) - Python setup, package or manual install and upgrades
* [Setup & First Run](setup-and-first-run.md) - credentials, target selection and the setup wizard
* [Configuration](configuration.md) - settings, notifications and secret storage
* [Usage](usage.md) - monitoring, output and command options
* [Troubleshooting](troubleshooting.md) - Doctor checks and recovery steps
* [Testing](testing.md) - automated checks and documentation builds
* [About](about.md) - contributing, security, licensing and support
