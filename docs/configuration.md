# Configuration

Examples on this page use the PyPI command `xbox_monitor`. Manual script users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format-by-installation-method).

<a id="configuration-file"></a>
## Configuration File

You can pass most settings as command-line options or save them in a configuration file for later runs.

The easiest way to create this file is `xbox_monitor --setup`.

To edit every available setting yourself, generate a default configuration file:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
xbox_monitor --generate-config > xbox_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
xbox_monitor --generate-config xbox_monitor.conf
```

> **Windows PowerShell:** Pass the filename directly to `--generate-config`. PowerShell redirection can write UTF-16, which the tool rejects with a "null bytes" error.

When the named file already exists, `--generate-config` asks before replacing it and keeps a timestamped `.bak` backup next to it. Add `--force` to replace it without the question.

The file contains a short explanation above each setting.

A configuration file is read as data, not executed. The tool accepts only `SETTING = value` lines where the name is one of the documented settings and the value is a plain literal such as a string, number, `True`, `False`, `None`, a list or a dictionary. Comments and blank lines are fine.

Imports, function calls, expressions and unknown settings are rejected with the setting and line number to correct.

If the same setting appears in more than one place, the item later in this list wins:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Values from the selected `.env` file
4. Secret environment variables
5. Command-line options

By default the tool looks for a configuration file named `xbox_monitor.conf` in the current directory, the home directory (`~`) and the script directory. Use `--config-file` to name another location or `--config-file none` to disable automatic config discovery for one run.

<a id="monitored-target"></a>
## Monitored Target

The Xbox gamertag is a positional argument. It is required to start monitoring:

```sh
xbox_monitor "<xbox_gamertag>"
```

Use the gamertag, not the Microsoft account e-mail address. Quote it when it contains spaces.

To stop repeating it, save it in the configuration file:

```ini
XBOX_GAMERTAG = "xbox_gamertag"
```

Then `xbox_monitor` alone starts monitoring that user. A positional argument still wins, so you can watch someone else for one run without editing the file:

```sh
xbox_monitor "Other Gamertag"
```

<a id="time-zone"></a>
## Time Zone

By default the time zone is detected with `tzlocal`. Set it manually in `xbox_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

To list every time zone pytz supports:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

<a id="smtp-settings"></a>
## SMTP Settings

Email notifications need SMTP server details for the sending account. Add them to `xbox_monitor.conf` or use the setup wizard. Setup checks the login without sending an email. To replace only the password, run `xbox_monitor --set-smtp-password`. Password entry is hidden and preserves spaces.

Every alert is sent as both HTML and plain text in one message. Mail clients that render HTML show the gamertag, the game, the status and the values that changed in bold. The gamertag links to its Xbox profile page. Clients that do not render HTML fall back to the plain text, which is unchanged.

Send one test message to verify the settings:

```sh
xbox_monitor --send-test-email
```

<a id="webhook-settings"></a>
## Webhook Settings

Alerts can also be delivered to a **Discord** channel or an **ntfy** topic. The webhook channel is configured and switched on separately from email, so you can send game changes to Discord while email stays off or use both.

Save the destination privately, which never puts it in your shell history:

```sh
xbox_monitor --set-webhook-url
```

Hidden URL entry recognizes Discord and ntfy URLs. A bare topic name is saved as an ntfy.sh URL. The service is detected from the URL, so `WEBHOOK_PROVIDER` only needs setting for a self-hosted ntfy server. While `WEBHOOK_PROVIDER` is left at its default, that detection is silent and `--verbose` reports it. A warning appears only when your configuration file sets a provider the URL disagrees with.

The URL is checked for shape without contacting the service, because the only confirmation Discord or ntfy can give is a delivered notification. The command prints `--send-test-webhook` as the next step, which does deliver one.

Then switch the channel on and choose which events it sends:

```python
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"                    # or "ntfy"
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True     # user gets online or offline
WEBHOOK_GAME_CHANGE_NOTIFICATION = True         # game starts, changes or stops
WEBHOOK_STATUS_NOTIFICATION = False             # every status change, including away
WEBHOOK_ERROR_NOTIFICATION = True               # monitoring failures and their recovery, enabled by default
```

`WEBHOOK_ERROR_NOTIFICATION` and its email counterpart `ERROR_NOTIFICATION` each cover both the failure alert and the recovery alert that follows it on that channel. `--no-webhook-error-notify` and `-e` switch them off for one run.

A `WEBHOOK_URL` that is unset or still holding its `your_webhook_url` placeholder switches webhook alerts off at startup instead of failing at the first alert. `--verbose` reports why.

Which events actually fire and how a failed delivery is retried is covered in [Webhook Notifications](usage.md#webhook-notifications).

<a id="ntfy"></a>
### ntfy

For ntfy it is the complete topic URL, such as `https://ntfy.sh/xbox-monitor-long-random-value` or just the topic name when it is hosted on ntfy.sh. Set the provider in `xbox_monitor.conf` for a self-hosted ntfy server:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

ntfy alerts are sent as a native message with the subject as the title, so no template is involved. Use `WEBHOOK_HEADERS` to add ntfy options such as priority or tags:

```python
WEBHOOK_HEADERS = {"Priority": "5", "Tags": "video_game"}
```

Topics on the public ntfy.sh service are public unless protected through an account reservation. Treat an unprotected topic name like a password. Use `NTFY_ACCESS_TOKEN` when the topic needs authentication:

```ini
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

Xbox Monitor sends this value as `Authorization: Bearer <token>`. `NTFY_ACCESS_TOKEN` takes precedence over an `Authorization` entry in `WEBHOOK_HEADERS`. Header values support the same placeholders as `WEBHOOK_TEMPLATE` and apply to both Discord and ntfy.

<a id="discord"></a>
### Discord

If you are new to Discord, follow these steps to get your private webhook URL:

1. Open your Xbox alerts server and choose the channel that should receive them.
2. Select **Edit Channel**, open **Integrations** then choose **Webhooks**.
3. Select **New Webhook**, choose a name if you want then select **Copy Webhook URL**.
4. Save it with `xbox_monitor --set-webhook-url`.

Treat this link like a password because anyone who has it can post through it.

Keep the default provider in `xbox_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "discord"
```

Discord alerts are sent as an embed built from `WEBHOOK_TEMPLATE`. Mentions are always disabled, whatever the template says.

Discord alerts carry the same emphasis as the HTML email, since Discord renders markdown in an embed. Bold values stay bold and links stay clickable. Only Discord gets that wording: ntfy receives the plain body, because it would show the markers literally.

<a id="advanced-discord-format-customization"></a>
### Advanced Discord-format customization

`WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` override the webhook's own display name and picture for Discord-format payloads. Both are ignored by ntfy:

```ini
WEBHOOK_USERNAME = "Xbox Monitor"
WEBHOOK_AVATAR_URL = "https://example.com/path/avatar.png"
```

`WEBHOOK_TEMPLATE` controls the Discord-format request body. It supports these placeholders:

- `{title}`
- `{description}`
- `{version}`
- `{image_url}`
- `{fields}` and `{fields_str}`
- `{color}`
- `{timestamp}`
- `{username}`
- `{avatar_url}`

Discord templates must produce a JSON object. Use a dictionary or a JSON string encoding an object, including legacy strings with doubled object braces. Lists, non-JSON strings and unsupported placeholders are rejected before delivery. Alert text is kept literal and all payloads replace `allowed_mentions` with `{"parse": []}` so alert text cannot trigger Discord mentions. Reloaded settings apply to the next delivery.

`WEBHOOK_TRANSFORMS` applies string methods to shared placeholder values before the template and headers are rendered:

```ini
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
    ("description", "strip"),
]
```

The tuple format is `(field_to_target, method_name, *optional_arguments)`. Invalid templates, avatar URLs, transforms or formatted headers fail before a request is attempted. `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to the Discord request format. ntfy continues to use its native publish API while transformations and header placeholders use the same shared title and description values.

<a id="terminal-colours"></a>
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
| `username` | `bright_cyan underline` | The monitored gamertag, a name in the friends list, the detected install method and wizard menu numbers |
| `id` | `bright_magenta` | The XUID |
| `status_active` | `green` | An online presence or a game that just started |
| `status_away` | `yellow` | An away presence |
| `status_inactive` | `red` | An inactive presence or a game that just stopped |
| `status_offline` | `red` | An offline presence |
| `status_other` | `white` | A presence value the tool does not recognise |
| `game` | `bright_yellow` | Game titles, including the title column of the recently played and recent achievements listings |
| `platform` | `blue` | Console names and the platform tag beside a game |
| `achievement` | `bright_green` | Gamerscore and achievement names |
| `duration` | `green` | Time spans such as `3 hours, 21 minutes` and the total column of the recently played listing |
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

<a id="network-timeouts-and-retries"></a>
## Network Timeouts and Retries

Requests to Xbox Live and to the Microsoft sign-in endpoint use a 30 second timeout. A token refresh that fails because of a network timeout or a temporary server-side error, HTTP 429 or 5xx, is retried up to three times with an exponentially growing delay.

On a slow or unstable connection you can raise both:

* `XBOX_API_TIMEOUT`: timeout for Xbox Live and Microsoft authentication requests, in seconds, default 30
* `TOKEN_REFRESH_RETRIES`: how many refresh attempts to make before giving up, default 3, set to 1 to disable retrying
* `TOKEN_REFRESH_RETRY_DELAY`: delay before the first retry, doubled after every failed attempt, in seconds, default 5

An expired or revoked refresh token is a credential problem rather than a network problem, so it is reported immediately and starts the interactive re-authorization flow instead of being retried.

<a id="storing-secrets"></a>
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

Each command rewrites its assignment in the dotenv file in place and keeps every other line and comment. Each asks first when the value is already set. `--setup` does the same as part of the guided run.

`--set-smtp-password` checks the rest of the mail server settings before it asks for anything and names the one that is still missing, so you never type a password that cannot be checked. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SENDER_EMAIL` and `RECEIVER_EMAIL` first or run `--setup`. An exported `SMTP_PASSWORD` wins over the saved one at startup, so the command says so after saving rather than leaving you with a value the next run will not read.

Export them on Linux, Unix, macOS and WSL:

```sh
export MS_APP_CLIENT_ID="your_ms_application_client_id"
export MS_APP_CLIENT_SECRET="your_ms_application_secret_value"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="your_webhook_url"
export NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

On **Windows Command Prompt** use `set` and on **Windows PowerShell** use `$env`.

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
xbox_monitor <xbox_gamertag> --env-file /path/.env-xbox_monitor
```

Switch the search off with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
xbox_monitor <xbox_gamertag> --env-file none
```

The Xbox token cache named by `MS_AUTH_TOKENS_FILE` holds a live refresh token. The tool creates it readable only by its owner. `--doctor` warns when an existing one is readable by other accounts.

As a fallback, secrets can also be stored in the configuration file or the source.

A forgotten `export` can shadow the dotenv file invisibly, so `--debug` names every secret and the source it resolved from, never the value:

```text
[DEBUG 12:00:00] Secret resolution: name=MS_APP_CLIENT_ID, source=environment, value=set, chars=36
[DEBUG 12:00:00] Secret resolution: name=SMTP_PASSWORD, source=dotenv file, value=set
```

<a id="tls-verification"></a>
## TLS Verification

Every outbound connection verifies the server certificate by default. Xbox Live, the Microsoft sign-in endpoint, the connectivity check, the SMTP handshake and the webhook service all use the same setting.

```ini
VERIFY_SSL = True
```

Set it to `False` only on a network that intercepts TLS with its own certificate authority. While it is off, an intercepted connection cannot be told apart from the real service, so `--doctor` reports it as a warning and the startup summary states it.
