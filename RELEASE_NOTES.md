# xbox_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 1.9.2 (TBD)

**Bug fixes**:

- **BUGFIX:** Made `SIGHUP` recreate the Xbox authentication client after application credential rotation

# Changes in 1.9.1 (26 May 2026)

**Bug fixes**:

- **BUGFIX:** Recalculate the liveness counter after config and CLI overrides are applied
- **BUGFIX:** Make connectivity checks use the finalized URL and timeout settings
- **BUGFIX:** Validate polling intervals before the monitor starts to avoid tight retry loops

# Changes in 1.9 (02 Mar 2026)

- **IMPROVE:** Switched from **xbox-webapi-python** to **[python-xbox](https://github.com/tr4nt0r/python-xbox)** to ensure better long-term stability and active maintenance (thanks [@tomballgithub](https://github.com/tomballgithub))
- **NEW:** Added **activity detection fallback for appear-offline users** - when a user's profile is set to "Appear Offline", the tool now uses **title history** to still detect and report gaming activity
- **NEW:** Implemented **debug mode** (`--debug` flag or `DEBUG_MODE` config option) - provides full technical logging for authentication, presence tracking and activity detection
- **IMPROVE:** Enhanced `--generate-config` to support writing directly to a file (e.g. `xbox_monitor --generate-config xbox_monitor.conf`). This avoids UTF-16 encoding issues on **Windows PowerShell**
- **IMPROVE:** Expanded tabs to spaces in output log files to ensure consistent alignment across different viewers
- **IMPROVE:** Enhanced friends list fetching logic to use fixed python-xbox library
- **IMPROVE:** **Game name** is now included in **title history** activity notifications
- **IMPROVE:** Implemented **automatic re-authentication** when OAuth token refresh fails, improving long-term monitoring reliability

# Changes in 1.8 (06 Jan 2026)

**Features and Improvements**:

- **NEW:** Added **User Information Display Mode** (`-i` / `--info`) providing comprehensive Xbox profile insights, including **XUID**, **real name**, **location**, **account tier** (Game Pass Core/Ultimate or Free), **gamerscore**, **online status**, **last online date**, **platform information**, and **friends count**
- **NEW:** Added **friends list display** in info mode (via `-f` / `--friends` flag) with presence details (game/activity)
- **NEW:** Added **recently played games** display in info mode with **last played date** and **total play time** for each title
- **NEW:** Added **recent achievements** display in info mode (via `-r` / `--recent-achievements` flag)
- **NEW:** Added command-line arguments to limit output: `-n` / `--achievements-count` and `-m` / `--games-count`
- **IMPROVE:** Added **step-by-step progress messages** during startup/fetching with status indicators

# Changes in 1.7 (03 Jan 2026)

**Bug fixes**:

- **BUGFIX:** Fixed **platform detection logic bug** where only the first platform name in the check was being evaluated (**Xbox Series X/S detection**)
- **BUGFIX:** Replaced blocking `time.sleep()` calls with `await asyncio.sleep()` in **async function** to prevent **event loop blocking**
- **BUGFIX:** Added protection against **division by zero** when calculating `LIVENESS_CHECK_COUNTER` if `XBOX_CHECK_INTERVAL` is set to 0

# Changes in 1.6.1 (13 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

# Changes in 1.6 (22 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install xbox_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **IMPROVE:** Enhanced startup summary to show loaded config and dotenv file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **IMPROVE:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Xbox endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **IMPROVE:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Added validation for configured time zones
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Updated horizontal line for improved output aesthetics
- **IMPROVE:** Email notifications now auto-disable if SMTP config is invalid
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed issue where manually defined `LOCAL_TIMEZONE` wasn't applied correctly

# Changes in 1.5 (19 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Support for float type of timestamps added in date/time related functions
- **IMPROVE:** Function get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False
- **IMPROVE:** Checking if correct version of Python (>=3.8) is installed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.4 (23 May 2024)

**Features and Improvements**:

- **NEW:** New feature counting overall time and number of played games in the session
- **NEW:** Support for short offline interruption, so if user gets offline and online again (for example due to rebooting the console) during the next OFFLINE_INTERRUPT seconds (configurable in .py file, by default 7 mins) then we set online start timestamp back to the previous one + we also keep stats from the previous session (like total time and number of played games)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

# Changes in 1.3 (19 May 2024)

**Features and Improvements**:

- **NEW:** Information when user is in-game during status changes (console + emails)
- **IMPROVE:** pep8 style convention corrections

# Changes in 1.2 (15 May 2024)

**Features and Improvements**:

- **IMPROVE:** Improvements for running the code in Python under Windows
- **NEW:** Automatic detection of local timezone if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- **IMPROVE:** Information about time zone is displayed in the start screen now
- **IMPROVE:** Better checking for wrong command line arguments

# Changes in 1.1 (13 May 2024)

**Features and Improvements**:

- **NEW:** Support for detecting games played by users (player starts/stops or changes the played game)
- **NEW:** Support for detecting status changes reported by Xbox app on mobile devices (Android & iOS/iPadOS)
- **NEW:** Support for Away status on Android devices (Xbox consoles, Windows and iOS devices do not report it)
- **IMPROVE:** Information about played games added to email notifications and CSV file
- **NEW:** Possibility to define MS_APP_CLIENT_ID via command line argument (-u / --ms_app_client_id)
- **NEW:** Possibility to define MS_APP_CLIENT_SECRET via command line argument (-w / --ms_app_client_secret)
- **NEW:** New command line argument -g / --game_change_notification + SIGUSR2 signal handler to cover game changes notifications
- **NEW:** New command line argument -s / --status_notification + SIGCONT signal handler to cover all status changes notifications
- **IMPROVE:** Updated mapping of platforms including mobile devices
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen
- **IMPROVE:** In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)
- **IMPROVE:** Exception handling for function converting the timezone

**Bug fixes**:

- **BUGFIX:** Handling situations when JSON file storing info about the last status gets corrupted or when there are issuing saving the state

# Changes in 1.0 (27 Apr 2024)

**Features and Improvements**:

- **NEW:** Switch from global authentication performed by xbox-authenticate tool to OAuth2 auth functionality in the code
