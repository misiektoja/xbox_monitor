# xbox_monitor

Powerful tool for real-time monitoring of **Xbox Live players' activities**.

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

## Get started

```sh
pip install xbox_monitor
```

Then run the guided setup:

```sh
xbox_monitor --setup
```

Check the setup before relying on it:

```sh
xbox_monitor --doctor <xbox_gamertag>
```

[Installation](installation.md) covers the requirements and the manual install. [Setup & First Run](setup-and-first-run.md) covers the guided setup, the Microsoft Entra application credentials, the first authorization and the privacy settings the monitored account needs.

## Screenshots

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor.png" alt="xbox_monitor_screenshot" width="90%"/>
</p>
