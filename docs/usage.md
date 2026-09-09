# Usage

## User Information Display Mode

The tool can print a detailed view of an Xbox profile. This mode shows the information once and exits rather than monitoring.

Use `-i` or `--info` with the gamertag:

```sh
xbox_monitor <xbox_gamer_tag> -i
```

If `MS_APP_CLIENT_ID` and `MS_APP_CLIENT_SECRET` are not stored anywhere, pass them with `-u` and `-w`:

```sh
xbox_monitor <xbox_gamer_tag> -i -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

This displays:

- Gamertag and XUID
- Real name, location and bio, when available
- Account tier, Game Pass Core, Ultimate or Free
- Gamerscore
- Online status, last online timestamp and the last played title while the user is offline
- Platform information
- Friends count
- Recently played games with last played date and total play time

To also list every friend and their current activity, add `-f` or `--friends`:

```sh
xbox_monitor <xbox_gamer_tag> -i --friends
```

To also show the most recently earned achievements, add `-r` or `--recent-achievements`:

```sh
xbox_monitor <xbox_gamer_tag> -i --recent-achievements
```

Limit how many items are shown with `-m` for games and `-n` for achievements:

```sh
xbox_monitor <xbox_gamer_tag> -i -r -m 10 -n 5
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_info.png" alt="xbox_monitor_info" width="100%"/>
</p>

## Monitoring Mode

To monitor a user, pass their Xbox Live gamertag:

```sh
xbox_monitor <xbox_gamer_tag>
```

Set `XBOX_GAMERTAG` in the configuration file to monitor the same account without naming it every time. `--setup` offers to save it for you. A gamertag passed as an argument always wins over the saved one.

If the credentials are not stored anywhere, pass them with `-u` and `-w`:

```sh
xbox_monitor <xbox_gamer_tag> -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

The first run performs the [OAuth2 authorization](setup-and-first-run.md#first-authorization) once and saves the tokens.

The tool runs until interrupted with `Ctrl+C`. Use `tmux` or `screen` to keep it running.

You can monitor several players by running several copies.

Output is written to `xbox_monitor_<gamer_tag>.log`. Change it with `XBOX_LOGFILE`, or switch it off with `DISABLE_LOGGING`, `-d` or `--disable-logging`.

Set `ASCII_LOG_SEPARATORS` to `"Auto"`, the default, to use ASCII separator-only lines on Windows, `"On"` to use them everywhere, or `"Off"` to keep Unicode separators in logs on every system. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

The timestamp and last status are saved to `xbox_<gamer_tag>_last_status.json` after every change, so the last status survives a restart.

## Email Notifications

To be told when a user gets online or offline, set `ACTIVE_INACTIVE_NOTIFICATION` to `True` or use `-a`:

```sh
xbox_monitor <xbox_gamer_tag> -a
```

To be told when a user starts, stops or changes a game, set `GAME_CHANGE_NOTIFICATION` to `True` or use `-g`:

```sh
xbox_monitor <xbox_gamer_tag> -g
```

To be told about every status change, online, away or offline, set `STATUS_NOTIFICATION` to `True` or use `-s`:

```sh
xbox_monitor <xbox_gamer_tag> -s
```

To stop the error email, which is on by default, set `ERROR_NOTIFICATION` to `False` or use `-e`:

```sh
xbox_monitor <xbox_gamer_tag> -e
```

The error email fires only for a credential failure, since every other kind of failure clears on its own.

Set the [SMTP settings](configuration.md#smtp-settings) first.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_email_notifications.png" alt="xbox_monitor_email_notifications" width="80%"/>
</p>

## CSV Export

To save every reported activity to a CSV file, set `CSV_FILE` or use `-b`:

```sh
xbox_monitor <xbox_gamer_tag> -b xbox_gamer_tag.csv
```

The file is created if it does not exist.

## Signal Controls (macOS/Linux/Unix)

Signals change the behaviour of a running copy without a restart.

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when the user gets online or offline (-a) |
| USR2 | Toggle email notifications when the user starts, stops or changes a game (-g) |
| CONT | Toggle email notifications for every status change, online, away or offline (-s) |
| TRAP | Increase the check interval used while the user is online, by 30 seconds |
| ABRT | Decrease the check interval used while the user is online, by 30 seconds |
| HUP | Reload secrets from the dotenv file |

Send them with `kill` or `pkill`:

```sh
pkill -USR1 -f "xbox_monitor <xbox_gamer_tag>"
```

Windows supports a limited set of signals, so this works only on Linux, Unix and macOS.

## Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to colour logs.

Add this to your GRC config at `~/.grc/grc.conf`:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Copy [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/grc/conf.monitor_logs) to `~/.grc/` and the log files are coloured when read through `grc`:

```sh
grc tail -F -n 100 xbox_monitor_<gamer_tag>.log
```
