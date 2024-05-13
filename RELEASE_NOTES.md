# xbox_monitor release notes

This is a high-level summary of the most important changes. 

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
