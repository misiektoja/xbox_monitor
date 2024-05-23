# xbox_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.4 (23 May 2024)

**Features and Improvements**:

- New feature counting overall time and number of played games in the session
- Support for short offline interruption, so if user gets offline and online again (for example due to rebooting the console) during the next OFFLINE_INTERRUPT seconds (configurable in .py file, by default 7 mins) then we set online start timestamp back to the previous one + we also keep stats from the previous session (like total time and number of played games)
- Information about log file name visible in the start screen
- Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

# Changes in 1.3 (19 May 2024)

**Features and Improvements**:

- Information when user is in-game during status changes (console + emails)
- pep8 style convention corrections

# Changes in 1.2 (15 May 2024)

**Features and Improvements**:

- Improvements for running the code in Python under Windows
- Automatic detection of local timezone if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- Information about time zone is displayed in the start screen now
- Better checking for wrong command line arguments

# Changes in 1.1 (13 May 2024)

**Features and Improvements**:

- Support for detecting games played by users (player starts/stops or changes the played game)
- Support for detecting status changes reported by Xbox app on mobile devices (Android & iOS/iPadOS)
- Support for Away status on Android devices (Xbox consoles, Windows and iOS devices do not report it)
- Information about played games added to email notifications and CSV file 
- Possibility to define MS_APP_CLIENT_ID via command line argument (-u / --ms_app_client_id)
- Possibility to define MS_APP_CLIENT_SECRET via command line argument (-w / --ms_app_client_secret)
- New command line argument -g / --game_change_notification + SIGUSR2 signal handler to cover game changes notifications
- New command line argument -s / --status_notification + SIGCONT signal handler to cover all status changes notifications
- Updated mapping of platforms including mobile devices
- Email sending function send_email() has been rewritten to detect invalid SMTP settings
- Strings have been converted to f-strings for better code visibility
- Info about CSV file name in the start screen
- In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)
- Exception handling for function converting the timezone

**Bugfixes**:

- Handling situations when JSON file storing info about the last status gets corrupted or when there are issuing saving the state

# Changes in 1.0 (27 Apr 2024)

**Features and Improvements**:

- Switch from global authentication performed by xbox-authenticate tool to OAuth2 auth functionality in the code
