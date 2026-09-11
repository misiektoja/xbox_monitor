# Setup & First Run

## Before You Start

Install the tool using [Installation](installation.md). You will need an Xbox gamertag and the [Microsoft Entra application credentials](#microsoft-entra-application-credentials). Quote a gamertag that contains spaces. The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The setup wizard asks a few questions, runs the [first authorization](#first-authorization) for you and writes a ready-to-run configuration. Start it directly with:

```sh
xbox_monitor --setup
```

Settings go to `xbox_monitor.conf` and secrets go to `.env` in the current directory. Use `--config-file` and `--env-file` or the summary's **File destinations** section to choose other files. Setup asks before replacing existing files or secrets. See [Storing Secrets](configuration.md#storing-secrets) for backup details.

The wizard asks for the account, polling intervals, application credentials, email and [webhook alerts](configuration.md#webhook-settings) and output files. Review or change any section from the summary. A rerun uses saved settings as defaults. Declining a section disables it.

If an answer is invalid, setup explains how to correct it and lets you retry.

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
