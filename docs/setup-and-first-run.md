# Setup & First Run

Printed commands use short names. Activate the tool's virtual environment before running them. For a downloaded script, run them from the script directory. Recovery commands retain selected configuration and dotenv paths.

Before replacing a configuration, setup copies retained inline credentials to the selected private dotenv file when that file has no value for the same key. An existing dotenv value, including an explicit empty value, keeps precedence. If preservation fails, the original configuration stays in place. Setup backups omit inline credentials.

When rebuilding an existing configuration, setup keeps its saved `DOTENV_FILE` unless you pass `--env-file PATH`. A nonempty exported secret takes precedence over the dotenv file. An explicit empty value in that file still overrides the configuration, both after saving and on the next run. Quoted dotenv keys receive the same replacement confirmation as unquoted keys.

Setup replaces each file separately. If saving secrets fails after the configuration was saved, setup stops and identifies the saved configuration. Correct the destination then rerun `--setup` with the same `--config-file` and `--env-file`, review the settings and run `--doctor` before monitoring. A crash between replacements can also leave a new configuration beside the previous dotenv file. The configuration backup can recover non-secret settings. Replaced secrets are not backed up.

## Before You Start

Install the tool using [Installation](installation.md). You will need an Xbox gamertag and the [Microsoft Entra application credentials](#microsoft-entra-application-credentials). Quote a gamertag that contains spaces. The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The setup wizard asks a few questions, runs the [first authorization](#first-authorization) for you and writes a ready-to-run configuration. Start it directly with:

```sh
xbox_monitor --setup
```

It writes the secrets to a dotenv file and everything else to `xbox_monitor.conf`, both in the current directory unless `--config-file` and `--env-file` say otherwise. Both destinations are checked before the first question, so an unwritable path is reported straight away rather than after you have answered everything. When the configuration file already exists it asks whether to replace it. It offers to write somewhere else instead. A rebuilt file starts from the settings already in place with your answers applied over them. A section you decline is cleared rather than carried over, so declining email leaves no mail server behind. A secret already in the dotenv file is never replaced without asking. A saved webhook URL or ntfy access token is offered by name, so it can be kept, replaced or, for the token, switched off, without ever being displayed.

It covers the monitored account, the polling intervals, the application credentials, email alerts, [webhook alerts](configuration.md#webhook-settings) and the files the tool writes. Each section can be skipped and re-entered from the summary. The summary's **File destinations** section changes where the configuration and dotenv files are written. Moving the dotenv destination reviews the private settings again. Kept file credentials are saved to the new destination when you choose Save. An existing value at that destination, including an empty value, takes precedence unless you explicitly replace it. The old file is left intact.

Every answer setup cannot use is explained and offered again. Declining the retry moves on rather than asking the same question forever: a value question keeps the default it showed and a channel such as email or webhook is switched off with its alerts.

Nothing is written until you choose **Save settings** on the summary. Ctrl+C at any question leaves both files untouched.

## Quick Start

To configure it by hand instead, register a [Microsoft Entra application](#microsoft-entra-application-credentials), then track the activity of `xbox_gamer_tag`:

```sh
xbox_monitor --set-ms-app-credentials
xbox_monitor "<xbox_gamertag>"
```

Or, if you installed [manually](installation.md#manual-installation):

```sh
python3 xbox_monitor.py --set-ms-app-credentials
python3 xbox_monitor.py "<xbox_gamertag>"
```

Pass the Xbox gamertag, not the Microsoft account e-mail address and not the real name. A gamertag copied out of a profile link works too.

Check the setup before relying on it. The preflight report writes nothing and exits non-zero when something is wrong:

```sh
xbox_monitor --doctor <xbox_gamertag>
```

To get the list of all supported command-line arguments and flags:

```sh
xbox_monitor --help
```

## Microsoft Entra Application Credentials

The tool signs in to Xbox Live through an application you register yourself, so the credentials stay yours. The portal is [Microsoft Entra ID](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade), previously called Azure AD.

Register a new application:

- Name it, for example *xbox_monitor*
- For account type select **Personal Microsoft accounts only**
- For redirect URI select the **Web** type and enter `http://localhost/auth/callback`

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app1.png" alt="xbox_monitor_azure_ad_app1" width="90%"/>
</p>

Copy the value of **Application (client) ID** into `MS_APP_CLIENT_ID`.

Next to **Client credentials** click **Add a certificate or secret**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app2.png" alt="xbox_monitor_azure_ad_app2" width="90%"/>
</p>

Add a new client secret with a description such as *xbox_monitor_secret* and a long expiry, such as two years.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app3.png" alt="xbox_monitor_azure_ad_app3" width="60%"/>
</p>

Copy the contents of the **Value** column into `MS_APP_CLIENT_SECRET`. The portal shows this value once.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_azure_ad_app4.png" alt="xbox_monitor_azure_ad_app4" width="100%"/>
</p>

Supply the two secrets in one of these ways:

- Let `--setup` or `--set-ms-app-credentials` ask for them through a hidden prompt and save them to the dotenv file
- Pass them at runtime with `-u` / `--ms-app-client-id` and `-w` / `--ms-app-client-secret`
- Export them as [environment variables](configuration.md#storing-secrets)
- Put them in a [dotenv file](configuration.md#storing-secrets) for persistent use

As a fallback they can also go in the configuration file or the source.

If they live in a dotenv file, you can change their values and send `SIGHUP` to the running process to reload them without a restart. See [Storing Secrets](configuration.md#storing-secrets) and [Signal Controls](usage.md#signal-controls-macoslinuxunix).

`--doctor` reports which secrets are loaded and which source each one came from, by name and never by value.

## First Authorization

The first run performs OAuth2 authorization with the credentials you supplied. `--setup` and `--set-ms-app-credentials` run the same flow right after collecting the credentials, so the tokens are already in place before monitoring starts. The tool prints a URL to open in a browser.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_oauth1.png" alt="xbox_monitor_oauth1" width="90%"/>
</p>

The browser is then redirected to localhost and shows a connection error. That is expected. Copy the part after `?code=` from the address bar, leaving out the trailing `&state=` part. Paste that into the tool.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/assets/xbox_monitor_oauth2.png" alt="xbox_monitor_oauth2" width="70%"/>
</p>

The tokens are saved to the file named by `MS_AUTH_TOKENS_FILE`, `xbox_tokens.json` in the current directory by default, so a restart does not ask again. The file holds a live refresh token, so it is created readable only by its owner.

`--doctor` never runs this flow, because it writes no files. It reports a missing token cache as a warning naming the command that creates one.

## User Privacy Settings

Monitoring only works when the monitored account allows it.

The monitored user should open the [Xbox profile privacy and online safety settings](https://account.xbox.com/Settings).

Set **Others can see if you're online** to **Friends** or **Everyone**. Setting **Others can see your Xbox profile details** the same way is recommended.

When the profile hides its activity, the tool reports it as a privacy setting on that account rather than a credential problem. `--doctor` says the same.

## Continue with Usage

Use [Usage](usage.md) for monitoring and output options or [Configuration](configuration.md) to adjust saved settings. If setup or monitoring fails, run [Doctor Preflight](troubleshooting.md#doctor-preflight) and follow the reported recovery steps.
