# xbox_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 2.1 (TBD)

Version **2.1** gives every monitoring failure unified subject and body across email and webhook, followed by a **recovery alert** when monitoring resumes. Network failures now link to a new **Connection Problems** page section. It also restores the colours missing from presence changes, console tags and the friends and listing tables. Alert delivery messages stay within the correct check report and alert channels that still use placeholder configuration values are shown as not configured.

**Features and improvements**:

- **IMPROVE:** **Failure alerts share one shape** - Every monitoring failure email and webhook uses the subject **`Xbox Monitor error: <what went wrong> (user: <gamertag>)`** and lists the fix, the guide link, how many checks failed in a row, since when and when the next retry happens. A **recovery alert** follows on the channels that received the failure alert once monitoring resumes. `-e` / `--no-error-notify` and `--no-webhook-error-notify` switch both off

**Bug fixes**:

- **BUGFIX:** **Network failures point at the right page** - A timed-out or unreachable Xbox Live request now link to the new **Connection Problems** section, which explains the automatic retries and what to check if the failure continues.
- **BUGFIX:** **Presence changes and console tags are coloured again** - A status change printed `offline` or `online` uncoloured, the **`User is currently in-game:`** row left the game title uncoloured and a console tag such as **`(iPhone/iPad)`** stayed plain beside a game or a status change. All four now use the colours the `COLOR_THEME` table documents.
- **BUGFIX:** **The friends list and the listing tables are coloured** - **`--show-friends`** printed every row plain. A name now takes the gamertag colour, the presence beside it is read through the same table the **`Status:`** row uses and a title a friend is playing is coloured as a game. The **recently played games** and **recent achievements** tables colour each column for what it holds.
- **BUGFIX:** **An `away` presence is yellow in a replayed log** - The bundled `grc` recipe painted **`away`** red inside **`changed status from ... to away`** while the live output and the **`Status:`** row used yellow. The recipe also now colours the Xbox console tags and the friends list rows. Copy `grc/conf.monitor_logs` to `~/.grc/` again to pick these up
- **BUGFIX:** **Alert deliveries stay inside their report** - The hourly **`Monitoring degraded`** reminder closed its report before the error alert was sent, so **`Sending email notification to ...`** and its webhook equivalent landed under the separator and started a second, headless block. The reminder now closes below its delivery lines, keeping one check's report in one block
- **BUGFIX:** **Unset alert channels are reported as unset** - The verbose startup summary read the values the sample configuration ships as a real destination, so a run that had never been given a mail server printed **`Email transport: your_smtp_server_ssl:587`**, a recipient of **`your_receiver_email`** and a webhook provider of **`Discord`**. Those rows now read **`Not configured`** and the channel rollup above them reads **`Off (not configured)`** rather than naming alert types nothing could deliver

# Changes in 2.0 (18 Sep 2026)

Version **2.0** adds **guided setup with Microsoft authorization**, a read-only **Doctor preflight check** and **Discord and ntfy alerts**. **Coloured output**, startup summaries and verbose/debug modes make monitoring easier to follow. Authentication recovery and game detection improve, saved history and credentials are protected and downloads can be verified. The release requires **Python 3.11 or newer**.

**Features and improvements**:

- **NEW:** **Guided setup** - `--setup` wizard collects the gamertag, intervals, credentials, notifications and output files, including browser authorization. Review settings before saving and confirm replacements. Reruns preserve saved settings and retained credentials. A first run without a saved target offers setup
- **NEW:** **Doctor preflight check** - `--doctor` checks configuration, authentication, profile and activity access, notifications and output destinations with suggested fixes. It writes no files, does not start interactive sign-in and sends test notifications only after confirmation
- **NEW:** **Discord and ntfy alerts** - Choose presence, game and error notifications independently of email. Save the destination with `--set-webhook-url` and check delivery with `--send-test-webhook`. Protected ntfy topics are supported
- **NEW:** **Private credential entry** - `--set-ms-app-credentials` collects hidden application credentials and runs browser authorization. `--set-smtp-password` checks a hidden password with the mail server before saving, without sending a message
- **NEW:** **Saved gamertag and status file** - Set `XBOX_GAMERTAG` to start monitoring without arguments. Use `XBOX_STATUS_FILE` or `--status-file` to choose where the last seen status is stored
- **NEW:** **Clearer output and diagnostics** - Coloured output and a short startup summary show the active settings. `--verbose` adds operational updates and `--debug` adds technical traces. Secrets are redacted and logs retain the full summary. Copy the updated `grc/conf.monitor_logs` to `~/.grc/` to use the live terminal colours in saved logs
- **IMPROVE:** **Clearer errors and recovery** - Failures include repair guidance, periodic outage reminders and recovery notices. Temporary failures trigger error alerts after five minutes, while expired credentials alert immediately
- **IMPROVE:** **Screen width and TLS settings** - `--truncate N` limits screen width while logs retain full lines. It works without `wcwidth`, which improves Unicode width measurements. `VERIFY_SSL` covers outbound certificate checks, including email. Verification is on by default and disabling it produces a warning
- **IMPROVE:** **Notification output** - Subjects omit program-name prefixes. Set `DELIVERY_CONFIRMATIONS = False` to hide delivery confirmations while keeping verbose diagnostics
- **IMPROVE:** **Documentation and verifiable downloads** - A [searchable guide](https://misiektoja.github.io/xbox_monitor/) covers setup, usage and troubleshooting. Releases include checksums and signed build attestations

**Bug fixes**:

- **BUGFIX:** **Reliable authentication and profile reports** - Temporary Microsoft and Xbox Live failures retry without unnecessary sign-in prompts. Authorization rejections explain the required action. Information mode and startup show the Bio and an offline user's last played title again
- **BUGFIX:** **Dashboard apps no longer count as games** - Home, the Xbox app and guide, Microsoft Store, Game Pass, Edge and Settings no longer trigger game sessions, game alerts or played time
- **BUGFIX:** **Protected tokens and status history** - Token and status updates are atomic and token-cache permissions are restricted to the owner. Damaged status records are reported before replacement. Timestamps ahead of the clock are retained with corrected timing
- **BUGFIX:** **Safer configuration loading** - Configuration files are read as settings instead of executed as Python. Plain values and references to other settings still work. Replace imports, function calls and calculations with plain settings
- **BUGFIX:** **Safer configuration and secret updates** - `--generate-config FILE` confirms replacement and creates a backup. Non-interactive replacement requires `--force`. Shell redirection with `>` bypasses these protections. Exported secrets work without a dotenv file. Command-line credentials and nonempty startup exports retain priority after `SIGHUP`. Change those values and restart to replace them. Reloads apply changed or removed file-owned secrets
- **BUGFIX:** **Safer email delivery** - Mail-server rejection messages redact credentials. Emails accepted by the mail server no longer become false failures if closing the connection fails, avoiding duplicate retries
- **BUGFIX:** **Reliable startup and status reminders** - Invalid settings include repair guidance. Configured screen settings apply, liveness reminders cover online and offline targets and redirected output avoids terminal-clearing errors

Smaller fixes and development changes are listed in the [full change history](https://github.com/misiektoja/xbox_monitor/compare/v1.9.3...v2.0).

# Changes in 1.9.3 (04 Aug 2026)

**Bug fixes**:

- **BUGFIX:** Fixed indentation of ASCII log separators in summary screen

# Changes in 1.9.2 (04 Aug 2026)

Version **1.9.2** applies refreshed Xbox credentials without a restart, gives clearer timezone recovery guidance and lets saved logs use portable separators.

**Features and improvements**:

- **IMPROVE:** **Clear timezone recovery** - When automatic detection fails, the startup error now identifies the optional `tzlocal` dependency, shows how to install it and explains that `LOCAL_TIMEZONE` can be set manually
- **IMPROVE:** **Portable log separators** - The new `ASCII_LOG_SEPARATORS` setting controls whether separator-only lines saved to log files use ASCII hyphens. `"Auto"` enables them on Windows by default, `"On"` enables them on every operating system and `"Off"` preserves Unicode separators. Terminal separators remain Unicode and log files remain UTF-8

**Bug fixes**:

- **BUGFIX:** **Live Xbox credential reloads** - After `SIGHUP` loads a changed Microsoft application client ID or secret, the monitor reauthenticates and recreates the Xbox client before the next presence check so the new credentials take effect without a restart

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
