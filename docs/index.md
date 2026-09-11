# xbox_monitor

Powerful tool for real-time monitoring of **Xbox Live players' activities**.

<a id="-quick-install"></a>
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

- **Real-time tracking** of Xbox Live users' gaming activity, including when a user gets online or offline and which games they play
- **Basic statistics for user activity**: duration in different states, time spent playing a game, overall time and number of games played in a session
- **Detailed user information** display mode covering XUID, online status and last online date, platform, account tier, gamerscore, real name, location, friends count and optionally the friends list, recently played games with last played date and total play time, plus recently earned achievements
- **Activity detection for appear-offline users**, using title history to report gaming activity even when the monitored profile is set to Appear Offline
- **Email notifications** for various events: the user gets online, away or offline, starts, finishes or changes a game, plus monitoring errors
- **Webhook notifications** to a Discord channel or an ntfy topic, with the same events switched on separately from email
- **Guided setup** with `--setup`, which collects the credentials, runs the one-time authorization and writes the config and dotenv files
- **Preflight diagnostics** with `--doctor`, which checks the whole setup without writing anything
- **CSV export** of every reported activity, with **status persistence** across restarts
- **Coloured terminal output** with a configurable theme, switched off automatically when the output is redirected
- **Built-in OAuth2 authentication** with manual authorization support
- **Smart session continuity**: short offline interruptions are handled and session statistics are preserved
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments
- **Control of the running copy** through signals
- **Functional, procedural Python** with minimal OOP

## Screenshots

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="90%"/>
</p>

<a id="common-commands"></a>
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
