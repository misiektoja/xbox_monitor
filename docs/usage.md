# Usage

<a id="command-format"></a>
## Command Format by Installation Method

Examples use the PyPI command. For a downloaded script, run commands from the directory containing `xbox_monitor.py` and keep the same arguments:

| Installation | Command |
| --- | --- |
| PyPI or pipx | `xbox_monitor [OPTIONS]` |
| Manual script on macOS or Linux | `python3 xbox_monitor.py [OPTIONS]` |
| Manual script on Windows | `python xbox_monitor.py [OPTIONS]` |

For example, `xbox_monitor --setup` becomes `python3 xbox_monitor.py --setup` on macOS or Linux. Use `python` on Windows. Replace placeholders such as `"<xbox_gamertag>"` with an Xbox gamertag, quoted when it contains spaces.

The manual-script examples assume the current directory contains `xbox_monitor.py`. Commands printed by setup, Doctor and recovery messages use the running interpreter and the full script path. Packaged installations use the running interpreter with `-m xbox_monitor`.

For first-time configuration, follow [Setup & First Run](setup-and-first-run.md). Use [Doctor Preflight](troubleshooting.md#doctor-preflight) to check a setup before monitoring.

## User Information Display Mode

The tool can print a detailed view of an Xbox profile. This mode shows the information once and exits rather than monitoring.

Use `-i` or `--info` with the gamertag:

```sh
xbox_monitor <xbox_gamertag> -i
```

If `MS_APP_CLIENT_ID` and `MS_APP_CLIENT_SECRET` are not stored anywhere, pass them with `-u` and `-w`:

```sh
xbox_monitor <xbox_gamertag> -i -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
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
xbox_monitor <xbox_gamertag> -i --friends
```

To also show the most recently earned achievements, add `-r` or `--recent-achievements`:

```sh
xbox_monitor <xbox_gamertag> -i --recent-achievements
```

Limit how many items are shown with `-m` for games and `-n` for achievements:

```sh
xbox_monitor <xbox_gamertag> -i -r -m 10 -n 5
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_info.png" alt="xbox_monitor_info" width="100%"/>
</p>

## Monitoring Mode

To monitor a user, pass their Xbox Live gamertag:

```sh
xbox_monitor <xbox_gamertag>
```

Set `XBOX_GAMERTAG` in the configuration file to monitor the same account without naming it every time. `--setup` offers to save it for you. A gamertag passed as an argument always wins over the saved one.

If the credentials are not stored anywhere, pass them with `-u` and `-w`:

```sh
xbox_monitor <xbox_gamertag> -u "your_ms_application_client_id" -w "your_ms_application_secret_value"
```

The first run performs the [OAuth2 authorization](setup-and-first-run.md#first-authorization) once and saves the tokens.

The tool runs until interrupted with `Ctrl+C`. Use `tmux` or `screen` to keep it running.

You can monitor several players by running several copies.

Output is written to `xbox_monitor_<xbox_gamertag>.log`. Change it with `XBOX_LOGFILE` or switch it off with `DISABLE_LOGGING`, `-d` or `--disable-logging`.

Set `ASCII_LOG_SEPARATORS` to `"Auto"`, the default, to use ASCII separator-only lines on Windows, `"On"` to use them everywhere or `"Off"` to keep Unicode separators in logs on every system. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

Set `TRUNCATE_CHARS` or use the `--truncate` flag to cut each screen line to a maximum width, which stops long game titles from wrapping. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. Truncation needs the optional `wcwidth` library to measure display width. If it is missing, the tool says so at startup and leaves lines untouched.

Names that come from Xbox Live, such as game titles and profile text, can contain terminal control sequences. They are removed before the text reaches the screen, the log file, the CSV file or an email, so a crafted name cannot clear your screen or overwrite a line that was already printed. Error messages are also checked for your secrets before they are shown or logged.

The timestamp and last status are saved after every change, so the last status survives a restart. Set `XBOX_STATUS_FILE` or use the `--status-file` flag to keep it somewhere other than `xbox_<xbox_gamertag>_last_status.json` in the current directory:

```sh
xbox_monitor <xbox_gamertag> --status-file ~/xbox/last_status.json
```

The status file is written through a temporary file in the same directory, so an interrupted run cannot leave a half-written file behind.

## Startup Summary

Monitoring mode prints the settings that are actually in effect before the first check:

```
* Target:                       misiektoja
* Polling intervals:            [offline: 3 minutes] [online: 1 minute]
* Notifications (email):        On (status changes, game changes, errors)
* Notifications (webhook):      On (online and offline changes, errors)
* Output:                       xbox_monitor_misiektoja.log
* Config:                       xbox_monitor.conf
* Dotenv:                       .env
* More details:                 use --verbose or --debug
```

Optional features appear once you switch them on. `TLS verification` appears here whenever certificate checking is off.

`--verbose` or `--debug` replaces this with the complete list, in the order it prints: the tolerated offline gap, the mail server and the masked recipient, the webhook service alerts go to and whether that channel is switched on, whether the delivery confirmations are printed, the log file, the liveness interval, the CSV file, the status file, the token cache, the truncation width, the process id, the Python version, the operating system, the resolved time zone, the install method, which secrets came from the dotenv file, the environment, the configuration file or the command line, whether certificate checking is on, how log separators are written, whether colour is actually in use and the two flags themselves.

The sibling monitors print the same rows in the same order, so a setting sits in the same place whichever of them you are reading. Each channel's own settings are indented under it. The token cache row is the one addition, since only this tool signs in through Microsoft.

The log file always receives the complete list, whichever view the terminal was shown, so a log attached to a bug report carries every effective setting.

## Email Notifications

To be told when a user gets online or offline, set `ACTIVE_INACTIVE_NOTIFICATION` to `True` or use `-a`:

```sh
xbox_monitor <xbox_gamertag> -a
```

To be told when a user starts, stops or changes a game, set `GAME_CHANGE_NOTIFICATION` to `True` or use `-g`:

```sh
xbox_monitor <xbox_gamertag> -g
```

Xbox reports its own dashboard surfaces the same way it reports a game, so Home, the Xbox app and guide, the Microsoft Store, Game Pass, Edge and Settings are ignored. Opening one of them does not start a game session, send a game notification or add to the played time in the offline summary.

To be told about every status change, online, away or offline, set `STATUS_NOTIFICATION` to `True` or use `-s`:

```sh
xbox_monitor <xbox_gamertag> -s
```

To stop the error email, which is on by default, set `ERROR_NOTIFICATION` to `False` or use `-e`:

```sh
xbox_monitor <xbox_gamertag> -e
```

The error alert fires at once for a failure that cannot clear on its own, such as expired credentials or a profile that stopped sharing its activity. A failure that can clear on its own, such as a timeout or a rate limit, is alerted on only once it has lasted **5 minutes**, so a short outage does not reach you. Either way the alert is sent once per channel. A channel that could not deliver is tried again on a later failing check, after **5 minutes** at first and then after twice the previous wait, up to an hour. The alert is not repeated until a check succeeds. The same rule governs the webhook error alert.

Set the [SMTP settings](configuration.md#smtp-settings) first.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_email_notifications.png" alt="xbox_monitor_email_notifications" width="80%"/>
</p>

## Webhook Notifications

Alerts can also go to a **Discord** channel or an **ntfy** topic. Once the [webhook settings](configuration.md#webhook-settings) name a destination, each event type is switched on separately, the same way email alerts are: the user getting online or offline, a game starting, changing or stopping, every status change including away, plus monitoring errors.

The same settings have command-line equivalents for one run. Naming any single alert also switches the channel on:

```sh
xbox_monitor <xbox_gamertag> --webhook-game-change
xbox_monitor <xbox_gamertag> --webhook --no-webhook-error-notify
xbox_monitor <xbox_gamertag> --webhook-url <url>
```

`--webhook-url` leaves the private URL in your shell history, so prefer `--set-webhook-url` for anything permanent.

Verify the destination without starting monitoring:

```sh
xbox_monitor --send-test-webhook
```

A failed delivery is retried once. A rate limit waits the delay the service asked for and bounds it. Redirects are never followed. When both channels are enabled, each is delivered independently: an alert that reached Discord is not sent again just because the email failed.

## CSV Export

To save every reported activity to a CSV file, set `CSV_FILE` or use `-b`:

```sh
xbox_monitor <xbox_gamertag> -b xbox_gamer_tag.csv
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
pkill -USR1 -f "xbox_monitor <xbox_gamertag>"
```

Windows supports a limited set of signals, so this works only on Linux, Unix and macOS.

## Terminal Colours

Terminal output is coloured by default. Colour switches itself off when the output is not an interactive terminal, when `TERM` is unset or `dumb`, when `NO_COLOR` is set and when the output is piped or redirected, so a log file or a piped run never contains escape sequences.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

Turn it off for one run:

```sh
xbox_monitor <xbox_gamertag> --no-color
```

Turn it off permanently in the configuration file:

```python
COLORED_OUTPUT = False
```

On Windows, install [colorama](https://pypi.org/project/colorama/) for colours in the older Command Prompt. Windows Terminal needs nothing extra.

Each part of the output has a logical name. `COLOR_THEME` in the configuration file overrides only the names it lists. Combine attributes with spaces or `+`, for example `"bright_cyan bold"` or `"red underline"`. Valid colours are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and their `bright_` variants, plus the `bold`, `dim`, `underline` and `blink` attributes. An empty string leaves that part uncoloured.

Generated configuration files ship this block commented out, so the built-in defaults apply and a later change to them reaches you. Overrides you added are written back as a real block when setup rebuilds the file, so they are not lost. Delete the block or edit only the entries you want to change:

```python
COLOR_THEME = {
    "game": "bright_magenta bold",
    "duration": "cyan",
}
```

| Theme key | Default | What it colours |
| --- | --- | --- |
| `header` | `bright_cyan` | Report and wizard headings, plus the tool name in the startup banner |
| `section` | `bright_white` | Section names and every command the tool tells you to run |
| `username` | `bright_cyan underline` | The monitored gamertag, the detected install method and wizard menu numbers |
| `id` | `bright_magenta` | The XUID |
| `status_active` | `green` | An online presence or a game that just started |
| `status_away` | `yellow` | An away presence |
| `status_inactive` | `red` | An inactive presence or a game that just stopped |
| `status_offline` | `red` | An offline presence |
| `status_other` | `white` | A presence value the tool does not recognise |
| `game` | `bright_yellow` | Game titles |
| `platform` | `blue` | Console names and the platform tag beside a game |
| `achievement` | `bright_green` | Gamerscore and achievement names |
| `duration` | `green` | Time spans such as `3 hours, 21 minutes` |
| `status_change` | `yellow` | The `changed status` and `changed game` part of a change report |
| `timestamp_label` | *(empty)* | The `Timestamp:` label, left uncoloured by default |
| `timestamp_value` | `cyan` | The timestamp itself |
| `info` | `cyan` | `To fix:` lines, notes, prompts and default markers |
| `warning` | `yellow` | `* Warning:` lines and `[WARN]` rows |
| `error` | `red` | `* Error:` lines and `[FAIL]` rows |
| `signal` | `yellow` | `* Signal ... received` lines |
| `email` | `bright_cyan` | Lines reporting an email being sent |
| `webhook` | `bright_blue` | Lines reporting a webhook being sent |
| `date` | `magenta` | Single dates and times |
| `date_range` | `magenta` | Date and time ranges |
| `boolean_true` | `green` | `True`, `Enabled`, `On` and `[PASS]` rows |
| `boolean_false` | `red` | `False`, `Disabled` and `Off` |
| `count_up` | `green` | A count that went up, with the `(+n)` beside it |
| `count_down` | `red` | A count that went down, with the `(-n)` beside it |
| `link` | `blue underline` | URLs |
| `help_heading` | `bright_cyan bold` | The `--help` group headings and example task names |
| `help_usage` | `bright_white bold` | The `usage:` label |
| `help_option` | `bright_green` | Option names such as `--doctor` |
| `help_metavar` | `yellow` | The value each option takes, such as a path or a number of seconds |
| `help_placeholder` | `bright_magenta` | Values to replace in the help examples |
| `help_command` | `bright_white` | The commands in the help examples |
| `help_comment` | `bright_black` | The `#` comment above each help example |
| `help_default` | `bright_black` | The `(default: ...)` notes |

## Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to colour logs.

The bundled recipe follows the same colours as the live output. It also covers the other monitors in the family, so one copy in `~/.grc/` colours every tool's logs.

Add this to your GRC config at `~/.grc/grc.conf`:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Copy [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/grc/conf.monitor_logs) to `~/.grc/` and the log files are coloured when read through `grc`:

```sh
grc tail -F -n 100 xbox_monitor_<xbox_gamertag>.log
```
