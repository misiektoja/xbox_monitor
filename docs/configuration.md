# Configuration

## Configuration File

The quickest way to get a configuration file is [`--setup`](setup-and-first-run.md#quick-start), which fills it in from your answers.

Most settings can also be set on the command line. To keep them, generate the default template and save it as `xbox_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
xbox_monitor --generate-config > xbox_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
xbox_monitor --generate-config xbox_monitor.conf
```

!!! important
    On **Windows PowerShell**, redirecting with `>` writes the file as UTF-16, which makes the tool fail with null-byte errors. Pass the filename directly to `--generate-config` so it is written as UTF-8.

When the named file already exists, the tool asks before replacing it and keeps the previous version as `xbox_monitor.conf.<timestamp>.bak` next to it. Outside a terminal, add `--force` to replace it without a prompt. Redirecting with `>` truncates the file before the tool starts, so that form cannot be protected.

Then edit `xbox_monitor.conf` and change the settings you need. Each one carries a comment describing it.

Configuration files are read as data. Only documented `SETTING = value` lines with plain literal values are accepted, so a file picked up from the working directory cannot run code.

By default the tool looks for `xbox_monitor.conf` in the current directory, then the home directory, then the directory holding the script. To use a different path:

```sh
xbox_monitor <xbox_gamer_tag> --config-file /path/xbox_monitor_new.conf
```

## Target Account

Set `XBOX_GAMERTAG` to save the account you usually watch. A gamertag passed on the command line always wins over the saved one, and with a saved value you can start monitoring with no arguments at all:

```sh
xbox_monitor
```

`XBOX_STATUS_FILE` and the `--status-file` flag choose where the last seen status is kept, which otherwise defaults to `xbox_<gamer_tag>_last_status.json` in the current directory.

## Time Zone

By default the time zone is detected with `tzlocal`. Set it manually in `xbox_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

To list every time zone pytz supports:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

An invalid time zone stops a normal run, because nothing could be timestamped. Under `--doctor` it becomes a reported row instead, so the rest of the report still runs.

## SMTP Settings

To use email notifications, set the SMTP options in `xbox_monitor.conf`.

Check the settings by sending a real test message:

```sh
xbox_monitor --send-test-email
```

`--doctor` checks the same settings and signs in without sending anything, then offers a real test message only after you approve it separately.

Email is switched off automatically while `SMTP_HOST`, `SMTP_USER` or `SMTP_PASSWORD` is still one of the shipped placeholders, so a fresh install never looks configured when it is not.

## Webhook Settings

Alerts can also be delivered to a **Discord** channel or an **ntfy** topic. The webhook channel is configured and switched on separately from email, so you can send game changes to Discord while email stays off, or use both.

Save the destination privately, which never puts it in your shell history:

```sh
xbox_monitor --set-webhook-url
```

For Discord this is the URL from Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL. For ntfy it is the complete topic URL, such as `https://ntfy.sh/your-private-topic`, or just the topic name when it is hosted on ntfy.sh. The service is detected from the URL, so `WEBHOOK_PROVIDER` only needs setting for a self-hosted ntfy server.

The URL is checked for shape without contacting the service, because the only confirmation Discord or ntfy can give is a delivered notification. The command prints `--send-test-webhook` as the next step, which does deliver one.

Then switch the channel on and choose which events it sends:

```python
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"                    # or "ntfy"
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True     # user gets online or offline
WEBHOOK_GAME_CHANGE_NOTIFICATION = True         # game starts, changes or stops
WEBHOOK_STATUS_NOTIFICATION = False             # every status change, including away
WEBHOOK_ERROR_NOTIFICATION = True               # monitoring errors, enabled by default
```

A `WEBHOOK_URL` left unset, or left at its `your_webhook_url` placeholder, switches webhook alerts off at startup instead of failing at the first alert. `--verbose` reports why.

Discord alerts are sent as an embed built from `WEBHOOK_TEMPLATE`, which supports the `title`, `description`, `version`, `color`, `timestamp`, `username` and `avatar_url` placeholders. Mentions are always disabled, whatever the template says. `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` override the webhook's own display name and picture, and both are ignored by ntfy.

ntfy alerts are sent as a native message with the subject as the title, so no template is involved. Use `WEBHOOK_HEADERS` to add ntfy options such as priority or tags, and `NTFY_ACCESS_TOKEN` when the topic needs authentication:

```python
WEBHOOK_HEADERS = {"Priority": "5", "Tags": "video_game"}
```

`WEBHOOK_TRANSFORMS` applies string methods to the values before they are sent, for example to strip Markdown from the body:

```python
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
]
```

Which events actually fire, and how a failed delivery is retried, is covered in [Webhook Notifications](usage.md#webhook-notifications).

## TLS Verification

Every outbound connection verifies the server certificate by default. Xbox Live, the Microsoft sign-in endpoint, the connectivity check, the SMTP handshake and the webhook service all use the same setting.

```ini
VERIFY_SSL = True
```

Set it to `False` only on a network that intercepts TLS with its own certificate authority. While it is off, an intercepted connection cannot be told apart from the real service, so `--doctor` reports it as a warning and the startup summary states it.

## Check Intervals

To change the polling intervals, use `-k` and `-c`, or the matching settings:

```sh
xbox_monitor <xbox_gamer_tag> -k 30 -c 120
```

* `XBOX_ACTIVE_CHECK_INTERVAL`, `-k`: check interval while the user is online or away, in seconds
* `XBOX_CHECK_INTERVAL`, `-c`: check interval while the user is offline, in seconds

An active interval below 30 seconds invites the Xbox Live rate limiter, which stops the tool seeing anything. `--doctor` warns when the configured interval is that short.

## Network Timeouts and Retries

Requests to Xbox Live and to the Microsoft sign-in endpoint use a 30 second timeout. A token refresh that fails because of a network timeout or a temporary server-side error, HTTP 429 or 5xx, is retried up to three times with an exponentially growing delay.

On a slow or unstable connection you can raise both:

* `XBOX_API_TIMEOUT`: timeout for Xbox Live and Microsoft authentication requests, in seconds, default 30
* `TOKEN_REFRESH_RETRIES`: how many refresh attempts to make before giving up, default 3, set to 1 to disable retrying
* `TOKEN_REFRESH_RETRY_DELAY`: delay before the first retry, doubled after every failed attempt, in seconds, default 5

An expired or revoked refresh token is a credential problem rather than a network problem, so it is reported immediately and starts the interactive re-authorization flow instead of being retried.

## Storing Secrets

Store `MS_APP_CLIENT_ID`, `MS_APP_CLIENT_SECRET`, `SMTP_PASSWORD`, `WEBHOOK_URL` and `NTFY_ACCESS_TOKEN` as environment variables or in a dotenv file rather than in the configuration file.

The tool can collect them for you through a hidden prompt, check them and save them to the dotenv file. Neither value is echoed and neither ends up in the shell history:

```sh
# Asks for both Microsoft application credentials, then runs the one-time browser authorization
xbox_monitor --set-ms-app-credentials

# Asks for the SMTP password and signs in to the mail server before saving it, without sending anything
xbox_monitor --set-smtp-password

# Asks for the Discord webhook or ntfy topic URL and checks its shape before saving it, without contacting the service
xbox_monitor --set-webhook-url
```

Each command rewrites its assignment in the dotenv file in place, keeps every other line and comment, and asks first when the value is already set. `--setup` does the same as part of the guided run.

Export them on Linux, Unix, macOS and WSL:

```sh
export MS_APP_CLIENT_ID="your_ms_application_client_id"
export MS_APP_CLIENT_SECRET="your_ms_application_secret_value"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="your_webhook_url"
export NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

On **Windows Command Prompt** use `set`, and on **Windows PowerShell** use `$env`.

A dotenv file keeps them across sessions:

```ini
MS_APP_CLIENT_ID="your_ms_application_client_id"
MS_APP_CLIENT_SECRET="your_ms_application_secret_value"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="your_webhook_url"
NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

By default the tool looks for a file named `.env` in the current directory and then upward from it. Point it somewhere else with `DOTENV_FILE` or `--env-file`:

```sh
xbox_monitor <xbox_gamer_tag> --env-file /path/.env-xbox_monitor
```

Switch the search off with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
xbox_monitor <xbox_gamer_tag> --env-file none
```

A secret already exported in the environment wins over the same name in the dotenv file at startup, so a one-off value or one injected by systemd or a container is not silently shadowed. A `SIGHUP` reload is the exception: there the edited file is exactly what should take effect.

`--doctor` reports which secrets are loaded and which source each one came from, by name and never by value. Diagnostic output is redacted, so a report can be pasted into a public bug report.

The Xbox token cache named by `MS_AUTH_TOKENS_FILE` holds a live refresh token. The tool creates it readable only by its owner, and `--doctor` warns when an existing one is readable by other accounts.

As a fallback, secrets can also be stored in the configuration file or the source.
