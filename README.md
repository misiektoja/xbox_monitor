# xbox_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/xbox_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/xbox_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/xbox_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.8+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/xbox_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/xbox_monitor?style=flat-square&color=green" alt="Last Commit" />
</p>

Powerful tool for real-time monitoring of **Xbox Live players' activities**.

### 🚀 Quick Install
```sh
pip install xbox_monitor
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="85%"/>
</p>

<a id="features"></a>
## Features

- **Real-time tracking** of Xbox Live users' gaming activity (including detection when a user gets online or offline and played games)
- **Basic statistics for user activity** (how long in different states, how long a game is played, overall time and number of played games in the session etc.)
- **Detailed user information** display mode providing comprehensive Xbox profile insights, including **XUID**, **online status** and **last online date**, **platform information**, **account tier** (Game Pass Core/Ultimate or Free), **gamerscore**, **real name**, **location**, **friends count** and optionally **friends list** with activity details, **recently played games** with **last played date** and **total play time**, and **recently earned achievements**
- **Activity detection for appear-offline users** - uses title history to detect and report gaming activity even when the monitored user's profile is set to "Appear Offline"
- **Email notifications** for different events (player gets online, away or offline and starts, finishes or changes a game, errors)
- **Saving all user activities** with timestamps to a **CSV file**
- **Built-in OAuth2 authentication** with manual authorization support
- **Status persistence** - automatically saves last status to JSON file to resume monitoring after restart
- **Smart session continuity** - handles short offline interruptions and preserves session statistics
- **Flexible configuration** - support for config files, dotenv files, environment variables and command-line arguments
- Possibility to **control the running copy** of the script via signals
- **Functional, procedural Python** (minimal OOP)

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
   * [Upgrading](#upgrading)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [Azure AD App Credentials](#azure-ad-app-credentials)
   * [User Privacy Settings](#user-privacy-settings)
   * [Time Zone](#time-zone)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [User Information Display Mode](#user-information-display-mode)
   * [Monitoring Mode](#monitoring-mode)
   * [Email Notifications](#email-notifications)
   * [CSV Export](#csv-export)
   * [Check Intervals](#check-intervals)
   * [Debug Mode](#debug-mode)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [License](#license)

<a id="requirements"></a>
## Requirements

* Python 3.8 or higher
* Libraries: [python-xbox](https://github.com/tr4nt0r/python-xbox), `requests`, `python-dateutil`, `httpx`, `pytz`, `tzlocal`, `python-dotenv`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install xbox_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[xbox_monitor.py](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/xbox_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install python-xbox requests python-dateutil httpx pytz tzlocal python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

<a id="upgrading"></a>
### Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install xbox_monitor -U
```

If you installed manually, download the newest *[xbox_monitor.py](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/xbox_monitor.py)* file to replace your existing installation.

<a id="quick-start"></a>
## Quick Start

- Grab your [Azure app credentials](#azure-ad-app-credentials) and track the `xbox_gamer_tag` gaming activities:


```sh
xbox_monitor <xbox_gamer_tag> -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

Or if you installed [manually](#manual-installation):

```sh
python3 xbox_monitor.py <xbox_gamer_tag> -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

To get the list of all supported command-line arguments / flags:

```sh
xbox_monitor --help
```

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `xbox_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
xbox_monitor --generate-config > xbox_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
xbox_monitor --generate-config xbox_monitor.conf
```

> **IMPORTANT**: On **Windows PowerShell**, using redirection (`>`) can cause the file to be encoded in UTF-16, which will lead to "null bytes" errors when running the tool. It is highly recommended to provide the filename directly as an argument to `--generate-config` to ensure UTF-8 encoding.

Edit the `xbox_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

<a id="azure-ad-app-credentials"></a>
### Azure AD App Credentials

Log in to [Azure AD](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) and register new app.

- Name your app (e.g. *xbox_monitor*)
- For account type select **Personal Microsoft accounts only**
- For redirect URL select **Web** type and put: **http://localhost/auth/callback**

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app1.png" alt="xbox_monitor_azure_ad_app1" width="90%"/>
</p>

Then copy value of **Application (client) ID** to `MS_APP_CLIENT_ID`.

Then next to **Client credentials** click **Add a certificate or secret**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app2.png" alt="xbox_monitor_azure_ad_app2" width="90%"/>
</p>

Add a new client secret with long expiration date (like 2 years) and some description (e.g. *xbox_monitor_secret*).

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app3.png" alt="xbox_monitor_azure_ad_app3" width="60%"/>
</p>

Copy the contents from **Value** column to `MS_APP_CLIENT_SECRET`.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app4.png" alt="xbox_monitor_azure_ad_app4" width="100%"/>
</p>

After performing authentication the token will be saved into the default `xbox_tokens.json` file in current working dir (you can change it via `MS_AUTH_TOKENS_FILE`).

Provide the `MS_APP_CLIENT_ID` and `MS_APP_CLIENT_SECRET` secrets using one of the following methods:
 - Pass it at runtime with `-u` / `--ms-app-client-id` and `-w` / `--ms-app-client-secret`
 - Set it as an [environment variable](#storing-secrets) (e.g. `export MS_APP_CLIENT_ID=...; export MS_APP_CLIENT_SECRET=...`)
 - Add it to [.env file](#storing-secrets) (`MS_APP_CLIENT_ID=...` and `MS_APP_CLIENT_SECRET=...`) for persistent use

Fallback:
 - Hard-code it in the code or config file

If you store the `MS_APP_CLIENT_ID` and `MS_APP_CLIENT_SECRET` in a dotenv file you can update their values and send a `SIGHUP` signal to the process to reload the file with the new secret values without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

<a id="user-privacy-settings"></a>
### User Privacy Settings

In order to monitor Xbox user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Xbox profile privacy & online safety settings](https://account.xbox.com/Settings).

The value in **Others can see if you're online** (and preferably also **Others can see your Xbox profile details**) should be set to **Friends** or **Everyone**.

<a id="time-zone"></a>
### Time Zone

By default, time zone is auto-detected using `tzlocal`. You can set it manually in `xbox_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

You can get the list of all time zones supported by pytz like this:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

<a id="smtp-settings"></a>
### SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `xbox_monitor.conf` file.

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
xbox_monitor --send-test-email
```

<a id="storing-secrets"></a>
### Storing Secrets

It is recommended to store secrets like `MS_APP_CLIENT_ID`, `MS_APP_CLIENT_SECRET` or `SMTP_PASSWORD` as either an environment variable or in a dotenv file.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export MS_APP_CLIENT_ID="your_ms_application_client_id"
export MS_APP_CLIENT_SECRET="your_ms_application_secret_value"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
MS_APP_CLIENT_ID="your_ms_application_client_id"
MS_APP_CLIENT_SECRET="your_ms_application_secret_value"
SMTP_PASSWORD="your_smtp_password"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
xbox_monitor <xbox_gamer_tag> --env-file /path/.env-xbox_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
xbox_monitor <xbox_gamer_tag> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

<a id="usage"></a>
## Usage

<a id="user-information-display-mode"></a>
### User Information Display Mode

The tool provides a detailed user information display mode that shows comprehensive Xbox profile insights. This mode displays information once and then exits (it does not run continuous monitoring).

To get detailed user information for Xbox user's gamer tag (`xbox_gamer_tag` in the example below), use the `-i` or `--info` flag:

```sh
xbox_monitor <xbox_gamer_tag> -i
```

If you have not set `MS_APP_CLIENT_ID` and `MS_APP_CLIENT_SECRET` secrets, you can use `-u` and `-w` flags:

```sh
xbox_monitor <xbox_gamer_tag> -i -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

This displays:
- Gamertag and XUID
- Real name and Location (if available)
- Account Tier (Game Pass Core/Ultimate or Free)
- Gamerscore
- Online status and last online timestamp
- Platform information
- Friends count
- Recently played games with last played date and total play time

To also list all friends and their current activity, add the `-f` or `--friends` flag:

```sh
xbox_monitor <xbox_gamer_tag> -i --friends
```

To also display the list of most recently earned achievements, add the `-r` or `--recent-achievements` flag:

```sh
xbox_monitor <xbox_gamer_tag> -i --recent-achievements
```

You can limit the number of displayed items using `-m` (for games) and `-n` (for achievements):

```sh
xbox_monitor <xbox_gamer_tag> -i -r -m 10 -n 5
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_info.png" alt="xbox_monitor_info" width="100%"/>
</p>

<a id="monitoring-mode"></a>
### Monitoring Mode

To monitor specific user activity, just type the player's Xbox Live gamer tag (`xbox_gamer_tag` in the example below):

```sh
xbox_monitor <xbox_gamer_tag>
```

If you have not set `MS_APP_CLIENT_ID` and `MS_APP_CLIENT_SECRET` secrets, you can use `-u` and `-w` flags:

```sh
xbox_monitor <xbox_gamer_tag> -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

By default, the tool looks for a configuration file named `xbox_monitor.conf` in:
 - current directory
 - home directory (`~`)
 - script directory

 If you generated a configuration file as described in [Configuration](#configuration), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:


```sh
xbox_monitor <xbox_gamer_tag> --config-file /path/xbox_monitor_new.conf
```

The first time the tool is executed it will perform OAuth2 authentication using the data you provided.

It will generate a URL you need to paste in your web browser and authorize the tool.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_oauth1.png" alt="xbox_monitor_oauth1" width="90%"/>
</p>

The request in your web browser will be redirected to localhost. You will receive an error indicating a connection failure. Ignore this and simply copy the part after `?code=` in the callback URL and paste it into the tool.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_oauth2.png" alt="xbox_monitor_oauth2" width="70%"/>
</p>

The tool will save the token to a file specified in `MS_AUTH_TOKENS_FILE` configuration option, so it can be reused in case the tool is restarted (with no need to authenticate again).

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Xbox Live players by running multiple instances of the script.

The tool automatically saves its output to `xbox_monitor_<gamer_tag>.log` file. It can be changed in the settings via `XBOX_LOGFILE` configuration option or disabled completely via `DISABLE_LOGGING` / `-d` flag.

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

The tool also saves the timestamp and last status (after every change) to `xbox_<gamer_tag>_last_status.json` file, so the last status is available after the restart of the tool.

<a id="email-notifications"></a>
### Email Notifications

To enable email notifications when a user gets online or offline:
- set `ACTIVE_INACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
xbox_monitor <xbox_gamer_tag> -a
```

To be informed when a user starts, stops or changes the played game:
- set `GAME_CHANGE_NOTIFICATION` to `True`
- or use the `-g` flag

```sh
xbox_monitor <xbox_gamer_tag> -g
```

To get email notifications about any changes in user status (online/away/offline):
- set `STATUS_NOTIFICATION` to `True`
- or use the `-s` flag

```sh
xbox_monitor <xbox_gamer_tag> -s
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
xbox_monitor <xbox_gamer_tag> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_email_notifications.png" alt="xbox_monitor_email_notifications" width="80%"/>
</p>

<a id="csv-export"></a>
### CSV Export

If you want to save all reported activities of the Xbox Live user to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
xbox_monitor <xbox_gamer_tag> -b xbox_gamer_tag.csv
```

The file will be automatically created if it does not exist.

<a id="check-intervals"></a>
### Check Intervals

If you want to customize polling intervals, use `-k` and `-c` flags (or corresponding configuration options):

```sh
xbox_monitor <xbox_gamer_tag> -k 30 -c 120
```

* `XBOX_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online or away (seconds)
* `XBOX_CHECK_INTERVAL`, `-c`: check interval when the user is offline (seconds)

<a id="debug-mode"></a>
### Debug Mode

To enable full technical logging for authentication, presence tracking and activity detection, use the `--debug` flag:

```sh
xbox_monitor <xbox_gamer_tag> --debug
```

Alternatively, set `DEBUG_MODE` to `True` in your configuration file for persistent debug logging.

<a id="signal-controls-macoslinuxunix"></a>
### Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline (-a) |
| USR2 | Toggle email notifications when user starts/stops/changes the game (-g) |
| CONT | Toggle email notifications for all user status changes (online/away/offline) (-s) |
| TRAP | Increase the check timer for player activity when user is online (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online (by 30 seconds) |
| HUP | Reload secrets from .env file |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "xbox_monitor <xbox_gamer_tag>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
### Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 xbox_monitor_<gamer_tag>.log
```

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/xbox_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/xbox_monitor/blob/main/LICENSE).
