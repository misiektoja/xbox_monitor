#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.0

Tool implementing real-time tracking of Xbox Live players activities:
https://github.com/misiektoja/xbox_monitor/

Python pip3 requirements:

python-xbox
python-dateutil
httpx
pytz
tzlocal (optional)
python-dotenv (optional)
wcwidth (optional, measures wide characters correctly when TRUNCATE_CHARS is set)
colorama (optional, for better colours on Windows terminals)
"""

VERSION = "2.0"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Optional Xbox gamer tag to monitor when none is given on the command line
# A gamer tag passed as an argument always wins over this value
XBOX_GAMERTAG = ""

# Register a new app in Azure AD:
# https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
#
# - Name your app (e.g. xbox_monitor)
# - For account type, select: "Personal Microsoft accounts only"
# - For redirect URL, select "Web" and set it to: http://localhost/auth/callback
#
# Copy the value of 'Application (client) ID'
#
# Provide the MS_APP_CLIENT_ID secret using one of the following methods:
#   - Pass it at runtime with -u / --ms-app-client-id
#   - Set it as an environment variable (e.g. export MS_APP_CLIENT_ID=...)
#   - Add it to ".env" file (MS_APP_CLIENT_ID=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
MS_APP_CLIENT_ID = "your_ms_application_client_id"

# Next to 'Client credentials' click 'Add a certificate or secret'
# - Add a new client secret with a long expiration (e.g. 2 years) and a description (e.g. xbox_monitor_secret)
# - Copy the 'Value' of the secret
#
# Provide the MS_APP_CLIENT_SECRET secret using one of the following methods:
#   - Pass it at runtime with -w / --ms-app-client-secret
#   - Set it as an environment variable (e.g. export MS_APP_CLIENT_SECRET=...)
#   - Add it to ".env" file (MS_APP_CLIENT_SECRET=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
MS_APP_CLIENT_SECRET = "your_ms_application_secret_value"

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when user goes online/offline
# Can also be enabled via the -a flag
ACTIVE_INACTIVE_NOTIFICATION = False

# Whether to send an email on game start/change/stop
# Can also be enabled via the -g flag
GAME_CHANGE_NOTIFICATION = False

# Whether to send an email on all status changes (online/away/offline)
# Can also be enabled via the -s flag
STATUS_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# ----------------------------
# Webhook Notifications
# ----------------------------

# Master switch for webhook notifications through Discord or ntfy
# The event settings below select which alerts are sent
# Can also be enabled via the --webhook flag
WEBHOOK_ENABLED = False

# Service used to deliver webhook notifications: "discord" or "ntfy"
# A recognised Discord or ntfy.sh URL corrects a mismatched value at runtime
# Can also be set via the --webhook-provider flag
WEBHOOK_PROVIDER = "discord"

# Private destination used to send webhook notifications
# Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
# ntfy: complete topic URL such as https://ntfy.sh/your-private-topic
#
# Provide the WEBHOOK_URL secret using one of the following methods:
#   - Enter it privately with --set-webhook-url
#   - Set it as an environment variable (e.g. export WEBHOOK_URL=...)
#   - Add it to ".env" file (WEBHOOK_URL=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
#
# The --webhook-url flag overrides it for one run, but leaves the private URL in shell history
WEBHOOK_URL = "your_webhook_url"

# Discord display name (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_USERNAME = "Xbox Monitor"

# Discord avatar URL (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_AVATAR_URL = ""

# Whether to send a webhook alert when user goes online/offline
# Can also be enabled via the --webhook-active-inactive flag
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = False

# Whether to send a webhook alert on game start/change/stop
# Can also be enabled via the --webhook-game-change flag
WEBHOOK_GAME_CHANGE_NOTIFICATION = False

# Whether to send a webhook alert on all status changes (online/away/offline)
# Can also be enabled via the --webhook-status flag
WEBHOOK_STATUS_NOTIFICATION = False

# Whether to send a webhook alert on errors
# Can also be enabled via --webhook-errors or disabled via --no-webhook-error-notify
WEBHOOK_ERROR_NOTIFICATION = True

# Optional request headers for advanced webhook integrations
# Values support the same placeholders as WEBHOOK_TEMPLATE
WEBHOOK_HEADERS = {}

# Optional ntfy access token for Bearer authentication
#
# Provide the NTFY_ACCESS_TOKEN secret using one of the following methods:
#   - Set it as an environment variable (e.g. export NTFY_ACCESS_TOKEN=...)
#   - Add it to ".env" file (NTFY_ACCESS_TOKEN=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
NTFY_ACCESS_TOKEN = ""

# ----------------------------
# Advanced Webhook Settings
# ----------------------------

# Discord-format webhook request payload template
# Applies only when WEBHOOK_PROVIDER is "discord". The "ntfy" provider needs no template and ignores this
# value: it sends the alert body as a native ntfy message with the subject as its title. Use WEBHOOK_HEADERS
# to add ntfy options such as priority or tags
# Supported placeholders: title, description, version, color, timestamp, username and avatar_url
WEBHOOK_TEMPLATE = {
    "username": "{username}",
    "avatar_url": "{avatar_url}",
    "allowed_mentions": {
        "parse": [],
    },
    "embeds": [{
        "title": "{title}",
        "description": "{description}",
        "color": "{color}",
        "footer": {
            "text": "Xbox Monitor v{version}",
        },
        "timestamp": "{timestamp}",
    }],
}

# Optional transformations applied to WEBHOOK_TEMPLATE and WEBHOOK_HEADERS values
# Tuple format: (field_to_target, method_name, *optional_arguments)
#
# Examples:
#   [
#       ("title", "upper"),
#       ("description", "replace", "**", ""),
#       ("description", "strip"),
#   ]
WEBHOOK_TRANSFORMS = []

# How often to check for player activity when the user is offline; in seconds
# Can also be set using the -c flag
XBOX_CHECK_INTERVAL = 300  # 5 min

# How often to check for player activity when the user is online; in seconds
# Can also be set using the -k flag
XBOX_ACTIVE_CHECK_INTERVAL = 90  # 1,5 min

# Set your local time zone so that Xbox API timestamps are converted accordingly (e.g. 'Europe/Warsaw').
# Use this command to list all time zones supported by pytz:
#   python3 -c "import pytz; print('\\n'.join(pytz.all_timezones))"
# If set to 'Auto', the tool will try to detect your local time zone automatically (requires tzlocal)
LOCAL_TIMEZONE = 'Auto'

# If the user disconnects (offline) and reconnects (online) within OFFLINE_INTERRUPT seconds,
# the online session start time will be restored to the previous session's start time (short offline interruption),
# and previous session statistics (like total playtime and number of played games) will be preserved
OFFLINE_INTERRUPT = 420  # 7 mins

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 86400  # 24 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://user.auth.xboxlive.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Whether to verify TLS certificates on every outbound connection
# Leave this on unless the network intercepts TLS with its own certificate authority, which some corporate
# networks do; turning it off makes an intercepted connection indistinguishable from the real service
VERIFY_SSL = True

# Timeout for Xbox Live and Microsoft authentication API requests; in seconds
# The underlying HTTP library defaults to 5 seconds which is too aggressive for the
# Microsoft token endpoint and can abort the tool with a read timeout
XBOX_API_TIMEOUT = 30

# How many attempts to make when a token refresh fails with a network timeout or a
# temporary server-side error; set to 1 to disable retrying
TOKEN_REFRESH_RETRIES = 3

# Delay before the first token refresh retry; in seconds
# The delay doubles after every failed attempt
TOKEN_REFRESH_RETRY_DELAY = 5

# After authentication, the access token will be saved to the following file
MS_AUTH_TOKENS_FILE = "xbox_tokens.json"

# CSV file to write all status & game changes
# Can also be set using the -b flag
CSV_FILE = ""

# File the tool saves the last seen status to, so a restart resumes from the previous session
# Leave empty to use xbox_<xbox_gamertag>_last_status.json in the current directory
# Can also be set using the --status-file flag
XBOX_STATUS_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Base name for the log file. Output will be saved to xbox_monitor_<xbox_gamertag>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/xbox_monitor
XBOX_LOGFILE = "xbox_monitor"

# Whether to disable logging to xbox_monitor_<xbox_gamertag>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Cut every printed line to this many characters, so long lines do not wrap in a narrow terminal
# 0 disables it, 999 uses the detected terminal width. The optional wcwidth library measures wide characters correctly
# Log files always keep the untruncated text
# Can also be set using the --truncate flag
TRUNCATE_CHARS = 0

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Whether to colour terminal output
# Colour is dropped automatically when the output is not a terminal, when NO_COLOR is set
# or when --no-color is passed. Log files always stay plain text
COLORED_OUTPUT = True

# Optional overrides for individual colours, merged over the built-in theme
# The defaults are shown below. Uncomment only the entries you want to change: a complete copy
# here would pin this palette, so later changes to the built-in one would never reach you
# COLOR_THEME = {
#     "header": "bright_cyan",
#     "section": "bright_white",
#     "username": "bright_cyan underline",
#     "id": "bright_magenta",
#     "status_active": "green",
#     "status_away": "yellow",
#     "status_inactive": "red",
#     "status_offline": "red",
#     "status_other": "white",
#     "game": "bright_yellow",
#     "platform": "blue",
#     "achievement": "bright_green",
#     "duration": "green",
#     "status_change": "yellow",
#     "timestamp_label": "",
#     "timestamp_value": "cyan",
#     "info": "cyan",
#     "warning": "yellow",
#     "error": "red",
#     "signal": "yellow",
#     "email": "bright_cyan",
#     "webhook": "bright_blue",
#     "date": "magenta",
#     "date_range": "magenta",
#     "boolean_true": "green",
#     "boolean_false": "red",
#     "count_up": "green",
#     "count_down": "red",
#     "link": "blue underline",
#     # Help screen
#     "help_heading": "bright_cyan bold",
#     "help_usage": "bright_white bold",
#     "help_option": "bright_green",
#     "help_metavar": "yellow",
#     "help_placeholder": "bright_magenta",
#     "help_command": "bright_white",
#     "help_comment": "bright_black",
#     "help_default": "bright_black",
# }

# Report rare operational events such as recoveries and degraded features (can also be enabled via --verbose flag)
# Independent of DEBUG_MODE, which reports every technical step instead
VERBOSE_MODE = False

# Enable debug mode for technical logging (can also be enabled via --debug flag)
# Shows technical details, timestamps and internal state changes
DEBUG_MODE = False

# Whether verbose output confirms each delivered email and webhook alert
# Applies only when VERBOSE_MODE is enabled
DELIVERY_CONFIRMATIONS = True

# Value used by signal handlers increasing/decreasing the check for player activity
# when user is online/away (XBOX_ACTIVE_CHECK_INTERVAL); in seconds
XBOX_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
XBOX_GAMERTAG = ""
MS_APP_CLIENT_ID = ""
MS_APP_CLIENT_SECRET = ""
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
ACTIVE_INACTIVE_NOTIFICATION = False
GAME_CHANGE_NOTIFICATION = False
STATUS_NOTIFICATION = False
ERROR_NOTIFICATION = False
WEBHOOK_ENABLED = False
WEBHOOK_PROVIDER = ""
WEBHOOK_URL = ""
WEBHOOK_USERNAME = ""
WEBHOOK_AVATAR_URL = ""
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = False
WEBHOOK_GAME_CHANGE_NOTIFICATION = False
WEBHOOK_STATUS_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
WEBHOOK_HEADERS: dict = {}
NTFY_ACCESS_TOKEN = ""
WEBHOOK_TEMPLATE: dict = {}
WEBHOOK_TRANSFORMS: list = []
XBOX_CHECK_INTERVAL = 0
XBOX_ACTIVE_CHECK_INTERVAL = 0
LOCAL_TIMEZONE = ""
OFFLINE_INTERRUPT = 0
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = False
XBOX_API_TIMEOUT = 0
TOKEN_REFRESH_RETRIES = 0
TOKEN_REFRESH_RETRY_DELAY = 0
MS_AUTH_TOKENS_FILE = ""
CSV_FILE = ""
XBOX_STATUS_FILE = ""
DOTENV_FILE = ""
XBOX_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
TRUNCATE_CHARS = 0
HORIZONTAL_LINE = 0
# Counts the reports printed so far, so a check can tell whether it said anything before the banner claims it was quiet
REPORTS_PRINTED = 0
CLEAR_SCREEN = False
COLORED_OUTPUT = False
COLOR_THEME: dict = {}
VERBOSE_MODE = False
DEBUG_MODE = False
DELIVERY_CONFIRMATIONS = True
XBOX_ACTIVE_CHECK_SIGNAL_VALUE = 0

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "xbox_monitor.conf"

# Where the OAuth tokens are cached when the setting that names the file is empty
DEFAULT_TOKENS_FILENAME = "xbox_tokens.json"

# List of secret keys to load from env/config
SECRET_KEYS = ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Secrets whose length is issued by Microsoft rather than chosen by the user, so reporting it discloses nothing
FIXED_LENGTH_SECRET_KEYS = frozenset(("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"))

# Where each secret's effective value came from, recorded while precedence is applied so it can be reported later
SECRET_SOURCES = {}

# The closed set of layers a secret can come from, so a typo raises instead of inventing a source
SECRET_SOURCE_ORDER = ("configuration file", "dotenv file", "environment", "command line")

# Secrets that were already exported before the dotenv file was loaded, captured at startup
EXPORTED_SECRET_KEYS = frozenset()

# Documentation the tool links to from errors, doctor rows and the welcome screen
DOCS_BASE_URL = "https://misiektoja.github.io/xbox_monitor"
INSTALLATION_GUIDE_URL = f"{DOCS_BASE_URL}/installation/"
QUICK_START_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/"
CONFIG_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#configuration-file"
CREDENTIALS_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#microsoft-entra-application-credentials"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
PRIVACY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#user-privacy-settings"
TIMEZONE_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#time-zone"
SMTP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#smtp-settings"
WEBHOOK_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#webhook-settings"
TLS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#tls-verification"
INTERVALS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#check-intervals"
DIAGNOSTICS_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#verbose-and-debug-output"
DOCTOR_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#doctor-preflight"

# How the positional target may be written. Reused by the recovery advice and every prompt, because three
# hand-written phrasings of the same list is what these tools drift into
XBOX_TARGET_FORMS = "Xbox gamertag, not the Microsoft account e-mail or the real name"

# True once monitoring has printed its header, so a verbose notice after that closes its own block
MONITORING_ACTIVE = False

# How LOCAL_TIMEZONE was resolved, so the doctor reports the configured value rather than the resolved one
LOCAL_TIMEZONE_STATE = "config"

# Doctor label for each timezone outcome, kept identical to the sibling monitors
TIMEZONE_CHECK_LABELS = {"config": "Local timezone is valid", "auto": "Local timezone can be detected", "auto_unavailable": "Automatic timezone detection is unavailable", "auto_failed": "Automatic timezone detection failed", "invalid": "Local timezone is invalid"}

# Version incremented when SIGHUP reloads Xbox application credentials
XBOX_AUTH_REFRESH_VERSION = 0

# Seconds rather than checks, because a failing run usually retries on a different interval than a healthy one
LIVENESS_REMINDER_SECONDS = 0

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

CLI_CONFIG_PATH = None

# Set when --config-file none switches discovery off, so no later lookup can find a file the run rejected
CONFIG_DISCOVERY_DISABLED = False

# The settings a configuration file actually assigned, so a built-in default is never mistaken for a choice
CONFIGURED_SETTING_NAMES = set()

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"

# Global to track if we're at start of line (for debug_print to handle interleaving)
STDOUT_AT_START_OF_LINE = True


import sys
import contextvars
import functools

# Declared once so the startup gate, the packaging metadata and any later environment check cannot disagree
MINIMUM_PYTHON_VERSION = (3, 11)
MINIMUM_PYTHON_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

if sys.version_info < MINIMUM_PYTHON_VERSION:
    print(f"* Error: Python version {MINIMUM_PYTHON_VERSION_TEXT} or higher required !")
    sys.exit(1)


import time
import json
from typing import Any, List, cast
from dataclasses import dataclass, field
import importlib.util
import os
from datetime import datetime, timezone
from dateutil import relativedelta
from dateutil.parser import isoparse
import calendar
import signal
import smtplib
import ssl
from email.header import Header
from email.utils import parsedate_to_datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import ast
import csv
try:
    import pytz
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the pytz library !\n\nTo install it, run:\n    pip3 install pytz\n\nOnce installed, re-run this tool")
try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None
try:
    from colorama import init as colorama_init  # type: ignore[import]
except ImportError:
    colorama_init = None
import platform
import re
import ipaddress
import asyncio
import httpx
from httpx import HTTPStatusError
try:
    from pythonxbox.api.client import XboxLiveClient
    from pythonxbox.authentication.manager import AuthenticationManager
    from pythonxbox.common.exceptions import AuthenticationException
    from pythonxbox.authentication.models import OAuth2TokenResponse
    from pythonxbox.common.signed_session import SignedSession
    from pythonxbox.api.provider.presence.models import PresenceLevel
    from pythonxbox.api.provider.titlehub.models import TitleFields
    from pythonxbox.api.provider.userstats.models import GeneralStatsField
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Python-Xbox library !\n\nTo install it, run:\n    pip install python-xbox\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/tr4nt0r/python-xbox/")
import shutil
import shlex
import getpass
import textwrap
from collections import namedtuple
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


# The four shared status markers. A fifth neutral marker is the single biggest source of drift between these
# tools, because every state it would cover is a state the others already call PASS
DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# Doctor sections in the order they are printed
DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")

# The theme entry each doctor result marker is drawn in, so a failure reads as one at a glance
DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}

# Delivery results are printed as they happen rather than inside a section, but they still count in the summary
DOCTOR_DELIVERY_SECTION = "Optional delivery tests"

# Imported without a guard, so the tool cannot start when one of these is missing
DOCTOR_REQUIRED_DEPENDENCIES = (("pythonxbox", "python-xbox"), ("httpx", "httpx"), ("dateutil", "python-dateutil"), ("pytz", "pytz"))

# Guarded imports the tool degrades around, with what stops working and what to do instead. The last field
# names the only operating system a row applies to, so a machine it cannot affect is not warned about it
DOCTOR_OPTIONAL_DEPENDENCIES = (
    ("tzlocal", "tzlocal", "Used only to auto-detect the local time zone", "Automatic time zone detection is unavailable", "Or set LOCAL_TIMEZONE to a pytz timezone name in the config file", ""),
    ("dotenv", "python-dotenv", "Used only to read secrets from a dotenv file", "Secrets cannot be read from a dotenv file", "Or export them as environment variables", ""),
    ("wcwidth", "wcwidth", "Used only to measure display width for screen truncation", "Wide characters count as one column, so a line holding them can run past the limit", "", ""),
    ("colorama", "colorama", "Used only for coloured output in the older Windows Command Prompt", "Coloured output may not render in the older Windows Command Prompt", "Or use Windows Terminal, which needs nothing extra", "Windows"),
)

# An active check interval below this invites the Xbox Live rate limiter, which stops the tool seeing anything
DOCTOR_MIN_SAFE_ACTIVE_INTERVAL = 30

# Seconds the passive doctor sign-in waits, shorter than a real delivery so a dead host does not stall the report
DOCTOR_SMTP_TIMEOUT = 5

# Shared doctor label for the email channel, kept identical to the sibling monitors
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"

# The webhook readiness label names the service it validated, so anything matching on it matches this prefix
WEBHOOK_READY_CHECK_LABEL = "Webhook URL, headers and alert choices look valid"

# The label every sibling monitor uses when email alerts are on but the settings they would use cannot deliver
EMAIL_UNUSABLE_CHECK_LABEL = "Email alerts are enabled but unusable"

# Width of the progress line currently on screen, which is what erasing it needs to know
DOCTOR_PROGRESS_WIDTH = 0


# Stores one doctor result before the report is rendered
@dataclass(frozen=True)
class DoctorCheck:
    section: str
    status: str
    label: str
    detail: str = ""
    advice: "RecoveryAdvice | None" = None


# Collects doctor results plus the readiness later steps depend on
@dataclass
class DoctorReport:
    checks: list = field(default_factory=list)
    authenticated: bool = False
    email_ready: bool = False
    webhook_ready: bool = False


# Creates one doctor result, refusing a marker outside the shared four and redacting every field it shows
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    # A row the user has to act on is useless without an action, so the row is rejected rather than printed bare
    if status in ("WARN", "FAIL") and (advice is None or not advice.fix):
        raise ValueError(f"Doctor {status} rows require a fix")
    safe_label = sanitize_error_text(label)
    safe_detail = sanitize_error_text(detail)
    # Several advice objects carry the same text as their summary and printing it twice reads as two problems
    return DoctorCheck(section, status, safe_label, "" if safe_detail == safe_label else safe_detail, advice)


# Reports whether one module could be imported, without importing it
def dependency_is_installed(module_name, spec_finder=None):
    finder = importlib.util.find_spec if spec_finder is None else spec_finder
    try:
        return finder(module_name) is not None
    except (ImportError, ValueError):
        return False


# Returns the raw terminal stream, so the transient progress line is not captured by the log writer
def doctor_terminal_stream():
    stream = sys.stdout
    while isinstance(stream, (Logger, TerminalStream)):
        stream = stream.terminal
    return stream


# Shows one transient step only on an interactive terminal, erased by overwriting its own width
# The line stays uncoloured on purpose: it is erased by writing exactly len(line) spaces and an escape
# sequence would make that width wrong and leave a styled remnant behind
def doctor_progress(label):
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty():
        doctor_progress_clear()
        line = f"* Checking {label} ..."
        DOCTOR_PROGRESS_WIDTH = len(line)
        terminal.write("\r" + line)
        terminal.flush()


# Clears the transient progress line, so nothing of it survives into the report
def doctor_progress_clear():
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty() and DOCTOR_PROGRESS_WIDTH:
        terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        terminal.flush()
        DOCTOR_PROGRESS_WIDTH = 0


# Prints the notice that has to be true before anything runs
# Renders one doctor result marker in the colour its status calls for
def render_doctor_marker(status):
    return colorize(DOCTOR_MARK_STYLES.get(status, "info"), f"[{status}]")


def render_doctor_notice():
    print("Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.\n")


# Checks the interpreter, the dependencies the tool needs and the ones it degrades around
def doctor_check_environment(version_info=None, spec_finder=None):
    checks = []
    selected = tuple(sys.version_info if version_info is None else version_info)
    version_text = ".".join(str(part) for part in selected[:3])
    minimum_detail = f"Minimum supported version: {MINIMUM_PYTHON_VERSION_TEXT}"
    if selected[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported", minimum_detail))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", recovery_fix_with_guide(f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", INSTALLATION_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, minimum_detail, advice))

    for module_name, package_name in DOCTOR_REQUIRED_DEPENDENCIES:
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", recovery_fix_with_guide(f"Install it with: {pip_install_command(package_name)}", INSTALLATION_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    for module_name, package_name, purpose, effect, alternative, only_on in DOCTOR_OPTIONAL_DEPENDENCIES:
        if only_on and platform.system() != only_on:
            continue
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Optional dependency {package_name} is installed", purpose))
        else:
            advice = missing_dependency_advice(package_name, effect, alternative)
            checks.append(make_doctor_check("Environment", "WARN", f"Optional dependency {package_name} is not installed", f"{effect}. Every other feature is unaffected", advice))

    return checks


# Groups the secrets that are actually set by the source each value was resolved from
def doctor_secret_sources():
    grouped = {}
    for key in SECRET_KEYS:
        if secret_is_set(globals().get(key)):
            grouped.setdefault(SECRET_SOURCES.get(key, "configuration file"), []).append(key)
    return grouped


# Reports which secrets are in effect and where each one came from, by name and never by value
def doctor_secret_checks():
    grouped = doctor_secret_sources()
    if not grouped:
        return [make_doctor_check("Configuration", "PASS", "No secrets loaded", "Nothing was read from a dotenv file, the environment, the configuration file or the command line")]
    return [make_doctor_check("Configuration", "PASS", f"Secrets loaded from the {source}", ", ".join(names)) for source, names in sorted(grouped.items())]


# Names every on/off setting holding something other than True or False, since a string such as "false" would count as on
def runtime_boolean_errors():
    errors = []
    for statement in ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec").body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, bool):
            value = globals().get(statement.targets[0].id)
            if not isinstance(value, bool):
                errors.append(f"{statement.targets[0].id} must be True or False, not {value!r}")
    return errors


# Returns all type and range errors in settings that control runtime timing or counts
def runtime_configuration_errors():
    errors = []
    positive_numbers = (("XBOX_CHECK_INTERVAL", XBOX_CHECK_INTERVAL), ("XBOX_ACTIVE_CHECK_INTERVAL", XBOX_ACTIVE_CHECK_INTERVAL), ("CHECK_INTERNET_TIMEOUT", CHECK_INTERNET_TIMEOUT), ("XBOX_API_TIMEOUT", XBOX_API_TIMEOUT))
    nonnegative_numbers = (("OFFLINE_INTERRUPT", OFFLINE_INTERRUPT), ("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL), ("TOKEN_REFRESH_RETRY_DELAY", TOKEN_REFRESH_RETRY_DELAY))
    positive_integers = (("TOKEN_REFRESH_RETRIES", TOKEN_REFRESH_RETRIES),)
    for name, value in positive_numbers:
        if not finite_number(value) or value <= 0:
            errors.append(f"{name} must be a number greater than zero, not {value!r}")
    for name, value in nonnegative_numbers:
        if not finite_number(value) or value < 0:
            errors.append(f"{name} must be a number zero or greater, not {value!r}")
    for name, value in positive_integers:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"{name} must be an integer greater than zero, not {value!r}")
    if not isinstance(SMTP_PORT, int) or isinstance(SMTP_PORT, bool) or not 1 <= SMTP_PORT <= 65535:
        errors.append(f"SMTP_PORT must be an integer from 1 through 65535, not {SMTP_PORT!r}")
    return errors


# The values this file defines for the runtime settings checked above, so a configuration file that makes one
# unusable can be reported and then ignored instead of stopping the commands that exist to correct it
BUILT_IN_RUNTIME_SETTINGS = {statement.targets[0].id: statement.value.value for statement in ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec").body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name) and isinstance(statement.value, ast.Constant)}

# The values this file defines for the settings checked below, so a configuration file that makes one
# unusable can be reported and then ignored instead of stopping the commands that exist to correct it
BUILT_IN_SHAPE_SETTINGS = {name: globals()[name] for name in ('XBOX_LOGFILE', 'XBOX_STATUS_FILE', 'CSV_FILE', 'MS_AUTH_TOKENS_FILE', 'DOTENV_FILE', 'COLOR_THEME', 'TRUNCATE_CHARS') if name in globals()}

# Shape errors whose settings were replaced with the built-in values, so doctor still names them
DISCARDED_SETTING_ERRORS = []

DOTENV_STARTUP_ERRORS = {}


# Names the cause of a dotenv file the run could not load, so startup and doctor word the same failure the same way
def dotenv_load_problem(path, error):
    if isinstance(error, UnicodeError):
        return f"Dotenv file '{path}' is not valid UTF-8 text", "Save the dotenv file as UTF-8"
    if isinstance(error, OSError):
        return f"Dotenv file '{path}' could not be opened", "Check the dotenv file path and its read permissions"
    return f"Dotenv file '{path}' could not be read", "Check that the dotenv file is readable UTF-8 text"


# True when the selected command exists to correct the configuration, so a malformed setting is reported
# there instead of stopping the one run that could repair it
def command_reports_configuration(args=None):
    # Read from the parsed namespace rather than the raw words, since argparse also accepts abbreviations
    return any(getattr(args, name, False) for name in ("doctor", "setup", "set_ms_app_credentials", "set_smtp_password", "set_webhook_url"))


# Stops a monitoring run on a runtime setting it cannot use and lets the commands that repair configuration continue
def prepare_runtime_settings(errors, args=None):
    if not errors:
        return
    advice = make_recovery_advice("config.invalid", "Invalid settings: " + ". ".join(errors), recovery_fix_with_guide("Correct the reported settings in the configuration file or command line", CONFIG_GUIDE_URL), False)
    if not command_reports_configuration(args):
        print_recovery_advice(advice)
        raise SystemExit(1)
    # The secret commands never read these values, so the built-in one keeps them working until the setting is corrected
    for name in (error.split(" ", 1)[0] for error in errors):
        if name in BUILT_IN_RUNTIME_SETTINGS:
            globals()[name] = BUILT_IN_RUNTIME_SETTINGS[name]
    print_recovery_advice(advice, label="Warning")
    print()


# Validates effective path settings before startup expands or opens them
def prepare_configured_paths(args):
    overrides = {'DOTENV_FILE': 'env_file', 'CSV_FILE': 'csv_file', 'XBOX_STATUS_FILE': 'status_file'}
    settings = globals().copy()
    for name, argument in overrides.items():
        value = getattr(args, argument, None)
        if value:
            settings[name] = value
    if getattr(args, "truncate", None) is not None:
        settings["TRUNCATE_CHARS"] = args.truncate
        globals()["TRUNCATE_CHARS"] = args.truncate
    errors = configuration_shape_errors(settings)
    if not errors:
        # Cleared here so a run that starts with usable settings cannot inherit an earlier run's report
        DISCARDED_SETTING_ERRORS.clear()
        return
    advice = make_recovery_advice("config.invalid", "Invalid settings: " + ". ".join(errors), recovery_fix_with_guide("Correct the named settings in the configuration file or command line", CONFIG_GUIDE_URL), False)
    # A monitoring run cannot continue on a value this broken, but doctor, the setup wizard and the secret
    # commands are how it gets corrected, so they fall back to the built-in values and report the setting
    if not command_reports_configuration(args):
        print_recovery_advice(advice)
        raise SystemExit(1)
    DISCARDED_SETTING_ERRORS[:] = errors
    # Only the values that are broken after command-line overrides are replaced, so an override still wins
    for name, built_in in BUILT_IN_SHAPE_SETTINGS.items():
        if name in settings and configuration_shape_errors({name: settings[name]}):
            globals()[name] = built_in
    # Doctor lists the same settings as report rows, so a warning above it would only say them twice
    if not getattr(args, "doctor", False):
        print_recovery_advice(advice, label="Warning")
        print()


# Names malformed path and color settings before diagnostics consume their values
def configuration_shape_errors(settings=None):
    errors = list(DISCARDED_SETTING_ERRORS) if settings is None else []
    settings = globals() if settings is None else settings
    for name in ('XBOX_LOGFILE', 'XBOX_STATUS_FILE', 'CSV_FILE', 'MS_AUTH_TOKENS_FILE', 'DOTENV_FILE'):
        if name in settings and not isinstance(settings[name], (str, os.PathLike)):
            errors.append(f"{name} must be a path string")
    width = settings.get("TRUNCATE_CHARS", 0)
    if not isinstance(width, int) or isinstance(width, bool) or width < 0:
        errors.append("TRUNCATE_CHARS must be an integer zero or greater")
    theme = settings.get("COLOR_THEME", {})
    if not isinstance(theme, dict):
        errors.append("COLOR_THEME must be a dictionary of style strings")
    else:
        errors.extend(f"COLOR_THEME[{key!r}] must be a style string" for key, value in theme.items() if not isinstance(value, str))
    return errors


# Replaces every setting still holding a value this file cannot use with the built-in one, so a report reached
# from any entry point reads a usable value after it has named the setting
def discard_invalid_shape_settings():
    for name, built_in in BUILT_IN_SHAPE_SETTINGS.items():
        if configuration_shape_errors({name: globals().get(name)}):
            globals()[name] = built_in


# Reports the effective settings and the files the tool would write, without writing any of them
def doctor_check_configuration(config_path=None, env_path=None, config_advice=None, timezone_advice=None, xbox_gamertag=None):
    # Read before the unusable values are replaced, so each row names the value the user configured
    # Reported as ordinary rows so one malformed setting cannot hide the rest of the configuration report
    checks = [make_doctor_check("Configuration", "FAIL", detail, advice=make_recovery_advice("config.invalid", detail, recovery_fix_with_guide("Correct the named setting in the configuration file", CONFIG_GUIDE_URL), False)) for detail in configuration_shape_errors()]
    discard_invalid_shape_settings()
    if config_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", config_advice.summary, advice=config_advice))
    elif config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))

    if env_path and str(env_path) in DOTENV_STARTUP_ERRORS:
        detail, fix = DOTENV_STARTUP_ERRORS[str(env_path)]
        advice = make_recovery_advice("file.unreadable", detail, recovery_fix_with_guide(f"{fix}, then run Doctor again", CONFIG_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "FAIL", "Dotenv file could not be loaded", detail, advice))
    elif env_path and os.path.isfile(str(env_path)):
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    elif env_path:
        advice = make_recovery_advice("config.missing", "The requested dotenv file was not found", recovery_fix_with_guide("Create the file or select an existing path with --env-file", SECRETS_GUIDE_URL), False, f"Path: {env_path}")
        checks.append(make_doctor_check("Configuration", "WARN", advice.summary, advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))

    checks.extend(doctor_secret_checks())

    timezone_label = TIMEZONE_CHECK_LABELS[LOCAL_TIMEZONE_STATE]
    if timezone_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", timezone_label, timezone_advice.detail, timezone_advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", timezone_label, f"Time zone: {LOCAL_TIMEZONE}"))

    if finite_number(XBOX_CHECK_INTERVAL) and isinstance(XBOX_ACTIVE_CHECK_INTERVAL, (int, float)) and not isinstance(XBOX_ACTIVE_CHECK_INTERVAL, bool) and 0 < XBOX_ACTIVE_CHECK_INTERVAL < DOCTOR_MIN_SAFE_ACTIVE_INTERVAL:
        intervals = f"{display_time(XBOX_CHECK_INTERVAL)} while offline, {display_time(XBOX_ACTIVE_CHECK_INTERVAL)} while online"
        advice = make_recovery_advice("xbox.rate_limited", "Check intervals are short enough to be rate limited", recovery_fix_with_guide(f"Raise XBOX_ACTIVE_CHECK_INTERVAL to at least {DOCTOR_MIN_SAFE_ACTIVE_INTERVAL} seconds", INTERVALS_GUIDE_URL), True)
        checks.append(make_doctor_check("Configuration", "WARN", "Check intervals are short", intervals, advice))

    if VERIFY_SSL:
        checks.append(make_doctor_check("Configuration", "PASS", "TLS certificate verification is on", "Every outbound request checks the server certificate"))
    else:
        advice = make_recovery_advice("config.insecure", "TLS certificate verification is off", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "WARN", "TLS certificate verification is off", "VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service", advice))

    numeric_errors = runtime_configuration_errors()
    if numeric_errors:
        numeric_detail = "Invalid numeric settings: " + "; ".join(numeric_errors)
        advice = make_recovery_advice("config.invalid", "One or more numeric settings are invalid", recovery_fix_with_guide("Correct the reported settings in the configuration file", CONFIG_GUIDE_URL), False, numeric_detail)
        checks.append(make_doctor_check("Configuration", "FAIL", "One or more numeric settings are invalid", numeric_detail, advice))
    boolean_errors = runtime_boolean_errors()
    if boolean_errors:
        boolean_detail = "Invalid on/off settings: " + "; ".join(boolean_errors)
        advice = make_recovery_advice("config.invalid", "One or more on/off settings are invalid", recovery_fix_with_guide("Set the reported settings to True or False in the configuration file", CONFIG_GUIDE_URL), False, boolean_detail)
        checks.append(make_doctor_check("Configuration", "FAIL", "One or more on/off settings are invalid", boolean_detail, advice))

    try:
        ascii_log_separators_enabled()
    except ValueError as exc:
        advice = classify_recovery_error(context="config.invalid", detail=str(exc))
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if MS_AUTH_TOKENS_FILE:
        tokens_path = os.path.expanduser(MS_AUTH_TOKENS_FILE)
        if path_is_writable(tokens_path):
            checks.append(make_doctor_check("Configuration", "PASS", "Xbox token cache appears writable", f"Path: {tokens_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"Xbox token cache '{tokens_path}' cannot be written")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    else:
        advice = classify_recovery_error(context="config.invalid", detail="MS_AUTH_TOKENS_FILE is empty, so authorized tokens cannot be saved")
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled"))
    else:
        # A name with an extension is used as it is, so only a bare base name has to wait for the target
        log_path = resolve_log_path(xbox_gamertag) if (xbox_gamertag or Path(os.path.expanduser(XBOX_LOGFILE)).suffix) else ""
        if not log_path:
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination will be finalized after a target is selected", f"Base path: {Path(os.path.expanduser(XBOX_LOGFILE))}"))
        elif path_is_writable(log_path):
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination appears writable", f"Path: {log_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"Log destination is not writable: {log_path}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if CSV_FILE:
        csv_path = os.path.expanduser(CSV_FILE)
        if path_is_writable(csv_path):
            checks.append(make_doctor_check("Configuration", "PASS", "CSV destination appears writable", f"Path: {csv_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"CSV destination is not writable: {csv_path}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV logging is disabled"))

    # A configured path is fixed, so it stays checkable without a target. The default name carries the target
    status_path = os.path.expanduser(XBOX_STATUS_FILE) if XBOX_STATUS_FILE else (resolve_status_file(xbox_gamertag) if xbox_gamertag else "")
    if not status_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Status file will be finalized after a target is selected", "Base name: xbox_<xbox_gamertag>_last_status.json in the working directory"))
    elif path_is_writable(status_path):
        checks.append(make_doctor_check("Configuration", "PASS", "Status destination appears writable", f"Path: {status_path}"))
    else:
        advice = classify_recovery_error(context="file.unwritable", detail=f"Status destination is not writable: {status_path}")
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    return checks


# Reports whether the endpoint the tool checks at startup answers, using the configured URL, timeout and TLS setting
def doctor_check_connectivity():
    try:
        with httpx.Client(verify=tls_context(), timeout=CHECK_INTERNET_TIMEOUT) as client:
            client.get(CHECK_INTERNET_URL)
        debug_print("Doctor connectivity check", url=CHECK_INTERNET_URL, outcome="OK")
    except Exception as exc:
        debug_print("Doctor connectivity check", url=CHECK_INTERNET_URL, outcome="failed", error=f"{type(exc).__name__}: {exc}")
        advice = classify_recovery_error(exc, context="connectivity", detail=f"{CHECK_INTERNET_URL} could not be reached: {exc}")
        return [make_doctor_check("Connectivity", "FAIL", "The connectivity endpoint could not be reached", f"Endpoint: {CHECK_INTERNET_URL}", advice)]
    return [make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable", f"Endpoint: {CHECK_INTERNET_URL}")]


# Loads the cached tokens and refreshes them without writing anything, which is what the real run does first
# A real run answers an unreadable cache by starting the interactive sign-in, which writes a file, so here the
# same state has to become a diagnosis instead
async def doctor_refresh_tokens(auth_mgr):
    try:
        with open(Path(MS_AUTH_TOKENS_FILE).expanduser(), encoding="utf-8") as tokens_file:
            auth_mgr.oauth = OAuth2TokenResponse.model_validate_json(tokens_file.read())
    except OSError as exc:
        raise RecoveryError(classify_recovery_error(context="file.unreadable", detail=f"The Xbox token cache '{MS_AUTH_TOKENS_FILE}' could not be read: {exc}"), exc) from None
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(context="auth.token_cache", detail=f"The Xbox token cache '{MS_AUTH_TOKENS_FILE}' is not a saved token response ({type(exc).__name__})"), exc) from None
    await refresh_tokens_with_retry(auth_mgr)


# Signs in to Xbox Live with the saved tokens and looks the monitored profile up, writing nothing
async def doctor_check_xbox_live(report, xbox_gamertag=None, progress=None):
    checks = []
    credentials_missing = [name for name in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET") if not secret_is_set(globals().get(name))]
    if credentials_missing:
        advice = classify_recovery_error(context="secret.missing", detail=f"{join_names(credentials_missing)} is not set" if len(credentials_missing) == 1 else f"{join_names(credentials_missing)} are not set")
        checks.append(make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice))
        return checks + doctor_check_target_identity(report, xbox_gamertag)
    checks.append(make_doctor_check("Authentication", "PASS", "Microsoft application credentials are set", "MS_APP_CLIENT_ID and MS_APP_CLIENT_SECRET both hold a value"))

    tokens_path = Path(os.path.expanduser(MS_AUTH_TOKENS_FILE or ""))
    if not tokens_path.is_file():
        advice = make_recovery_advice("auth.token_cache", "No saved Xbox tokens were found", recovery_fix_with_guide(f"Authorize once by running: {render_command(['--setup'])}, or start monitoring with: {render_command(['<xbox_gamertag>'])}. Doctor writes no files, so it cannot run the sign-in flow for you", CREDENTIALS_GUIDE_URL), False, f"Expected the token cache at {tokens_path}")
        checks.append(make_doctor_check("Authentication", "WARN", "No saved Xbox tokens were found", f"Path: {tokens_path}", advice))
        return checks + doctor_check_target_identity(report, xbox_gamertag)

    if os.name == "posix" and (tokens_path.stat().st_mode & 0o077):
        advice = make_recovery_advice("auth.token_cache", "The Xbox token cache is readable by other accounts", recovery_fix_with_guide(f"Restrict it with: {render_command(['chmod', '600', str(tokens_path)])}", SECRETS_GUIDE_URL), False, f"{tokens_path} holds a refresh token")
        checks.append(make_doctor_check("Authentication", "WARN", "The Xbox token cache is readable by other accounts", f"Path: {tokens_path}", advice))
    else:
        checks.append(make_doctor_check("Authentication", "PASS", "The Xbox token cache is present", f"Path: {tokens_path}"))

    if progress is not None:
        progress("the Xbox Live sign-in")
    session = None
    try:
        session = create_signed_session()
        auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, "")
        try:
            await doctor_refresh_tokens(auth_mgr)
        except Exception as exc:
            advice = classify_recovery_error(exc, context="auth", detail=f"Refreshing the saved Xbox tokens failed: {exc}")
            checks.append(make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice))
            return checks + doctor_check_target_identity(report, xbox_gamertag)
        report.authenticated = True
        checks.append(make_doctor_check("Authentication", "PASS", "Xbox Live accepted the saved tokens", "The saved tokens were refreshed in memory and nothing was written"))
        identity_checks = doctor_check_target_identity(report, xbox_gamertag)
        checks.extend(identity_checks if identity_checks else await doctor_check_target(auth_mgr, xbox_gamertag, progress))
    finally:
        if session is not None:
            await session.aclose()
    return checks


# Reports whether a profile was even named and stays silent once authentication has already explained itself
def doctor_check_target_identity(report, xbox_gamertag=None):
    if not xbox_gamertag:
        advice = classify_recovery_error(context="target.missing", detail="No Xbox gamertag was provided")
        return [make_doctor_check("Target", "WARN", advice.summary, "Nothing will be monitored until one is given", advice)]
    if not report.authenticated:
        # Authentication already failed and reported why. A second row would repeat one problem as two
        return [make_doctor_check("Target", "SKIP", "The monitored profile was not checked", "Sign-in did not succeed, so no lookup was attempted")]
    return []


# Looks the monitored gamertag up with the session the authentication check already established
async def doctor_check_target(auth_mgr, xbox_gamertag, progress=None):
    if progress is not None:
        progress("the monitored profile")
    try:
        xbl_client = XboxLiveClient(auth_mgr)
        profile = await xbl_client.profile.get_profile_by_gamertag(str(xbox_gamertag))
        xuid = int(profile.profile_users[0].id)
        presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
        # Parsed and discarded on purpose. A profile that answers with a body monitoring cannot read is a target
        # failure the report has to show, and only parsing it proves the response is usable
        xbox_process_presence_class(presence, False)
    except Exception as exc:
        advice = classify_recovery_error(exc, context="target", detail=f"Looking up the gamertag '{xbox_gamertag}' failed: {exc}")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    return [make_doctor_check("Target", "PASS", f"Gamertag {xbox_gamertag} was found and activity is accessible", f"XUID: {xuid}")]


# Reports the first unusable email setting as a doctor detail and an action that names the same settings
def mail_sign_in_settings_problem():
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            return ("SMTP_HOST is not a valid IP address or hostname", "Correct SMTP_HOST or turn the email alerts off")

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError):
        return ("SMTP_PORT is not a port number between 1 and 65535", "Correct SMTP_PORT or turn the email alerts off")

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        return ("SENDER_EMAIL or RECEIVER_EMAIL is not an email address", "Correct SENDER_EMAIL and RECEIVER_EMAIL or turn the email alerts off")

    if not secret_is_set(SMTP_USER):
        return ("SMTP_USER is empty or still set to its placeholder", "Set SMTP_USER or turn the email alerts off")

    return None


# Reports the first unusable email setting, including the password a delivery needs but a sign-in supplies
def email_settings_problem():
    problem = mail_sign_in_settings_problem()
    if problem is not None:
        return problem
    if not secret_is_set(SMTP_PASSWORD):
        return ("SMTP_PASSWORD is empty or still set to its placeholder", f"Set SMTP_PASSWORD with {render_command(['--set-smtp-password'])} or turn the email alerts off")
    return None


# Returns advice for the first unusable SMTP server setting, or None when they are all present and valid
def validate_smtp_settings():
    problem = email_settings_problem()
    return classify_recovery_error(context="smtp.settings", detail=problem[0]) if problem is not None else None


# Signs in while removing the attempted password from SMTP rejection replies before they can be rendered
def smtp_login(connection, username, password):
    try:
        return connection.login(username, password)
    except smtplib.SMTPResponseException as error:
        reply = error.smtp_error
        if password:
            if isinstance(reply, bytes):
                reply = reply.replace(str(password).encode("utf-8"), b"<redacted>")
            else:
                reply = str(reply).replace(str(password), "<redacted>")
        error.smtp_error = reply
        error.args = (error.smtp_code, reply)
        raise


# Signs in to the configured SMTP server with one candidate password, without sending a message
def smtp_sign_in(password, timeout=15):
    global SMTP_PASSWORD

    candidate = str(password or "")
    if not secret_is_set(candidate):
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="No SMTP password was entered, so nothing was changed"))
    previous_password = SMTP_PASSWORD
    SMTP_PASSWORD = candidate
    try:
        settings_advice = validate_smtp_settings()
        if settings_advice is not None:
            raise RecoveryError(settings_advice)
        debug_print("SMTP sign-in check", host=SMTP_HOST, port=SMTP_PORT, user=SMTP_USER, starttls=bool(SMTP_SSL), timeout=timeout)
        connection = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout)
        if SMTP_SSL:
            connection.starttls(context=tls_context())
        try:
            smtp_login(connection, SMTP_USER, candidate)
        finally:
            try:
                connection.quit()
            except Exception as quit_error:
                debug_print("SMTP connection close", outcome="failed", error=f"{type(quit_error).__name__}: {quit_error}")
    except RecoveryError:
        raise
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="smtp", detail=f"Signing in to {SMTP_HOST} as {SMTP_USER} failed: {exc}"), exc) from None
    finally:
        SMTP_PASSWORD = previous_password
    return SMTP_USER


# Returns the doctor row for email alerts whose settings cannot deliver, worded the same way by every sibling monitor
def doctor_email_unusable_check(detail, fix):
    advice = make_recovery_advice("smtp.invalid", EMAIL_UNUSABLE_CHECK_LABEL, recovery_fix_with_guide(fix, SMTP_GUIDE_URL), False, detail)
    return make_doctor_check("Notifications", "WARN", EMAIL_UNUSABLE_CHECK_LABEL, detail, advice)


# Reports whether email alerts can fire at all, then whether the settings they would use are usable
def doctor_check_email_notifications(report):
    problem = email_settings_problem()
    # An error alert is on by default, so on its own it cannot make a fresh install look configured
    deliberate = ACTIVE_INACTIVE_NOTIFICATION or GAME_CHANGE_NOTIFICATION or STATUS_NOTIFICATION
    if not deliberate and problem is not None:
        return [make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent")]
    if problem is not None:
        return [doctor_email_unusable_check(*problem)]
    if not deliberate and not ERROR_NOTIFICATION:
        advice = make_recovery_advice("smtp.invalid", "Email is configured but no alert types are selected", recovery_fix_with_guide("Turn on at least one email alert in the configuration file", SMTP_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be emailed", advice)]
    try:
        smtp_sign_in(SMTP_PASSWORD, timeout=DOCTOR_SMTP_TIMEOUT)
    except RecoveryError as exc:
        return [make_doctor_check("Notifications", "FAIL", exc.advice.summary, exc.advice.detail, exc.advice)]
    alerts = ", ".join(name for name, enabled in (("status changes", ACTIVE_INACTIVE_NOTIFICATION), ("game changes", GAME_CHANGE_NOTIFICATION), ("all status changes", STATUS_NOTIFICATION), ("errors", ERROR_NOTIFICATION)) if enabled)
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", SMTP_READY_CHECK_LABEL, f"Alerts: {alerts}. No email was sent during this passive check")]


# Reports whether webhook alerts can fire at all, then whether the settings they would use are usable
def doctor_check_webhook_notifications(report):
    selected = webhook_notification_categories()
    # An error alert is on by default, so on its own it cannot make a fresh install look configured
    deliberate = WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION or WEBHOOK_GAME_CHANGE_NOTIFICATION or WEBHOOK_STATUS_NOTIFICATION
    if not WEBHOOK_ENABLED:
        if not deliberate:
            return [make_doctor_check("Notifications", "PASS", "Webhook alerts are disabled")]
        advice = make_recovery_advice("webhook.invalid", "Webhook alert types are selected but webhooks are switched off", recovery_fix_with_guide("Set WEBHOOK_ENABLED to True, or turn the alert types off", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    provider = normalized_webhook_provider()
    if not provider:
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_PROVIDER must be discord or ntfy")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not validate_webhook_url():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    for validation_error in (validate_webhook_customization(provider), validate_webhook_headers(provider)):
        if validation_error is not None:
            advice = classify_recovery_error(context="webhook", detail=validation_error)
            return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not selected:
        advice = make_recovery_advice("webhook.invalid", "Webhook alerts are on but no alert types are selected", recovery_fix_with_guide("Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    report.webhook_ready = True
    return [make_doctor_check("Notifications", "PASS", f"{WEBHOOK_READY_CHECK_LABEL} for {webhook_provider_display_name()}", f"Alerts: {', '.join(selected)}. The private link was not displayed. No webhook was sent during this passive check")]


# Asks for delivery consent, treating a closed or interrupted input as no
def ask_yes_no(question, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = read_interactively(input, colorize("info", f"{question} {hint}: ")).strip().casefold()
        except EOFError:
            print("\nDelivery test skipped.")
            return False
        except KeyboardInterrupt:
            # Ctrl+C ends the run here the way it does anywhere else, rather than only declining this one test
            signal_handler(signal.SIGINT, None)
            raise
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Prints one result the way the report renders it, so a row printed after the report matches the rows above it
def print_doctor_check(check):
    print(f"{render_doctor_marker(check.status)} {check.label}")
    if check.detail:
        print(f"  {colorize_links(check.detail)}")


# Offers a real delivery test for each channel that already passed, approved separately from the report
def offer_doctor_delivery_tests(report):
    if not (report.email_ready or report.webhook_ready) or not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    print("\n" + colorize("section", "Optional delivery tests") + "\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    offered = []
    if report.email_ready:
        if ask_yes_no("Send one test email now? This will deliver a real message"):
            delivered = send_email("Xbox Monitor doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=DOCTOR_SMTP_TIMEOUT, report_delivery=False) == 0
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", "Doctor test email delivered", "One real test email was sent after confirmation")
            else:
                advice = make_recovery_advice("smtp.connection", "Doctor test email delivery failed", recovery_fix_with_guide("Review the SMTP error above and correct the email settings", SMTP_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test email could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent", "You declined the real delivery test. Run doctor again and approve the email test when ready")
        offered.append(check)
        # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
        report.checks.append(check)
        print_doctor_check(check)
    if report.webhook_ready:
        provider = webhook_provider_display_name()
        if ask_yes_no(f"Send one test webhook through {provider} now? This will publish a real notification"):
            delivered = send_webhook("Xbox Monitor doctor test webhook", "This test notification was sent after approval in --doctor. Your webhook delivery settings work.", "status", force=True, report_delivery=False) == 0
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", f"Doctor test webhook through {provider} delivered", "One real test webhook was sent after confirmation")
            else:
                advice = make_recovery_advice("webhook.connection", f"Doctor test webhook through {provider} delivery failed", recovery_fix_with_guide("Review the webhook error above and correct the destination settings", WEBHOOK_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test webhook could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", f"Test webhook through {provider} was not sent", "You declined the real delivery test. Run doctor again and approve the webhook test when ready")
        offered.append(check)
        report.checks.append(check)
        print_doctor_check(check)
    return offered


# Runs every section in order, reporting each step while it is still running
def build_doctor_report(xbox_gamertag=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None, progress=None):
    report = DoctorReport()
    steps = (
        ("environment", lambda: doctor_check_environment()),
        ("configuration", lambda: doctor_check_configuration(config_path, env_path, config_advice, timezone_advice, xbox_gamertag)),
        ("connectivity", lambda: doctor_check_connectivity()),
        ("authentication", lambda: asyncio.run(doctor_check_xbox_live(report, xbox_gamertag, progress))),
        ("notifications", lambda: doctor_check_email_notifications(report) + doctor_check_webhook_notifications(report)),
    )
    for label, run_step in steps:
        if progress is not None:
            progress(label)
        report.checks.extend(run_step())
    return report


# Renders the heading and every non-empty section, with a fix line on the rows that are not a pass
def render_doctor_sections(report):
    # The install method is context rather than a check: it cannot fail, so it is stated once here
    # instead of occupying a result row that no marker describes. The raw key is what support reports use
    lines = [colorize("header", "Doctor"), f"Detected install method: {colorize('username', detect_install_method())}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", colorize("section", section)))
        for check in section_checks:
            lines.append(f"{render_doctor_marker(check.status)} {check.label}")
            if check.detail:
                lines.append(f"  {colorize_links(check.detail)}")
            if check.advice is not None and check.status != "PASS":
                # The fix carries its own guide line, so each line is indented and styled on its own rather
                # than leaving one colour sequence open across the newline
                lines.extend(f"  {colorize_fix_line(advice_line)}" for advice_line in f"To fix: {check.advice.fix}".splitlines())
    return sanitize_error_text("\n".join(lines))


# Renders the one sentence that says whether the setup is usable and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        sentence = colorize("error", f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool.")
    elif warnings:
        sentence = colorize("warning", f"  All critical checks passed with {warnings} warning(s). Review the warnings above.")
    else:
        sentence = colorize("boolean_true", "  All checks passed. You are good to go!")
    return "\n".join(("", colorize("header", "Summary"), sentence, "", colorize_links(f"Guide: {DOCTOR_GUIDE_URL}")))


# Runs the preflight report plus any approved delivery test and returns the process exit code
def run_doctor(xbox_gamertag=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None):
    render_doctor_notice()
    progress = doctor_progress if doctor_terminal_stream().isatty() else None
    try:
        report = build_doctor_report(xbox_gamertag, config_path, env_path, config_advice, timezone_advice, progress)
    finally:
        doctor_progress_clear()
    print(render_doctor_sections(report))
    offer_doctor_delivery_tests(report)
    print(render_doctor_summary(report.checks))
    return 1 if any(check.status == "FAIL" for check in report.checks) else 0


# One startup summary setting, routed to the concise view, the full view or both. The log keeps the full view
StartupSummaryRow = namedtuple("StartupSummaryRow", ["label", "value", "concise", "full"])
StartupSummaryRow.__new__.__defaults__ = (False, True)


# Reports whether the reader asked for the complete startup summary rather than the concise one
def full_startup_summary_enabled():
    return bool(VERBOSE_MODE or DEBUG_MODE)


# Returns the email alert rollup, naming what is switched on rather than printing four separate booleans
def startup_notification_state():
    enabled = [name for name, on in (("status changes", ACTIVE_INACTIVE_NOTIFICATION), ("game changes", GAME_CHANGE_NOTIFICATION), ("all status changes", STATUS_NOTIFICATION), ("errors", ERROR_NOTIFICATION)) if on]
    return "On (" + ", ".join(enabled) + ")" if enabled else "Off"


# Returns the webhook alert rollup, which reads Off whenever the channel itself is switched off
def startup_webhook_notification_state():
    enabled = webhook_notification_categories() if WEBHOOK_ENABLED else []
    return "On (" + ", ".join(enabled) + ")" if enabled else "Off"


# Hides the middle of an address's local part, so a log can be shared while the reader can still spot a typo
def mask_email_address(address):
    text = str(address or "").strip()
    local, at_sign, domain = text.partition("@")
    if not at_sign or not local or not domain:
        return text
    masked = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}" if len(local) > 2 else f"{local[0]}{'*' * (len(local) - 1)}"
    return f"{masked}@{domain}"


# Names the mail server this run would use, leaving out the account that signs in to it
def startup_email_transport():
    if not SMTP_HOST or not SMTP_PORT:
        return "Not configured"
    return f"{SMTP_HOST}:{SMTP_PORT} ({'STARTTLS' if SMTP_SSL else 'TLS off'})"


# Names the configured webhook service and whether the channel is switched on, which are two separate settings
def startup_webhook_provider():
    if not normalized_webhook_provider() or not str(WEBHOOK_URL or "").strip():
        return "Not configured"
    return f"{webhook_provider_display_name()} ({'enabled' if WEBHOOK_ENABLED else 'disabled'})"


# Builds every summary row in the order the sibling tools print them, most useful first
def build_startup_summary(xbox_gamertag=None, config_path=None, env_path=None, log_path=None):
    supplied = doctor_secret_sources()
    from_dotenv = sorted(supplied.get("dotenv file", ()))
    from_environment = sorted(supplied.get("environment", ()))
    # Bucketed by exact source rather than by "everything else", so a command-line secret is not filed as config
    from_config = sorted(supplied.get("configuration file", ()))
    from_command_line = sorted(supplied.get("command line", ()))
    output_state = str(log_path) if log_path else "Terminal only (logging disabled)"
    return [
        StartupSummaryRow("Target", str(xbox_gamertag) if xbox_gamertag else "None", concise=True),
        StartupSummaryRow("Polling intervals", f"[offline: {display_time(XBOX_CHECK_INTERVAL)}] [online: {display_time(XBOX_ACTIVE_CHECK_INTERVAL)}]", concise=True),
        StartupSummaryRow("Offline grace period", display_time(OFFLINE_INTERRUPT) if OFFLINE_INTERRUPT else "Disabled"),
        StartupSummaryRow("Notifications (email)", startup_notification_state(), concise=True),
        StartupSummaryRow("Email transport", startup_email_transport()),
        StartupSummaryRow("Email recipient", mask_email_address(RECEIVER_EMAIL) if RECEIVER_EMAIL else "Not configured"),
        StartupSummaryRow("Notifications (webhook)", startup_webhook_notification_state(), concise=True),
        StartupSummaryRow("Webhook provider", startup_webhook_provider()),
        StartupSummaryRow("Delivery confirmations", str(DELIVERY_CONFIRMATIONS)),
        StartupSummaryRow("Output", output_state, concise=True, full=False),
        StartupSummaryRow("Output logging", str(log_path) if log_path else "Disabled"),
        StartupSummaryRow("Config", str(config_path) if config_path else ("Discovery disabled" if CONFIG_DISCOVERY_DISABLED else "None"), concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        # Each optional feature earns a concise row only once it is actually switched on
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Status file", resolve_status_file(xbox_gamertag) if xbox_gamertag else "None"),
        StartupSummaryRow("Token cache", MS_AUTH_TOKENS_FILE or "None"),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Process id", str(os.getpid())),
        StartupSummaryRow("Python version", platform.python_version()),
        StartupSummaryRow("Operating system", f"{platform.platform(terse=True)} ({platform.machine()})"),
        StartupSummaryRow("Local timezone", LOCAL_TIMEZONE),
        StartupSummaryRow("Install method", install_method_display_name()),
        StartupSummaryRow("Secrets from dotenv", ", ".join(from_dotenv) if from_dotenv else "None"),
        StartupSummaryRow("Secrets from environment", ", ".join(from_environment) if from_environment else "None"),
        StartupSummaryRow("Secrets from config file", ", ".join(from_config) if from_config else "None"),
        StartupSummaryRow("Secrets from command line", ", ".join(from_command_line) if from_command_line else "None"),
        StartupSummaryRow("TLS verification", "On" if VERIFY_SSL else "Off, server certificates are not checked", concise=not VERIFY_SSL),
        StartupSummaryRow("ASCII log separators", f"{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})"),
        # The resolved state, not the setting: colour also switches itself off when the output is not a terminal
        StartupSummaryRow("Coloured output", f"{COLOR_ENABLED} (setting: {COLORED_OUTPUT})"),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
        # Points at the two modes for a reader who does not know they exist, so the full view drops it
        StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False),
    ]


# Rows that detail the channel named right above them, indented so the block reads as one setting with its details
STARTUP_SUMMARY_NESTED_LABELS = ("Email transport", "Email recipient", "Email images", "Webhook provider", "ntfy images")


# Formats one summary row with an aligned value column, wrapping only the rollup that grows long
def format_startup_summary_row(row):
    indent = "  " if row.label in STARTUP_SUMMARY_NESTED_LABELS else ""
    prefix = f"* {indent}{(row.label + ':'):<{30 - len(indent)}}"
    if row.label in ("Notifications (email)", "Notifications (webhook)"):
        return textwrap.fill(str(row.value), width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False) + "\n"
    return f"{prefix}{row.value}\n"


# Prints the summary, showing the concise rows unless the full view was asked for. The log file always keeps
# the complete set, so a bug report made from a log carries every effective setting whatever the terminal showed
def emit_startup_summary(rows, show_full=False, stream=None):
    destination = sys.stdout if stream is None else stream
    # A stream that does not split its output has no log file to hold the full view, so those writes go nowhere
    write_log = getattr(destination, "log_only", lambda line: None)
    write_terminal = getattr(destination, "terminal_only", None)
    if write_terminal is None:
        write_terminal = destination.write
    for row in rows:
        line = format_startup_summary_row(row)
        if row.full:
            write_log(line)
        if row.full if show_full else row.concise:
            write_terminal(line)
    write_log("\n")
    write_terminal("\n")
    destination.flush()


# Reports whether separator-only log lines should use ASCII on this system
def ascii_log_separators_enabled():
    mode = str(ASCII_LOG_SEPARATORS).strip().lower()
    if mode not in {"auto", "on", "off"}:
        raise ValueError("ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'")
    return mode == "on" or (mode == "auto" and platform.system() == "Windows")


# Converts Unicode-only horizontal separator lines to ASCII when configured
def normalize_log_separators(message):
    if not ascii_log_separators_enabled():
        return message
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Any escape sequence, used to keep the log file plain text
ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

# The only escape sequence this tool emits is an SGR colour/style change, so it is the only one worth keeping
SGR_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Every other control character is dropped, keeping only tab and newline. A carriage return would let Xbox-supplied
# text overwrite an already printed line and the inline doctor progress that uses one writes to the terminal directly
TERMINAL_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


# Collapses the whitespace a mail header cannot carry, so Xbox-supplied text in a subject cannot inject one
def sanitize_email_header(value):
    return re.sub(r"\s+", " ", TERMINAL_CONTROL_RE.sub("", str(value or ""))).strip()


# Removes terminal control sequences that Xbox-supplied text could use to drive the terminal, keeping this tool's own colours
def sanitize_terminal_text(message):
    if not isinstance(message, str) or not message:
        return message
    parts = []
    position = 0
    for match in SGR_SEQUENCE_RE.finditer(message):
        parts.append(TERMINAL_CONTROL_RE.sub("", message[position:match.start()]))
        parts.append(match.group(0))
        position = match.end()
    parts.append(TERMINAL_CONTROL_RE.sub("", message[position:]))
    return "".join(parts)


# Internal flag and style map for colour handling
COLOR_ENABLED = False
_COLOR_STYLES: dict = {}

# Default built-in colour theme. Values can be overridden via COLOR_THEME in config
DEFAULT_COLOR_THEME = {
    # Headings and commands the wizard tells you to run
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "bright_cyan underline",
    "id": "bright_magenta",
    # Presence status values
    "status_active": "green",
    "status_away": "yellow",
    "status_inactive": "red",
    "status_offline": "red",
    "status_other": "white",
    # Xbox info
    "game": "bright_yellow",
    "platform": "blue",
    "achievement": "bright_green",
    "duration": "green",
    # Activity info
    "status_change": "yellow",
    # Misc
    "timestamp_label": "",
    "timestamp_value": "cyan",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    "email": "bright_cyan",
    "webhook": "bright_blue",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
    # Counters and differences
    "count_up": "green",
    "count_down": "red",
    "link": "blue underline",
    # Help screen
    "help_heading": "bright_cyan bold",
    "help_usage": "bright_white bold",
    "help_option": "bright_green",
    "help_metavar": "yellow",
    "help_placeholder": "bright_magenta",
    "help_command": "bright_white",
    "help_comment": "bright_black",
    "help_default": "bright_black",
}

# Whole-line styles, listed so the palette test can prove no value colour disappears inside one of them.
# Warnings and signals are not on this list: both are yellow, which is the colour of the words reporting an
# activity change, so they mark their own opening words instead of painting the line
BLOCK_STYLE_PARTS = ("error", "info", "email", "webhook")

# Parts that carry a name supplied by Xbox or by the user, or that report a change, which a block style
# must never hide
NAME_STYLE_PARTS = ("username", "id", "game", "platform", "achievement", "status_change", "link")

# COLOR_THEME key names used by older releases. This tool shipped the current names, so there is nothing to alias yet
_THEME_KEY_ALIASES: dict = {}

ANSI_RESET = "\033[0m"

# Mapping of style names to ANSI SGR codes
_STYLE_CODES = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "blink": "5",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

# Output labels whose value is coloured with one theme style, longest label first so a prefix cannot win
_LABEL_STYLES = (
    (("Gamertag:", "Target:"), "username"),
    (("XUID:",), "id"),
    (("Current game:", "Title name:", "Game:"), "game"),
    (("Platform:",), "platform"),
    (("Gamerscore:",), "achievement"),
)

# Pre-compiled regexes used for line-level colourisation
_FROM_TO_COUNT_RE = re.compile(r"(from\s+)(\d+)(\s+to\s+)(\d+)")
_DIFF_COUNT_UP_RE = re.compile(r"(\(\+\d+\))")
_DIFF_COUNT_DOWN_RE = re.compile(r"(\(-\d+\))")
# The separator is a space in prose and an equals sign in the key=value diagnostic fields. A gamertag may contain
# spaces, which cannot be told from the rest of the sentence, so only the space-free form is coloured inside prose.
# Only these exact phrases introduce a gamertag: a bare "user" also begins "user was" and "user with" and the
# alternation matches at the earliest position rather than on the longest phrase, so it would colour the next word
_USER_TAG_RE = re.compile(r"((?:Xbox gamer tag|Xbox user|for user|of user|gamertag):?|user:)([\t ]+|=)((?!ID\b)[\w.#-]+)")

# A quoted value right after "user" is the monitored gamertag, the same value the "Gamertag:" row reports
_QUOTED_USER_CONTEXT_RE = re.compile(r"\buser\s+$", re.IGNORECASE)
_DURATION_RE = re.compile(r"~?\b[0-9]{1,20}[ \t]{1,20}(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b", re.IGNORECASE)
_LONG_DATE_RE = re.compile(r"\b(?:\w{3}\s+)?\d{1,2}\s+\w{3}(?:\s+\d{2,4})?[\s,]*\d{2}:\d{2}(:\d{2})?(\s*[AP]M)?\b", re.IGNORECASE)
_TIME_ONLY_RE = re.compile(r"(?<![\w:])(~?(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[AP]M)?)(?![\w:])", re.IGNORECASE)
_SHORT_RANGE_DATE_RE = re.compile(r"\(\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\)", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(r"\b\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\b", re.IGNORECASE)
_HOUR_RANGE_RE = re.compile(r"\b\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\b", re.IGNORECASE)
_URL_RE = re.compile(r"(https?://[^\s\]]+)")
_BOOLEAN_TRUE_RE = re.compile(r"\bTrue\b|\bEnabled\b")
_BOOLEAN_FALSE_RE = re.compile(r"\bFalse\b|\bDisabled\b")
# The TLS row reports a word rather than a boolean, and its off state is the one setting that weakens
# a security property, so the state word is coloured like a boolean
_TLS_STATE_RE = re.compile(r"^(\* TLS verification:\s+)(On|Off)(.*)$")
_NOTIFICATION_SUMMARY_STATE_RE = re.compile(r"^(\* Notifications \((?:email|webhook)\):\s+)(On|Off)(.*)$")
# Words that report a problem. The same word used as a key in a 'key=value' diagnostic detail names a setting
# such as 'timeout=15' or a counter such as 'failures=3', so it leaves its line unpainted
_ERROR_KEYWORD_RE = re.compile(r"\b(?:failures?|failed|forbidden|timeout)\b(?!\s*=)")
# A debug trace line records what the tool tried, including attempts that fail and are then handled, so it keeps
# its own colours instead of being painted as the failure it reports
_DEBUG_LINE_RE = re.compile(r"^\[debug \d{2}:\d{2}:\d{2}\]")
# Doctor status markers, coloured with the same theme parts the reference tools use for them
_DOCTOR_MARK_RE = re.compile(r"^\[(PASS|WARN|FAIL|SKIP)\]")
_DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}
# Quoted names such as game titles. At least one word character is required so a run of ASCII art between two
# apostrophes is not read as a name. The closing quote has to be followed by whitespace, punctuation or the end
# of the line, so a title's own apostrophe does not end the name early: "Tom Clancy's Rainbow Six Siege"
_QUOTED_CONTENT_RE = re.compile(r"(')([^\n]*?\w[^\n]*?)(')(?=[\s.,;:!?)\]]|$)")

# Quoted values shaped like a file name or a filesystem path stay plain, since a log or state destination is
# not content. Game titles routinely contain slashes and dots, so only these two shapes are excluded
_QUOTED_FILE_LIKE_RE = re.compile(r"^[~.]?[\\/]|^[A-Za-z]:[\\/]|\.[A-Za-z0-9]{1,8}$")

# A quoted '<name>' inside a printed command is the placeholder the reader has to replace, not a game title
_QUOTED_PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")

# A quoted command-line option is part of an instruction rather than a name
_QUOTED_OPTION_RE = re.compile(r"^-")

# A quoted piece of a URL, such as the '?code=' or '&state=' a prompt points at. Only a leading '?' or '&' counts,
# so a title may end in a question mark and a title such as 'Ratchet & Clank' is still a name
_QUOTED_URL_PART_RE = re.compile(r"^[?&]|://")
_ONLINE_WORD_RE = re.compile(r"\b(ONLINE)\b")
_AWAY_WORD_RE = re.compile(r"\b(AWAY)\b")
_OFFLINE_WORD_RE = re.compile(r"\b(OFFLINE)\b")
# The verbs the monitoring loop uses to report an activity change, coloured like the state they move to
_GAME_STARTED_RE = re.compile(r"\bstarted playing\b")
_GAME_STOPPED_RE = re.compile(r"\bstopped playing\b")
_STATUS_CHANGE_RE = re.compile(r"\b(?:changed status|changed game)\b")

# The opening word of a warning and the name of a reported signal, marked instead of painting the line
_WARNING_LABEL_RE = re.compile(r"^\s*\*+\s*(Warning:|Caution:)")
_SIGNAL_NAME_RE = re.compile(r"(?<=^\* Signal )(\w+)(?= received$)")


# Builds an ANSI escape sequence from a style description string
def _build_ansi_sequence(style_str):
    if not isinstance(style_str, str) or not style_str:
        return ""
    parts = re.split(r"[+ ]+", str(style_str).strip().lower())
    codes = [_STYLE_CODES[part] for part in parts if part in _STYLE_CODES]
    return f"\033[{';'.join(codes)}m" if codes else ""


# Detects whether the given output stream likely supports ANSI colours
def _stream_supports_color(stream):
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.getenv("NO_COLOR"):
        return False
    # On Windows with colorama, skip the TERM check since colorama handles the ANSI translation itself
    if not (colorama_init and platform.system() == "Windows"):
        if os.getenv("TERM", "").lower() in ("", "dumb", "unknown"):
            return False
    # A piped stdin usually means the output is being captured, so escape codes would end up in a file
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        return False
    return True


# Initializes colour handling from the configuration and the terminal's capabilities
def init_color_output(stream):
    global COLOR_ENABLED, _COLOR_STYLES

    # Windows needs colorama started before the support check, since it is what enables ANSI there
    if colorama_init and platform.system() == "Windows":
        try:
            colorama_init(autoreset=False)
        except Exception as exc:
            debug_print("Colorama initialisation", outcome="failed", error=f"{type(exc).__name__}: {exc}")

    COLOR_ENABLED = bool(globals().get("COLORED_OUTPUT", False)) and _stream_supports_color(stream)
    if not COLOR_ENABLED:
        _COLOR_STYLES = {}
        return

    user_theme = globals().get("COLOR_THEME") if isinstance(globals().get("COLOR_THEME"), dict) else {}
    theme = {**DEFAULT_COLOR_THEME, **(user_theme or {})}

    # A config written against an older key name still wins over the default, unless it also sets the current name
    for legacy_name, current_name in _THEME_KEY_ALIASES.items():
        if user_theme and legacy_name in user_theme and current_name not in user_theme:
            theme[current_name] = user_theme[legacy_name]

    _COLOR_STYLES = {name: sequence for name, style in theme.items() if (sequence := _build_ansi_sequence(style))}


# Applies a configured colour style, named by logical part, to the given text
def colorize(part, text):
    if not COLOR_ENABLED:
        return text
    start = _COLOR_STYLES.get(part)
    return f"{start}{text}{ANSI_RESET}" if start else text


# Returns the coloured representation of one Xbox presence status word
def colorize_status(status_text):
    status = (status_text or "").strip().lower()
    if status in ("online", "active", "available", "yes"):
        key = "status_active"
    elif status == "away":
        key = "status_away"
    elif status in ("inactive", "no"):
        key = "status_inactive"
    elif status == "offline":
        key = "status_offline"
    else:
        key = "status_other"
    return colorize(key, status_text)


# Splits a recognized output label from its value without applying a backtracking expression
def _split_output_label(value, labels):
    body = value.rstrip("\n")
    cursor = len(body) - len(body.lstrip())
    if body[cursor:cursor + 1] == "*":
        cursor += 1
        cursor += len(body[cursor:]) - len(body[cursor:].lstrip())
    for label in labels:
        if not body.startswith(label, cursor):
            continue
        value_start = cursor + len(label)
        value_start += len(body[value_start:]) - len(body[value_start:].lstrip())
        if value_start == cursor + len(label):
            return None
        return body[:value_start], body[value_start:]
    return None


# Applies a block style while preserving the highlights already inside the line
def _apply_style_nested(line, style_name):
    start_style = _COLOR_STYLES.get(style_name)
    if not start_style:
        return line
    # Every internal reset returns to the block style instead of to plain, so one span cannot cancel the block
    line = f"{start_style}{line}{ANSI_RESET}"
    line = line.replace(ANSI_RESET, f"{ANSI_RESET}{start_style}")
    if line.endswith(f"{ANSI_RESET}{start_style}"):
        line = line[:-len(start_style)]
    return line


# Applies one substitution only to the parts of a line that are not already inside a colour span, so a later
# rule cannot reclaim text an earlier rule has already coloured
def _sub_outside_color(pattern, replacement, line):
    if ANSI_RESET not in line:
        return pattern.sub(replacement, line)
    parts = []
    position = 0
    inside = False
    for match in SGR_SEQUENCE_RE.finditer(line):
        segment = line[position:match.start()]
        parts.append(segment if inside else pattern.sub(replacement, segment))
        parts.append(match.group(0))
        inside = match.group(0) != ANSI_RESET
        position = match.end()
    trailing = line[position:]
    parts.append(trailing if inside else pattern.sub(replacement, trailing))
    return "".join(parts)


# Colours one quoted name unless the quoted value is shaped like a file name or a path
def _colorize_quoted_name(match, style_name):
    name = match.group(2)
    if _QUOTED_FILE_LIKE_RE.search(name) or _QUOTED_PLACEHOLDER_RE.match(name) or _QUOTED_OPTION_RE.match(name) or _QUOTED_URL_PART_RE.search(name):
        return match.group(0)
    # What sits right before the quote decides the colour, so a quoted gamertag is not read as a game title
    if _QUOTED_USER_CONTEXT_RE.search(match.string[:match.start()]):
        style_name = "username"
    return f"{match.group(1)}{colorize(style_name, name)}{match.group(3)}"


# Colors a count transition using decimal text comparison without unbounded integer conversion
def _colorize_count_change(match):
    before, after = ("".join(str(int(digit)) for digit in match.group(index)).lstrip("0") or "0" for index in (2, 4))
    style = "count_up" if (len(after), after) >= (len(before), before) else "count_down"
    return f"{match.group(1)}{colorize(style, match.group(2))}{match.group(3)}{colorize(style, match.group(4))}"


# Applies the colour rules to a single output line
def _colorize_line(line):
    lowered = line.lower()

    # The notification summary row carries its own On/Off state word
    notification_match = _NOTIFICATION_SUMMARY_STATE_RE.match(line)
    if notification_match:
        prefix, state, suffix = notification_match.groups()
        return f"{prefix}{colorize('boolean_true' if state == 'On' else 'boolean_false', state)}{suffix}"

    # The TLS row reports its state as a word rather than as a boolean
    tls_match = _TLS_STATE_RE.match(line)
    if tls_match:
        prefix, state, suffix = tls_match.groups()
        return f"{prefix}{colorize('boolean_true' if state == 'On' else 'boolean_false', state)}{suffix}"

    # Doctor status markers keep the rest of their line plain so long labels stay readable
    doctor_match = _DOCTOR_MARK_RE.match(line)
    if doctor_match:
        return colorize(_DOCTOR_MARK_STYLES[doctor_match.group(1)], doctor_match.group(0)) + line[doctor_match.end():]

    # Timestamp lines get a dimmed label and a coloured value
    labeled_value = _split_output_label(line, ("Timestamp:", "Liveness check, timestamp:"))
    if labeled_value:
        label, rest = labeled_value
        return f"{colorize('timestamp_label', label)}{colorize('timestamp_value', rest)}" + ("\n" if line.endswith("\n") else "")

    # Any '<something> URL:' row is a link, checked before the label table so 'Profile URL:' is not read as a name
    if _split_output_label(line, ("URL:",)) or " URL:" in line:
        return _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Status rows report the monitored player's presence
    labeled_value = _split_output_label(line, ("STATUS:", "Status:"))
    if labeled_value:
        label, status = labeled_value
        return f"{label}{colorize_status(status)}" + ("\n" if line.endswith("\n") else "")

    # Labelled Xbox metadata rows keep their label plain and colour only the value
    for labels, style_name in _LABEL_STYLES:
        labeled_value = _split_output_label(line, labels)
        if not labeled_value:
            continue
        label, rest = labeled_value
        return f"{label}{colorize(style_name, rest)}" + ("\n" if line.endswith("\n") else "")

    # Highlight the gamertag named inside a sentence
    line = _sub_outside_color(_USER_TAG_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('username', mo.group(3))}", line)

    # Highlight counters and their differences
    line = _sub_outside_color(_FROM_TO_COUNT_RE, _colorize_count_change, line)
    line = _sub_outside_color(_DIFF_COUNT_UP_RE, lambda mo: colorize("count_up", mo.group(0)), line)
    line = _sub_outside_color(_DIFF_COUNT_DOWN_RE, lambda mo: colorize("count_down", mo.group(0)), line)

    # Highlight durations
    line = _sub_outside_color(_DURATION_RE, lambda mo: colorize("duration", mo.group(0)), line)

    # Highlight date ranges before single dates so a range is not split into two dates
    line = _sub_outside_color(_SHORT_RANGE_DATE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_DATE_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_HOUR_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_LONG_DATE_RE, lambda mo: colorize("date", mo.group(0)), line)
    line = _sub_outside_color(_TIME_ONLY_RE, lambda mo: colorize("date", mo.group(0)), line)

    # Highlight URLs and links
    line = _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Highlight quoted names. A line that is only a quoted string is a free-form description, so it stays plain
    if not line.lstrip().startswith("'"):
        line = _sub_outside_color(_QUOTED_CONTENT_RE, lambda mo: _colorize_quoted_name(mo, "game"), line)

    # Highlight boolean values
    line = _sub_outside_color(_BOOLEAN_TRUE_RE, lambda mo: colorize("boolean_true", mo.group(0)), line)
    line = _sub_outside_color(_BOOLEAN_FALSE_RE, lambda mo: colorize("boolean_false", mo.group(0)), line)

    # Highlight the presence keywords and the verbs that report an activity change
    line = _sub_outside_color(_ONLINE_WORD_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_AWAY_WORD_RE, lambda mo: colorize("status_away", mo.group(0)), line)
    line = _sub_outside_color(_OFFLINE_WORD_RE, lambda mo: colorize("status_offline", mo.group(0)), line)
    line = _sub_outside_color(_GAME_STARTED_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_GAME_STOPPED_RE, lambda mo: colorize("status_inactive", mo.group(0)), line)
    line = _sub_outside_color(_STATUS_CHANGE_RE, lambda mo: colorize("status_change", mo.group(0)), line)

    # Mark the opening word of a warning and the name of a reported signal, rather than painting the whole line
    line = _sub_outside_color(_WARNING_LABEL_RE, lambda mo: mo.group(0)[:mo.start(1) - mo.start(0)] + colorize("warning", mo.group(1)), line)
    line = _sub_outside_color(_SIGNAL_NAME_RE, lambda mo: colorize("signal", mo.group(0)), line)

    # Block highlighting, applied last so the colours added above survive through the nesting logic
    is_debug_line = bool(_DEBUG_LINE_RE.match(lowered))
    is_error = not is_debug_line and (bool(_ERROR_KEYWORD_RE.search(lowered)) or "critical:" in lowered or "* error" in lowered)

    if lowered.startswith("to fix:"):
        line = _apply_style_nested(line, "info")
    elif is_error:
        line = _apply_style_nested(line, "error")
    elif "sending email" in lowered:
        line = _apply_style_nested(line, "email")
    elif "sending webhook" in lowered:
        line = _apply_style_nested(line, "webhook")

    return line


# Applies colourisation to multi-line text, preserving the line breaks
def apply_color_to_text(text):
    if not COLOR_ENABLED or not isinstance(text, str):
        return text
    parts = []
    for chunk in text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            stripped = chunk.rstrip("\r\n")
            parts.append(_colorize_line(stripped) + chunk[len(stripped):])
        else:
            parts.append(_colorize_line(chunk))
    return "".join(parts)


# Colours every link in a line, for the screens printed before the output stream colouriser is installed
def colorize_links(text):
    return _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), text)


# Colours one line of a fix block the way the output stream colours it, keeping its guide line a link
def colorize_fix_line(line):
    return colorize_links(line) if line.lstrip().startswith("Guide: ") else colorize("info", line)


# Cuts every line to the configured display width, measuring what the terminal shows rather than the byte count
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        # Without wcwidth every character costs one column, so truncation still applies and only wide characters are measured short
        wcwidth = len
    truncated_lines = []
    for line in message.split("\n"):
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = []
        position = 0
        style_open = False
        while position < len(expanded_line):
            # A colour sequence is copied through free of charge, so styling never eats into the visible width
            escape = SGR_SEQUENCE_RE.match(expanded_line, position)
            if escape:
                truncated.append(escape.group(0))
                style_open = escape.group(0) not in ("\x1b[0m", "\x1b[m")
                position = escape.end()
                continue
            char_width = wcwidth(expanded_line[position])
            if char_width is None or char_width < 0:
                char_width = 0
            if current_width + char_width > truncate_width:
                # The cut may have dropped the reset, which would leave the colour running into every later line
                if style_open:
                    truncated.append(ANSI_RESET)
                break
            truncated.append(expanded_line[position])
            current_width += char_width
            position += 1
        truncated_lines.append("".join(truncated))
    return "\n".join(truncated_lines)


# Resolves the configured and command-line truncation settings, expanding the terminal-width sentinel
def resolve_truncate_chars(cli_value, configured_value, logging_disabled):
    truncate_chars = configured_value if cli_value is None else cli_value
    if truncate_chars:
        try:
            import wcwidth  # noqa: F401
        except ImportError:
            # Truncation still applies without the library, so the run is warned rather than left printing full lines
            print_recovery_advice(missing_dependency_advice("wcwidth", "Screen truncation measures every character as one column"), label="Warning")
            print()
    if logging_disabled:
        return 0
    if truncate_chars == 999:
        terminal_size = shutil.get_terminal_size()
        print(f"The detected terminal screen width is: {terminal_size.columns} characters\n")
        return terminal_size.columns
    return truncate_chars


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        # The early sanitizing stream is unwrapped so sanitizing and colouring happen exactly once. Writing
        # through it would colourise every line twice and the second pass no longer sees the label it
        # already coloured, so it would recolour the value with the generic rules
        self.terminal = unwrap_terminal_stream(sys.stdout)
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        global STDOUT_AT_START_OF_LINE
        if message:
            STDOUT_AT_START_OF_LINE = message.endswith('\n')
        message = sanitize_terminal_text(message)
        # Expand tabs for file output and drop every escape, so the log file stays plain text
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", message).expandtabs(8)))
        # Truncated before colouring, so escape sequences never count toward the displayed width
        message = self._truncate_terminal(message)
        self.terminal.write(apply_color_to_text(message))
        self.terminal.flush()
        self.logfile.flush()

    # Writes text the log file should keep but the terminal has already shown or does not need
    def log_only(self, message):
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", sanitize_terminal_text(message)).expandtabs(8)))
        self.logfile.flush()

    # Writes text meant for the reader at the terminal, which the log file has its own version of
    def terminal_only(self, message):
        global STDOUT_AT_START_OF_LINE
        if message:
            STDOUT_AT_START_OF_LINE = message.endswith('\n')
        message = sanitize_terminal_text(message)
        message = self._truncate_terminal(message)
        self.terminal.write(apply_color_to_text(message))
        self.terminal.flush()

    def flush(self):
        pass

    # Limits the terminal line across separate writes while leaving the log complete
    def _truncate_terminal(self, message):
        # The limit is fixed once at startup, so with truncation off there is no column to keep track of
        if not TRUNCATE_CHARS:
            return message
        try:
            from wcwidth import wcwidth
        except ImportError:
            wcwidth = len
        column = getattr(self, "_terminal_column", 0)
        clipped = getattr(self, "_terminal_clipped", False)
        output = []
        position = 0
        while position < len(message):
            escape = ANSI_ESCAPE_RE.match(message, position)
            if escape:
                output.append(escape.group(0))
                position = escape.end()
                continue
            char = message[position]
            position += 1
            if char in ("\n", "\r"):
                output.append(char)
                column, clipped = 0, False
                continue
            width = 8 - column % 8 if char == "\t" else max(0, wcwidth(char))
            if char == "\t" and TRUNCATE_CHARS:
                width = min(width, max(0, TRUNCATE_CHARS - column))
            if TRUNCATE_CHARS and (clipped or column + width > TRUNCATE_CHARS):
                clipped = True
                continue
            output.append(" " * width if char == "\t" and TRUNCATE_CHARS else char)
            column += width
        self._terminal_column, self._terminal_clipped = column, clipped
        return "".join(output)


# Sanitizing and colouring stdout wrapper, used before the logging policy has been resolved
class TerminalStream(object):
    # Stores the wrapped terminal stream
    def __init__(self, stream):
        self.terminal = stream

    # Writes one sanitized and coloured message to the wrapped terminal
    def write(self, message):
        global STDOUT_AT_START_OF_LINE
        if message:
            STDOUT_AT_START_OF_LINE = message.endswith('\n')
        message = sanitize_terminal_text(message)
        if TRUNCATE_CHARS:
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(apply_color_to_text(message))
        self.terminal.flush()

    # Writes one message to the terminal while matching the Logger interface
    def terminal_only(self, message):
        self.write(message)

    # Discards log-only output while file logging is not set up
    def log_only(self, message):
        return

    # Flushes the wrapped terminal
    def flush(self):
        self.terminal.flush()

    # Forwards the remaining stream attributes to the wrapped terminal
    def __getattr__(self, name):
        return getattr(self.terminal, name)


# Help screen parts. argparse measures its column layout on the plain text, so the palette is applied to the
# finished help screen rather than to the pieces argparse assembles and the layout stays identical
_HELP_USAGE_LABEL = "usage:"
_HELP_HEADING_RE = re.compile(r"^\S.*:$")
_HELP_OPTION_ROW_RE = re.compile(r"^( {2,})(-{1,2}[^\s,]+(?:, *--?[^\s,]+)*)(.*)$")
_HELP_POSITIONAL_ROW_RE = re.compile(r"^( {2,})([A-Z][A-Z0-9_]*)( {2,}.*)$")
_HELP_COLUMN_GAP_RE = re.compile(r" {2,}")
# A value placeholder is an upper-case metavar, a choice list or an angle-bracket name, including a
# colon-joined pair of them
_HELP_METAVAR_RE = re.compile(r"\{[^}]*\}|<[^>]+>|\b[A-Z][A-Z0-9_]*(?::[A-Z][A-Z0-9_]*)*\b")
_HELP_OPTION_RE = re.compile(r"(?<![\w-])(--?[A-Za-z][\w-]*)")
_HELP_PLACEHOLDER_RE = re.compile(r"<[^>]+>")
_HELP_DEFAULT_RE = re.compile(r"\(default:[^)]*\)")


# Colours the links and the default notes inside one line of help prose
def _colorize_help_prose(line):
    line = _URL_RE.sub(lambda match: colorize("link", match.group(1)), line)
    return _HELP_DEFAULT_RE.sub(lambda match: colorize("help_default", match.group(0)), line)


# Colours the option names and the value placeholders of one usage line or option column
def _colorize_help_signature(text):
    text = _HELP_METAVAR_RE.sub(lambda match: colorize("help_metavar", match.group(0)), text)
    return _sub_outside_color(_HELP_OPTION_RE, lambda match: colorize("help_option", match.group(1)), text)


# Colours the usage block, the group headings and the option rows of the help screen
def _colorize_help_body(text):
    lines = []
    in_usage = False
    for line in text.split("\n"):
        if line.startswith(_HELP_USAGE_LABEL):
            in_usage = True
            lines.append(colorize("help_usage", _HELP_USAGE_LABEL) + _colorize_help_signature(line[len(_HELP_USAGE_LABEL):]))
            continue
        if in_usage:
            if line.strip():
                lines.append(_colorize_help_signature(line))
                continue
            in_usage = False
        if _HELP_HEADING_RE.match(line):
            lines.append(colorize("help_heading", line))
            continue
        option_row = _HELP_OPTION_ROW_RE.match(line)
        if option_row:
            indent, names, remainder = option_row.groups()
            gap = _HELP_COLUMN_GAP_RE.search(remainder)
            metavars, description = (remainder[:gap.start()], remainder[gap.start():]) if gap else (remainder, "")
            lines.append(indent + _colorize_help_signature(names + metavars) + _colorize_help_prose(description))
            continue
        positional_row = _HELP_POSITIONAL_ROW_RE.match(line)
        if positional_row:
            indent, name, description = positional_row.groups()
            lines.append(indent + colorize("help_metavar", name) + _colorize_help_prose(description))
            continue
        lines.append(_colorize_help_prose(line))
    return "\n".join(lines)


# Colours the examples of the help epilog: the task headings, the comments and the commands to run
def _colorize_help_epilog(text):
    lines = []
    for line in text.split("\n"):
        if _HELP_HEADING_RE.match(line):
            lines.append(colorize("help_heading", line))
            continue
        if not line.strip() or not line.startswith(" "):
            lines.append(_colorize_help_prose(line))
            continue
        if line.lstrip().startswith("#"):
            comment = _apply_style_nested(_colorize_help_prose(line), "help_comment")
            lines.append(comment)
            continue
        placeholders = _HELP_PLACEHOLDER_RE.sub(lambda match: colorize("help_placeholder", match.group(0)), line)
        command = _apply_style_nested(placeholders, "help_command")
        lines.append(command)
    return "\n".join(lines)


# Colours one finished help screen, leaving its column layout untouched
def colorize_help_text(text, epilog=None):
    if not COLOR_ENABLED or not isinstance(text, str) or not text:
        return text
    examples = (epilog or "").strip("\n")
    start = text.rfind(examples) if examples else -1
    if start == -1:
        return _colorize_help_body(text)
    return _colorize_help_body(text[:start]) + _colorize_help_epilog(text[start:])


# Parser that colours its own help screen and writes it past the output colouriser, which would otherwise
# repaint the finished help with the rules meant for monitoring output
class ColoredHelpParser(argparse.ArgumentParser):
    # Returns the help screen with the help palette already applied
    def format_help(self) -> str:
        return colorize_help_text(super().format_help(), self.epilog)

    # Writes one parser message straight to the terminal behind any colouring wrapper
    def _print_message(self, message, file=None) -> None:
        if not message:
            return
        stream = sys.stderr if file is None else file
        target = unwrap_terminal_stream(stream)
        target.write(sanitize_terminal_text(message))
        flush = getattr(target, "flush", None)
        if callable(flush):
            flush()


# Returns the underlying terminal behind any number of sanitizing stream wrappers
def unwrap_terminal_stream(stream):
    while isinstance(stream, TerminalStream):
        stream = stream.terminal
    return stream


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=None, timeout=None):
    check_url = CHECK_INTERNET_URL if url is None else url
    check_timeout = CHECK_INTERNET_TIMEOUT if timeout is None else timeout
    try:
        with httpx.Client(verify=tls_context(), timeout=check_timeout) as client:
            client.get(check_url)
    except Exception as e:
        debug_print("Connectivity check", url=check_url, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="connectivity", detail=f"The connectivity endpoint {check_url} could not be reached: {e}")
        return False
    debug_print("Connectivity check", url=check_url, outcome="OK")
    return True


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    # Don't clear screen if stdout is redirected (not a TTY)
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception as e:
        debug_print("Terminal screen clear", outcome="failed", error=f"{type(e).__name__}: {e}")
        print("* Cannot clear the screen contents")


# Returns whether this process was started from the packaged entry point or from a downloaded script
def detect_install_method():
    return "manual" if os.path.basename(sys.argv[0] or "").endswith(".py") else "pip"


# Returns a readable name for one install method
def install_method_display_name(method=None):
    return {"pip": "PyPI install", "manual": "downloaded script"}.get(method or detect_install_method(), "unknown install")


# The documentation placeholders a printed command carries unquoted, because the reader replaces them before running it
COMMAND_PLACEHOLDERS = frozenset(("<xbox_gamertag>", "<client_id>", "<client_secret>", "<new-file>"))


# Returns one command argument quoted for the shell of the host operating system
def quote_command_argument(argument):
    text = str(argument)
    # Matched exactly rather than by shape, since any other angle-bracket value is user-derived and would otherwise reach the shell unquoted
    if text in COMMAND_PLACEHOLDERS:
        return text
    return subprocess.list2cmdline([text]) if platform.system() == "Windows" else shlex.quote(text)


# Returns the command that starts this tool on the detected install, as the argument parts before any option
def install_command_prefix(method=None):
    executable = "python" if platform.system() == "Windows" else "python3"
    if (method or detect_install_method()) == "manual":
        return [executable, "xbox_monitor.py"]
    return ["xbox_monitor"]


# True when a command writes the dotenv file itself, so it refuses an --env-file that switches dotenv loading off
def command_writes_dotenv(arguments=()):
    return any(str(argument) == "--setup" or str(argument).startswith("--set-") for argument in arguments)


# True when a command writes the config file itself, so it refuses a --config-file that switches discovery off
def command_writes_config(arguments=()):
    return any(str(argument) == "--setup" for argument in arguments)


# Returns the --config-file and --env-file arguments this run was given, skipping any the caller already passed
def active_path_arguments(arguments=()):
    given = {str(argument) for argument in arguments}
    paths = []
    active_config = CLI_CONFIG_PATH or ("none" if CONFIG_DISCOVERY_DISABLED else None)
    # The "none" sentinel is carried so the printed command checks the setup this run checked, except into a
    # command that writes the config file, since those refuse the sentinel at their own argument gate
    if active_config and "--config-file" not in given and not (str(active_config).casefold() == "none" and command_writes_config(arguments)):
        paths.extend(("--config-file", str(active_config)))
    # The "none" sentinel is carried so the printed command checks the setup this run checked, except into a
    # command that writes the dotenv file, since those refuse the sentinel at their own argument gate
    if DOTENV_FILE and "--env-file" not in given and not (str(DOTENV_FILE).casefold() == "none" and command_writes_dotenv(arguments)):
        paths.extend(("--env-file", str(DOTENV_FILE)))
    return paths


# Returns a copy-pasteable command line for this tool, carrying the config and dotenv paths this run was given
def render_command(arguments=None, include_paths=True, *, method=None):
    selected = [str(argument) for argument in (arguments or ())]
    parts = [*install_command_prefix(method), *selected, *(active_path_arguments(selected) if include_paths else ())]
    return " ".join(quote_command_argument(part) for part in parts)


# Reads one answer with Python's default Ctrl+C behavior, so the prompt reports the outcome instead of the signal handler
def read_interactively(reader, *args, **kwargs):
    try:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except (ValueError, OSError):
        # Handlers can only be replaced from the main thread, which is where every prompt runs
        return reader(*args, **kwargs)
    try:
        return reader(*args, **kwargs)
    finally:
        try:
            signal.signal(signal.SIGINT, previous_handler)
        except (ValueError, OSError):
            pass


# How far ahead of this machine's clock a saved timestamp may be before the tool stops timing against it
STATE_FUTURE_TOLERANCE_SECONDS = 300


# Rejects timestamps that cannot safely reach date conversion
def valid_state_timestamp(value):
    if not finite_number(value) or value < 0:
        return False
    try:
        datetime.fromtimestamp(value)
    except (ValueError, OverflowError, OSError):
        return False
    return True


# Reports whether a saved timestamp is far enough ahead of this machine's clock to be untrustworthy. The tool
# wrote the file itself, so a clock moved backwards is the usual cause and is not a reason to refuse to run
def state_timestamp_ahead(value):
    return finite_number(value) and value > time.time() + STATE_FUTURE_TOLERANCE_SECONDS


# Reads saved history without adopting malformed values
def read_status_record(path):
    with open(path, "r", encoding="utf-8") as source:
        record = json.load(source)
    if not isinstance(record, list) or len(record) < 2:
        raise ValueError("expected a status list containing a timestamp and status text")
    if not isinstance(record[1], str) or not record[1].strip():
        raise ValueError("the saved status must be nonempty text")
    if not valid_state_timestamp(record[0]):
        raise ValueError("the saved timestamp must be finite, nonnegative and representable")
    return record


# Replaces a saved timestamp this machine's clock cannot support, so only the timing restarts and the saved
# entry itself is kept. A file this tool wrote must not be able to stop the next run over a corrected clock
def reconcile_status_record(record, path):
    if not record or not state_timestamp_ahead(record[0]):
        return record
    print(f"* Warning: The saved status in '{path}' is dated ahead of this machine's clock.")
    print(f"  Keeping the saved status {str(record[1]).upper()} and timing it from now. Check the system clock if this repeats.")
    return [int(time.time()), *record[1:]]


# Accepts finite numeric values without overflowing on unusually large integers
def finite_number(value):
    import math
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


# Preserves inline credentials privately before setup replaces their only saved source
def preserve_inline_config_secrets(config_path, env_path):
    from dotenv import dotenv_values
    source = Path(config_path).expanduser()
    if not source.is_file():
        return None
    original = {}
    if not load_config_file(source, namespace=original, report_errors=False):
        raise ValueError("Existing configuration could not be read before preserving its inline secrets")
    defaults = _config_template_defaults()
    destination = Path(env_path).expanduser()
    saved = dotenv_values(str(destination), interpolate=False) if destination.exists() else {}
    updates = {}
    for key in SECRET_KEYS:
        value = original.get(key)
        if isinstance(value, str) and value and value != defaults.get(key) and saved.get(key) is None:
            updates[key] = value
    if not updates:
        return None
    try:
        return update_dotenv_file(destination, updates)
    except Exception as exc:
        raise OSError(f"Could not preserve inline secrets in '{destination}'. The original configuration was not replaced") from exc


# Removes inline secret assignments from a setup backup while preserving other configuration text
def redact_config_backup(content):
    import ast
    try:
        text = content.decode("utf-8")
        tree = ast.parse(text)
    except (UnicodeError, SyntaxError) as exc:
        raise ValueError("Cannot create a secret-free configuration backup. Correct the existing file's UTF-8 encoding or assignment syntax before running setup") from exc
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    replacements = []
    secret_values = set()
    for statement in ast.walk(tree):
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        if any(isinstance(target, ast.Name) and target.id in SECRET_KEYS for target in targets):
            value = statement.value
            if value is not None and value.end_lineno is not None and value.end_col_offset is not None:
                start = offsets[value.lineno - 1] + value.col_offset
                end = offsets[value.end_lineno - 1] + value.end_col_offset
                replacements.append((start, end))
                if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
                    secret_values.add(value.value)
    for start, end in sorted(replacements, reverse=True):
        content = content[:start] + b'""' + content[end:]
    import io
    import tokenize
    text = content.decode("utf-8")
    lines = text.splitlines(keepends=True)
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            comment = token.string
            for secret in sorted(secret_values, key=len, reverse=True):
                comment = comment.replace(secret, "<redacted>")
            row, start = token.start
            end = token.end[1]
            lines[row - 1] = lines[row - 1][:start] + comment + lines[row - 1][end:]
    return "".join(lines).encode("utf-8")


# Copies an existing file to a timestamped private backup before it is replaced, returning the backup path or None
def create_timestamped_backup(destination, attempts=100, redact_secrets=False):
    destination_path = Path(destination).expanduser()
    if not destination_path.is_file():
        return None
    existing_bytes = destination_path.read_bytes()
    if redact_secrets:
        existing_bytes = redact_config_backup(existing_bytes)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    for attempt in range(attempts):
        suffix = f".{stamp}.bak" if attempt == 0 else f".{stamp}-{attempt}.bak"
        backup_path = destination_path.with_name(destination_path.name + suffix)
        try:
            # O_EXCL so a backup can never overwrite an earlier one, even under a concurrent run
            descriptor = os.open(str(backup_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as backup_file:
                backup_file.write(existing_bytes)
                backup_file.flush()
                os.fsync(backup_file.fileno())
        except Exception as backup_error:
            debug_print("Backup write", path=str(backup_path), outcome="failed", error=f"{type(backup_error).__name__}: {backup_error}")
            try:
                os.unlink(str(backup_path))
            except OSError:
                pass
            raise
        return str(backup_path)
    raise OSError(f"Could not create a unique backup for '{destination_path}' after {attempts} attempts")


# Writes one file through a temporary file in the same directory, so a crash cannot leave a half-written file
def write_file_atomically(destination, content, mode=None):
    destination_path = Path(destination).expanduser()
    if destination_path.parent != Path(""):
        destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if mode is not None and os.name == "posix":
            os.chmod(str(temporary_path), mode)
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
        debug_print("Atomic file write", path=str(destination_path), outcome="OK", bytes=len(content.encode("utf-8")), mode=oct(mode) if mode is not None else None)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return str(destination_path)


# Raised when an existing config is not replaced because nobody could confirm it, as opposed to a path in the way of writing one
class ConfigExistsError(FileExistsError):
    pass


# Confirms replacing one existing generated config or requires --force when there is nobody to ask
def confirm_generated_config_replacement(destination, force=False, interactive=None, input_func=input):
    destination_path = Path(destination).expanduser()
    if not destination_path.exists() or force:
        return True
    terminal_is_interactive = bool(sys.stdin.isatty()) if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise ConfigExistsError(f"Config file '{destination_path}' already exists and there is no terminal to confirm replacing it")
    try:
        answer = str(read_interactively(input_func, f"Config file '{destination_path}' exists. Replace it and keep a timestamped backup? [y/N]: ")).strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = ""
    return answer in {"y", "yes"}


# Writes one generated config atomically, backing up whatever was there first
def write_generated_config(output_file, content, force=False, interactive=None, input_func=input, redact_secrets=False):
    destination = Path(os.path.expanduser(str(output_file)))
    if not confirm_generated_config_replacement(destination, force, interactive, input_func):
        return None, False
    backup_path = create_timestamped_backup(destination, redact_secrets=redact_secrets)
    write_file_atomically(destination, content)
    return backup_path, True


# Returns a value fit to show as a prompt default, hiding the shipped placeholders
def _wizard_default(value):
    text = str(value or "")
    return text if text and not text.startswith("your_") else ""


# Prints the shared line telling the user how defaults and cancelling work
def _wizard_print_default_guidance():
    print("Press Enter to accept the shown default. Ctrl+C cancels.\n")


# Reads one setup line. Cancelling propagates to the one handler in run_setup_wizard, which reports
# that nothing was written
def _wizard_input(prompt_text, input_func=None):
    prompt = input if input_func is None else input_func
    try:
        return read_interactively(prompt, colorize("info", prompt_text))
    except (EOFError, KeyboardInterrupt):
        # The interrupted prompt owns the line break, so every handler prints its message alone
        print()
        raise


# Asks one free-text question, returning the shown default when the answer is empty
def _wizard_ask_text(question, default="", required=False, input_func=None):
    suffix = f" [{default}]" if default else ""
    while True:
        answer = _wizard_input(f"{question}{suffix}: ", input_func=input_func).strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print("  This value is required.")
        if not _wizard_offer_retry(question, input_func=input_func):
            return ""


# Asks one yes or no question with a visible default
def _wizard_ask_yes_no(question, default=True, input_func=None):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _wizard_input(f"{question} {hint}: ", input_func=input_func).strip().casefold()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers the one way out after an entry the wizard cannot use, so declining keeps every answer already given
def _wizard_offer_retry(label, consequence="", input_func=None):
    if consequence:
        return not _wizard_ask_yes_no(f"Continue without the {label}? {consequence}", default=False, input_func=input_func)
    return _wizard_ask_yes_no(f"Try entering the {label} again?", default=True, input_func=input_func)


# Asks one numbered multiple-choice question and returns the chosen index
def _wizard_ask_choice(question, options, default_index=0, input_func=None):
    print()
    print(question)
    for index, (label, description) in enumerate(options, 1):
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {colorize('username', str(index))}. {label}{colorize('info', marker) if marker else ''}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        answer = _wizard_input(f"Choose [1-{len(options)}]: ", input_func=input_func).strip()
        if not answer:
            return default_index
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Trims the parenthetical hint from a question, so the retry offer that repeats it stays one readable line
def _wizard_retry_label(question):
    return question.split(" (")[0].strip()


# Asks until the answer is a positive whole number or the default is accepted
def _wizard_ask_positive_int(question, default, maximum=None, input_func=None):
    while True:
        answer = _wizard_ask_text(question, default=str(default), required=True, input_func=input_func)
        # An empty answer means the retry offer was declined, so the default stands instead of asking again
        if not answer:
            return int(default)
        try:
            parsed = int(answer)
        except ValueError:
            parsed = 0
        if parsed > 0 and (maximum is None or parsed <= maximum):
            return parsed
        print(f"  Enter a whole number from 1 through {maximum}." if maximum is not None else "  Enter a positive whole number.")
        # A value the helper cannot use is a rejected entry, so it gets the same way out an empty one gets
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {default}.")
            return int(default)


# Renders a duration as raw seconds plus a readable form, so the value that reaches the config stays visible
def _wizard_format_duration(seconds):
    remaining = int(seconds)
    parts = []
    for suffix, count in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, count)
        if value:
            parts.append(f"{value}{suffix}")
    raw = f"{int(seconds)}s"
    readable = " ".join(parts) or raw
    return raw if readable == raw else f"{raw} - {readable}"


# Asks one duration, accepting the formats people actually type
def _wizard_ask_duration(question, default, input_func=None):
    prompt_text = f"{question} [{_wizard_format_duration(default)}]: "
    while True:
        answer = _wizard_input(prompt_text, input_func=input_func).strip()
        if not answer:
            return default
        seconds = parse_duration_input(answer)
        if seconds is not None:
            return seconds
        print("  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.")
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {_wizard_format_duration(default)}.")
            return default


# Asks one secret through a hidden prompt with debug output off, so it never reaches the screen, the shell history or the debug stream
def _wizard_ask_secret(question, getpass_func=None, strip=True):
    try:
        # Colorized like the visible prompts, so a hidden answer does not look like a different question
        return read_secret_privately(colorize("info", f"{question}: "), getpass_func=getpass_func, strip=strip)
    except (EOFError, KeyboardInterrupt):
        print()
        raise


# Renders one setting for the generated config, keeping a mapping readable instead of on one very long line
def render_config_value(value):
    if isinstance(value, dict) and value:
        return "{\n" + "".join(f"    {key!r}: {item!r},\n" for key, item in value.items()) + "}"
    return repr(value)


# Renders an explicit assignment for a setting the template ships commented out, so overrides the user wrote
# survive a rewrite instead of being replaced by the commented default
def _rendered_commented_setting(variable, values):
    value = values.get(variable)
    if not isinstance(value, dict) or not value:
        return []
    lines = ["", f"{variable} = {{"]
    lines.extend(f"    {render_config_value(str(name))}: {render_config_value(str(setting))}," for name, setting in value.items())
    lines.append("}")
    return lines


# Renders one configuration file from the built-in template with the chosen values substituted in
def generate_config_with_current_values(config_values):
    tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    replacements = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        name = statement.targets[0].id
        # A secret belongs in the dotenv file, so its template placeholder stays even when the running values hold the real one
        if name not in config_values or name in SECRET_KEYS:
            continue
        replacements[name] = (statement.lineno, getattr(statement, "end_lineno", statement.lineno), render_config_value(config_values[name]))
    lines = CONFIG_BLOCK.strip("\n").split("\n")
    # The template keeps its own leading blank line, so template line numbers are one ahead of this list
    offset = 1 if CONFIG_BLOCK.startswith("\n") else 0
    commented_pattern = re.compile(r"^#\s*([A-Z][A-Z0-9_]*)\s*=\s*\{$")
    commented_block = ""
    skip_until = 0
    output = []
    for number, line in enumerate(lines, 1):
        template_line = number + offset
        if template_line < skip_until:
            continue
        replaced = next((name for name, (start, _end, _value) in replacements.items() if start == template_line), None)
        if replaced is None:
            output.append(line)
            stripped = line.strip()
            commented_match = commented_pattern.match(stripped)
            if commented_match and commented_match.group(1) in COMMENTED_CONFIG_SETTINGS:
                commented_block = commented_match.group(1)
            elif commented_block and stripped == "# }":
                output.extend(_rendered_commented_setting(commented_block, config_values))
                commented_block = ""
            continue
        start, end, rendered = replacements[replaced]
        output.append(f"{replaced} = {rendered}")
        skip_until = end + 1
    return "\n".join(output) + "\n"


# Matches one dotenv assignment, tolerating the export prefix used when the same file is also sourced by a shell
def match_dotenv_assignment(line, key):
    return re.match(rf"^(\s*(?:export\s+)?){re.escape(key)}\s*=", str(line))


# Renders one quoted dotenv assignment, keeping the export prefix of the line it replaces
def render_dotenv_assignment(key, value, prefix=""):
    # A line break inside a value would split the assignment, so it is escaped rather than written through
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    suffix = ' # monitor:literal' if '${' in str(value) else ''
    return f'{prefix}{key}="{escaped}"{suffix}'


# Reports whether one dotenv file already assigns the requested key
def _dotenv_contains_key(path, key):
    target = Path(path).expanduser()
    if not target.is_file():
        return False
    return any(binding.key == key for binding in _dotenv_bindings(target.read_text(encoding="utf-8")))


# Returns the dotenv parser's own bindings for one file's text, where a quoted value written across several lines is one binding
def _dotenv_bindings(text):
    from io import StringIO
    from dotenv.parser import parse_stream
    return list(parse_stream(StringIO(text)))


# Replaces dotenv assignments in place in one pass, leaving every other line and every comment untouched
def update_dotenv_file(destination, updates):
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    target = Path(destination).expanduser()
    if not target.parent.is_dir():
        raise FileNotFoundError(f"The directory for '{target}' does not exist")
    for key, value in updates.items():
        if key not in SECRET_KEYS:
            raise ValueError(f"Refusing to write an unknown dotenv key: {key}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    output_parts = []
    replaced = set()
    # Rebuilt from the parser's own bindings rather than physical lines, since a quoted value can span several
    # of them and replacing only the first leaves the rest of the old secret behind as broken syntax
    for binding in _dotenv_bindings(existing):
        original = binding.original.string
        blank_prefix = original[:len(original) - len(original.lstrip("\r\n"))]
        if binding.key is None or binding.key not in updates:
            output_parts.append(original)
            continue
        # A secret cleared by its owner is removed rather than emptied, so a disabled value cannot linger here
        if binding.key in replaced or not updates[binding.key]:
            output_parts.append(blank_prefix)
            replaced.add(binding.key)
            continue
        replaced.add(binding.key)
        # An already exported assignment is rewritten in place. Appending a second one would leave the old
        # credential on disk, with only the load order deciding which one wins
        head = original[len(blank_prefix):]
        # Keep key quotes out of the indentation and export prefix
        written_prefix = head[:head.index(binding.key)].rstrip("'")
        output_parts.append(f"{blank_prefix}{render_dotenv_assignment(binding.key, updates[binding.key], written_prefix)}\n")
    content = "".join(output_parts)
    # A file that did not end in a newline would otherwise take the first new assignment onto its last line
    if content and not content.endswith("\n"):
        content += "\n"
    for key, value in updates.items():
        if key not in replaced and value:
            content += f"{render_dotenv_assignment(key, value)}\n"
    # Checked before it replaces the file, so a rewrite can never publish a secret the next run cannot read back
    rewritten = resolve_dotenv_values(content, override=True)
    if any(rewritten.get(key, "") != value for key, value in updates.items()):
        raise ValueError(f"Updating '{target}' would not store the requested values")
    # Written through a temporary file, so an interrupted write cannot leave the file without its secrets.
    # No backup is taken here: a copy of the credential being replaced is the one thing not worth keeping
    write_file_atomically(target, content, mode=0o600)
    for key in updates:
        verbose_print(f"Saved {key} in '{target}'")
    return str(target)


# Returns the dotenv file a one-shot secret command writes to, refusing the disabled setting
def resolve_secret_env_path(env_file, flag):
    selected = env_file if env_file else DOTENV_FILE
    if selected and str(selected).casefold() == "none":
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail=f"{flag} needs a dotenv file to write to, so it cannot be used with 'none'"))
    return Path(os.path.expanduser(str(selected))) if selected else Path.cwd() / ".env"


# Walks up to the first directory that exists, so a destination under a missing folder can still be judged
def nearest_existing_parent(path):
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Checks one setup destination without creating or modifying it, so an unwritable path is caught before any question
def _wizard_validate_destination(path, label):
    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory")
    parent = nearest_existing_parent(destination)
    if not parent.is_dir():
        raise ValueError(f"{label} does not have a usable parent directory")
    if not os.access(str(parent), os.W_OK):
        raise ValueError(f"{label} is not writable through parent '{parent}'")
    return destination


# Loads the selected setup baseline and preserves its dotenv path unless explicitly overridden
def _wizard_seed_destination(state, env_file):
    saved = {}
    if state.config_path.is_file() and not load_config_file(state.config_path, namespace=saved):
        raise ValueError(f"Configuration file '{state.config_path}' could not be read. Correct it before retrying setup.")
    state.baseline_values.update({key: value for key, value in saved.items() if key not in SECRET_KEYS})
    state.config_values.update(state.baseline_values)
    selected = env_file if env_file is not None else saved.get("DOTENV_FILE") or state.env_path
    if str(selected).casefold() == "none":
        raise ValueError("Setup needs a writable dotenv destination. Pass --env-file PATH to choose one.")
    state.env_path = _wizard_validate_destination(selected, "Dotenv destination")
    if state.env_path == state.config_path.resolve():
        raise ValueError("Configuration and dotenv destinations must be different files. Pass --env-file with another path.")
    state.config_values["DOTENV_FILE"] = str(state.env_path)


# Resolves both setup destinations, refusing the disabled settings that leave nowhere to write
def _wizard_destinations(config_file=None, env_file=None):
    if config_file is not None and str(config_file).casefold() == "none":
        raise ValueError("--setup has nowhere to write the configuration")
    if env_file is not None and str(env_file).casefold() == "none":
        raise ValueError("--setup has nowhere to write the secrets")
    config_path = Path(config_file).expanduser() if config_file is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    env_path = Path(env_file).expanduser() if env_file is not None else Path.cwd() / ".env"
    return _wizard_validate_destination(config_path, "Configuration destination"), _wizard_validate_destination(env_path, "Dotenv destination")


# Confirms replacing an existing config before any question is asked, so a long run cannot end in a surprise
def _wizard_choose_config_destination(config_path, input_func=None):
    selected = Path(config_path)
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. A timestamped backup is kept. Rebuild it from your answers, starting from its current settings?", default=False, input_func=input_func):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel", input_func=input_func)
        if not alternative:
            return None
        try:
            selected = _wizard_validate_destination(alternative, "Configuration destination")
        except ValueError as exc:
            print(f"  {exc}.")
    return selected


# Reads saved secrets with the same interpolation rules as normal startup
def _wizard_private_values(env_path):
    if not env_path or not Path(env_path).exists():
        return {}
    return resolve_dotenv_values(Path(env_path).read_text(encoding="utf-8"), override=False)


# Returns genuine environment credentials without treating previously loaded file values as exports
def _wizard_exported_secrets():
    state = globals().get("DOTENV_RELOAD_STATE", {})
    owned = set(globals().get("DOTENV_MANAGED_KEYS", ())) | set(globals().get("DOTENV_BASE_VALUES", ())) | set(state.get("base", ()))
    exported = set(globals().get("EXPORTED_ENVIRONMENT_KEYS", ())) | set(globals().get("EXPORTED_SECRET_KEYS", ())) | set(state.get("exported", ()))
    sources = globals().get("SECRET_SOURCES", {})
    return {key: os.environ[key] for key in SECRET_KEYS if os.environ.get(key) and key not in command_line_secret_keys() and (key in exported or (key not in owned and sources.get(key) not in ("dotenv file", "dotenv file reload")))}


# Returns the secret stored in the dotenv file or None when the file has no assignment for it
def _wizard_saved_secret_value(key, env_path):
    value = _wizard_private_values(env_path).get(key)
    return value if isinstance(value, str) else None


# Returns the effective credential and whether a startup export supplies it
def effective_secret_after_setup(key, env_path, secret_updates):
    if key in command_line_secret_keys():
        return str(globals().get(key) or ""), False
    exported = _wizard_exported_secrets().get(key)
    if exported:
        return exported, True
    if key in secret_updates:
        return str(secret_updates[key] or ""), False
    saved = _wizard_saved_secret_value(key, env_path)
    if saved is not None:
        return saved, False
    # Nothing private holds it, so the configuration file is what a restart would read
    return str(globals().get(key) or ""), False


# Reports whether setup will retain a usable credential from the selected file or pending answers
def _wizard_existing_secret(key, env_path, secret_updates=None):
    value = _wizard_exported_secrets().get(key)
    if value is None:
        value = (secret_updates or {}).get(key)
    if value is None:
        value = read_private_settings(env_path).get(key)
    return secret_is_set(value)


# Queues one secret for the save step, asking first when the dotenv file already assigns it
def _wizard_queue_secret(state, key, value, input_func=None):
    if not value:
        return False
    if _dotenv_contains_key(state.env_path, key) and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False, input_func=input_func):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    state.secret_updates[key] = value
    return True


# Holds every wizard answer until the user explicitly saves, so nothing is written during questioning
class WizardSetupState:
    # Starts from the values already in effect, which become both the defaults and the revert target
    def __init__(self, config_path, env_path, baseline_values):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.baseline_values = dict(baseline_values)
        self.config_values = dict(baseline_values)
        self.secret_updates = {}
        self.retained_secrets = {}
        self.token_json = ""
        self.target = ""
        self.persist_target = True


# The mail server settings the wizard collects and how long its sign-in check waits for the server
WIZARD_SMTP_CONFIG_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
WIZARD_SMTP_TIMEOUT = 5

# The email alert settings the wizard offers, in the order the questions are asked
WIZARD_EMAIL_NOTIFICATION_KEYS = ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "STATUS_NOTIFICATION", "ERROR_NOTIFICATION")

# The recommended preset leaves STATUS_NOTIFICATION off: it also mails every away transition, which is a lot of mail
WIZARD_RECOMMENDED_EMAIL_KEYS = ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION")

WIZARD_WEBHOOK_NOTIFICATION_KEYS = ("WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", "WEBHOOK_GAME_CHANGE_NOTIFICATION", "WEBHOOK_STATUS_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")

# The same reasoning as the email preset: every away transition would publish its own notification
WIZARD_RECOMMENDED_WEBHOOK_KEYS = ("WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", "WEBHOOK_GAME_CHANGE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")

# Where the Microsoft application the tool signs in through is registered
ENTRA_PORTAL_URL = "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"

# Each editable section: internal name, menu label and description, then the keys reverted when it is re-entered
WIZARD_SECTIONS = (
    ("Target", "Target", "Change the Xbox account that is monitored.", ("XBOX_GAMERTAG",), ()),
    ("Polling", "Polling interval", "Change how often Xbox Live is checked.", ("XBOX_CHECK_INTERVAL", "XBOX_ACTIVE_CHECK_INTERVAL"), ()),
    ("Authentication", "Authentication", "Enter the Microsoft application credentials and authorize again.", (), ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET")),
    ("Email", "Email notifications", "Change SMTP details and email events.", WIZARD_SMTP_CONFIG_KEYS + WIZARD_EMAIL_NOTIFICATION_KEYS, ("SMTP_PASSWORD",)),
    ("Webhook", "Webhook alerts", "Change Discord or ntfy details and events.", ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER") + WIZARD_WEBHOOK_NOTIFICATION_KEYS, ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN")),
    ("Output", "Output files", "Change the log, CSV and status file destinations.", ("DISABLE_LOGGING", "CSV_FILE", "XBOX_STATUS_FILE"), ()),
    ("Destinations", "File destinations", "Change the configuration or dotenv output path.", (), ()),
)


# Restores one section to the values setup started with and drops any secret it had queued
def _wizard_reset_section(state, config_keys, secret_keys):
    for key in config_keys:
        if key in state.baseline_values:
            state.config_values[key] = state.baseline_values[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)
        if key in state.retained_secrets:
            state.secret_updates[key] = state.retained_secrets[key]


# Returns one declined section to the built-in template values, so nothing the user turned down is written
def _wizard_clear_section(state, config_keys, secret_keys=()):
    defaults = _config_template_defaults()
    for key in config_keys:
        if key in defaults:
            state.config_values[key] = defaults[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Asks which account to watch, accepting the gamertag or a profile link and rejecting the e-mail mistake
def _wizard_collect_target_section(state, initial_target=None, input_func=None):
    question = "Xbox gamertag to monitor"
    while True:
        answer = _wizard_ask_text(question, default=str(initial_target or state.target or ""), required=True, input_func=input_func)
        if not answer:
            # The question already offered another attempt and it was declined, so the section ends instead of asking again
            break
        try:
            state.target = normalize_xbox_target(answer)
        except ValueError as exc:
            print(f"  {exc}")
            if not _wizard_offer_retry(question, input_func=input_func):
                break
            continue
        break
    if not state.target:
        print("  No target selected. Nothing can be monitored until one is set. Run --setup again or pass the target on the command line.")
        _wizard_apply_target(state)
        return
    state.persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=state.persist_target, input_func=input_func)
    _wizard_apply_target(state)


# Mirrors the settled target into the config values, so an unsaved target is left out of the file
def _wizard_apply_target(state):
    state.config_values["XBOX_GAMERTAG"] = state.target if state.persist_target and state.target else ""


# Asks how often the tool checks, in whichever duration format the user prefers
def _wizard_collect_polling_section(state, input_func=None):
    state.config_values["XBOX_CHECK_INTERVAL"] = _wizard_ask_duration("Polling interval while the user is offline (seconds or use s/m/h/d)", int(state.config_values.get("XBOX_CHECK_INTERVAL") or XBOX_CHECK_INTERVAL), input_func=input_func)
    state.config_values["XBOX_ACTIVE_CHECK_INTERVAL"] = _wizard_ask_duration("Polling interval while the user is online (seconds or use s/m/h/d)", int(state.config_values.get("XBOX_ACTIVE_CHECK_INTERVAL") or XBOX_ACTIVE_CHECK_INTERVAL), input_func=input_func)


# Reports whether both Microsoft application credentials are available, counting the ones just entered
def _wizard_credentials_ready(state):
    return all(secret_is_set(state.secret_updates.get(key) or state.config_values.get(key)) for key in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"))


# Returns the Microsoft application credentials the wizard should sign in with
def _wizard_credentials(state):
    return tuple(str(state.secret_updates.get(key) or state.config_values.get(key) or "") for key in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"))


# Signs in through the interactive OAuth flow and returns the token response as JSON without writing anything
async def _wizard_request_tokens(client_id, client_secret, input_func=None):
    async with create_signed_session() as session:
        auth_mgr = AuthenticationManager(session, client_id, client_secret, "")
        print(f"\n  Open this URL in a browser and approve the request:\n  {auth_mgr.generate_authorization_url()}\n")
        code = _wizard_input("Paste the authorization code, the part after '?code=' in the callback URL: ", input_func=input_func).strip()
        if not code:
            return ""
        # The code is exchanged for tokens here, which takes long enough to look like a hang without a notice
        print("  Checking the sign-in with Microsoft ...")
        auth_mgr.oauth = await auth_mgr.request_oauth_token(code)
        await auth_mgr.refresh_tokens()
        return str(auth_mgr.oauth.model_dump_json())


# Collects the Microsoft application credentials, then authorizes once so monitoring has a token to refresh
def _wizard_collect_auth_section(state, input_func=None, getpass_func=None, authorizer=None):
    print(colorize_links(f"Register an application at {ENTRA_PORTAL_URL}"))
    print(colorize_links("  Account type 'Personal Microsoft accounts only', redirect URI of type Web set to http://localhost/auth/callback"))
    print("  Then copy its Application (client) ID and a client secret value.")
    print(colorize_links(f"  Guide: {CREDENTIALS_GUIDE_URL}"))
    already_configured = _wizard_credentials_ready(state) or any(_wizard_existing_secret(key, state.env_path, secret_updates=state.secret_updates) or _dotenv_contains_key(state.env_path, key) for key in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"))
    if already_configured and not _wizard_ask_yes_no("Replace the Microsoft application credentials already configured?", default=False, input_func=input_func):
        _wizard_collect_authorization(state, input_func=input_func, authorizer=authorizer)
        return
    while True:
        client_id = _wizard_ask_secret("Application (client) ID", getpass_func=getpass_func)
        client_secret = _wizard_ask_secret("Client secret value", getpass_func=getpass_func)
        if client_id and client_secret:
            state.secret_updates["MS_APP_CLIENT_ID"] = client_id
            state.secret_updates["MS_APP_CLIENT_SECRET"] = client_secret
            break
        # Monitoring cannot run without both, so leaving them unset has to be a decision rather than a fallthrough
        if not _wizard_offer_retry("Microsoft application credentials", "Nothing can be monitored until both are set", input_func=input_func):
            return
    _wizard_collect_authorization(state, input_func=input_func, authorizer=authorizer)


# Offers the one-time browser sign-in, holding the resulting tokens in memory until the user saves
def _wizard_collect_authorization(state, input_func=None, authorizer=None):
    if not _wizard_credentials_ready(state):
        return
    tokens_path = Path(os.path.expanduser(str(state.config_values.get("MS_AUTH_TOKENS_FILE") or MS_AUTH_TOKENS_FILE or "")))
    already_authorized = bool(str(tokens_path)) and tokens_path.is_file()
    question = "Authorize again with your Microsoft account?" if already_authorized else "Authorize with your Microsoft account now?"
    if not _wizard_ask_yes_no(question, default=not already_authorized, input_func=input_func):
        return
    authorize = _wizard_request_tokens if authorizer is None else authorizer
    client_id, client_secret = _wizard_credentials(state)
    while True:
        try:
            tokens = asyncio.run(authorize(client_id, client_secret, input_func=input_func))
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as exc:
            advice = classify_recovery_error(exc, context="auth", detail=f"The Microsoft sign-in did not complete: {exc}")
            print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
            print(f"  To fix: {advice.fix}")
            tokens = ""
        if tokens:
            state.token_json = str(tokens)
            print(f"  Microsoft accepted the sign-in. The tokens are written to '{tokens_path}' when you save.")
            return
        # The tokens are what monitoring refreshes on every run, so skipping this has to be a decision too
        if not _wizard_offer_retry("Microsoft sign-in", "Monitoring will ask for it on its first run", input_func=input_func):
            return


# Reports whether the saved settings already send email, so a rerun proposes keeping the channel it has
def _wizard_email_enabled(config_values):
    # The error alert ships switched on, so on its own it counts only once a mail server has been named
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        if key != "ERROR_NOTIFICATION" and bool(config_values.get(key)):
            return True
    return bool(config_values.get("ERROR_NOTIFICATION")) and secret_is_set(config_values.get("SMTP_HOST"))


# Asks whether to send email alerts and collects only the settings that choice needs
def _wizard_collect_email_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Configure email notifications?", default=_wizard_email_enabled(state.config_values), input_func=input_func):
        _wizard_disable_email(state)
        return
    while True:
        state.config_values["SMTP_HOST"] = _wizard_ask_text("SMTP host", default=_wizard_default(state.config_values.get("SMTP_HOST")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_HOST"):
            return
        state.config_values["SMTP_PORT"] = _wizard_ask_positive_int("SMTP port", int(state.config_values.get("SMTP_PORT") or 587), maximum=65535, input_func=input_func)
        state.config_values["SMTP_SSL"] = _wizard_ask_yes_no("Enable TLS/SSL for SMTP?", default=bool(state.config_values.get("SMTP_SSL")), input_func=input_func)
        state.config_values["SMTP_USER"] = _wizard_ask_text("SMTP username", default=_wizard_default(state.config_values.get("SMTP_USER")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_USER"):
            return
        state.config_values["SENDER_EMAIL"] = _wizard_ask_text("Sender email", default=_wizard_default(state.config_values.get("SENDER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SENDER_EMAIL"):
            return
        state.config_values["RECEIVER_EMAIL"] = _wizard_ask_text("Receiver email", default=_wizard_default(state.config_values.get("RECEIVER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "RECEIVER_EMAIL"):
            return
        password = _wizard_ask_secret("SMTP password", getpass_func=getpass_func, strip=False)
        _wizard_queue_secret(state, "SMTP_PASSWORD", password, input_func=input_func)
        # The sign-in has to prove the value the next run resolves rather than the one just typed. A declined
        # replacement and an exported variable both leave setup reporting success for a password nothing will use
        effective_password, supplied_by_export = effective_secret_after_setup("SMTP_PASSWORD", state.env_path, state.secret_updates)
        if supplied_by_export and password:
            print("  SMTP_PASSWORD is exported in this environment and an export wins at startup, so the next run uses that value rather than the one just entered.")
            print("  The check below signs in with the exported value. Unset it to use the one saved here.")
        outcome = _wizard_smtp_sign_in_accepted({name: state.config_values[name] for name in WIZARD_SMTP_CONFIG_KEYS}, effective_password, input_func=input_func)
        if outcome is None:
            _wizard_disable_email(state)
            return
        if outcome:
            break
    preset = _wizard_ask_choice("Which email notifications should be enabled?", [
        ("Status and errors, recommended", "Online and offline changes, game changes and monitoring errors."),
        ("Every supported event", "Adds a mail for every away transition as well."),
        ("Custom", "Choose each notification type separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {name: name in WIZARD_RECOMMENDED_EMAIL_KEYS for name in WIZARD_EMAIL_NOTIFICATION_KEYS}
    elif preset == 1:
        selected = {name: True for name in WIZARD_EMAIL_NOTIFICATION_KEYS}
    else:
        print()
        questions = (
            ("ACTIVE_INACTIVE_NOTIFICATION", "Email when the user goes online or offline?"),
            ("GAME_CHANGE_NOTIFICATION", "Email when the user starts, changes or stops a game?"),
            ("STATUS_NOTIFICATION", "Email on every status change, including away?"),
            ("ERROR_NOTIFICATION", "Email on monitoring errors?"),
        )
        selected = {name: _wizard_ask_yes_no(question, default=False, input_func=input_func) for name, question in questions}
    state.config_values.update(selected)


# Collects an optional ntfy access token without displaying it or contacting the service
def _wizard_collect_ntfy_access_token(state, input_func=None, getpass_func=None):
    if _wizard_existing_secret("NTFY_ACCESS_TOKEN", state.env_path, secret_updates=state.secret_updates):
        choice = _wizard_ask_choice("Which ntfy authentication should be used?", [
            ("Keep the saved access token", "Keeps the private value without displaying or changing it."),
            ("Paste a new access token", "Uses a hidden prompt then saves the replacement in .env."),
            ("Do not use an access token", "Disables the saved token. Authentication in the topic URL still works."),
        ], input_func=input_func)
        if choice == 0:
            return
        if choice == 2:
            state.secret_updates["NTFY_ACCESS_TOKEN"] = ""
            print("  The saved ntfy access token will be disabled without being displayed.")
            return
    elif not _wizard_ask_yes_no("Authenticate this ntfy topic with a separate access token?", default=False, input_func=input_func):
        print("  No separate access token selected. Authentication already present in the topic URL still works.")
        return
    while True:
        token = _wizard_ask_secret("Paste the ntfy access token only", getpass_func=getpass_func)
        if not token or ("\r" not in token and "\n" not in token and not token.casefold().startswith(("bearer ", "basic "))):
            if token:
                state.secret_updates["NTFY_ACCESS_TOKEN"] = token
            return
        print("  Paste only the access token without a Bearer or Basic prefix.")
        if not _wizard_offer_retry("ntfy access token", input_func=input_func):
            return


# Collects the webhook destination and the alerts that should reach it
def _wizard_collect_webhook_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Set up webhook alerts (Discord, ntfy etc.)?", default=bool(state.config_values.get("WEBHOOK_ENABLED")), input_func=input_func):
        _wizard_disable_webhook(state)
        return
    choice = _wizard_ask_choice("Which webhook service should receive alerts?", [
        ("Discord", "Sends a Discord embed to one channel webhook."),
        ("ntfy", "Sends a native notification to one ntfy topic URL."),
    ], input_func=input_func)
    provider = "discord" if choice == 0 else "ntfy"
    state.config_values["WEBHOOK_PROVIDER"] = provider
    if provider == "discord":
        print("  In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.")
    else:
        print("  In ntfy: choose a hard-to-guess topic. Paste its complete topic URL, or just the topic name when it is hosted on ntfy.sh.")
    replace_webhook = True
    if _wizard_existing_secret("WEBHOOK_URL", state.env_path, secret_updates=state.secret_updates):
        url_choice = _wizard_ask_choice("Which webhook URL should be used?", [
            ("Keep the saved URL", "Keeps the private value without displaying or changing it."),
            ("Paste a new URL", "Uses a hidden prompt then saves the new private value in .env."),
        ], input_func=input_func)
        replace_webhook = url_choice == 1
    if replace_webhook:
        while True:
            entered = _wizard_ask_secret("Paste the Discord webhook URL" if provider == "discord" else "Paste the ntfy topic URL or ntfy.sh topic name", getpass_func=getpass_func)
            webhook_url = normalize_ntfy_topic_url(entered) if provider == "ntfy" else str(entered).strip()
            if validate_webhook_url(webhook_url):
                state.secret_updates["WEBHOOK_URL"] = webhook_url
                break
            # Nothing can be delivered without a destination, so giving up has to stay reachable from the prompt.
            # The branch is chosen by what was typed rather than by the normalized value, since a rejected ntfy
            # topic normalizes to an empty string and would otherwise be reported as nothing entered
            if not str(entered).strip():
                if not _wizard_offer_retry("webhook URL", "Webhook alerts stay off until one is set", input_func=input_func):
                    _wizard_disable_webhook(state)
                    return
                continue
            if provider == "ntfy":
                print("  Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.")
            else:
                print("  That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.")
            if not _wizard_offer_retry("webhook URL", input_func=input_func):
                _wizard_disable_webhook(state)
                return
    if provider == "ntfy":
        _wizard_collect_ntfy_access_token(state, input_func=input_func, getpass_func=getpass_func)
    state.config_values["WEBHOOK_ENABLED"] = True
    preset = _wizard_ask_choice("Which webhook alerts should be sent?", [
        ("Status and errors, recommended", "Online and offline changes, game changes and monitoring errors."),
        ("Every supported alert", "Adds a notification for every away transition as well."),
        ("Custom", "Choose each webhook alert separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {name: name in WIZARD_RECOMMENDED_WEBHOOK_KEYS for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS}
    elif preset == 1:
        selected = {name: True for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS}
    else:
        print()
        questions = (
            ("WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", "Send a webhook alert when the user goes online or offline?"),
            ("WEBHOOK_GAME_CHANGE_NOTIFICATION", "Send a webhook alert when the user starts, changes or stops a game?"),
            ("WEBHOOK_STATUS_NOTIFICATION", "Send a webhook alert on every status change, including away?"),
            ("WEBHOOK_ERROR_NOTIFICATION", "Send a webhook alert on monitoring errors?"),
        )
        selected = {name: _wizard_ask_yes_no(question, default=False, input_func=input_func) for name, question in questions}
    state.config_values.update(selected)


# Switches the channel and every alert it owns off together, so a half-configured webhook cannot be written
def _wizard_disable_webhook(state):
    _wizard_clear_section(state, ("WEBHOOK_PROVIDER",), ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN"))
    state.config_values["WEBHOOK_ENABLED"] = False
    for key in WIZARD_WEBHOOK_NOTIFICATION_KEYS:
        state.config_values[key] = False


# Signs in to the collected mail server without sending anything, so a refused login is caught during setup
def _wizard_verify_smtp(values, password):
    names = WIZARD_SMTP_CONFIG_KEYS + ("SMTP_PASSWORD",)
    previous = {name: globals()[name] for name in names}
    try:
        globals().update(values)
        # A blank answer keeps the password already stored, which is the one the sign-in must then prove
        smtp_sign_in(password or previous["SMTP_PASSWORD"], timeout=WIZARD_SMTP_TIMEOUT)
        return None
    except RecoveryError as exc:
        return exc.advice
    except Exception as exc:
        return classify_recovery_error(exc, context="smtp")
    finally:
        globals().update(previous)


# Reports the outcome of the sign-in check: True to continue, False to ask again, None to switch email off
def _wizard_smtp_sign_in_accepted(values, password, input_func=None):
    print("  Checking the sign-in with the mail server ...")
    advice = _wizard_verify_smtp(values, password)
    if advice is None:
        print("  The mail server accepted the sign-in. No email was sent.")
        return True
    print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
    print(f"  To fix: {advice.fix}")
    if _wizard_offer_retry("mail server settings", input_func=input_func):
        return False
    if advice.retryable:
        # Being offline is the usual reason a correct setup fails here, so the answers are kept rather than discarded
        print("  The settings were kept without being checked. Run --doctor to check the sign-in again.")
        return True
    print("  Email notifications stay off until the mail server accepts the settings.")
    return None


# Switches every email alert off together, so an abandoned answer cannot leave half a mail server configured
def _wizard_disable_email(state):
    _wizard_clear_section(state, WIZARD_SMTP_CONFIG_KEYS, ("SMTP_PASSWORD",))
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        state.config_values[key] = False


# Reports whether one required mail server answer was abandoned, switching the channel off when it was
def _wizard_email_answer_missing(state, key):
    if state.config_values.get(key):
        return False
    print("  Email notifications stay off until every mail server setting is answered.")
    _wizard_disable_email(state)
    return True


# Adds the .csv extension when the answer carries none, so a bare name still names a CSV file
def _wizard_normalize_csv_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".csv"


# Adds the .json extension when the answer carries none, so a bare name still names the JSON status file
def _wizard_normalize_status_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".json"


# Collects the files monitoring would write
def _wizard_collect_output_section(state, input_func=None):
    state.config_values["DISABLE_LOGGING"] = not _wizard_ask_yes_no("Write the normal per-target log file?", default=not bool(state.config_values.get("DISABLE_LOGGING")), input_func=input_func)
    saved_csv = str(state.config_values.get("CSV_FILE") or "")
    # Asked as its own question, since Enter on the path prompt takes the shown default and so could never clear a saved one
    if _wizard_ask_yes_no("Write a CSV file of the changes?", default=bool(saved_csv), input_func=input_func):
        state.config_values["CSV_FILE"] = _wizard_normalize_csv_path(_wizard_ask_text("CSV output path", default=saved_csv, required=True, input_func=input_func))
    else:
        state.config_values["CSV_FILE"] = ""
    state.config_values["XBOX_STATUS_FILE"] = _wizard_normalize_status_path(_wizard_ask_text("Optional status file path (blank uses the default name in the working directory)", default=str(state.config_values.get("XBOX_STATUS_FILE") or ""), input_func=input_func))


# Reads the selected private file before setup changes paths or pending answers
def read_private_settings(env_path):
    path = Path(env_path)
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    bindings = list(_dotenv_bindings(content))
    invalid = next((binding for binding in bindings if binding.error), None)
    if invalid is not None:
        raise ValueError(f"Dotenv file '{path}' has invalid syntax near line {invalid.original.line}. Correct that assignment before retrying.")
    owned = globals().get("DOTENV_RELOAD_STATE", {}).get("loaded", ())
    environment = {key: value for key, value in os.environ.items() if value and key not in owned}
    return resolve_dotenv_values(content, override=False, environment=environment)


# Rechecks retained answers against the new destination before collecting replacement choices
def _wizard_move_private_settings(state, selected_env):
    retained = read_private_settings(state.env_path)
    retained.update(state.secret_updates)
    selected = read_private_settings(selected_env)
    carried = {key: value for key, value in retained.items() if key in SECRET_KEYS and isinstance(value, str) and selected.get(key) is None}
    state.retained_secrets = dict(carried)
    state.secret_updates = dict(carried)
    state.env_path = selected_env
    for key in SECRET_KEYS:
        value = selected.get(key, carried.get(key))
        if isinstance(value, str):
            state.config_values[key] = value


# Changes where setup writes, re-asking the sections that hold secrets when the dotenv destination moves
def _wizard_collect_destination_section(state, input_func=None, getpass_func=None):
    new_config_path = state.config_path
    while True:
        config_text = _wizard_ask_text("Configuration file destination", default=str(state.config_path), required=True, input_func=input_func)
        try:
            selected_config = _wizard_validate_destination(config_text, "Configuration destination")
            break
        except ValueError as exc:
            print(f"  {exc}.")
    # Both sides are compared resolved, so an unchanged answer written a different way is not read as a move
    if selected_config != Path(new_config_path).expanduser().resolve():
        chosen_config = _wizard_choose_config_destination(selected_config, input_func=input_func)
        # Giving up on every offered path keeps the current destination rather than cancelling the whole setup
        if chosen_config is not None:
            new_config_path = chosen_config
    while True:
        env_text = _wizard_ask_text("Dotenv file destination", default=str(state.env_path), required=True, input_func=input_func)
        if env_text.casefold() == "none":
            print("  Setup needs a writable dotenv file and cannot use 'none'.")
            continue
        try:
            selected_env = _wizard_validate_destination(env_text, "Dotenv destination")
        except ValueError as exc:
            print(f"  {exc}.")
            continue
        # One file cannot hold both, since saving the configuration would overwrite the secrets beside it
        if selected_env == Path(new_config_path).expanduser().resolve():
            print("  The dotenv file has to be a different file from the configuration.")
            continue
        break
    if selected_env == Path(state.env_path).expanduser().resolve():
        state.config_path = new_config_path
        state.config_values["DOTENV_FILE"] = str(selected_env)
        return
    _wizard_move_private_settings(state, selected_env)
    state.config_path = new_config_path
    state.config_values["DOTENV_FILE"] = str(selected_env)
    print("  The dotenv destination changed. Review authentication and notification settings. Values in the selected file are kept unless you replace them.")
    _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)
    for key, value in state.retained_secrets.items():
        state.secret_updates.setdefault(key, value)


# Runs one editable section again after resetting only the keys it owns
def _wizard_edit_setup_section(state, input_func=None, getpass_func=None):
    options = [(label, description) for _name, label, description, _config_keys, _secret_keys in WIZARD_SECTIONS]
    options.append(("Return to summary", "Keep every current answer."))
    choice = _wizard_ask_choice("Which setup section should be changed?", options, input_func=input_func)
    if choice == len(WIZARD_SECTIONS):
        return
    name, _label, _description, config_keys, secret_keys = WIZARD_SECTIONS[choice]
    _wizard_reset_section(state, config_keys, secret_keys)
    if name == "Target":
        state.target = ""
    if name == "Authentication":
        state.token_json = ""
    print()
    collectors = {
        "Target": lambda: _wizard_collect_target_section(state, input_func=input_func),
        "Polling": lambda: _wizard_collect_polling_section(state, input_func=input_func),
        "Authentication": lambda: _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func),
        "Email": lambda: _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func),
        "Webhook": lambda: _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func),
        "Output": lambda: _wizard_collect_output_section(state, input_func=input_func),
        "Destinations": lambda: _wizard_collect_destination_section(state, input_func=input_func, getpass_func=getpass_func),
    }
    collectors[name]()


# The theme part each setup summary row draws its value in, for rows whose value has a known kind
WIZARD_SUMMARY_VALUE_STYLES = {"Target": "username", "Polling interval while offline": "duration", "Polling interval while online": "duration"}


# Colours one setup summary value from its row label
def _wizard_summary_value(label, value):
    text = str(value)
    part = WIZARD_SUMMARY_VALUE_STYLES.get(label)
    if part:
        return colorize(part, text)
    if text.startswith("enabled") or text == "complete":
        return colorize("boolean_true", text)
    if text in ("disabled", "incomplete"):
        return colorize("boolean_false", text)
    return text


# Prints one aligned label and value block, so every summary row lines up
def _wizard_print_summary_rows(rows):
    width = max(len(label) for label, _ in rows) + 1
    for label, value in rows:
        print(f"  {(label + ':'):<{width}} {_wizard_summary_value(label, value)}")


# Shows everything that is about to be written, by name and never by secret value
def _wizard_print_setup_summary(state):
    email_labels = {"ACTIVE_INACTIVE_NOTIFICATION": "online/offline", "GAME_CHANGE_NOTIFICATION": "game", "STATUS_NOTIFICATION": "every status", "ERROR_NOTIFICATION": "errors"}
    enabled_email = [email_labels[name] for name in WIZARD_EMAIL_NOTIFICATION_KEYS if state.config_values.get(name)]
    webhook_labels = {"WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION": "online/offline", "WEBHOOK_GAME_CHANGE_NOTIFICATION": "game", "WEBHOOK_STATUS_NOTIFICATION": "every status", "WEBHOOK_ERROR_NOTIFICATION": "errors"}
    enabled_webhook = [webhook_labels[name] for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS if state.config_values.get(name)]
    rows = [
        ("Target", state.target or "not set"),
        ("Persist target", "yes" if state.persist_target else "no"),
        ("Polling interval while offline", _wizard_format_duration(int(state.config_values.get("XBOX_CHECK_INTERVAL") or 0))),
        ("Polling interval while online", _wizard_format_duration(int(state.config_values.get("XBOX_ACTIVE_CHECK_INTERVAL") or 0))),
        ("Application credentials", "complete" if _wizard_credentials_ready(state) else "incomplete"),
        ("Microsoft sign-in", "authorized in this session" if state.token_json else "not done yet"),
        ("Email", "enabled" if enabled_email else "disabled"),
        ("Email notifications", ", ".join(enabled_email) if enabled_email else "none"),
        ("Webhook", f"enabled ({webhook_provider_display_name(state.config_values.get('WEBHOOK_PROVIDER'))})" if state.config_values.get("WEBHOOK_ENABLED") else "disabled"),
        ("Webhook alerts", ", ".join(enabled_webhook) if enabled_webhook else "none"),
        ("Output log", "disabled" if state.config_values.get("DISABLE_LOGGING") else "enabled"),
        ("CSV output", state.config_values.get("CSV_FILE") or "disabled"),
        ("Status file", state.config_values.get("XBOX_STATUS_FILE") or (default_status_file(state.target) if state.target else "xbox_<xbox_gamertag>_last_status.json")),
        ("Config destination", state.config_path),
        ("Dotenv destination", state.env_path),
        ("Install method", install_method_display_name()),
    ]
    print("\n" + colorize("header", "Setup summary") + "\n")
    _wizard_print_summary_rows(rows)


# Loops on the summary until the user saves or explicitly discards, so nothing is written by accident
def _wizard_review_setup(state, input_func=None, getpass_func=None):
    while True:
        state.secret_updates = {**state.retained_secrets, **state.secret_updates}
        _wizard_print_setup_summary(state)
        action = _wizard_ask_choice("What would you like to do?", [
            ("Save settings", "Write the displayed settings to the selected files."),
            ("Review or change settings", "Edit one section without losing the other answers."),
            ("Discard answers and exit", "Leave the destination files unchanged."),
        ], input_func=input_func)
        if action == 0:
            return True
        if action == 1:
            _wizard_edit_setup_section(state, input_func=input_func, getpass_func=getpass_func)
            continue
        print()
        if _wizard_ask_yes_no("Discard all entered answers and exit?", default=False, input_func=input_func):
            return False
        print("  Setup answers retained.")


# Prints where setup will write and which install method the printed commands are written for
def _wizard_print_setup_destinations(config_path, env_path):
    print(f"Detected install method: {colorize('username', detect_install_method())}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")


# Puts the values setup just saved into effect, so doctor checks the written files instead of the earlier state.
# Returns the timezone advice, since the saved config can name a zone the startup resolution never saw
def _wizard_apply_saved_values(state, env_path=None):
    exported = _wizard_exported_secrets()
    selected_path = state.env_path if env_path is None else env_path
    try:
        saved = _wizard_private_values(selected_path)
    except (OSError, UnicodeError, ValueError) as exc:
        print_recovery_error(exc, context="file", detail=f"Could not read saved secrets from '{selected_path}'")
        raise SystemExit(1) from None
    saved_config = _config_template_defaults()
    if not load_config_file(state.config_path, namespace=saved_config):
        raise SystemExit(1)
    globals().update(saved_config)
    for key in SECRET_KEYS:
        if key in exported:
            value, source = exported[key], "environment"
        elif saved.get(key) is not None:
            value, source = saved[key], "dotenv file"
        else:
            value, source = saved_config.get(key), "configuration file"
        globals()[key] = value
        if source == "dotenv file":
            os.environ[key] = str(value)
        elif key not in exported:
            os.environ.pop(key, None)
        record_secret_source(key, source)
    return resolve_local_timezone()


# Builds the exact local command that starts this monitor, used when setup offers to launch it
def _wizard_local_command_args(target=None, config_path=None, env_path=None):
    executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
    arguments = [executable, str(Path(__file__).resolve())]
    if target:
        arguments.append(str(target))
    if config_path:
        arguments.extend(["--config-file", str(config_path)])
    if env_path:
        arguments.extend(["--env-file", str(env_path)])
    return arguments


# Hands the terminal to the monitor, replacing this process where the platform allows it
def _wizard_launch_monitor(arguments):
    command = [str(argument) for argument in arguments]
    if platform.system() == "Windows":
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return 0
    os.execv(command[0], command)
    return 0


# Runs the guided setup, holding every answer until the user saves
def run_setup_wizard(initial_target=None, config_file=None, env_file=None, input_func=None, getpass_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(colorize_links(f"Guide: {QUICK_START_GUIDE_URL}"))
        return 1

    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except ValueError as exc:
        print_recovery_error(context="file.unwritable", detail=str(exc))
        return 1

    print(colorize("header", "Setup Wizard") + "\n")
    print("This asks a few questions and writes a ready-to-run configuration.")
    _wizard_print_default_guidance()
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.\n")
    _wizard_print_setup_destinations(config_path, env_path)

    baseline_values = {name: value for name, value in globals().items() if name in _config_allowed_names()}
    state = WizardSetupState(config_path, env_path, baseline_values)
    state.config_values["DOTENV_FILE"] = str(env_path)

    try:
        # Asked before anything else, so a config that has to be replaced is agreed to rather than discovered at Save
        config_existed = Path(config_path).exists()
        chosen_config = _wizard_choose_config_destination(config_path, input_func=input_func)
        if chosen_config is None:
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
        state.config_path = chosen_config
        _wizard_seed_destination(state, env_file)
        # A destination nothing was asked about printed nothing, so the separator would leave a blank gap
        if config_existed:
            print()
        _wizard_collect_target_section(state, initial_target, input_func=input_func)
        print()
        _wizard_collect_polling_section(state, input_func=input_func)
        print()
        _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_output_section(state, input_func=input_func)
        saved = _wizard_review_setup(state, input_func=input_func, getpass_func=getpass_func)
    except (OSError, UnicodeError, ValueError) as exc:
        print_recovery_error(exc, context="config")
        print("Correct the selected file or pass --env-file with a writable destination.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print(colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1

    if not saved:
        print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1

    # Everything above only filled the state, so this is the first and only point anything reaches disk
    try:
        preserved_dotenv = preserve_inline_config_secrets(state.config_path, state.env_path)
        config_backup, _written = write_generated_config(state.config_path, generate_config_with_current_values(state.config_values), force=True, redact_secrets=True)
    except Exception as exc:
        print_recovery_error(exc, context="file.unwritable", detail=f"Could not write the configuration to '{state.config_path}': {exc}")
        return 1
    secrets_written = bool(preserved_dotenv)
    if state.secret_updates:
        try:
            update_dotenv_file(state.env_path, state.secret_updates)
            secrets_written = True
        except Exception as exc:
            print_recovery_error(exc, context="file.unwritable", detail=f"Could not write the secrets to '{state.env_path}': {exc}")
            print(f"Configuration was saved to '{state.config_path}'. Setup is incomplete and monitoring was not started.")
            print("Correct the dotenv destination then run --setup again with the same --config-file and --env-file. Review the saved settings before starting monitoring.")
            return 1
    tokens_path = Path(os.path.expanduser(str(state.config_values.get("MS_AUTH_TOKENS_FILE") or MS_AUTH_TOKENS_FILE or "")))
    tokens_written = False
    if state.token_json:
        try:
            # The cache holds a refresh token, so it is private to the owner and never left half-written
            write_file_atomically(tokens_path, state.token_json, mode=0o600)
            tokens_written = True
        except Exception as exc:
            print_recovery_error(exc, context="file.unwritable", detail=f"Could not write the Xbox tokens to '{tokens_path}': {exc}")
            return 1

    print("\n" + colorize("header", "Saved files") + "\n")
    print(f"  Configuration: {state.config_path}")
    if config_backup:
        print(f"  Backup:        {config_backup}")
    if secrets_written:
        print(f"  Secrets:       {state.env_path}")
    if tokens_written:
        print(f"  Xbox tokens:   {tokens_path}")

    doctor_offered = bool(state.target)
    doctor_exit = None
    if doctor_offered:
        print()
    try:
        if doctor_offered and _wizard_ask_yes_no("Run doctor now? It writes no files and offers real delivery tests only with separate approval.", default=True, input_func=input_func):
            print()
            timezone_advice = _wizard_apply_saved_values(state, env_path=state.env_path if state.env_path.is_file() else None)
            doctor_exit = run_doctor(xbox_gamertag=state.target, config_path=str(state.config_path), env_path=str(state.env_path) if state.env_path.is_file() else None, timezone_advice=timezone_advice)
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional check
        print(colorize("warning", "Setup is saved. Use the commands below when ready."))

    env_arguments = ["--env-file", str(state.env_path)] if state.env_path.is_file() else []
    # A saved target is already in the config file, so the printed commands stay short
    target_arguments = [] if state.persist_target or not state.target else [state.target]
    paths = ["--config-file", str(state.config_path)] + env_arguments
    print("\n" + colorize("header", "Next steps") + "\n")
    print_labelled_command("Check setup again:", render_command(["--doctor", *target_arguments, *paths]))
    start_label = "After Doctor passes, start monitoring:" if doctor_exit not in (None, 0) else "Start monitoring:"
    print_labelled_command(start_label, render_command([*target_arguments, *paths]))
    print(colorize_links(f"Guide: {QUICK_START_GUIDE_URL}\n"))

    try:
        # Only a doctor run that passed proves the saved setup can monitor, so the launch offer waits for it
        start_monitoring = bool(state.target and doctor_exit == 0 and _wizard_ask_yes_no("Start monitoring now? Monitoring will continue until Ctrl+C.", default=True, input_func=input_func))
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional launch
        print(colorize("warning", "Setup is saved. Start monitoring with the command above when ready."))
        return 0
    if start_monitoring:
        launch_arguments = _wizard_local_command_args(target=None if state.persist_target else state.target, config_path=state.config_path, env_path=state.env_path if state.env_path.is_file() else None)
        sys.stdout.flush()
        return _wizard_launch_monitor(launch_arguments)
    return 0


# Renders the --help examples: one heading per task, then a comment and the command it describes
def render_help_examples(groups, guide_url):
    blocks = []
    for title, entries in groups:
        block = [f"{title}:"]
        for comment, command in entries:
            if len(block) > 1:
                block.append("")
            block.extend(f"  # {line}" for line in comment.split("\n"))
            if command:
                block.append(f"  {command}")
        blocks.append("\n".join(block))
    return "Examples:\n\n" + "\n\n".join(blocks) + f"\n\nGuide: {guide_url}\n"


# Returns the --help epilog, listing the commands worth knowing rather than every command there is
def help_examples():
    prefix = render_command(include_paths=False)
    groups = (
        ("Getting started", (
            ("Guided setup, recommended for the first run", f"{prefix} --setup"),
            ("Or save the Microsoft application credentials and authorize once", f"{prefix} --set-ms-app-credentials"),
            ("Check the setup before relying on it", f"{prefix} --doctor <xbox_gamertag>"),
            ("Start monitoring", f"{prefix} <xbox_gamertag>"),
        )),
        ("Notifications", (
            ("Email when the user goes online or offline, and on game changes", f"{prefix} <xbox_gamertag> -a -g"),
            ("Send one test email", f"{prefix} --send-test-email"),
            ("Send one test webhook", f"{prefix} --send-test-webhook"),
        )),
        ("Information and diagnostics", (
            ("Show detailed profile information and exit", f"{prefix} -i <xbox_gamertag>"),
            ("Trace what the tool is doing", f"{prefix} <xbox_gamertag> --debug"),
        )),
    )
    return render_help_examples(groups, QUICK_START_GUIDE_URL)


# Prints the commands a newcomer needs next, instead of an argparse usage error nobody can act on
def print_welcome_screen(input_func=None, interactive=None, config_file=None, env_file=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    prefix = render_command(include_paths=False)
    print(f"For <xbox_gamertag>, use the {XBOX_TARGET_FORMS}.\n")
    print_labelled_command("Quickest start (already configured):", f"{prefix} <xbox_gamertag>")
    # The suffix names the prompt printed below, so it only appears when that prompt does
    print_labelled_command("Easiest start (guided setup wizard):", f"{prefix} --setup", "   (or just answer Y below)" if terminal_is_interactive else "")
    print_labelled_command("Check setup before monitoring:", f"{prefix} --doctor <xbox_gamertag>")
    print_labelled_command("Show profile details and exit:", f"{prefix} -i <xbox_gamertag>")
    print(f"Full options: {colorize('section', prefix + ' --help')}")
    print(colorize_links(f"\nGuide:        {QUICK_START_GUIDE_URL}\n"))
    if terminal_is_interactive:
        try:
            start_setup = _wizard_ask_yes_no("Run the guided setup wizard now?", default=True, input_func=input_func)
        except (EOFError, KeyboardInterrupt):
            # This prompt sits outside the wizard, which handles its own interrupts
            print(colorize("warning", "Setup cancelled."))
            return 1
        if start_setup:
            print()
            return run_setup_wizard(config_file=config_file, env_file=env_file, input_func=input_func)
    # Without a terminal there was nothing to answer, so a bare invocation stays the usage error it was
    return 0 if terminal_is_interactive else 1


# The one-shot commands that write a secret, which stay usable when no gamertag was given
SECRET_ACTION_FLAGS = ("--set-ms-app-credentials", "--set-smtp-password", "--set-webhook-url")


# Commands that print a one-shot result and exit, so the screen keeps whatever is already on it
KEEP_HISTORY_FLAGS = (*SECRET_ACTION_FLAGS, "--doctor", "--send-test-email", "--send-test-webhook", "--help", "-h")


# Returns True when the running command is a one-shot whose output has to stay scrollable
def keep_terminal_history():
    return any(flag in sys.argv for flag in KEEP_HISTORY_FLAGS)


# Reads only the persisted target from a config file, so a printed command can omit a positional the config already supplies
def config_file_target(config_path):
    if not config_path or str(config_path).casefold() == "none":
        return ""
    namespace = {}
    if not load_config_file(config_path, namespace=namespace, report_errors=False):
        return ""
    return str(namespace.get("XBOX_GAMERTAG") or "")


# Returns the config a printed command should name, so a run started with discovery off cannot point the reader
# at a file it deliberately ignored
def resolved_command_config(config_path=None):
    # A path the caller was given is what the command names, so a stale discovery flag cannot override it
    if config_path is not None:
        return "none" if str(config_path).casefold() == "none" else config_path
    return "none" if CONFIG_DISCOVERY_DISABLED else find_config_file()


# Returns the targets for the printed doctor and monitoring commands, dropping one the effective config already supplies
def command_targets(explicit_target=None, saved_target=None, placeholder="<xbox_gamertag>"):
    saved = str(saved_target or "")
    known = str(explicit_target or "") or saved
    if not known:
        # Monitoring cannot run without a target, so it keeps the placeholder while the doctor reports the gap itself
        return None, placeholder
    printed = None if known == saved else known
    return printed, printed


# Prints the commands to run next, with the file paths this run was given so they can be pasted as they are
def print_secret_next_steps(env_path, config_path=None, xbox_gamertag=None, test_step=None):
    paths = []
    if config_path or CONFIG_DISCOVERY_DISABLED:
        paths.extend(("--config-file", str(resolved_command_config(config_path))))
    paths.extend(("--env-file", str(env_path)))
    doctor_target, monitor_target = command_targets(xbox_gamertag, config_file_target(resolved_command_config(config_path)))
    print()
    if test_step:
        print_labelled_command(test_step[0], render_command([test_step[1], *paths]))
    print_labelled_command("Check setup again:", render_command(["--doctor", *((doctor_target,) if doctor_target else ()), *paths]))
    print_labelled_command("Once the checks pass, start monitoring:", render_command([*((monitor_target,) if monitor_target else ()), *paths]))


# Reads one secret through a hidden prompt, keeping it out of the debug stream that would print it verbatim
def read_secret_privately(prompt_text, getpass_func=None, strip=True):
    global DEBUG_MODE

    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    previous_debug_mode = DEBUG_MODE
    DEBUG_MODE = False
    try:
        value = str(read_interactively(hidden_prompt, prompt_text))
        return value.strip() if strip else value
    finally:
        DEBUG_MODE = previous_debug_mode


# Reports whether the user agreed to replace secrets a dotenv file already holds
def confirm_secret_replacement(destination, keys, subject, flag, guide_url, input_func=None):
    present = [key for key in keys if _dotenv_contains_key(destination, key)]
    if not present:
        return
    ask = input if input_func is None else input_func
    try:
        confirmed = str(read_interactively(ask, f"Replace the saved {subject} in '{destination}'? [y/N]: ")).strip().casefold() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice(subject, flag, guide_url, len(keys) > 1)) from None
    if not confirmed:
        # The subject names every value the command replaces, so its plural cannot follow how many are saved today
        raise RecoveryError(secret_replacement_declined_advice(subject, flag, guide_url, len(keys) > 1))


# Returns one entered secret unchanged, for the values whose surrounding whitespace is significant
def keep_entered_value(value):
    return str(value)


# Collects one secret through a hidden prompt, checks it with the given validator and writes it only then
def run_set_secret(key, flag, subject, guide_url, guidance, prompt_text, validator, describe_success, env_file=None, config_path=None, xbox_gamertag=None, interactive=None, input_func=None, getpass_func=None, normalize=None, test_step=None):
    destination = resolve_secret_env_path(env_file, flag)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail=f"{flag} needs an interactive terminal so the value stays hidden"))

    confirm_secret_replacement(destination, (key,), subject, flag, guide_url, input_func=input_func)
    print(guidance)
    try:
        entered = read_secret_privately(prompt_text, getpass_func=getpass_func, strip=False)
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice(subject, flag, guide_url)) from None

    print(f"* Checking the entered {subject} before changing the dotenv file ...")
    # What is stored can differ from what was typed, so a shorthand the validator accepted is saved in full.
    # The value checked with the service is the value written, never a second reading of the raw input
    stored = str(entered).strip() if normalize is None else normalize(entered)
    outcome = validator(stored)
    try:
        update_dotenv_file(destination, {key: stored})
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="file.unwritable", detail=f"Cannot save {key} to '{destination}': {exc}"), exc) from None

    print(f"* {describe_success(outcome)}")
    print(f"* Updated '{destination}', readable only by you")
    # Startup loads the dotenv file without overriding the environment, so a saved replacement that an export
    # shadows would never be read. The run would keep failing with the value that was just proven good
    if os.environ.get(key):
        print(f"* {key} is exported in this environment and an export wins at startup, so the next run uses that value rather than the one just saved")
        print(colorize("info", f"To fix: Unset the exported {key} to use the saved one"))
    print_secret_next_steps(destination, config_path, xbox_gamertag, test_step)
    return str(destination)


# Stores both Microsoft application credentials and the tokens the one-time browser sign-in returns
def run_set_ms_app_credentials(env_file=None, config_path=None, xbox_gamertag=None, interactive=None, input_func=None, getpass_func=None, authorizer=None):
    keys = ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET")
    destination = resolve_secret_env_path(env_file, "--set-ms-app-credentials")
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="--set-ms-app-credentials needs an interactive terminal so the values stay hidden"))

    confirm_secret_replacement(destination, keys, "Microsoft application credentials", "--set-ms-app-credentials", CREDENTIALS_GUIDE_URL, input_func=input_func)
    print(colorize_links(f"* Register an application at {ENTRA_PORTAL_URL}"))
    print(colorize_links("* Account type 'Personal Microsoft accounts only', redirect URI of type Web set to http://localhost/auth/callback"))
    print("* Then copy its Application (client) ID and a client secret value.")
    print(colorize_links(f"* Guide: {CREDENTIALS_GUIDE_URL}"))
    try:
        client_id = read_secret_privately("Enter the Application (client) ID (input hidden): ", getpass_func=getpass_func)
        client_secret = read_secret_privately("Enter the client secret value (input hidden): ", getpass_func=getpass_func)
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="Credential entry was cancelled and the dotenv file was not changed")) from None
    if not client_id or not client_secret:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="Both the client ID and the client secret are needed, so the dotenv file was not changed"))

    print("* Checking the entered Microsoft application credentials before changing the dotenv file ...")
    authorize = _wizard_request_tokens if authorizer is None else authorizer
    try:
        tokens = asyncio.run(authorize(client_id, client_secret, input_func=input_func))
    except (EOFError, KeyboardInterrupt):
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="The Microsoft sign-in was cancelled and the dotenv file was not changed")) from None
    except RecoveryError:
        raise
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="auth", detail=f"The Microsoft sign-in did not complete: {exc}"), exc) from None
    if not tokens:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="No authorization code was entered, so the dotenv file was not changed"))

    try:
        update_dotenv_file(destination, {"MS_APP_CLIENT_ID": client_id, "MS_APP_CLIENT_SECRET": client_secret})
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="file.unwritable", detail=f"Cannot save the Microsoft application credentials to '{destination}': {exc}"), exc) from None
    tokens_path = Path(os.path.expanduser(MS_AUTH_TOKENS_FILE or DEFAULT_TOKENS_FILENAME))
    try:
        # The cache holds a refresh token, so it is private to the owner and never left half-written
        write_file_atomically(tokens_path, str(tokens), mode=0o600)
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="file.unwritable", detail=f"Cannot save the Xbox tokens to '{tokens_path}': {exc}"), exc) from None

    print("* Microsoft accepted the sign-in")
    print(f"* Updated '{destination}', readable only by you")
    print(f"* Saved the Xbox tokens to '{tokens_path}', readable only by you")
    print_secret_next_steps(destination, config_path, xbox_gamertag)
    return str(destination)


# Accepts a complete webhook URL or a bare ntfy.sh topic name when ntfy is the selected provider
def normalize_webhook_destination(value):
    candidate = str(value or "").strip()
    return normalize_ntfy_topic_url(candidate) if normalized_webhook_provider() == "ntfy" or "://" not in candidate else candidate


# Checks one entered webhook destination without contacting the service, because the only confirmation a
# webhook service offers is a delivered notification and setting a URL must not publish one
def validate_webhook_destination(value, provider=None):
    candidate = normalize_webhook_destination(value)
    if not candidate:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="No webhook URL was entered, so the dotenv file was not changed"))
    if not validate_webhook_url(candidate):
        raise RecoveryError(classify_recovery_error(context="webhook", detail="WEBHOOK_URL needs a complete HTTPS link, so the dotenv file was not changed"))
    detected = detect_webhook_provider(candidate)
    configured = normalized_webhook_provider(provider)
    if provider is not None and detected and configured != detected:
        raise RecoveryError(classify_recovery_error(context="webhook", detail="The entered URL does not match --webhook-provider. Correct the flag or enter a URL for that service"))
    return webhook_provider_display_name(detected or configured)


# Stores one webhook destination in the dotenv file, so the private URL never has to appear on a command line
def run_set_webhook_url(env_file=None, config_path=None, xbox_gamertag=None, interactive=None, input_func=None, getpass_func=None, provider=None):
    return run_set_secret("WEBHOOK_URL", "--set-webhook-url", "webhook URL", WEBHOOK_GUIDE_URL, "* Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL\n* ntfy: the complete topic URL, or just the topic name when it is hosted on ntfy.sh", "Enter the webhook URL (input hidden): ", lambda value: validate_webhook_destination(value, provider), lambda provider: f"The entered value looks like a valid {provider} destination", env_file, config_path, xbox_gamertag, interactive, input_func, getpass_func, normalize_webhook_destination, ("Send a test webhook:", "--send-test-webhook"))


# Stores one SMTP password in the dotenv file after the mail server has actually accepted it
def run_set_smtp_password(env_file=None, config_path=None, xbox_gamertag=None, interactive=None, input_func=None, getpass_func=None):
    # Checked before the prompts, so nobody types a password only to be told the mail server was never configured
    settings_problem = mail_sign_in_settings_problem()
    if settings_problem is not None:
        raise RecoveryError(make_recovery_advice("smtp.invalid", f"The mail server settings are incomplete: {settings_problem[0]}", recovery_fix_with_guide(f"Correct it in the config file or run {render_command(['--setup'])}, then run: {render_command(['--set-smtp-password'])}", SMTP_GUIDE_URL), False))
    return run_set_secret("SMTP_PASSWORD", "--set-smtp-password", "SMTP password", SMTP_GUIDE_URL, f"* The password is checked by signing in to {SMTP_HOST} as {SMTP_USER}. Nothing is sent", "Enter the SMTP password (input hidden): ", smtp_sign_in, lambda user: f"The mail server accepted the password for {user}", env_file, config_path, xbox_gamertag, interactive, input_func, getpass_func, keep_entered_value, test_step=("Send a test email:", "--send-test-email"))


# Saves the last seen status atomically, so an interrupted write cannot strand a half-written status file
def save_last_status(status_file, status_ts, status):
    debug_print("Status file write", path=str(status_file), status=status, ts=status_ts)
    write_file_atomically(status_file, json.dumps([status_ts, status], indent=2) + "\n")


# Joins names the way a sentence does, so three of them do not read as "A and B and C"
def join_names(names):
    names = list(names)
    return "" if not names else str(names[0]) if len(names) == 1 else f"{', '.join(str(name) for name in names[:-1])} and {names[-1]}"


# Reports whether a setting holds a real value rather than being empty or one of the shipped placeholders
def secret_is_set(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("your_")


# Accepts a gamertag typed by hand or copied out of a profile link, rejecting the e-mail mistake
def normalize_xbox_target(value):
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        raise ValueError(f"Enter the {XBOX_TARGET_FORMS}")
    if "://" in text or text.startswith("www."):
        text = unquote(text.rstrip("/").rsplit("/", 1)[-1].split("?")[0].split("#")[0])
        text = text.strip()
    if "@" in text:
        raise ValueError(f"That looks like an e-mail address. Use the {XBOX_TARGET_FORMS}")
    # Modern gamertags carry a numeric suffix that is part of the name but not part of the length limit
    name, _, suffix = text.partition("#")
    if suffix and not (suffix.isdigit() and 1 <= len(suffix) <= 4):
        raise ValueError("The part after '#' in a gamertag is 1 to 4 digits")
    if not name.strip() or len(name) > 15 or any(character in name for character in "\\/:*?\"<>|"):
        raise ValueError("An Xbox gamertag is up to 15 characters and cannot contain \\ / : * ? \" < > |")
    return text


# Prints one labelled command in the shape the welcome screen and the next-steps blocks share
def print_labelled_command(label, command, suffix=""):
    print(label)
    print(f"    {colorize('section', command)}{colorize('info', suffix) if suffix else ''}\n")


# Prints the command that starts monitoring with the files this run checked, so a report read on its own
# ends with the next action rather than leaving the reader to assemble the command
def print_doctor_next_steps(xbox_gamertag=None, saved_target=None, doctor_exit=0):
    print("\n" + colorize("header", "Next steps") + "\n")
    label = "After Doctor passes, start monitoring:" if doctor_exit else "Start monitoring:"
    monitor_target = command_targets(xbox_gamertag, saved_target)[1]
    print_labelled_command(label, render_command([*([monitor_target] if monitor_target else [])]))
    # No trailing blank line: the command printer already left one and the report must not end on two
    print(colorize_links(f"Guide: {QUICK_START_GUIDE_URL}"))


# Parses a duration the way people type it, accepting bare seconds and s/m/h/d suffixes
def parse_duration_input(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip().casefold().replace(",", ".")
    if not text:
        return None
    units = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
             "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
             "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
             "d": 86400, "day": 86400, "days": 86400}
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]*)", text)
    # Anything the pattern did not consume is rejected, so "5x" or "abc" cannot read as a bare number
    if not matches or re.sub(r"(\d+(?:\.\d+)?)\s*([a-z]*)", "", text).strip():
        return None
    total = 0.0
    for amount, unit in matches:
        if unit and unit not in units:
            return None
        total += float(amount) * units.get(unit, 1)
    seconds = int(round(total))
    return seconds if seconds > 0 else None


# Applies the diagnostic flags given on the command line, before and again after the config file is read
def apply_diagnostic_cli_flags(args):
    global VERBOSE_MODE, DEBUG_MODE
    if getattr(args, "verbose_mode", None):
        VERBOSE_MODE = True
    if getattr(args, "debug_mode", None):
        DEBUG_MODE = True


# Applies every secret the environment or a loaded dotenv file provides, recording where each value came from.
# Environment variables are a documented alternative to a dotenv file, so they apply even when no file was loaded
def apply_environment_secrets():
    for secret in SECRET_KEYS:
        val = os.getenv(secret)
        if val is not None:
            globals()[secret] = val
            # A shipped placeholder is not a value, so it never counts as a source
            if secret_is_set(val):
                record_secret_source(secret, "environment" if secret in EXPORTED_SECRET_KEYS else "dotenv file")
            else:
                SECRET_SOURCES.pop(secret, None)


# Resolves LOCAL_TIMEZONE and the state doctor reports it with, returning advice when no zone could be determined
def resolve_local_timezone():
    global LOCAL_TIMEZONE, LOCAL_TIMEZONE_STATE

    LOCAL_TIMEZONE_STATE = "config"
    timezone_advice = None
    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        if get_localzone is not None:
            try:
                local_tz = get_localzone()
            except Exception as e:
                debug_print("Local timezone detection", outcome="failed", error=f"{type(e).__name__}: {e}")
        if local_tz and is_valid_timezone(str(local_tz)):
            LOCAL_TIMEZONE = str(local_tz)
            LOCAL_TIMEZONE_STATE = "auto"
        elif get_localzone is None:
            LOCAL_TIMEZONE_STATE = "auto_unavailable"
            verbose_print("Automatic time zone detection is unavailable because the optional tzlocal library is missing")
            timezone_advice = make_recovery_advice("dependency.missing", "The local timezone could not be detected", recovery_fix_with_guide(f"Install tzlocal with: {pip_install_command('tzlocal')} or set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, "LOCAL_TIMEZONE is Auto but tzlocal is unavailable")
        else:
            LOCAL_TIMEZONE_STATE = "auto_failed"
            timezone_advice = make_recovery_advice("config.invalid", "The local timezone could not be detected", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, "tzlocal did not return a supported timezone")
    elif not is_valid_timezone(LOCAL_TIMEZONE):
        LOCAL_TIMEZONE_STATE = "invalid"
        timezone_advice = make_recovery_advice("config.invalid", f"Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, f"Time zone: {LOCAL_TIMEZONE}")
    return timezone_advice


# Applies the webhook options that were actually typed, then reconciles the provider with the destination
def apply_webhook_cli_overrides(args, parser):
    global WEBHOOK_ENABLED, WEBHOOK_PROVIDER, WEBHOOK_URL, WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION, WEBHOOK_GAME_CHANGE_NOTIFICATION, WEBHOOK_STATUS_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION
    if args.webhook_provider is not None:
        WEBHOOK_PROVIDER = str(args.webhook_provider)
    if args.webhook_url is not None:
        if not validate_webhook_url(args.webhook_url):
            parser.error("--webhook-url needs a complete HTTPS link without embedded credentials")
        WEBHOOK_URL = str(args.webhook_url).strip()
        WEBHOOK_ENABLED = True
        record_secret_source("WEBHOOK_URL", "command line", WEBHOOK_URL)
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    # Naming one alert also switches the channel on, so a single flag is enough to try it out
    if args.webhook_active_inactive is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True
    if args.webhook_game_change is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_GAME_CHANGE_NOTIFICATION = True
    if args.webhook_status is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_STATUS_NOTIFICATION = True
    if args.webhook_errors is not None:
        WEBHOOK_ERROR_NOTIFICATION = args.webhook_errors
        if args.webhook_errors:
            WEBHOOK_ENABLED = True
    # A recognised URL describes its own service, so it corrects a provider the settings got wrong
    if args.webhook_provider is None:
        detected = detect_webhook_provider(WEBHOOK_URL)
        if detected and detected != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected
            # The built-in default is not a choice anyone made, so detection there is the documented behaviour
            # rather than a mismatch. Only a provider the configuration actually sets is worth warning about
            if "WEBHOOK_PROVIDER" in CONFIGURED_SETTING_NAMES:
                print(f"* Warning: Configured webhook provider did not match the URL. Using {webhook_provider_display_name(detected)}.")
            else:
                verbose_print(f"Webhook provider detected from the URL: {webhook_provider_display_name(detected)}")


# The categories that mean the saved credentials themselves stopped working, which no retry can repair
AUTH_RECOVERY_CODES = frozenset({"auth.credentials_invalid", "auth.token_expired", "auth.token_cache", "auth.authorization"})

# Failed checks in a row before a failure that can clear on its own is worth an alert. A short outage recovers
# well inside this, so only an outage the operator has to know about reaches them
# How long a failure the tool can retry away must last before it is alerted, a failure it cannot is alerted at once
ERROR_ALERT_AFTER_SECONDS = 300  # 5 minutes
# How long a channel that could not deliver an error alert waits before the next attempt, doubled on every further failure up to the cap
ERROR_ALERT_RETRY_SECONDS = 300  # 5 minutes
ERROR_ALERT_RETRY_MAX_SECONDS = 3600  # 1 hour


# Tracks the error alert per channel: what was delivered, and how long a channel that failed waits before the next attempt
class ErrorAlertState:
    # Starts with nothing delivered and no channel on hold
    def __init__(self) -> None:
        self.email_sent = False
        self.webhook_sent = False
        self.email_failures = 0
        self.webhook_failures = 0
        self.email_retry_at = 0
        self.webhook_retry_at = 0

    # Forgets the delivered alert and any hold, so the next failure earns each channel a new one
    def reset(self) -> None:
        self.__init__()

    # Tells whether a channel still owes the alert and its wait after a failed attempt, if any, has passed
    def pending(self, channel: str, enabled, now: int) -> bool:
        return bool(enabled) and not getattr(self, f"{channel}_sent") and now >= getattr(self, f"{channel}_retry_at")

    # Records one attempt, holding a channel that failed for a growing wait so a broken server is not dialled on every check
    def record(self, channel: str, attempted: bool, delivered: bool, now: int) -> None:
        if not attempted:
            return
        if delivered:
            setattr(self, f"{channel}_sent", True)
            setattr(self, f"{channel}_failures", 0)
            setattr(self, f"{channel}_retry_at", 0)
            return
        failures = getattr(self, f"{channel}_failures") + 1
        delay = min(ERROR_ALERT_RETRY_SECONDS * 2 ** (failures - 1), ERROR_ALERT_RETRY_MAX_SECONDS)
        setattr(self, f"{channel}_failures", failures)
        setattr(self, f"{channel}_retry_at", now + delay)
        print(f"* The {channel} alert is on hold for {display_time(delay)} after {failures} {'attempt' if failures == 1 else 'attempts'}, then tried again")


# Stable recovery categories. Every code here is produced somewhere in this file and nothing else is accepted
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "config.insecure", "dependency.missing", "secret.missing",
    "auth.credentials_invalid", "auth.token_expired", "auth.token_cache", "auth.authorization", "auth.oauth_code",
    "network.unavailable", "network.timeout",
    "xbox.malformed_response", "xbox.rate_limited", "xbox.unavailable", "resource.exhausted",
    "target.missing", "target.not_found", "target.not_visible",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection",
    "file.exists", "file.unreadable", "file.unwritable", "secret.entry", "unknown",
})


# Carries one recovery category together with guidance that is safe to print
@dataclass(frozen=True)
class RecoveryAdvice:
    code: str
    summary: str
    fix: str
    retryable: bool
    detail: str = ""


# Carries recovery advice across an exception boundary with the original cause attached
class RecoveryError(Exception):
    # Stores the advice and links the original cause so a traceback still points at the real failure
    def __init__(self, advice, cause=None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# A value shorter than this is an ordinary word at least as often as it is a secret, so replacing it wherever
# it appears would corrupt the text it was added to protect. The assignment and header patterns below still
# redact a short secret everywhere an error can realistically expose one
MIN_REDACTABLE_SECRET_LENGTH = 12


# Returns every redactable secret value currently known to the process, longest first so overlaps redact fully
def known_secret_values():
    values = [value for key in SECRET_KEYS for value in (globals().get(key),) if isinstance(value, str) and secret_is_set(value) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH]
    return sorted(set(values) | set(_DELIVERY_SECRET_VALUES.get()), key=len, reverse=True)


# Redacts credentials and secret-bearing assignments from arbitrary text before it is shown, logged or emailed
def sanitize_error_text(value):
    text = str(value or "")
    for secret in known_secret_values():
        text = text.replace(secret, "<redacted>")
    patterns = (
        (r"(?m)(\b(?:MS_APP_CLIENT_ID|MS_APP_CLIENT_SECRET|SMTP_PASSWORD|WEBHOOK_URL|NTFY_ACCESS_TOKEN)\b\s*=\s*).*$", r"\1<redacted>"),
        # A webhook URL is itself the credential, so the whole link is replaced wherever it appears
        (r"(?i)https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^\s'\"<>]+", "<redacted>"),
        # An XBL3.0 header is 'XBL3.0 x=<userhash>;<token>', so stopping at the semicolon would leave the token
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?(?:bearer|basic|xbl3\.0)\s+)[^\s,'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:client_secret|client_id|access_token|refresh_token|id_token|smtp_password|webhook_url|ntfy_access_token)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)([?&](?:access_token|refresh_token|client_secret|code)=)[^&#\s]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Builds one piece of advice, rejecting any code outside the taxonomy and redacting every field
def make_recovery_advice(code, summary, fix, retryable, detail=""):
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), retryable, sanitize_error_text(detail))


# Appends the documentation link that matches the fix, on its own line
def recovery_fix_with_guide(fix, guide_url):
    return f"{fix}\nGuide: {guide_url}"


# Returns the advice a cancelled secret entry reports, worded the same way by every one-shot secret command
def secret_entry_cancelled_advice(subject, flag, guide_url, plural=False):
    return make_recovery_advice("secret.entry", f"{subject[:1].upper()}{subject[1:]} setup was cancelled and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again when you have the {'values' if plural else 'value'} ready", guide_url), False)


# Returns the advice a declined secret replacement reports, worded the same way by every one-shot secret command
def secret_replacement_declined_advice(subject, flag, guide_url, plural=False):
    kept = "were left as they are" if plural else "was left as it is"
    return make_recovery_advice("secret.entry", f"The saved {subject} {kept} and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again and answer y to replace the saved {'values' if plural else 'value'}", guide_url), False)


# Renders one piece of advice, adding the fix paragraph and the technical detail only where they help
def render_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error"):
    lines = [f"* {label}: {advice.summary}" + (f" ({retry_note})" if retry_note else "")]
    if with_fix:
        lines.append(f"To fix: {advice.fix}")
        # A detail that only repeats the summary spends a line saying nothing
        if (DEBUG_MODE if debug is None else debug) and advice.detail and advice.detail != advice.summary:
            lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Builds the subject for one recovery notification, naming what failed rather than the category it fell into
def recovery_email_subject(advice, xbox_gamertag):
    return f"{advice.summary} (Xbox user: {xbox_gamertag})"


# Builds the body for one recovery notification, repeating the fix the operator sees on screen
def recovery_email_body(advice, error_streak=0):
    lines = [advice.summary, "", f"To fix: {advice.fix}"]
    if error_streak > 1:
        lines.extend(["", f"Failed checks in a row: {error_streak}"])
    if advice.detail:
        lines.extend(["", f"Technical detail: {advice.detail}"])
    return "\n".join(lines) + get_cur_ts("\n\nTimestamp: ")


# Prints one built advice through the shared recovery block and returns it
def print_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error", tracker=None):
    print(render_recovery_advice(advice, debug, retry_note, with_fix and (tracker is None or tracker.should_render(advice)), label))
    return advice


# Classifies one failure and renders it through the shared recovery block
def render_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error"):
    return render_recovery_advice(classify_recovery_error(error, context, detail), debug, retry_note, with_fix, label)


# Classifies one failure, prints it through the shared recovery block and returns its stable advice
def print_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error", tracker=None):
    return print_recovery_advice(classify_recovery_error(error, context, detail), debug, retry_note, with_fix, label, tracker)


# Reports a step that failed and left its output degraded, naming the step in front of the classified failure
def report_degraded_error(subject, error, label="Error"):
    advice = classify_recovery_error(error)
    print_recovery_advice(make_recovery_advice(advice.code, f"{subject}: {advice.summary}", advice.fix, advice.retryable, advice.detail), label=label)
    return advice


# Decides how a lasting failure is reported: in full when it is new, then on the liveness cadence while it lasts
# How long a reported failure may go on before the run reminds about it, whatever the liveness banner is set to
OUTAGE_REMINDER_SECONDS = 3600  # 1 hour


# Returns the family a failure code belongs to, so the DNS and timeout failures of one internet outage count as one
def outage_family(code):
    return "network" if str(code or "").startswith("network.") else str(code or "")


class OutageReporter:
    # Starts with no failure recorded and reports a new retryable failure once confirm_checks checks in a row failed
    def __init__(self, confirm_checks=1):
        self.confirm_checks = max(1, confirm_checks)
        self.code = None
        self.since = 0
        self.reported_at = 0
        self.failures = 0
        self.reported = False

    # Records one failed check and returns "full" when the failure is to be reported in full, "changed" when a
    # reported outage moved to another failure family, "reminder" once OUTAGE_REMINDER_SECONDS passed since the
    # last report or "" while nothing new is to be said
    def failed(self, advice):
        now = int(time.time())
        if not self.code:
            self.since = now
        self.failures += 1
        changed = self.code is not None and outage_family(advice.code) != outage_family(self.code)
        self.code = advice.code
        if not self.reported:
            # A failure the tool cannot retry away is reported at once, one it can waits for the next check to confirm it
            if advice.retryable and self.failures < self.confirm_checks:
                return ""
            self.reported = True
            self.reported_at = now
            return "full"
        if changed:
            self.reported_at = now
            return "changed" if advice.retryable else "full"
        # Timed rather than counted, because a failing run usually retries on a different interval than a healthy one
        if now - self.reported_at >= OUTAGE_REMINDER_SECONDS:
            self.reported_at = now
            return "reminder"
        return ""

    # Clears the failure after a successful check and returns how long it lasted, or None when nothing was reported
    def recovered(self):
        lasted = int(time.time()) - self.since if self.code and self.reported else None
        self.code = None
        self.since = 0
        self.reported_at = 0
        self.failures = 0
        self.reported = False
        return lasted


# Reports that nothing changed, so a quiet run still says it is alive on the liveness cadence
def print_liveness_banner(message):
    print(f"* {sanitize_error_text(message)}")
    print_cur_ts("Liveness check, timestamp:\t")


# Reminds about a lasting failure once an hour, so a broken run still says it is alive without repeating itself
def print_outage_liveness(target, advice, since, failures=0):
    count = f", {failures} failed {'check' if failures == 1 else 'checks'}" if failures else ""
    print(f"* Monitoring degraded for {target}. {advice.summary} since {get_date_from_ts(since)}{count}")
    print_cur_ts("Liveness check, timestamp:\t")


# Notes that a reported outage now fails differently, in one line rather than a second full report
def print_outage_change(target, advice):
    print(f"* Monitoring failure changed for {target}. {advice.summary}")


# Reports that a failure cleared, since a throttled failure no longer stops printing when it is over
def print_outage_recovery(target, lasted):
    print(f"* Monitoring recovered for {target} after {display_time(max(1, lasted))}")
    print_cur_ts("Timestamp:\t\t\t")


# Suppresses a repeated fix paragraph until the failure category changes or a check succeeds
class RecoveryHintTracker:
    # Starts with no category recorded, so the first failure is always reported in full
    def __init__(self):
        self.last_code = None

    # Reports whether this category is new and therefore worth printing the fix for again
    def should_render(self, advice):
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears the suppression after a successful check
    def reset(self):
        self.last_code = None


# Yields the exception and each cause or context up to max_depth, to walk an exception chain
def iter_exc_chain(error, max_depth=8):
    current = error
    for _ in range(max_depth):
        if current is None:
            return
        yield current
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)


# Reports whether this process hit the local file descriptor limit rather than a remote failure
def is_too_many_open_files(error):
    for current in iter_exc_chain(error):
        if isinstance(current, OSError) and getattr(current, "errno", None) == 24:
            return True
        # A server controls the wording of its own reply, so its text never proves a local limit here
        if getattr(current, "response", None) is not None:
            continue
        message = str(current).lower()
        if "too many open files" in message or re.search(r"\berrno 24\b", message):
            return True
    return False


# Returns the HTTP status carried by any exception in the chain or None when the failure was not a response
def http_status_from(error):
    for current in iter_exc_chain(error):
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
    return None


# Returns the fix for credentials the Microsoft sign-in endpoint would not accept
def credentials_recovery_fix():
    return f"Check MS_APP_CLIENT_ID and MS_APP_CLIENT_SECRET against the app registration in the Microsoft Entra admin center, then rerun: {render_command(['<xbox_gamertag>'])}"


# Returns the fix for a refresh token the sign-in endpoint no longer accepts
def token_recovery_fix():
    return f"Delete the token cache file and authorize again by running: {render_command(['<xbox_gamertag>'])}"


# Returns the next step for a failure no rule recognized, since a run already printing the technical cause cannot be told to re-run for it
def unknown_failure_fix():
    return "Check the technical detail below, then open an issue with this output if the problem continues" if DEBUG_MODE else "Rerun with --debug and check the technical detail it prints. If the problem continues, open an issue with that output"


# Tells whether a status code appears in a message as a whole number, so 4290 or a path segment such as /429 does not read as 429
def mentions_status_code(code, message):
    return re.search(rf"(?<![\w/]){code}(?!\w)", message) is not None


# Stops optional work when a local file descriptor limit has been reached
def stop_if_resource_exhausted(error):
    if is_too_many_open_files(error):
        print_recovery_error(error)
        raise SystemExit(1)


# Classifies a failure by context, exception type and message into one stable recovery category
def classify_recovery_error(error=None, context="runtime", detail=""):
    if isinstance(error, RecoveryError):
        return error.advice

    safe_detail = sanitize_error_text(detail or error or "")
    # Both are matched, since a caller that adds context would otherwise hide the error text the rules read
    message = " ".join(part for part in (str(detail or ""), str(error or "")) if part).lower()
    monitoring = context == "monitor"
    status = http_status_from(error)

    if error is not None and is_too_many_open_files(error):
        return make_recovery_advice("resource.exhausted", "This process ran out of file descriptors, which is a local limit and not an Xbox Live problem", recovery_fix_with_guide("Raise the file descriptor limit, for example with 'ulimit -n 4096', or set LimitNOFILE= if you run under systemd, then restart the tool", DIAGNOSTICS_GUIDE_URL), False, safe_detail)

    if any(isinstance(item, AuthenticationException) for item in iter_exc_chain(error)):
        return make_recovery_advice("auth.authorization", "Xbox Live rejected authorization for this account", recovery_fix_with_guide("Check the Microsoft application credentials and Xbox account permissions, including child-account restrictions, then run --doctor again", CREDENTIALS_GUIDE_URL), False, safe_detail)

    if context == "config.missing":
        return make_recovery_advice("config.missing", safe_detail or "The configuration file was not found", recovery_fix_with_guide(f"Check the --config-file path, or create one with: {render_command(['--generate-config', 'xbox_monitor.conf'], include_paths=False)}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "config.invalid":
        return make_recovery_advice("config.invalid", safe_detail or "The configuration file could not be loaded", recovery_fix_with_guide(f"Config files are read as data. Only documented SETTING = value lines with plain literal values are accepted. Correct the reported line, or write a fresh template to a different path with: {render_command(['--generate-config', '<new-file>'], include_paths=False)}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "secret.missing":
        return make_recovery_advice("secret.missing", safe_detail or "A required credential is missing", recovery_fix_with_guide(f"Register an application in the Microsoft Entra admin center, then put its client ID and secret in MS_APP_CLIENT_ID and MS_APP_CLIENT_SECRET in your dotenv file, or pass them directly: {render_command(['<xbox_gamertag>', '-u', '<client_id>', '-w', '<client_secret>'])}", CREDENTIALS_GUIDE_URL), False, safe_detail)

    if context == "target.missing":
        return make_recovery_advice("target.missing", safe_detail or "No Xbox gamertag was provided", recovery_fix_with_guide(f"Pass the account to watch: {render_command(['<xbox_gamertag>'])}. Use the {XBOX_TARGET_FORMS}", QUICK_START_GUIDE_URL), False, safe_detail)

    if context == "secret.entry":
        return make_recovery_advice("secret.entry", safe_detail or "The value was not entered, so nothing was written", recovery_fix_with_guide("Run the command again from an interactive terminal and enter the value when prompted", SECRETS_GUIDE_URL), False, safe_detail)

    if context == "file.exists":
        return make_recovery_advice("file.exists", safe_detail or "The destination file already exists", recovery_fix_with_guide("Re-run with --force to replace it after a timestamped backup, or write to a different path", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "file.unreadable":
        return make_recovery_advice("file.unreadable", safe_detail or "A file the tool needs could not be read", recovery_fix_with_guide("Check that the path exists and that this user can read it, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "file.unwritable":
        # The wizard reaches this either because a destination was switched off or because the path cannot be written
        if "nowhere to write the secrets" in message:
            return make_recovery_advice("file.unwritable", safe_detail or "--setup has nowhere to write the secrets", recovery_fix_with_guide("Replace '--env-file none' with a writable path, or drop the flag to write .env in the current directory", SECRETS_GUIDE_URL), False, safe_detail)
        if "nowhere to write the configuration" in message:
            return make_recovery_advice("file.unwritable", safe_detail or "--setup has nowhere to write the configuration", recovery_fix_with_guide(f"Replace '--config-file none' with a writable path, or drop the flag to write {DEFAULT_CONFIG_FILENAME} in the current directory", CONFIG_GUIDE_URL), False, safe_detail)
        return make_recovery_advice("file.unwritable", safe_detail or "A file the tool needs could not be written", recovery_fix_with_guide("Check that the directory exists, that this user can write to it and that there is free space, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "connectivity":
        # Classified from the error, because the detail names the endpoint rather than the failure
        cause = str(error or "").lower()
        if "timed out" in cause or "timeout" in cause:
            return make_recovery_advice("network.timeout", "The connectivity endpoint did not answer in time", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True, safe_detail)
        return make_recovery_advice("network.unavailable", "The connectivity endpoint could not be reached", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True, safe_detail)

    if context == "smtp.settings":
        return make_recovery_advice("smtp.invalid", f"The SMTP settings are incorrect: {safe_detail}" if safe_detail else "The SMTP settings are incorrect", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL and RECEIVER_EMAIL then run: {render_command(['--send-test-email'])}", SMTP_GUIDE_URL), False, safe_detail)

    if context == "webhook":
        if mentions_status_code("429", message) or "rate limit" in message:
            return make_recovery_advice("webhook.rate_limited", "The webhook service is rate limiting deliveries", recovery_fix_with_guide(f"Enable fewer webhook alert types, or wait until the service accepts deliveries again, then run: {render_command(['--send-test-webhook'])}", WEBHOOK_GUIDE_URL), True, safe_detail)
        # Every configuration problem this tool reports names the setting that has to change, which the
        # text of a rejection from Discord or ntfy never does
        if "webhook_" in message or "ntfy_access_token" in message:
            return make_recovery_advice("webhook.invalid", safe_detail or "The webhook settings cannot be used", recovery_fix_with_guide(f"Correct the reported setting, then run: {render_command(['--send-test-webhook'])}", WEBHOOK_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("could not be reached", "connection", "timed out", "timeout")):
            return make_recovery_advice("webhook.connection", "The webhook service could not be reached", recovery_fix_with_guide("Check your internet connection, DNS and firewall, then try again", WEBHOOK_GUIDE_URL), True, safe_detail)
        return make_recovery_advice("webhook.rejected", safe_detail or "The webhook service refused the delivery", recovery_fix_with_guide(f"Confirm the webhook still exists and that the saved URL is current, then run: {render_command(['--send-test-webhook'])}", WEBHOOK_GUIDE_URL), False, safe_detail)

    if context.startswith("smtp"):
        for current in iter_exc_chain(error):
            if isinstance(current, smtplib.SMTPAuthenticationError):
                return make_recovery_advice("smtp.authentication", "The SMTP server rejected the login", recovery_fix_with_guide(f"Check SMTP_USER and SMTP_PASSWORD. Providers such as Gmail need an app password rather than the account password. Then run: {render_command(['--send-test-email'])}", SMTP_GUIDE_URL), False, safe_detail)
            if isinstance(current, (smtplib.SMTPException, ssl.SSLError, OSError)):
                return make_recovery_advice("smtp.connection", "The SMTP server could not be reached", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT and SMTP_SSL, and that the port is not blocked. Then run: {render_command(['--send-test-email'])}", SMTP_GUIDE_URL), True, safe_detail)

    if context == "auth.oauth_code":
        return make_recovery_advice("auth.oauth_code", safe_detail or "The authorization code was not accepted", recovery_fix_with_guide("Open the authorization URL again and copy the whole value after '?code=' from the address bar, without the trailing '&state=' part", CREDENTIALS_GUIDE_URL), False, safe_detail)

    if context == "auth.token_cache":
        return make_recovery_advice("auth.token_cache", safe_detail or "The saved Xbox tokens could not be read", recovery_fix_with_guide(f"Delete the token cache file named by MS_AUTH_TOKENS_FILE and authorize again by running: {render_command(['<xbox_gamertag>'])}", CREDENTIALS_GUIDE_URL), False, safe_detail)

    if status == 429 or "too many requests" in message or "rate limit" in message:
        return make_recovery_advice("xbox.rate_limited", "Xbox Live is rate limiting this application", recovery_fix_with_guide("Raise XBOX_CHECK_INTERVAL and XBOX_ACTIVE_CHECK_INTERVAL, or run fewer instances against the same application, then restart", INTERVALS_GUIDE_URL), True, safe_detail)

    if status in (401, 403) or "invalid_grant" in message or "unauthorized" in message:
        if context in ("auth", "monitor") or "invalid_grant" in message:
            # A grant that expired is fixed by authorizing again, while a rejected application is fixed in Entra
            expired = monitoring or "invalid_grant" in message
            code = "auth.token_expired" if expired else "auth.credentials_invalid"
            return make_recovery_advice(code, "The Microsoft sign-in endpoint rejected the saved credentials", recovery_fix_with_guide(token_recovery_fix() if expired else credentials_recovery_fix(), CREDENTIALS_GUIDE_URL), False, safe_detail)
        return make_recovery_advice("target.not_visible", "That Xbox profile does not share its activity with this application", recovery_fix_with_guide("Ask the monitored user to allow others to see their online status and activity in the Xbox privacy settings", PRIVACY_GUIDE_URL), False, safe_detail)

    if status == 404 or "not found" in message:
        return make_recovery_advice("target.not_found", "Xbox Live does not know that gamertag", recovery_fix_with_guide(f"Check the spelling. Use the {XBOX_TARGET_FORMS}", QUICK_START_GUIDE_URL), False, safe_detail)

    if status is not None and status >= 500:
        return make_recovery_advice("xbox.unavailable", "Xbox Live returned a server-side error", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check the Xbox Live service status", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    for current in iter_exc_chain(error):
        if isinstance(current, (httpx.TimeoutException, TimeoutError)):
            return make_recovery_advice("network.timeout", "Xbox Live took too long to answer", recovery_fix_with_guide(f"Nothing to do in most cases, the tool retries on its own. If it continues, raise XBOX_API_TIMEOUT, currently {XBOX_API_TIMEOUT} seconds, and check your connection and any proxy", DIAGNOSTICS_GUIDE_URL), True, safe_detail)
        if isinstance(current, (httpx.TransportError, ConnectionError)):
            return make_recovery_advice("network.unavailable", "Xbox Live could not be reached", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check your internet connection, DNS and firewall", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if "timed out" in message or "timeout" in message:
        return make_recovery_advice("network.timeout", "Xbox Live took too long to answer", recovery_fix_with_guide(f"Nothing to do in most cases, the tool retries on its own. If it continues, raise XBOX_API_TIMEOUT, currently {XBOX_API_TIMEOUT} seconds, and check your connection and any proxy", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if "connection reset by peer" in message or "connection aborted" in message or "temporarily unavailable" in message or "name or service not known" in message:
        return make_recovery_advice("network.unavailable", "Xbox Live could not be reached", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check your internet connection, DNS and firewall", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    for current in iter_exc_chain(error):
        if isinstance(current, (AttributeError, TypeError, KeyError, IndexError)):
            return make_recovery_advice("xbox.malformed_response", "Xbox Live returned a response in an unexpected shape", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, upgrade python-xbox and rerun with --debug", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    return make_recovery_advice("unknown", "Something unexpected went wrong", recovery_fix_with_guide(unknown_failure_fix(), DIAGNOSTICS_GUIDE_URL), True, safe_detail)


# Returns the TLS context every connection uses, unverified while VERIFY_SSL is off. One builder covers the
# Xbox client and the SMTP handshake alike, so a source sweep can pin that nothing else makes its own
def tls_context():
    context = ssl.create_default_context()
    if not VERIFY_SSL:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


# Returns the file the tool saves the last seen status to, so a restart resumes from it
def resolve_status_file(xbox_gamertag):
    if XBOX_STATUS_FILE:
        return os.path.expanduser(XBOX_STATUS_FILE)
    return default_status_file(xbox_gamertag)


# Returns the status file name a target gets when no path is configured
def default_status_file(xbox_gamertag):
    return f"xbox_{xbox_gamertag}_last_status.json"


# Returns the log file path for one monitored user, without creating anything
def resolve_log_path(xbox_gamertag):
    log_path = Path(os.path.expanduser(XBOX_LOGFILE))
    if log_path.suffix == "":
        named = f"{log_path.name}_{xbox_gamertag}.log"
        log_path = log_path.parent / named if log_path.parent != Path('.') else Path(named)
    return log_path


# Reports whether a path could be written, without creating anything, so the doctor leaves no files behind
def path_is_writable(path):
    target = Path(os.path.expanduser(str(path)))
    if target.exists():
        return target.is_file() and os.access(target, os.W_OK)
    parent = target.parent if str(target.parent) else Path(".")
    return parent.is_dir() and os.access(parent, os.W_OK)


# Returns a compact dependency installation hint for the active platform
def pip_install_command(requirement):
    return " ".join(quote_command_argument(part) for part in (("python" if platform.system() == "Windows" else "python3"), "-m", "pip", "install", requirement))


# Returns advice for a missing optional library with a compact installation hint
def missing_dependency_advice(package, effect, alternative=""):
    fix = f"Install it with: {pip_install_command(package)}"
    if alternative:
        fix = f"{fix}. {alternative}"
    return make_recovery_advice("dependency.missing", f"{effect} because the optional '{package}' library is missing", recovery_fix_with_guide(fix, INSTALLATION_GUIDE_URL), False)


# The ASCII startup banner, kept to plain ASCII so it renders on every console including Windows
STARTUP_BANNER = r"""
 .---------------.   __  __ ____    ___  __  __
|       (Y)      |   \ \/ /| __ )  / _ \ \ \/ /
|    (X)   (B)   |    \  / |  _ \ | | | | \  /
|       (A)      |    /  \ | |_) || |_| | /  \
|      o   o     |   /_/\_\|____/  \___/ /_/\_\
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


# Prints the ASCII startup banner with its separately aligned version
def print_startup_banner():
    print("\n".join(colorize("header", line) if line else line for line in STARTUP_BANNER.splitlines()))
    print(colorize("info", f"{'':21}v{VERSION}") + "\n")


# Describes a secret in diagnostic output without revealing any part of it. A password the user chose reports
# presence only: its length is a real disclosure in output that ends up pasted into bug reports
def secret_fingerprint(value, key=None):
    fields = secret_fields(value, key)
    return f"{fields['value']}, {fields['chars']} chars" if fields["chars"] else fields["value"]


# Returns the diagnostic fields describing one secret, keeping the length out of the value so a line still splits on ", "
def secret_fields(value, key=None):
    return {"value": "set" if secret_is_set(value) else "not set", "chars": len(str(value).strip()) if key in FIXED_LENGTH_SECRET_KEYS and secret_is_set(value) else None}


# Records where one secret resolved from, so a later layer replaces the earlier answer instead of adding to it
def record_secret_source(name, source, value=None):
    if source == "command line" and DOTENV_RELOAD_STATE:
        DOTENV_RELOAD_STATE["base"][name] = globals().get(name) if value is None else value
        DOTENV_RELOAD_STATE.setdefault("base_sources", {})[name] = source
    if source not in SECRET_SOURCE_ORDER:
        raise ValueError(f"Unsupported secret source: {source}")
    # A placeholder is not a value, so it earns neither a source nor a row
    if not secret_is_set(globals().get(name) if value is None else value):
        SECRET_SOURCES.pop(name, None)
        return
    SECRET_SOURCES[name] = source


# Renders one diagnostic line as an operation followed by comma-separated key=value fields, dropping unset ones
def format_diagnostic_line(operation, fields):
    rendered = ", ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    return f"{operation}: {rendered}" if rendered else str(operation)


# Prints a technical diagnostic line, shown only when debug mode is on
# Debug output exists to be pasted into a public bug report, so it is redacted here rather than at every call site
# The parameter is named _operation because tools in this family wrap calls that legitimately have an
# operation field and a caller passing operation= would collide with the positional
def debug_print(_operation, **fields):
    global STDOUT_AT_START_OF_LINE
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "" if STDOUT_AT_START_OF_LINE else "\n"
        message = format_diagnostic_line(_operation, fields)
        print(f"{prefix}[DEBUG {timestamp}] {sanitize_error_text(message)}")
        STDOUT_AT_START_OF_LINE = True


# Prints a rare operational event, shown only when verbose mode is on
def verbose_print(message):
    global STDOUT_AT_START_OF_LINE
    if VERBOSE_MODE:
        prefix = "" if STDOUT_AT_START_OF_LINE else "\n"
        print(f"{prefix}* {sanitize_error_text(message)}")
        STDOUT_AT_START_OF_LINE = True


# Prints one delivery confirmation in verbose mode unless DELIVERY_CONFIRMATIONS turns them off
def verbose_delivery_print(message):
    if DELIVERY_CONFIRMATIONS:
        verbose_print(message)


# Prints verbose-only notices as one block, so a standalone line is not left without the timestamp trailer
def verbose_notice(*messages):
    if not VERBOSE_MODE or not messages:
        return
    for message in messages:
        verbose_print(message)
    # Before monitoring starts the notice belongs to the startup screen, which the monitoring header closes
    if MONITORING_ACTIVE:
        print_cur_ts("Timestamp:\t\t\t")


# Marks the point where output stops being the startup screen, so later notices close their own block
def mark_monitoring_started():
    global MONITORING_ACTIVE
    MONITORING_ACTIVE = True


# Returns a printable description of an exception, including its type since some network errors carry an empty message
def format_exception(e):
    msg = str(e).strip()
    return f"{type(e).__name__}: {msg}" if msg else type(e).__name__


# Creates the Xbox HTTP session with an explicit timeout, as the library default of 5 seconds is too aggressive
def create_signed_session():
    session = SignedSession(ssl_context=tls_context())
    session.timeout = httpx.Timeout(float(XBOX_API_TIMEOUT))
    return session


# Reports whether an exception is a transient network or server-side failure that is worth retrying
def is_transient_auth_error(e):
    if isinstance(e, HTTPStatusError):
        return e.response.status_code == 429 or e.response.status_code >= 500
    return isinstance(e, httpx.TransportError)


# Refreshes all tokens, retrying transient network and server-side failures with exponential backoff
async def refresh_tokens_with_retry(auth_mgr):
    global STDOUT_AT_START_OF_LINE
    delay = TOKEN_REFRESH_RETRY_DELAY
    for attempt in range(1, TOKEN_REFRESH_RETRIES + 1):
        try:
            await auth_mgr.refresh_tokens()
            return
        except Exception as e:
            if attempt >= TOKEN_REFRESH_RETRIES or not is_transient_auth_error(e):
                raise
            prefix = "" if STDOUT_AT_START_OF_LINE else "\n"
            print(f"{prefix}* Token refresh attempt {attempt} of {TOKEN_REFRESH_RETRIES} failed ({format_exception(e)}), retrying in {display_time(delay)}")
            STDOUT_AT_START_OF_LINE = True
            debug_print("Token refresh attempt", attempt=f"{attempt}/{TOKEN_REFRESH_RETRIES}", outcome="failed", error=f"{type(e).__name__}: {e}", retry_in=display_time(delay))
            await asyncio.sleep(delay)
            delay *= 2


# Starts interactive OAuth flow and stores the new OAuth token on the auth manager
async def oauth_interactive_auth(auth_mgr):
    print("\nAuthorizing via OAuth ...")
    url = auth_mgr.generate_authorization_url()
    print(f"\nOpen this URL in your web browser to authorize:\n{url}")
    authorization_code = str(read_interactively(input, "\nEnter authorization code (part after '?code=' in callback URL): ")).strip()
    if not authorization_code:
        raise ValueError("Authorization code cannot be empty")
    auth_mgr.oauth = await auth_mgr.request_oauth_token(authorization_code)


# Loads cached OAuth tokens, refreshes them and falls back to interactive re-authentication when needed
async def authenticate_and_refresh_tokens(auth_mgr):
    token_file_loaded = False
    try:
        debug_print("Token cache read", path=MS_AUTH_TOKENS_FILE)
        with open(MS_AUTH_TOKENS_FILE) as f:
            tokens = f.read()
        auth_mgr.oauth = OAuth2TokenResponse.model_validate_json(tokens)
        token_file_loaded = True
        debug_print("Token cache read", path=MS_AUTH_TOKENS_FILE, outcome="OK")
    except FileNotFoundError:
        print(f"\n* No saved Xbox tokens at '{MS_AUTH_TOKENS_FILE}' yet, so this run will ask you to authorize once")
    except Exception as e:
        print()
        print_recovery_error(e, context="auth.token_cache", detail=f"The Xbox token cache '{MS_AUTH_TOKENS_FILE}' could not be read: {e}", label="Warning")

    if not token_file_loaded:
        await oauth_interactive_auth(auth_mgr)

    try:
        debug_print("Token refresh")
        await refresh_tokens_with_retry(auth_mgr)
        debug_print("Token refresh", outcome="OK")
    except HTTPStatusError as e:
        # Temporary server-side errors are not a credential problem, so do not force interactive re-authentication
        if is_transient_auth_error(e):
            raise
        print()
        print_recovery_error(e, context="auth", detail=f"Refreshing the saved Xbox tokens failed: {format_exception(e)}", label="Warning")
        print("* Re-authorization is required")
        await oauth_interactive_auth(auth_mgr)
        debug_print("Token refresh after re-authorization")
        await refresh_tokens_with_retry(auth_mgr)
        debug_print("Token refresh after re-authorization", outcome="OK")

    # The cache holds a refresh token, so it is private to the owner and never left half-written
    write_file_atomically(MS_AUTH_TOKENS_FILE, auth_mgr.oauth.model_dump_json(), mode=0o600)


# Returns a debug-friendly timestamp representation, prevents "Unix epoch" confusion when ts is 0/missing
def get_debug_date_from_ts(ts):
    if isinstance(ts, (int, float)) and ts <= 0:
        return "N/A (missing/zero)"
    return get_date_from_ts(ts)


# Converts absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if isinstance(timestamp1, str):
        try:
            timestamp1 = isoparse(timestamp1)
        except Exception as e:
            debug_print("Timestamp parse", field="timestamp1", outcome="failed", error=f"{type(e).__name__}: {e}")
            return ""

    if isinstance(timestamp1, int):
        dt1 = datetime.fromtimestamp(int(ts1), tz=timezone.utc)
    elif isinstance(timestamp1, float):
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1, tz=timezone.utc)
    elif isinstance(timestamp1, datetime):
        dt1 = timestamp1
        if dt1.tzinfo is None:
            dt1 = pytz.utc.localize(dt1)
        else:
            dt1 = dt1.astimezone(pytz.utc)
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if isinstance(timestamp2, str):
        try:
            timestamp2 = isoparse(timestamp2)
        except Exception as e:
            debug_print("Timestamp parse", field="timestamp2", outcome="failed", error=f"{type(e).__name__}: {e}")
            return ""

    if isinstance(timestamp2, int):
        dt2 = datetime.fromtimestamp(int(ts2), tz=timezone.utc)
    elif isinstance(timestamp2, float):
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2, tz=timezone.utc)
    elif isinstance(timestamp2, datetime):
        dt2 = timestamp2
        if dt2.tzinfo is None:
            dt2 = pytz.utc.localize(dt2)
        else:
            dt2 = dt2.astimezone(pytz.utc)
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        days_total = date_diff.days

        if show_weeks:
            weeks = days_total // 7
            days = days_total % 7
        else:
            weeks = 0
            days = days_total

        hours = date_diff.hours if show_hours or ts_diff <= 86400 else 0
        minutes = date_diff.minutes if show_minutes or ts_diff <= 3600 else 0
        seconds = date_diff.seconds if show_seconds or ts_diff <= 60 else 0

        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")

        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Closes an SMTP session without changing the result of an accepted or failed message
def smtp_quit_quietly(smtp_object):
    if smtp_object is None:
        return
    try:
        smtp_object.quit()
    except Exception as quit_error:
        debug_print("SMTP quit", outcome="failed", error=f"{type(quit_error).__name__}: {quit_error}")
        try:
            smtp_object.close()
        except Exception as close_error:
            debug_print("SMTP close", outcome="failed", error=f"{type(close_error).__name__}: {close_error}")


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15, report_delivery=True):
    settings_advice = validate_smtp_settings()
    if settings_advice is not None:
        debug_print("Email delivery", outcome="skipped", reason="the SMTP settings are unusable")
        print_recovery_advice(settings_advice)
        return 1

    if not subject or not isinstance(subject, str):
        print_recovery_error(context="smtp.settings", detail="the message subject is empty")
        return 1

    if not body and not body_html:
        print_recovery_error(context="smtp.settings", detail="the message has no plain-text and no HTML body")
        return 1

    smtpObj = None
    try:
        if use_ssl:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=tls_context())
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtp_login(smtpObj, SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        # A game title or bio arrives from Xbox Live, so a line break in it would start a second header
        email_msg["Subject"] = str(Header(sanitize_email_header(subject), 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
    except Exception as e:
        debug_print("Email delivery", host=SMTP_HOST, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="smtp", detail=f"Sending the email through {SMTP_HOST} failed: {e}")
        return 1
    finally:
        smtp_quit_quietly(smtpObj)
    debug_print("Email delivery", host=SMTP_HOST, outcome="OK", subject=subject)
    if report_delivery:
        verbose_delivery_print(f"Email sent to {RECEIVER_EMAIL}")
    return 0


# Webhook notifications, delivered through Discord or ntfy
# ----------------------------------------------------------

# One retry only. An alert that is already late is worth less than a monitoring loop that keeps polling
WEBHOOK_MAX_ATTEMPTS = 2

# The service supplies the rate-limit delay, so it is bounded before it is trusted
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
WEBHOOK_TIMEOUT_SECONDS = 10

# Discord rejects an embed longer than these limits and ntfy rejects a message above its byte limit,
# so an over-long alert is trimmed here rather than being refused by the service
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096
NTFY_MESSAGE_LIMIT_BYTES = 4095
NTFY_TRUNCATION_SUFFIX = "\n\n[Notification truncated to fit ntfy's 4 KB message limit]"

# The embed colour each alert is drawn in, so a webhook reader can tell them apart at a glance. Every status
# alert shares one colour, so the two status settings do not read as two different kinds of event
WEBHOOK_EVENT_COLORS = {"status": 0x107C10, "game": 0x8957E5, "error": 0xE74C3C}


# Returns whether a webhook URL is a complete private HTTPS link
def validate_webhook_url(url=None):
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        httpx.URL(selected_url.strip())
        parsed = urlsplit(selected_url.strip())
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return False
    except (ValueError, httpx.InvalidURL):
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Returns the webhook destination host on its own, so delivery can be traced without printing the private URL
def webhook_destination_host(url=None):
    try:
        return urlsplit(str(WEBHOOK_URL if url is None else url).strip()).hostname or "unknown host"
    except ValueError:
        return "unknown host"


# Converts a complete ntfy URL or a bare ntfy.sh topic name into a complete HTTPS URL
def normalize_ntfy_topic_url(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if validate_webhook_url(normalized):
        return normalized
    if re.fullmatch(r"[-_A-Za-z0-9]{1,64}", normalized):
        return f"https://ntfy.sh/{normalized}"
    return ""


# Returns the normalized configured webhook provider or an empty string when it is not one of the supported two
def normalized_webhook_provider(provider=None):
    selected_provider = WEBHOOK_PROVIDER if provider is None else provider
    if not isinstance(selected_provider, str):
        return ""
    normalized = selected_provider.strip().casefold()
    return normalized if normalized in ("discord", "ntfy") else ""


# Returns the user-facing spelling of one webhook provider
def webhook_provider_display_name(provider=None):
    normalized = normalized_webhook_provider(provider)
    if normalized:
        return "Discord" if normalized == "discord" else "ntfy"
    return sanitize_error_text(WEBHOOK_PROVIDER if provider is None else provider)


# Detects Discord and public ntfy destinations from their distinctive URL shapes
def detect_webhook_provider(url):
    if not validate_webhook_url(url):
        return ""
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError:
        return ""
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname == "ntfy.sh":
        return "ntfy"
    discord_host = hostname in ("discord.com", "discordapp.com") or hostname.endswith(".discord.com") or hostname.endswith(".discordapp.com")
    discord_path = re.match(r"^/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^/]+/?$", parsed.path) is not None
    return "discord" if discord_host and discord_path else ""


# Returns whether one webhook alert is switched on, independently of the matching email setting
def webhook_event_enabled(notification_type):
    settings = {
        "status": WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION,
        "all_status": WEBHOOK_STATUS_NOTIFICATION,
        "game": WEBHOOK_GAME_CHANGE_NOTIFICATION,
        "error": WEBHOOK_ERROR_NOTIFICATION,
    }
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Returns the enabled webhook alert names, in the order the startup summary and doctor print them
def webhook_notification_categories():
    settings = (
        (WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION, "online and offline changes"),
        (WEBHOOK_GAME_CHANGE_NOTIFICATION, "game changes"),
        (WEBHOOK_STATUS_NOTIFICATION, "all status changes"),
        (WEBHOOK_ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if enabled]


# Parses a rate-limit delay from the response and bounds an untrusted server value to a short wait
def webhook_retry_after_seconds(response):
    candidates = []
    headers = getattr(response, "headers", {}) or {}
    if hasattr(headers, "get"):
        candidates.append(headers.get("Retry-After"))
    try:
        payload = response.json()
    except Exception as diag_exc:
        debug_print("Webhook retry response has no JSON body", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            seconds = float(candidate)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(candidate))
                seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            except Exception as diag_exc:
                debug_print("Cannot parse the webhook Retry-After value", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                continue
        return max(0.0, min(seconds, WEBHOOK_MAX_RETRY_AFTER_SECONDS))
    return WEBHOOK_FALLBACK_RETRY_SECONDS


# Substitutes the supported placeholders through a nested webhook template
def format_payload(template, payload):
    if isinstance(template, dict):
        return {key: format_payload(value, payload) for key, value in template.items()}
    if isinstance(template, list):
        return [format_payload(value, payload) for value in template]
    if isinstance(template, tuple):
        return tuple(format_payload(value, payload) for value in template)
    if isinstance(template, str):
        # Discord rejects a colour sent as text, so this one placeholder resolves to the number itself
        if template == "{color}":
            return payload.get("color", WEBHOOK_EVENT_COLORS["status"])
        try:
            return template.format(**payload)
        # A placeholder the payload cannot fill, such as {title[9]} or the positional {0}, is a setting
        # to correct rather than a delivery failure, so it names the template text that could not render
        except Exception as exc:
            raise ValueError(f"WEBHOOK_TEMPLATE cannot render '{template}': {type(exc).__name__}: {exc}. Use plain placeholders such as {{title}} and {{description}}") from exc
    return template


# Parses legacy and current Discord templates before validating their object shape
def render_discord_template(template, values):
    if isinstance(template, str):
        try:
            template = json.loads(template)
        except json.JSONDecodeError:
            try:
                # Legacy templates doubled JSON braces for str.format, while quoted values remain templates
                unescaped = re.sub(r'("(?:\\.|[^"\\])*")|(\{\{|\}\})', lambda match: match.group(1) if match.group(1) is not None else match.group(2)[0], template)
                template = json.loads(unescaped)
            except json.JSONDecodeError as exc:
                raise ValueError("WEBHOOK_TEMPLATE must be a dictionary or a JSON object string") from exc
    if not isinstance(template, dict):
        raise ValueError("WEBHOOK_TEMPLATE must be a dictionary or a JSON object string")
    return format_payload(template, values)


# Returns a configuration error for unsafe or unsupported webhook customization
def validate_webhook_customization(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    if selected_provider == "discord":
        if not isinstance(WEBHOOK_USERNAME, str):
            return "WEBHOOK_USERNAME must be a string"
        if not isinstance(WEBHOOK_AVATAR_URL, str):
            return "WEBHOOK_AVATAR_URL must be a string"
        if WEBHOOK_AVATAR_URL.strip() and not validate_webhook_url(WEBHOOK_AVATAR_URL):
            return "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"
        if not isinstance(WEBHOOK_TEMPLATE, (dict, str)):
            return "WEBHOOK_TEMPLATE must be a dictionary or a JSON object string"
    if not isinstance(WEBHOOK_TRANSFORMS, (list, tuple)):
        return "WEBHOOK_TRANSFORMS must be a list or tuple"
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        if not isinstance(transform, (list, tuple)) or len(transform) < 2 or not isinstance(transform[0], str) or not isinstance(transform[1], str):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} must contain a field name and a string method name"
        # Only public str methods are reachable, so a template cannot call arbitrary attributes of the value
        if transform[1].startswith("_") or not callable(getattr("", transform[1], None)):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} uses an unsupported string method"
    if selected_provider == "discord":
        try:
            render_discord_template(WEBHOOK_TEMPLATE, {"title": "", "description": "", "username": "", "avatar_url": "", "image_url": "", "fields_str": "", "fields": [], "color": 0, "timestamp": "", "version": VERSION})
        # The rendering error names the placeholder to correct, which the shape message cannot
        except ValueError as exc:
            return str(exc)
        except TypeError:
            return "WEBHOOK_TEMPLATE must be a dictionary or a JSON object string"
    return None


# Applies the configured string transformations to one webhook value mapping
def apply_webhook_transforms(payload):
    transformed = dict(payload)
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        field_name = transform[0]
        method_name = transform[1]
        if field_name not in transformed or not isinstance(transformed[field_name], str):
            continue
        try:
            transformed[field_name] = getattr(transformed[field_name], method_name)(*transform[2:])
        except Exception as exc:
            raise ValueError(f"WEBHOOK_TRANSFORMS entry {index + 1} could not apply {field_name}.{method_name}") from exc
    return transformed


# Builds the bounded placeholder values shared by the template, the headers and both providers
def build_webhook_values(title, description, notification_type):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "Xbox Monitor"
    safe_description = re.sub(r"\r\n?", "\n", sanitize_error_text(description)).strip()[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    username = WEBHOOK_USERNAME.strip()[:80] if isinstance(WEBHOOK_USERNAME, str) else ""
    avatar_url = WEBHOOK_AVATAR_URL.strip() if isinstance(WEBHOOK_AVATAR_URL, str) else ""
    payload = {"title": safe_title, "description": safe_description, "version": VERSION, "color": WEBHOOK_EVENT_COLORS.get(notification_type, WEBHOOK_EVENT_COLORS["status"]), "timestamp": datetime.now().astimezone().isoformat(), "username": username, "avatar_url": avatar_url}
    return apply_webhook_transforms(payload)


# Builds one customized Discord-format payload, keeping mentions disabled whatever the template says
def build_webhook_payload(title, description, notification_type, payload_values=None):
    values = build_webhook_values(title, description, notification_type) if payload_values is None else payload_values
    try:
        payload = render_discord_template(WEBHOOK_TEMPLATE, values)
    # The named placeholder error is the one a user can act on, so it reaches the caller unchanged
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("WEBHOOK_TEMPLATE could not be formatted with the supported placeholders") from exc
    if not isinstance(payload, dict):
        raise ValueError("WEBHOOK_TEMPLATE must be a JSON object or a dictionary")
    # An empty name or avatar means "use the webhook default", which Discord expects as an absent key
    if payload.get("username") == "":
        payload.pop("username")
    if payload.get("avatar_url") == "":
        payload.pop("avatar_url")
    payload["allowed_mentions"] = {"parse": []}
    return payload


# Truncates text to a UTF-8 byte limit without leaving a partial character behind
def truncate_utf8_bytes(text, max_bytes, suffix=""):
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    encoded_suffix = suffix.encode("utf-8")
    if len(encoded_suffix) >= max_bytes:
        return encoded_suffix[:max_bytes].decode("utf-8", errors="ignore")
    return encoded[:max_bytes - len(encoded_suffix)].decode("utf-8", errors="ignore") + suffix


# Builds one bounded ntfy title and message pair
def build_ntfy_webhook_message(title, description):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "Xbox Monitor"
    safe_message = truncate_utf8_bytes(sanitize_error_text(description), NTFY_MESSAGE_LIMIT_BYTES, NTFY_TRUNCATION_SUFFIX)
    return safe_title, safe_message


# Returns a safe validation error for one custom webhook header mapping
def _validate_webhook_header_mapping(headers):
    if not isinstance(headers, dict):
        return "WEBHOOK_HEADERS must be a dictionary of string header names and values"
    normalized_names = set()
    for name, value in headers.items():
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            return "WEBHOOK_HEADERS contains an invalid HTTP header name"
        normalized_name = name.casefold()
        if normalized_name in normalized_names:
            return "WEBHOOK_HEADERS contains duplicate case-insensitive header names"
        normalized_names.add(normalized_name)
        if not isinstance(value, str):
            return f"WEBHOOK_HEADERS value for {name} must be a string"
        # A line break in a header value would let a configured value inject a second header
        if "\r" in value or "\n" in value:
            return f"WEBHOOK_HEADERS value for {name} must not contain line breaks"
    return None


# Returns a safe configuration error for the custom headers or the ntfy access token
def validate_webhook_headers(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    header_error = _validate_webhook_header_mapping(WEBHOOK_HEADERS)
    if header_error is not None:
        return header_error
    if selected_provider == "ntfy":
        if not isinstance(NTFY_ACCESS_TOKEN, str):
            return "NTFY_ACCESS_TOKEN must be a string"
        token = NTFY_ACCESS_TOKEN.strip()
        if "\r" in token or "\n" in token:
            return "NTFY_ACCESS_TOKEN must not contain line breaks"
        if token.casefold().startswith(("bearer ", "basic ")):
            return "NTFY_ACCESS_TOKEN must contain only the access token, without an Authorization scheme"
    return None


# Builds the provider-specific headers, substituting placeholders and adding the private ntfy authentication
def build_webhook_headers(provider, payload):
    validation_error = validate_webhook_headers(provider)
    if validation_error is not None:
        raise ValueError(validation_error)
    try:
        formatted_headers = format_payload(WEBHOOK_HEADERS, payload)
    except Exception as exc:
        raise ValueError("WEBHOOK_HEADERS could not be formatted with the supported placeholders") from exc
    # Re-checked after substitution, because a placeholder value could carry a line break the template did not
    formatted_error = _validate_webhook_header_mapping(formatted_headers)
    if formatted_error is not None:
        raise ValueError(formatted_error)
    headers = dict(cast("dict[str, str]", formatted_headers))
    if not any(name.casefold() == "user-agent" for name in headers):
        headers["User-Agent"] = f"XboxMonitor/{VERSION}"
    if provider == "ntfy":
        headers = {name: value for name, value in headers.items() if name.casefold() != "content-type"}
        headers["Content-Type"] = "text/plain; charset=utf-8"
        token = NTFY_ACCESS_TOKEN.strip()
        if token:
            headers = {name: value for name, value in headers.items() if name.casefold() != "authorization"}
            headers["Authorization"] = f"Bearer {token}"
    return headers


# Reports one webhook configuration or delivery failure through the shared recovery renderer, so it carries a
# category and a fix line like every other failure this tool prints
def print_webhook_error(message):
    print_recovery_error(context="webhook", detail=str(message))


# Sends one webhook request with the destination, deadline and redirect policy every delivery shares
def post_webhook_request(client, destination=None, **request_kwargs):
    destination = str(WEBHOOK_URL if destination is None else destination).strip()
    if not validate_webhook_url(destination):
        raise httpx.InvalidURL("WEBHOOK_URL must contain a complete HTTPS link")
    return client.post(destination, **request_kwargs)


_DELIVERY_SECRET_VALUES: contextvars.ContextVar[tuple] = contextvars.ContextVar("delivery_secret_values", default=())


# Keeps in-flight credentials available to error redaction across settings reloads
def _retain_webhook_secrets(deliver):
    @functools.wraps(deliver)
    # Restores the previous redaction scope after this delivery finishes
    def retained(*args, **kwargs):
        settings = globals().copy()
        values = [settings.get(name) for name in SECRET_KEYS]
        headers = settings.get("WEBHOOK_HEADERS")
        if isinstance(headers, dict):
            for name, value in headers.items():
                if isinstance(name, str) and name.casefold() == "authorization" and isinstance(value, str):
                    values.append(value)
                    parts = value.split(None, 1)
                    if len(parts) == 2 and parts[0].casefold() in ("bearer", "basic"):
                        values.append(parts[1])
        # The same minimum length every other redaction path applies, so a short secret cannot blank out ordinary words
        secrets = tuple(value for value in values if isinstance(value, str) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH and not value.startswith("your_"))
        token = _DELIVERY_SECRET_VALUES.set(_DELIVERY_SECRET_VALUES.get() + secrets)
        try:
            return deliver(*args, **kwargs)
        finally:
            _DELIVERY_SECRET_VALUES.reset(token)
    return retained


@_retain_webhook_secrets
# Sends one webhook through its own bounded retry path, which never shares the Xbox Live retry policy
def send_webhook(title, description, notification_type="status", force=False, sleeper=None, report_delivery=True):
    if not force and not webhook_event_enabled(notification_type):
        debug_print("Webhook delivery", outcome="skipped", type=notification_type, reason="alerts are disabled")
        return 1
    destination = str(WEBHOOK_URL or "").strip()
    if not validate_webhook_url(destination):
        print_webhook_error("WEBHOOK_URL must contain a complete HTTPS link")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_webhook_error("WEBHOOK_PROVIDER must be discord or ntfy")
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_webhook_error(customization_error)
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_webhook_error(header_error)
        return 1
    try:
        webhook_values = build_webhook_values(title, description, notification_type)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_webhook_error(exc)
        return 1
    sleep_func = time.sleep if sleeper is None else sleeper
    ntfy_title, ntfy_message = build_ntfy_webhook_message(str(webhook_values["title"]), str(webhook_values["description"])) if provider == "ntfy" else ("", "")
    if destination != str(WEBHOOK_URL or "").strip():
        print_recovery_error(context="webhook", detail="Webhook settings changed while preparing the delivery. Retry the notification with the current settings")
        return 1
    last_error = None
    # Redirects are refused, so a moved endpoint cannot forward the alert and its authorization header elsewhere
    with httpx.Client(verify=tls_context(), timeout=WEBHOOK_TIMEOUT_SECONDS, follow_redirects=False) as client:
        for attempt in range(WEBHOOK_MAX_ATTEMPTS):
            attempt_number = attempt + 1
            try:
                debug_print("Webhook delivery", channel=provider, host=webhook_destination_host(destination), attempt=f"{attempt_number}/{WEBHOOK_MAX_ATTEMPTS}", timeout=f"{WEBHOOK_TIMEOUT_SECONDS}s")
                if provider == "ntfy":
                    response = post_webhook_request(client, destination=destination, content=ntfy_message.encode("utf-8"), params={"title": ntfy_title}, headers=request_headers)
                else:
                    response = post_webhook_request(client, destination=destination, json=discord_payload, headers=request_headers)
                # A rate limit and a server fault are the only answers worth repeating and only once
                retryable = response.status_code == 429 or 500 <= response.status_code <= 599
                debug_print("Webhook delivery", channel=provider, attempt=f"{attempt_number}/{WEBHOOK_MAX_ATTEMPTS}", status=response.status_code, retryable=retryable)
                if 200 <= response.status_code <= 299:
                    if report_delivery:
                        verbose_delivery_print(f"Webhook sent through {webhook_provider_display_name(provider)}")
                    return 0
                last_error = f"HTTP {response.status_code}: {sanitize_error_text(getattr(response, 'text', ''))[:200]}"
                if not retryable or attempt_number == WEBHOOK_MAX_ATTEMPTS:
                    print_webhook_error(last_error)
                    return 1
                delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
                debug_print("Webhook delivery", channel=provider, retry_in=f"{delay:.1f}s", next_attempt=f"{attempt_number + 1}/{WEBHOOK_MAX_ATTEMPTS}")
                sleep_func(delay)
            except httpx.HTTPError as exc:
                last_error = exc
                debug_print("Webhook delivery", channel=provider, attempt=f"{attempt_number}/{WEBHOOK_MAX_ATTEMPTS}", outcome="failed", error=f"{type(exc).__name__}: {exc}")
                if attempt_number == WEBHOOK_MAX_ATTEMPTS:
                    print_webhook_error(exc)
                    return 1
                debug_print("Webhook delivery", channel=provider, retry_in=f"{WEBHOOK_FALLBACK_RETRY_SECONDS:.1f}s", next_attempt=f"{attempt_number + 1}/{WEBHOOK_MAX_ATTEMPTS}")
                sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    print_webhook_error(last_error)
    return 1


# Sends one alert through the email and webhook channels, each switched on independently of the other
def send_notification_channels(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None):
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    email_delivered = False
    webhook_delivered = False
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        email_delivered = send_email(subject, body, body_html, SMTP_SSL) == 0
    if webhook_attempted:
        print(f"Sending webhook notification via {webhook_provider_display_name()}")
        webhook_delivered = send_webhook(subject, body, notification_type, force=True) == 0
    # Delivery, not the attempt, so a channel that failed is retried while one that succeeded is not resent
    return email_delivered, webhook_delivered


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
        debug_print("CSV initialization", path=csv_file_name, outcome="OK")
    except Exception as e:
        debug_print("CSV initialization", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, status, gamename):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': gamename})

        debug_print("CSV entry write", path=csv_file_name, outcome="OK", status=status)
    except Exception as e:
        debug_print("CSV entry write", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Returns current local time without timezone info (naive)
def now_local_naive():
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE)).replace(microsecond=0, tzinfo=None)


# Returns current local time with timezone info (aware)
def now_local():
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE))


# Converts ISO datetime string to localized datetime (aware)
def convert_iso_str_to_datetime(dt_str):
    if not dt_str:
        return None

    try:
        if isinstance(dt_str, datetime):
            utc_dt = dt_str
        else:
            utc_dt = isoparse(dt_str)

        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(pytz.timezone(LOCAL_TIMEZONE))
    except Exception as e:
        debug_print("Timestamp conversion to local time", outcome="failed", error=f"{type(e).__name__}: {e}")
        return None


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(now_local_naive()).weekday()]} {now_local_naive().strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    global REPORTS_PRINTED
    REPORTS_PRINTED += 1
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception as e:
            debug_print("Timestamp parse", field="ts", outcome="failed", error=f"{type(e).__name__}: {e}")
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    return (f'{calendar.day_abbr[ts_new.weekday()]} {ts_new.strftime("%d %b %Y, %H:%M:%S")}')


# Returns the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr 25, 15:08 (if always_show_year == True and current year can be the same)
# Sun 21 Apr (if show_hour == False)
# Sun 21 Apr 15:08:32 (if show_seconds == True)
# 21 Apr 15:08 (if show_weekday == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True, show_weekday=True, show_seconds=False, always_show_year=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)
    if always_show_year:
        show_year = True

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception as e:
            debug_print("Timestamp parse", field="ts", outcome="failed", error=f"{type(e).__name__}: {e}")
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M:%S" if show_seconds else " %H:%M"
    else:
        hour_strftime = ""

    weekday_str = f"{calendar.day_abbr[ts_new.weekday()]} " if show_weekday else ""

    if (show_year and ts_new.year != datetime.now(tz).year) or always_show_year:
        hour_prefix = "," if show_hour else ""
        return f'{weekday_str}{ts_new.strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}'
    else:
        return f'{weekday_str}{ts_new.strftime(f"%d %b{hour_strftime}")}'


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception as e:
            debug_print("Timestamp parse", field="ts", outcome="failed", error=f"{type(e).__name__}: {e}")
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    out_strf = "%H:%M:%S" if show_seconds else "%H:%M"
    return ts_new.strftime(out_strf)


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False, always_show_year=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts1, datetime):
        ts1_new = int(round(ts1.timestamp()))
    elif isinstance(ts1, int):
        ts1_new = ts1
    elif isinstance(ts1, float):
        ts1_new = int(round(ts1))
    else:
        return ""

    if isinstance(ts2, datetime):
        ts2_new = int(round(ts2.timestamp()))
    elif isinstance(ts2, int):
        ts2_new = ts2
    elif isinstance(ts2, float):
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new, tz).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new, tz).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            if always_show_year:
                out_str = f"{get_short_date_from_ts(ts1_new, always_show_year=True)}{between_sep}{get_short_date_from_ts(ts2_new, always_show_year=True)}"
            else:
                out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new, always_show_year=always_show_year)}{between_sep}{get_short_date_from_ts(ts2_new, always_show_year=always_show_year)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"

    return str(out_str)


# Checks if the timezone name is correct
def is_valid_timezone(tz_name):
    return tz_name in pytz.all_timezones


# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global ACTIVE_INACTIVE_NOTIFICATION
    ACTIVE_INACTIVE_NOTIFICATION = not ACTIVE_INACTIVE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {ACTIVE_INACTIVE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global GAME_CHANGE_NOTIFICATION
    GAME_CHANGE_NOTIFICATION = not GAME_CHANGE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {GAME_CHANGE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch all status changes notifications
def toggle_all_status_changes_notifications_signal_handler(sig, frame):
    global STATUS_NOTIFICATION
    STATUS_NOTIFICATION = not STATUS_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [all status changes = {STATUS_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is online by XBOX_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global XBOX_ACTIVE_CHECK_INTERVAL
    XBOX_ACTIVE_CHECK_INTERVAL = XBOX_ACTIVE_CHECK_INTERVAL + XBOX_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Xbox timers: [active check interval: {display_time(XBOX_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is online by XBOX_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global XBOX_ACTIVE_CHECK_INTERVAL
    if XBOX_ACTIVE_CHECK_INTERVAL - XBOX_ACTIVE_CHECK_SIGNAL_VALUE > 0:
        XBOX_ACTIVE_CHECK_INTERVAL = XBOX_ACTIVE_CHECK_INTERVAL - XBOX_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Xbox timers: [active check interval: {display_time(XBOX_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


DOTENV_RELOAD_STATE = {}


# Names the effective source after a file-owned secret is reloaded or removed
def dotenv_reload_source(key):
    if key in DOTENV_RELOAD_STATE.get("managed", ()):
        return "dotenv file reload" if "dotenv file reload" in SECRET_SOURCE_ORDER else "dotenv file"
    return DOTENV_RELOAD_STATE.get("base_sources", {}).get(key, "environment" if key in DOTENV_RELOAD_STATE.get("exported", ()) else SECRET_SOURCE_ORDER[0])


# Resolves dotenv references while keeping explicitly marked private values literal
def resolve_dotenv_values(content, override=False, interpolate=True, environment=None):
    from io import StringIO
    try:
        from dotenv.main import with_warn_for_invalid_lines
        from dotenv.parser import parse_stream
        from dotenv.variables import parse_variables
    # A python-dotenv without these internals still reads the file, only without the literal marker. Writing a
    # value that needs the marker then fails its own read-back check rather than saving something unreadable
    except ImportError:
        if environment is not None:
            raise ValueError("The installed python-dotenv cannot resolve this file safely. Update python-dotenv") from None
        from dotenv.main import DotEnv
        debug_print("Dotenv literal markers are unavailable in the installed python-dotenv", outcome="skipped")
        return DotEnv(dotenv_path=None, stream=StringIO(content), override=override, interpolate=interpolate).dict()
    base_environment = dict(os.environ) if environment is None else environment
    values = {}
    for binding in with_warn_for_invalid_lines(parse_stream(StringIO(content))):
        if binding.key is None:
            continue
        value = binding.value
        literal = binding.key in SECRET_KEYS and binding.original.string.rstrip().endswith("# monitor:literal")
        if value is not None and interpolate and not literal:
            resolved_environment = dict(base_environment)
            if override:
                resolved_environment.update(values)
            else:
                resolved_environment = dict(values, **resolved_environment)
            value = "".join(atom.resolve(resolved_environment) for atom in parse_variables(value))
        values[binding.key] = value
    return values


# Returns the secrets explicitly supplied on the command line
def command_line_secret_keys():
    return frozenset(globals().get("COMMAND_LINE_SECRET_KEYS", ())) | frozenset(key for key, source in globals().get("SECRET_SOURCES", {}).items() if source == "command line")


# Reloads file-owned credentials while preserving startup exports and command-line choices
def load_managed_dotenv(path, override=False, interpolate=True, protected_keys=()):
    from io import StringIO
    from dotenv.parser import parse_stream
    if not override and not Path(path).is_file():
        return False
    content = Path(path).read_text(encoding="utf-8")
    if override:
        malformed = next((binding for binding in parse_stream(StringIO(content)) if binding.error), None)
        if malformed is not None:
            raise ValueError(f"Dotenv syntax error near line {malformed.original.line}. Correct the assignment and reload again")
    state: dict = DOTENV_RELOAD_STATE if override and DOTENV_RELOAD_STATE else dict(base={key: os.environ.get(key) or globals().get(key, "") for key in SECRET_KEYS}, exported={key for key, value in os.environ.items() if value}, managed=set())
    command_keys = command_line_secret_keys()
    protected = set(protected_keys) | state["exported"] | command_keys
    environment = {key: value for key, value in os.environ.items() if value and key not in state.get("loaded", state["managed"])}
    environment.update({key: str(globals().get(key) or "") for key in command_keys})
    values = resolve_dotenv_values(content, override=False, interpolate=interpolate, environment=environment)
    applied = {key for key, value in values.items() if value is not None and key not in protected and (override or not os.environ.get(key))}
    removed = state["managed"] - applied - protected
    for key in removed:
        value = state["base"].get(key)
        os.environ[key] = "" if value is None else str(value)
    for key in applied:
        os.environ[key] = str(values[key])
    state["managed"] = applied.intersection(SECRET_KEYS)
    state["loaded"] = set(state.get("loaded", ())) | applied
    if state is not DOTENV_RELOAD_STATE:
        DOTENV_RELOAD_STATE.clear()
        DOTENV_RELOAD_STATE.update(state)
    return bool(values)


# Signal handler for SIGHUP allowing to reload secrets from .env
def reload_secrets_signal_handler(sig, frame):
    global XBOX_AUTH_REFRESH_VERSION, WEBHOOK_PROVIDER
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_managed_dotenv(env_path, override=True)
            else:
                print("* No .env file found, skipping env-var reload")
        except ImportError:
            env_path = None
            print_recovery_advice(missing_dependency_advice("python-dotenv", "Secrets cannot be reloaded from a dotenv file", "Or export them as environment variables and restart"), label="Warning")

        except (OSError, UnicodeError, ValueError) as exc:
            print_recovery_advice(make_recovery_advice("config.invalid", "The dotenv reload failed. Existing secrets were kept", recovery_fix_with_guide("Check the dotenv file path, UTF-8 encoding and assignment syntax, then reload again", SECRETS_GUIDE_URL), False, str(exc)))
            return

    auth_credentials_changed = False
    webhook_url_changed = False
    if env_path:
        for secret in SECRET_KEYS:
            if secret in command_line_secret_keys():
                continue
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                if secret_is_set(val):
                    record_secret_source(secret, dotenv_reload_source(secret))
                else:
                    SECRET_SOURCES.pop(secret, None)
                if secret in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"):
                    auth_credentials_changed = True
                if secret == "WEBHOOK_URL":
                    webhook_url_changed = True
                print(f"* Reloaded {secret} from {env_path}")
    if auth_credentials_changed:
        XBOX_AUTH_REFRESH_VERSION += 1
    # A replacement destination can belong to the other service, which the reloaded URL is the only record of
    if webhook_url_changed:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        if detected_provider and detected_provider != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Updated webhook provider to {webhook_provider_display_name(detected_provider)}")

    print_cur_ts("Timestamp:\t\t\t")


# Returns mapping of platform code name to recognizable name
def xbox_get_platform_mapping(platform, short=True):
    platform_lower = str(platform).lower()
    if any(x in platform_lower for x in ["scarlett", "anaconda", "starkville", "lockhart", "edith"]):
        if short:
            platform = "XSX"
        else:
            platform = "Xbox One Series X/S"
    elif any(x in platform_lower for x in ["scorpio", "edmonton"]):
        if short:
            platform = "XONEX"
        else:
            platform = "Xbox One X/S"
    elif "durango" in str(platform).lower():
        if short:
            platform = "XONE"
        else:
            platform = "Xbox One"
    elif "xenon" in str(platform).lower():
        if short:
            platform = "X360"
        else:
            platform = "Xbox 360"
    elif "windows" in str(platform).lower():  # WindowsOneCore
        platform = "Windows"
    elif "ios" in str(platform).lower():
        platform = "iPhone/iPad"
    elif "android" in str(platform).lower():
        if not short:
            platform = "Android Phone/Tablet"
    return platform


# Zero-width characters Xbox embeds in some title names, such as the joiner inside "Microsoft Store"
_ZERO_WIDTH_TITLE_CHARS = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"))

# Xbox surfaces that presence reports like a title even though the user is not playing or watching anything
XBOX_SYSTEM_TITLES = frozenset({
    "online",
    "home",
    "xbox app",
    "xbox guide",
    "microsoft store",
    "xbox game pass",
    "microsoft edge",
    "settings",
})


# Strips the zero-width characters and padding Xbox leaves in a title name so it can be compared and displayed
def xbox_normalize_title_name(name):
    return " ".join(str(name or "").translate(_ZERO_WIDTH_TITLE_CHARS).split())


# Reports whether a presence title is an Xbox system surface rather than a game or app the user picked
def xbox_is_system_title(name):
    return xbox_normalize_title_name(name).casefold() in XBOX_SYSTEM_TITLES


# Processes Xbox presence class
def xbox_process_presence_class(presence, platform_short=True):
    status = ""
    title_name = ""
    game_name = ""
    platform = ""
    lastonline_ts = 0

    if 'state' in dir(presence):
        if presence.state:
            status = str(presence.state).lower()

    last_seen_class = ""
    last_seen_raw_title = ""
    last_seen_raw_ts = ""
    last_seen_raw_device = ""
    presence_titles_dbg = []

    if 'last_seen' in dir(presence):
        if presence.last_seen:
            last_seen_class = presence.last_seen
            last_seen_raw_title = getattr(last_seen_class, "title_name", "")
            last_seen_raw_ts = getattr(last_seen_class, "timestamp", "")
            last_seen_raw_device = getattr(last_seen_class, "device_type", "")
            if 'title_name' in dir(last_seen_class):
                if last_seen_class.title_name:
                    if not xbox_is_system_title(last_seen_class.title_name):
                        title_name = xbox_normalize_title_name(last_seen_class.title_name)
            if 'device_type' in dir(last_seen_class):
                if last_seen_class.device_type:
                    platform = last_seen_class.device_type
                    platform = xbox_get_platform_mapping(platform, platform_short)
            if 'timestamp' in dir(last_seen_class):
                if last_seen_class.timestamp:
                    lastonline_dt = convert_iso_str_to_datetime(last_seen_class.timestamp)
                    if lastonline_dt:
                        lastonline_ts = int(lastonline_dt.timestamp())
                    else:
                        lastonline_ts = 0
        elif 'type' in dir(presence):
            dev_type = presence.type
            platform = xbox_get_platform_mapping(dev_type, platform_short)

    if 'devices' in dir(presence):
        if presence.devices:
            devices_class = presence.devices
            try:
                platform = devices_class[0].type
                platform = xbox_get_platform_mapping(platform, platform_short)
            except IndexError:
                pass
            if 'titles' in dir(devices_class[0]):
                titles_class = devices_class[0].titles
                for title in titles_class:
                    t_name = getattr(title, "name", "")
                    t_placement = getattr(title, "placement", "")
                    if t_name:
                        presence_titles_dbg.append(f"{t_name} [{t_placement}]")
                    if not xbox_is_system_title(title.name) and title.placement != "Background":
                        game_name = xbox_normalize_title_name(title.name)
                        break

    debug_print("Presence parsed", state=status, title_name=title_name, game_name=game_name, platform=platform, lastonline=get_debug_date_from_ts(lastonline_ts))
    debug_print("Presence raw fields", last_seen_title=last_seen_raw_title, last_seen_device=last_seen_raw_device, last_seen_timestamp=last_seen_raw_ts)
    if presence_titles_dbg:
        debug_print("Presence device titles", titles=", ".join(presence_titles_dbg))
    else:
        debug_print("Presence device titles", titles="none")

    return status, title_name, game_name, platform, lastonline_ts


# Fetches the most recent last time played timestamp and game_name from title history
# This is useful for detecting activity when users have "appear offline" status
# Note: This timestamp only updates when a game session STARTS, not during or at the end
async def xbox_get_latest_title_played_ts(xbl_client, xuid):
    try:
        # Fetch 3 items to be safe (sometimes the first one is weird or missing timestamp)
        history_response = await xbl_client.titlehub.get_title_history(
            xuid,
            max_items=3
        )
        if history_response.titles:
            debug_print("Title history fetch", outcome="OK", items=len(history_response.titles))
            best_ts = 0
            best_game = ""
            for i, title in enumerate(history_response.titles, 1):
                if title.title_history and title.title_history.last_time_played:
                    played_dt = convert_iso_str_to_datetime(title.title_history.last_time_played)
                    if played_dt:
                        ts = int(played_dt.timestamp())
                        game_name = xbox_normalize_title_name(title.name) if getattr(title, 'name', "") else "Unknown"
                        debug_print("Title history item", index=i, game=game_name, played=get_date_from_ts(ts))
                        if best_ts == 0:
                            best_ts = ts
                            # A system surface still proves the user was active, so keep the timestamp and drop only the name
                            best_game = "" if xbox_is_system_title(game_name) else game_name

            if best_ts > 0:
                debug_print("Title history selection", game=best_game, played=get_date_from_ts(best_ts))
            return best_ts, best_game
    except Exception as e:
        stop_if_resource_exhausted(e)
        debug_print("Title history fetch", outcome="failed", error=f"{type(e).__name__}: {e}")
        verbose_notice("The title history fallback is unavailable, so an appear-offline user's activity may go unreported")
    return 0, ""


# Selects the best available last online timestamp (presence vs title history)
def xbox_get_best_lastonline_ts(lastonline_ts, title_history_ts):
    # Only use title history if it's significantly newer (20s jitter buffer) OR presence is missing (0)
    if title_history_ts > 0 and (title_history_ts > (lastonline_ts + 20) or lastonline_ts == 0):
        debug_print("Last active decision", source="title_history", history=get_debug_date_from_ts(title_history_ts), presence=get_debug_date_from_ts(lastonline_ts))
        return title_history_ts, True
    debug_print("Last active decision", source="presence", presence=get_debug_date_from_ts(lastonline_ts), history=get_debug_date_from_ts(title_history_ts))
    return lastonline_ts, False


# Gets detailed user information and displays it (for -i/--info mode)
async def get_user_info(gamertag, client=None, show_friends=False, show_recent_achievements=False, show_recent_games=False, achievements_count=5, games_count=10):

    # Helper to print step message
    def print_step(msg):
        global STDOUT_AT_START_OF_LINE
        sys.stdout.write(f"- {msg}".ljust(32))
        sys.stdout.flush()
        STDOUT_AT_START_OF_LINE = False

    # Helper to print OK
    def print_ok():
        global STDOUT_AT_START_OF_LINE
        print("OK")
        STDOUT_AT_START_OF_LINE = True

    if not client:
        print(f"* Fetching details for Xbox user '{gamertag}'...\n")

    session = None

    if not client:
        print_step("Authenticating with Xbox...")
        try:
            session = create_signed_session()
            auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, "")
            await authenticate_and_refresh_tokens(auth_mgr)

            xbl_client = XboxLiveClient(auth_mgr)
        except Exception as e:
            print()
            print_recovery_error(e, context="auth", detail=f"Signing in to Xbox Live failed: {format_exception(e)}")
            if session:
                await session.aclose()
            sys.exit(1)
        print_ok()
    else:
        xbl_client = client

    print_step("Fetching profile info...")
    try:
        profile = await xbl_client.profile.get_profile_by_gamertag(gamertag)
        if not profile.profile_users:
            print()
            print_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned a profile for '{gamertag}' with no account in it")
            if session:
                await session.aclose()
            sys.exit(1)

        user_obj = profile.profile_users[0]
        xuid = user_obj.id

        # Extract settings
        location = next((x.value for x in user_obj.settings if x.id == "Location"), "")
        bio = next((x.value for x in user_obj.settings if x.id == "Bio"), "")
        realname = next((x.value for x in user_obj.settings if x.id == "RealNameOverride"), "")
        gamerscore = next((x.value for x in user_obj.settings if x.id == "Gamerscore"), "0")
        tier = next((x.value for x in user_obj.settings if x.id == "AccountTier"), "")

    except Exception as e:
        print()
        print_recovery_error(e, context="target", detail=f"The profile for '{gamertag}' could not be read: {e}")
        if session:
            await session.aclose()
        sys.exit(1)
    debug_print("Profile fetch", outcome="OK", xuid=xuid, gamerscore=gamerscore, tier=tier)
    print_ok()

    print_step("Fetching presence info...")
    try:
        presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
        status, title_name, game_name, platform, lastonline_ts = xbox_process_presence_class(presence, False)
    except Exception as e:
        print()
        print_recovery_error(e, context="target", detail=f"The presence for '{gamertag}' could not be read: {e}")
        if session:
            await session.aclose()
        sys.exit(1)
    print_ok()

    # Fetch title history timestamp as fallback for "appear offline" users
    lastonline_source_history = False
    if status.lower() == "offline":
        print_step("Checking title history...")
        title_history_ts, _ = await xbox_get_latest_title_played_ts(xbl_client, xuid)
        lastonline_ts, lastonline_source_history = xbox_get_best_lastonline_ts(lastonline_ts, title_history_ts)
        print_ok()

    # Friends
    # Try library method first (works with fixed python-xbox), then fallback to direct API (for unfixed library)
    friends_count = 0
    friends_list = []
    print_step("Fetching friends info...")

    # First, try using the library's method (works if using fixed python-xbox library)
    try:
        friends_response = await xbl_client.people.get_friends_by_xuid(str(xuid))
        if friends_response.people:
            friends_list_raw = friends_response.people
            # Filter out the target user's own profile if it appears
            friends_list_filtered = [f for f in friends_list_raw if str(getattr(f, 'xuid', '')) != str(xuid)]

            if friends_list_filtered:
                # Library returned actual friends list (not just the user's profile)
                friends_list = [
                    {
                        'xuid': getattr(f, 'xuid', ''),
                        'gamertag': getattr(f, 'gamertag', 'Unknown'),
                        'presenceState': getattr(f, 'presence_state', 'Offline'),
                        'presenceDetails': [
                            {'presenceText': getattr(d, 'presence_text', '')}
                            for d in (getattr(f, 'presence_details', []) or [])
                        ]
                    }
                    for f in friends_list_filtered
                ]
                friends_count = len(friends_list)
                debug_print("Friends fetch", source="library", outcome="OK", count=friends_count)
            elif len(friends_list_raw) == 1:
                # Response contains only the target user's profile
                # Check if this is the unfixed library bug or if user genuinely has 0 friends
                user_profile = friends_list_raw[0]
                detail = getattr(user_profile, 'detail', None)
                actual_friend_count = getattr(detail, 'friend_count', 0) if detail else 0

                if actual_friend_count > 0:
                    # Bug: Library returned user profile but they have friends - fallback needed
                    debug_print("Friends fetch", source="library", outcome="degraded", reason="the library returned the user's own profile", friend_count=actual_friend_count)
                    raise ValueError("Unfixed library bug - response contains user profile instead of friends")
                else:
                    # User genuinely has 0 friends
                    friends_count = 0
                    friends_list = []
                    debug_print("Friends fetch", source="library", outcome="OK", count=0, confirmed=True)
            else:
                # Empty response - user has 0 friends
                friends_count = 0
                friends_list = []
                debug_print("Friends fetch", source="library", outcome="OK", count=0)
        else:
            # Empty people list - user has 0 friends
            friends_count = 0
            friends_list = []
            debug_print("Friends fetch", source="library", outcome="OK", count=0, response="empty")

    except Exception as e:
        stop_if_resource_exhausted(e)
        debug_print("Friends fetch", source="library", outcome="failed", error=f"{type(e).__name__}: {e}")
        # Fallback to direct API call (works with unfixed library)
        try:
            peoplehub_url = "https://peoplehub.xboxlive.com"
            decoration = "presenceDetail,preferredColor,detail"
            url = f"{peoplehub_url}/users/xuid({xuid})/people/social/decoration/{decoration}"
            headers = {
                "x-xbl-contract-version": "5",
                "Accept-Language": "en-US",
            }

            # Try to get the session from the XboxLiveClient
            http_session = None
            # The client's shape varies by library version, so each attribute is probed and read dynamically
            if hasattr(xbl_client, 'session'):
                http_session = getattr(xbl_client, 'session')  # noqa: B009
            elif hasattr(xbl_client, '_session'):
                http_session = getattr(xbl_client, '_session')  # noqa: B009
            elif hasattr(xbl_client, '_auth_mgr'):
                auth_mgr = getattr(xbl_client, '_auth_mgr')  # noqa: B009
                if hasattr(auth_mgr, 'session'):
                    http_session = getattr(auth_mgr, 'session')  # noqa: B009

            if http_session:
                # The probed session may not be the one built with the configured deadline, so it is passed here too
                response = await http_session.get(url, headers=headers, timeout=httpx.Timeout(float(XBOX_API_TIMEOUT)))
                response.raise_for_status()
                friends_data = response.json()

                if 'people' in friends_data:
                    friends_list_raw = friends_data['people']
                    friends_list = [f for f in friends_list_raw if str(f.get('xuid', '')) != str(xuid)]
                    friends_count = len(friends_list)
                    debug_print("Friends fetch", source="direct API", outcome="OK", count=friends_count)
            else:
                debug_print("Friends fetch", source="direct API", outcome="skipped", reason="no HTTP session was available")
                # Last fallback - get count from summary
                friends_summary = await xbl_client.people.get_friends_summary_by_xuid(str(xuid))
                if hasattr(friends_summary, 'target_following_count'):
                    friends_count = friends_summary.target_following_count
                    debug_print("Friends fetch", source="summary", outcome="OK", count=friends_count)

        except Exception as e2:
            stop_if_resource_exhausted(e2)
            debug_print("Friends fetch", source="direct API and summary", outcome="failed", error=f"{type(e2).__name__}: {e2}")
            report_degraded_error("The friends list could not be read", e2, label="Warning")

    if friends_list:
        debug_print("Friends list", count=len(friends_list))
        for i, friend in enumerate(friends_list, 1):
            f_gamertag = friend.get('gamertag', 'Unknown') if isinstance(friend, dict) else getattr(friend, 'gamertag', 'Unknown')
            f_state = friend.get('presenceState', 'Unknown') if isinstance(friend, dict) else getattr(friend, 'presence_state', 'Offline')
            debug_print("Friends list item", index=i, gamertag=f_gamertag, state=f_state)

    print_ok()

    # Title History (Recent Games)
    recent_games = []

    # Fetch history if we need to show recent games OR recent achievements (since we use games to look up achievements)
    if show_recent_games or show_recent_achievements:
        print_step("Fetching game history...")
        try:
            # Requesting details including ServiceConfigId (needed for stats) and Image
            history_response = await xbl_client.titlehub.get_title_history(
                xuid,
                fields=[TitleFields.ACHIEVEMENT, TitleFields.SERVICE_CONFIG_ID, TitleFields.IMAGE],
                max_items=max(20, games_count)
            )
            if history_response.titles:
                recent_games = history_response.titles[:]
        except Exception as e:
            stop_if_resource_exhausted(e)
            report_degraded_error("The game history could not be read", e, label="Warning")

        if recent_games:
            debug_print("Game history fetch", outcome="OK", count=len(recent_games))
            for i, title in enumerate(recent_games, 1):
                played_val = "Unknown"
                if title.title_history and title.title_history.last_time_played:
                    dt = convert_iso_str_to_datetime(title.title_history.last_time_played)
                    if dt:
                        played_val = get_date_from_ts(int(dt.timestamp()))
                debug_print("Game history item", index=i, title=title.name, last_played=played_val)
        else:
            debug_print("Game history fetch", outcome="OK", count=0)

        print_ok()

    # Recent Achievements
    recent_achievements = []
    if show_recent_achievements:
        print_step("Fetching achievements...")
        try:
            ach_response = await xbl_client.achievements.get_achievements_xboxone_recent_progress_and_info(xuid)
            if hasattr(ach_response, 'achievements'):
                recent_achievements = getattr(ach_response, 'achievements')  # noqa: B009
            # Sometimes it might return a list directly (rare but possible in some lib versions)
            elif isinstance(ach_response, list):
                recent_achievements = ach_response
        except Exception as e:
            stop_if_resource_exhausted(e)
            report_degraded_error("The achievements could not be read", e, label="Warning")

        if recent_achievements:
            debug_print("Recent achievements fetch", source="fast feed", outcome="OK", count=len(recent_achievements))
            for i, ach in enumerate(recent_achievements, 1):
                name = ach.name if hasattr(ach, 'name') and ach.name else "Unknown"
                state = ach.progress_state if hasattr(ach, 'progress_state') else "Unknown"
                time_unlocked = "N/A"
                if hasattr(ach, 'progression') and ach.progression.time_unlocked:
                    dt = convert_iso_str_to_datetime(ach.progression.time_unlocked)
                    if dt:
                        time_unlocked = get_date_from_ts(int(dt.timestamp()))
                debug_print("Recent achievements item", index=i, name=name, state=state, unlocked=time_unlocked)
        else:
            debug_print("Recent achievements fetch", source="fast feed", outcome="OK", count=0)

        print_ok()

    # Map Account Tier to descriptive text
    tier_lower = tier.lower() if tier else ""
    if tier_lower == "gold":
        tier_str = "Gold (Xbox Game Pass Core/Ultimate)"
    elif tier_lower == "silver":
        tier_str = "Silver (Free)"
    else:
        tier_str = tier

    print()
    print(f"Gamertag:\t\t\t{gamertag}")
    print(f"XUID:\t\t\t\t{xuid}")
    if realname:
        print(f"Real name:\t\t\t{realname}")
    if location:
        print(f"Location:\t\t\t{location}")
    if bio:
        # Xbox bios can span several lines, so continuation lines are indented to the value column
        bio_str = bio.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\n\t\t\t\t")
        print(f"Bio:\t\t\t\t{bio_str}")

    if tier:
        print(f"\nAccount Tier:\t\t\t{tier_str}")
    if gamerscore:
        if not tier:
            print()
        print(f"Gamerscore:\t\t\t{gamerscore}")

    print(f"\nStatus:\t\t\t\t{str(status).upper()}")
    if status.lower() == "offline":
        if lastonline_ts > 0:
            source_info = " (via title history)" if lastonline_source_history else ""
            print(f"Last online:\t\t\t{get_date_from_ts(lastonline_ts)}{source_info}")
        if title_name:
            print(f"Title name:\t\t\t{title_name}")
    else:
        if game_name:
            print(f"Current game:\t\t\t{game_name}")
        if platform:
            print(f"Platform:\t\t\t{platform}")

    print(f"\nFriends count:\t\t\t{friends_count}")
    if show_friends:
        if friends_list:
            print("\nFriends list:\n")
            for friend in friends_list:
                # Handle both dict (from direct API) and model object formats
                if isinstance(friend, dict):
                    f_gamertag = friend.get('gamertag', 'Unknown')
                    f_status = friend.get('presenceState', 'Offline')
                    if f_status == "Online":
                        presence_details = friend.get('presenceDetails', [])
                        for d in presence_details:
                            if d.get('presenceText'):
                                f_status = f"Online ({d.get('presenceText')})"
                                break
                else:
                    f_gamertag = friend.gamertag
                    f_status = "Offline"
                    if friend.presence_state == "Online":
                        f_status = "Online"
                        if friend.presence_details:
                            for d in friend.presence_details:
                                if d.presence_text:
                                    f_status += f" ({d.presence_text})"
                                    break
                print(f"{f_gamertag.ljust(30)} {f_status}")
        else:
            print("\n(Friends list details not available with current Xbox API library)")

    # Helper function to shorten string
    def _shorten_middle(s, max_len, ellipsis="..."):
        if s is None:
            return ""
        s = str(s)
        if len(s) <= max_len:
            return s
        keep = max_len - len(ellipsis)
        if keep <= 0:
            return ellipsis[:max_len]
        left = keep // 2
        right = keep - left
        return f"{s[:left]}{ellipsis}{s[-right:]}"

    if show_recent_games and recent_games:
        print("\nRecently played games:\n")

        # Determine column widths
        term_width = 100
        try:
            import shutil as sh
            term_width = sh.get_terminal_size(fallback=(100, 24)).columns
        except Exception as e:
            stop_if_resource_exhausted(e)
            debug_print("Terminal width probe", outcome="degraded", reason="the fallback width is used", error=f"{type(e).__name__}: {e}")

        w_num = 3
        w_last = 24
        w_total = 14
        fixed = 47
        w_title = max(24, term_width - fixed - 1)

        hdr = f"{'#'.ljust(w_num)}  {'Title'.ljust(w_title)}  {'Last played'.ljust(w_last)}  {'Total'.ljust(w_total)}"
        sep = f"{'-' * w_num}  {'-' * w_title}  {'-' * w_last}  {'-' * w_total}"
        print(colorize("section", hdr))
        print(sep)

        for i, title in enumerate(recent_games[:games_count], 1):
            t_name = title.name

            t_last = convert_iso_str_to_datetime(title.title_history.last_time_played) if title.title_history else None
            t_last_str = get_date_from_ts(t_last) if t_last else "n/a"

            # Fetch stats (Playtime)
            t_playtime = "0h 0m"
            if title.service_config_id:
                try:
                    stats = await xbl_client.userstats.get_stats(xuid, title.service_config_id, cast(List[GeneralStatsField], [GeneralStatsField.MINUTES_PLAYED]))
                    mins = 0

                    stat_list_scid = getattr(stats, 'stat_list_scid', None)
                    statlistscollection = getattr(stats, 'statlistscollection', None)

                    if stat_list_scid:
                        mins = next((s.value for s in stat_list_scid[0].stats if s.name == "MinutesPlayed"), 0)
                    elif statlistscollection:
                        mins = next((s.value for s in statlistscollection[0].stats if s.name == "MinutesPlayed"), 0)

                    if mins:
                        hours = int(mins) // 60
                        mins_rem = int(mins) % 60
                        t_playtime = f"{hours}h {mins_rem}m"
                except Exception as e:
                    stop_if_resource_exhausted(e)
                    debug_print("Play time formatting", outcome="failed", error=f"{type(e).__name__}: {e}")

            name_fmt = _shorten_middle(t_name, w_title)

            row = (
                f"{str(i).ljust(w_num)}  "
                f"{name_fmt.ljust(w_title)}  "
                f"{t_last_str.ljust(w_last)}  "
                f"{t_playtime.ljust(w_total)}"
            )
            print(row)

    if show_recent_achievements and recent_games:
        print("\nRecent Achievements:\n")
        debug_print("Recent achievements fetch", source="deep scan")

        all_recent_achievements = []

        # Process top recent games to get achievements
        for title_prog in recent_games:
            # print(f"DEBUG: Checking {title_prog.name}")
            try:
                game_achievements = await xbl_client.achievements.get_achievements_xboxone_gameprogress(xuid, title_prog.title_id)
                debug_print("Title achievements fetch", title=title_prog.name)

                ach_list = []
                if isinstance(game_achievements, list):
                    ach_list = game_achievements
                elif hasattr(game_achievements, 'achievements'):
                    ach_list = game_achievements.achievements

                unlocked_achs = [a for a in ach_list if a.progress_state == "Achieved"]
                if unlocked_achs:
                    debug_print("Title achievements fetch", title=title_prog.name, outcome="OK", unlocked=len(unlocked_achs))
                # print(f"DEBUG: Unlocked {len(unlocked_achs)}")

                for ach in unlocked_achs:
                    # Store as tuple (achievement, title_name) since we cannot modify the model
                    all_recent_achievements.append((ach, title_prog.name))

            except Exception as e:
                stop_if_resource_exhausted(e)
                debug_print("Title achievements fetch", title=title_prog.name, outcome="failed", error=f"{type(e).__name__}: {e}")

        # Sort ALL collected achievements by time_unlocked (descending)
        all_recent_achievements.sort(key=lambda x: x[0].progression.time_unlocked, reverse=True)

        # Determine column widths for achievements
        term_width = 100
        try:
            import shutil as sh
            term_width = sh.get_terminal_size(fallback=(100, 24)).columns
        except Exception as e:
            stop_if_resource_exhausted(e)
            debug_print("Terminal width probe", outcome="degraded", reason="the fallback width is used", error=f"{type(e).__name__}: {e}")

        w_date = 26
        remaining = term_width - w_date - 4 - 1
        w_game = int(remaining * 0.4)
        w_ach = remaining - w_game

        if w_game < 20:
            w_game = 20
        if w_ach < 30:
            w_ach = 30

        hdr = f"{'Date'.ljust(w_date)}  {'Game'.ljust(w_game)}  {'Achievement'.ljust(w_ach)}"
        sep = f"{'-' * w_date}  {'-' * w_game}  {'-' * w_ach}"
        print(colorize("section", hdr))
        print(sep)

        for ach, title_name in all_recent_achievements[:achievements_count]:
            t_unlock = convert_iso_str_to_datetime(ach.progression.time_unlocked)
            t_unlock_str = get_date_from_ts(t_unlock) if t_unlock else "n/a"

            a_name = ach.name

            game_fmt = _shorten_middle(title_name, w_game)
            ach_fmt = _shorten_middle(a_name, w_ach)

            print(f"{t_unlock_str.ljust(w_date)}  {game_fmt.ljust(w_game)}  {ach_fmt.ljust(w_ach)}")

    if session and not client:
        await session.aclose()


def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}
    """

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None


# Settings an older version wrote that this version no longer defines, ignored instead of rejected
RETIRED_CONFIG_SETTINGS = frozenset(())

# Settings the template ships commented out. They are still accepted, since the template is the allowlist
COMMENTED_CONFIG_SETTINGS = frozenset(("COLOR_THEME",))


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)) | COMMENTED_CONFIG_SETTINGS


# Returns the literal values the built-in config template ships with, used to clear a section the user declined
def _config_template_defaults():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    defaults = {}
    for statement in template_tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        try:
            defaults[statement.targets[0].id] = ast.literal_eval(statement.value)
        except ValueError:
            continue
    return defaults


# Keeps argparse from colouring its own help, so the help screen is coloured by this tool alone and --no-color is
# not left with a second palette to silence. From Python 3.14 argparse colours the help by default on a terminal
def argparse_color_kwargs() -> dict[str, Any]:
    return {"color": False} if sys.version_info >= (3, 14) else {}


# Returns the --config-file value straight from the arguments, before argparse has run
def early_config_file_argument(arguments=None):
    values = list(sys.argv[1:] if arguments is None else arguments)
    for index, argument in enumerate(values):
        if argument == "--config-file" and index + 1 < len(values):
            return values[index + 1]
        if argument.startswith("--config-file="):
            return argument.split("=", 1)[1]
    return None


# Applies the config settings that take effect before argument parsing, leaving errors to the later load.
# The screen clear and the startup banner both run before argparse, so a configured CLEAR_SCREEN or
# COLORED_OUTPUT would otherwise only take effect after the first output was already written
def apply_early_output_config():
    global CLEAR_SCREEN, COLORED_OUTPUT, COLOR_THEME

    try:
        cli_path = early_config_file_argument()
        if cli_path is not None and cli_path.casefold() == "none":
            # Config discovery is disabled for this run, so there is nothing to peek at
            return
        config_path = find_config_file(os.path.expanduser(cli_path) if cli_path else None)
        if not config_path:
            return
        # Reading a config no longer runs it, so this early peek cannot have side effects
        values = parse_config_content(Path(config_path).read_text(encoding="utf-8"), str(config_path))
    except Exception:
        # A broken or unreadable config is reported with full detail once the arguments are parsed
        return
    if isinstance(values.get("CLEAR_SCREEN"), bool):
        CLEAR_SCREEN = values["CLEAR_SCREEN"]
    if isinstance(values.get("COLORED_OUTPUT"), bool):
        COLORED_OUTPUT = values["COLORED_OUTPUT"]
    # --help is printed and exited from inside argparse, long before the config load, so the help_* overrides
    # have to be here or they could never colour the one screen they name. Unusable styles are dropped downstream
    if isinstance(values.get("COLOR_THEME"), dict):
        COLOR_THEME = values["COLOR_THEME"]


# Returns the parsed value with a legacy numeric on/off setting read as the boolean it stands for
def _normalized_config_value(name, value, defaults):
    # 0 and 1 were accepted for these settings before the values were checked, so they still mean off and on
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1) and isinstance(defaults.get(name), bool):
        return bool(value)
    return value


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content, filename="<config>", retired_out=None, reference_values=None):
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
    template_defaults = _config_template_defaults()
    parsed_values = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError(f"Line {getattr(statement, 'lineno', '?')}: only NAME = value assignments are allowed")
        name = statement.targets[0].id
        if name in RETIRED_CONFIG_SETTINGS and name not in allowed_names:
            if retired_out is not None and name not in retired_out:
                retired_out.append(name)
            continue
        if name not in allowed_names:
            raise ValueError(f"Line {statement.lineno}: unsupported configuration setting {name!r}")
        # One setting may reuse another, which the built-in template does and existing configs copy
        if isinstance(statement.value, ast.Name):
            referenced = statement.value.id
            if referenced not in allowed_names:
                raise ValueError(f"Line {statement.lineno}: {name} may only reference another configuration setting")
            source = parsed_values if referenced in parsed_values else (reference_values if reference_values is not None else globals())
            if referenced not in source:
                raise ValueError(f"Line {statement.lineno}: {name} references {referenced!r} before it has a value")
            parsed_values[name] = source[referenced]
            continue
        try:
            parsed_values[name] = _normalized_config_value(name, ast.literal_eval(statement.value), template_defaults)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
            raise ValueError(f"Line {statement.lineno}: {name} must be a plain value such as a number, string, True, False, None, list, tuple or dict") from exc
    return parsed_values


# Validates config content through the same restricted parser used at startup
def validate_config_content(content, filename="<generated-config>"):
    parse_config_content(content, filename)


# Reports settings an older version wrote that this version no longer defines
def describe_retired_settings(names, quoted_path):
    listed = ", ".join(sorted(names))
    return f"Config file {quoted_path} contains settings this version no longer uses, which were ignored: {listed}"


# Loads a config file as data and applies only recognized literal settings
def load_config_file(config_path, namespace=None, report_errors=True, advice_out=None):
    selected_namespace = globals() if namespace is None else namespace
    retired_settings = []
    try:
        content = Path(config_path).read_text(encoding="utf-8")
        # Parsed as data rather than executed, so a config file picked up from the working directory cannot run code
        parsed_values = parse_config_content(content, str(config_path), retired_settings)
        selected_namespace.update(parsed_values)
        # Only a load that reaches the module settings records a choice, not a copy read for the wizard or a report
        if selected_namespace is globals():
            CONFIGURED_SETTING_NAMES.update(parsed_values)
        debug_print("Configuration applied", path=str(config_path), settings=len(parsed_values), names=", ".join(sorted(parsed_values)) or "none")
        if retired_settings and report_errors:
            print(f"* Note: {describe_retired_settings(retired_settings, chr(39) + str(config_path) + chr(39))}")
        return True
    except SyntaxError as exc:
        detail = f"Config file '{config_path}' has invalid Python syntax"
        if exc.lineno is not None:
            detail += f" at line {exc.lineno}"
        detail += f" | Parser: {exc.msg}"
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}"
    debug_print("Configuration load", path=str(config_path), outcome="failed", reason=detail)
    advice = classify_recovery_error(context="config.invalid", detail=detail)
    if advice_out is not None:
        advice_out.append(advice)
    if report_errors:
        print_recovery_advice(advice)
    return False


# Parses a command-line interval value as a positive integer
def positive_interval_arg(value):
    try:
        parsed = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("must be an integer greater than 0") from e
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be an integer greater than 0")
    return parsed


# Coerces a timer setting to an integer with optional zero support
def normalize_timer_setting(name, value, allow_zero=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError(f"{name} must be an integer") from e
    if parsed < 0 or (parsed == 0 and not allow_zero):
        if allow_zero:
            raise ValueError(f"{name} must be 0 or greater")
        raise ValueError(f"{name} must be greater than 0")
    return parsed


# Validates the finalized connectivity timeout and token refresh retry values
def validate_connectivity_timer():
    global CHECK_INTERNET_TIMEOUT, TOKEN_REFRESH_RETRIES, TOKEN_REFRESH_RETRY_DELAY, XBOX_API_TIMEOUT
    CHECK_INTERNET_TIMEOUT = normalize_timer_setting("CHECK_INTERNET_TIMEOUT", CHECK_INTERNET_TIMEOUT)
    XBOX_API_TIMEOUT = normalize_timer_setting("XBOX_API_TIMEOUT", XBOX_API_TIMEOUT)
    TOKEN_REFRESH_RETRIES = normalize_timer_setting("TOKEN_REFRESH_RETRIES", TOKEN_REFRESH_RETRIES)
    TOKEN_REFRESH_RETRY_DELAY = normalize_timer_setting("TOKEN_REFRESH_RETRY_DELAY", TOKEN_REFRESH_RETRY_DELAY)


# Validates finalized monitor timer values and refreshes the liveness counter
def validate_monitor_timers():
    global LIVENESS_REMINDER_SECONDS, LIVENESS_CHECK_INTERVAL, XBOX_ACTIVE_CHECK_INTERVAL, XBOX_CHECK_INTERVAL
    XBOX_CHECK_INTERVAL = normalize_timer_setting("XBOX_CHECK_INTERVAL", XBOX_CHECK_INTERVAL)
    XBOX_ACTIVE_CHECK_INTERVAL = normalize_timer_setting("XBOX_ACTIVE_CHECK_INTERVAL", XBOX_ACTIVE_CHECK_INTERVAL)
    LIVENESS_CHECK_INTERVAL = normalize_timer_setting("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL, allow_zero=True)
    # Whole checks, so a check interval longer than the liveness interval still waits one check instead of reporting on every check
    LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0


# Main function that monitors activity of the specified Xbox user
async def xbox_monitor_user(xbox_gamertag, csv_file_name, achievements_count=5, games_count=10):

    alive_since = int(time.time())
    status_ts = 0
    status_ts_old = 0
    status_online_start_ts = 0
    status_online_start_ts_old = 0
    lastonline_ts = 0
    status = ""
    xuid = 0
    title_name = ""
    game_name = ""
    platform = ""
    game_ts = 0
    game_ts_old = 0
    game_total_ts = 0
    games_number = 0
    game_total_after_offline_counted = False
    title_history_ts_old = 0  # Track previous title history timestamp for "appear offline" activity detection
    title_history_game_old = ""  # Track game name for "appear offline" activity detection
    presence_lastonline_cache_ts = 0  # Last known valid presence.last_seen timestamp
    offline_grace_attempts = 3
    offline_grace_delay_seconds = 2

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file.unwritable", detail=f"The CSV file '{csv_file_name}' could not be prepared: {e}")

    # Create a XBOX HTTP client session
    async with create_signed_session() as session:

        # Initialize with global OAUTH config options (MS_APP_CLIENT_ID & MS_APP_CLIENT_SECRET)
        auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, "")

        # The monitoring heading above already named the target, so this line does not repeat it
        print("* Fetching profile details...\n")

        # Helper to print step message
        def _print_step(msg):
            global STDOUT_AT_START_OF_LINE
            sys.stdout.write(f"- {msg}".ljust(32))
            sys.stdout.flush()
            STDOUT_AT_START_OF_LINE = False

        # Helper to print OK
        def _print_ok():
            global STDOUT_AT_START_OF_LINE
            print("OK")
            STDOUT_AT_START_OF_LINE = True

        _print_step("Authenticating with Xbox...")
        try:
            await authenticate_and_refresh_tokens(auth_mgr)
        except Exception as e:
            print()
            print_recovery_error(e, context="auth", detail=f"Signing in to Xbox Live failed: {format_exception(e)}")
            sys.exit(1)

        _print_ok()

        # Construct the Xbox API client from AuthenticationManager instance
        xbl_client = XboxLiveClient(auth_mgr)
        auth_refresh_version = XBOX_AUTH_REFRESH_VERSION

        await get_user_info(xbox_gamertag, client=xbl_client, show_friends=False, show_recent_achievements=False, show_recent_games=False, achievements_count=achievements_count, games_count=games_count)

        # Get profile for user with specified gamer tag to grab some details like XUID
        try:
            profile = await xbl_client.profile.get_profile_by_gamertag(xbox_gamertag)
        except Exception as e:
            print_recovery_error(e, context="target", detail=f"The profile for '{xbox_gamertag}' could not be read: {e}")
            sys.exit(1)

        if 'profile_users' in dir(profile):

            try:
                xuid = int(profile.profile_users[0].id)
            except IndexError:
                print_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned a profile for '{xbox_gamertag}' with no account in it")
                sys.exit(1)

        if xuid == 0:
            print_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned no XUID for '{xbox_gamertag}'")
            sys.exit(1)

        # Get presence status (by XUID)
        try:
            presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
        except Exception as e:
            print_recovery_error(e, context="target", detail=f"The presence for '{xbox_gamertag}' could not be read: {e}")
            sys.exit(1)

        status, title_name, game_name, platform, lastonline_ts = xbox_process_presence_class(presence, False)
        if lastonline_ts > 0:
            presence_lastonline_cache_ts = lastonline_ts

        # Establish title history baseline
        title_history_ts, title_history_game = await xbox_get_latest_title_played_ts(xbl_client, xuid)

        if title_history_ts > 0:
            title_history_ts_old = title_history_ts
            title_history_game_old = title_history_game

        # Only use this when user appears offline - otherwise presence data is accurate
        if status == "offline":
            debug_print("Title history fallback", state="offline", source="already fetched")
            lastonline_ts, fallback_used = xbox_get_best_lastonline_ts(lastonline_ts, title_history_ts)
            if fallback_used:
                lastonline_ts = title_history_ts
        if not status:
            print_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned no online status for '{xbox_gamertag}'")
            sys.exit(1)

        status_ts_old = int(time.time())
        status_ts_old_bck = status_ts_old

        if status and status != "offline":
            status_online_start_ts = status_ts_old
            status_online_start_ts_old = status_online_start_ts

        xbox_last_status_file = resolve_status_file(xbox_gamertag)
        last_status_read = []
        last_status_ts = 0
        last_status = ""

        if os.path.isfile(xbox_last_status_file):
            try:
                last_status_read = reconcile_status_record(read_status_record(xbox_last_status_file), xbox_last_status_file)
            except Exception as e:
                print()
                print_recovery_error(e, context="file.unreadable", detail=f"Cannot load the saved status from '{xbox_last_status_file}': {e}. Correct the file or move it aside to start a new history")
                raise SystemExit(1) from None
            if last_status_read:
                last_status_ts = last_status_read[0]
                last_status = last_status_read[1]
                xbox_last_status_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(xbox_last_status_file)), pytz.timezone(LOCAL_TIMEZONE))

                print(f"\n* Last status loaded from file '{xbox_last_status_file}' ({get_short_date_from_ts(xbox_last_status_file_mdate_dt, show_weekday=False, always_show_year=True)})")

                if last_status_ts > 0:
                    last_status_dt_str = get_short_date_from_ts(last_status_ts, show_weekday=False, always_show_year=True)
                    print(f"* Last status read from file: {str(last_status).upper()} ({last_status_dt_str})")

                    if lastonline_ts and status == "offline":
                        if lastonline_ts >= last_status_ts:
                            status_ts_old = lastonline_ts
                        else:
                            status_ts_old = last_status_ts
                    if not lastonline_ts and status == "offline":
                        status_ts_old = last_status_ts
                    if status and status != "offline" and status == last_status:
                        status_online_start_ts = last_status_ts
                        status_online_start_ts_old = status_online_start_ts
                        status_ts_old = last_status_ts

        if last_status_ts > 0 and status != last_status:
            try:
                save_last_status(xbox_last_status_file, status_ts_old, status)
            except Exception as e:
                print()
                print_recovery_error(e, context="file.unwritable", detail=f"The last status could not be saved to '{xbox_last_status_file}': {e}")

        if status != "offline" and game_name:
            print(f"\nUser is currently in-game:\t{game_name}")
            game_ts_old = int(time.time())
            games_number += 1

        try:
            if csv_file_name and (status != last_status):
                write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
        except Exception as e:
            print_recovery_error(e, context="file.unwritable", detail=f"The CSV entry could not be written to '{csv_file_name}': {e}")

        if last_status_ts == 0:
            if lastonline_ts and status == "offline":
                status_ts_old = lastonline_ts
            try:
                save_last_status(xbox_last_status_file, status_ts_old, status)
            except Exception as e:
                print_recovery_error(e, context="file.unwritable", detail=f"The last status could not be saved to '{xbox_last_status_file}': {e}")

        if status_ts_old != status_ts_old_bck:
            if status == "offline":
                last_status_dt_str = get_date_from_ts(status_ts_old)
                print(f"\n* Last time user was available:\t{last_status_dt_str}")
            print(f"\n* User is {str(status).upper()} for:\t\t{calculate_timespan(now_local(), int(status_ts_old), show_seconds=False)}")

        status_old = status
        game_name_old = game_name

        print_cur_ts("\nTimestamp:\t\t\t")

        alive_since = int(time.time())
        error_alert = ErrorAlertState()
        # A poll that keeps failing for the same reason repeats the fix paragraph on every cycle without it
        recovery_hints = RecoveryHintTracker()
        # Every failed check prints its advice, so the end of a streak is worth one line closing it
        error_streak = 0
        outage = OutageReporter()

        m_subject = m_body = ""

        if status and status != "offline":
            sleep_interval = XBOX_ACTIVE_CHECK_INTERVAL
        else:
            sleep_interval = XBOX_CHECK_INTERVAL

        await asyncio.sleep(sleep_interval)

        # Main loop
        check_count = 0
        while True:
            check_count += 1
            reports_before_check = REPORTS_PRINTED
            try:
                if auth_refresh_version != XBOX_AUTH_REFRESH_VERSION:
                    auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, "")
                    await authenticate_and_refresh_tokens(auth_mgr)
                    xbl_client = XboxLiveClient(auth_mgr)
                    auth_refresh_version = XBOX_AUTH_REFRESH_VERSION
                    print("* Xbox authentication client recreated after credential reload")
                presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
                status, title_name, game_name, platform, lastonline_ts = xbox_process_presence_class(presence)
                if lastonline_ts > 0:
                    presence_lastonline_cache_ts = lastonline_ts

                if status == "offline":
                    # Give presence a short grace window when transitioning to offline with missing last_seen
                    if status_old != "offline" and lastonline_ts <= 0:
                        debug_print("Offline grace retry", reason="the offline transition carried no presence timestamp", attempts=offline_grace_attempts, delay=f"{offline_grace_delay_seconds}s")
                        for retry_num in range(1, offline_grace_attempts + 1):
                            debug_print("Sleep", seconds=offline_grace_delay_seconds, reason="waiting between offline grace retries")
                            await asyncio.sleep(offline_grace_delay_seconds)
                            retry_presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
                            retry_status, retry_title_name, retry_game_name, retry_platform, retry_lastonline_ts = xbox_process_presence_class(retry_presence)
                            debug_print("Offline grace retry attempt", attempt=f"{retry_num}/{offline_grace_attempts}", state=retry_status, lastonline=get_debug_date_from_ts(retry_lastonline_ts))

                            # Use refreshed offline payload if it now includes last_seen
                            if retry_status == "offline" and retry_lastonline_ts > 0:
                                status = retry_status
                                game_name = retry_game_name
                                platform = retry_platform
                                lastonline_ts = retry_lastonline_ts
                                presence_lastonline_cache_ts = retry_lastonline_ts
                                debug_print("Offline grace retry", outcome="OK", source="refreshed presence last_seen")
                                break

                            # If status bounced back online, stop offline fallback for this poll.
                            if retry_status and retry_status != "offline":
                                status = retry_status
                                game_name = retry_game_name
                                platform = retry_platform
                                lastonline_ts = retry_lastonline_ts
                                if retry_lastonline_ts > 0:
                                    presence_lastonline_cache_ts = retry_lastonline_ts
                                debug_print("Offline grace retry", outcome="skipped", reason="the user is no longer offline")
                                break

                if status == "offline":
                    debug_print("Title history fallback", state="offline", source="fresh fetch")
                    title_history_ts, title_history_game = await xbox_get_latest_title_played_ts(xbl_client, xuid)
                    presence_ts_for_decision = lastonline_ts
                    lastactive_source = "presence_last_seen_live"
                    lastactive_confidence = "high"

                    if presence_ts_for_decision <= 0 and presence_lastonline_cache_ts > 0:
                        presence_ts_for_decision = presence_lastonline_cache_ts
                        lastactive_source = "presence_last_seen_cached"
                        lastactive_confidence = "medium"
                        debug_print("Last active input", source="cached presence last_seen", ts=get_debug_date_from_ts(presence_ts_for_decision))
                    elif presence_ts_for_decision <= 0:
                        lastactive_source = "presence_last_seen_missing"
                        lastactive_confidence = "none"
                        verbose_notice("Xbox Live reported no last-seen timestamp, so the last active time is taken from the title history instead")

                    effective_lastactive_ts, source_is_history = xbox_get_best_lastonline_ts(presence_ts_for_decision, title_history_ts)
                    if source_is_history:
                        lastactive_source = "title_history_fallback"
                        lastactive_confidence = "low"

                    debug_print("Poll state", status=status)
                    debug_print("Title history state", ts=title_history_ts, game=title_history_game)
                    debug_print("Title history baseline", ts=title_history_ts_old, game=title_history_game_old)
                    debug_print("Last active chosen", source=lastactive_source, confidence=lastactive_confidence, ts=get_debug_date_from_ts(effective_lastactive_ts))

                if not status:
                    raise ValueError('Xbox user status is empty')
                outage_lasted = outage.recovered()
                if error_streak:
                    debug_print("Recovered", streak=error_streak)
                    if outage_lasted is not None:
                        print_outage_recovery(xbox_gamertag, outage_lasted)
                error_streak = 0
                error_alert.reset()
                recovery_hints.reset()
            except Exception as e:
                if status and status != "offline":
                    sleep_interval = XBOX_ACTIVE_CHECK_INTERVAL
                else:
                    sleep_interval = XBOX_CHECK_INTERVAL
                error_streak += 1
                advice = classify_recovery_error(e, context="monitor", detail=f"Reading the presence for '{xbox_gamertag}' failed: {e}")
                debug_print("Presence check", check=f"#{check_count}", outcome="failed", error=f"{type(e).__name__}: {e}", recovery_code=advice.code, retryable=advice.retryable, streak=error_streak)
                exhausted = advice.code == "resource.exhausted"
                # A failure that has not changed is left to the liveness cadence rather than repeated every check
                outage_outcome = outage.failed(advice)
                # A failure the tool can retry away is alerted once the outage has lasted ERROR_ALERT_AFTER_SECONDS, one it cannot at once
                alert_due = not advice.retryable or int(time.time()) - outage.since >= ERROR_ALERT_AFTER_SECONDS
                delivery_reported = False
                if outage_outcome == "full":
                    print_recovery_advice(advice, tracker=recovery_hints, retry_note="" if exhausted else f"retrying in {display_time(sleep_interval)}")
                elif outage_outcome == "changed":
                    print_outage_change(xbox_gamertag, advice)
                elif outage_outcome == "reminder":
                    print_outage_liveness(xbox_gamertag, advice, outage.since, outage.failures)
                now = int(time.time())
                error_email_pending = alert_due and error_alert.pending("email", ERROR_NOTIFICATION, now)
                error_webhook_pending = alert_due and error_alert.pending("webhook", webhook_event_enabled("error"), now)
                if error_email_pending or error_webhook_pending:
                    email_delivered, webhook_delivered = send_notification_channels("error", recovery_email_subject(advice, xbox_gamertag), recovery_email_body(advice, error_streak), email_enabled=error_email_pending, webhook_enabled=error_webhook_pending)
                    error_alert.record("email", error_email_pending, email_delivered, now)
                    error_alert.record("webhook", error_webhook_pending, webhook_delivered, now)
                    # A retry can reach the screen on a check the outage reporter keeps quiet, and a delivery line
                    # with nothing under it reads as a run that stopped there
                    delivery_reported = True
                if outage_outcome in ("full", "changed") or exhausted or delivery_reported:
                    print_cur_ts("Timestamp:\t\t\t")
                # A local file descriptor limit cannot be retried away inside this process
                if exhausted:
                    sys.exit(2)
                debug_print("Sleep", seconds=sleep_interval, reason="the presence check failed")
                await asyncio.sleep(sleep_interval)
                continue

            change = False
            act_inact_flag = False

            status_ts = int(time.time())
            game_ts = int(time.time())

            # Player status changed
            if status != status_old:

                platform_str = ""
                if platform:
                    platform_str = f" ({platform})"

                try:
                    save_last_status(xbox_last_status_file, status_ts, status)
                except Exception as e:
                    print_recovery_error(e, context="file.unwritable", detail=f"The last status could not be saved to '{xbox_last_status_file}': {e}", label="Warning")

                print(f"Xbox user {xbox_gamertag} changed status from {status_old} to {status}{platform_str}")
                status_range = get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True, always_show_year=True)
                print(f"User was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))} ({status_range})")

                m_subject_was_since = f", was {status_old}: {status_range}"
                m_subject_after = calculate_timespan(int(status_ts), int(status_ts_old), show_seconds=False)
                m_body_was_since = f" ({status_range})"

                m_body_short_offline_msg = ""

                # Player got online
                if status_old == "offline" and status and status != "offline":
                    print(f"*** User got ACTIVE ! (was offline since {get_date_from_ts(status_ts_old)})")
                    game_total_after_offline_counted = False
                    if (status_ts - status_ts_old) > OFFLINE_INTERRUPT or not status_online_start_ts_old:
                        status_online_start_ts = status_ts
                        game_total_ts = 0
                        games_number = 0
                    elif (status_ts - status_ts_old) <= OFFLINE_INTERRUPT and status_online_start_ts_old > 0:
                        status_online_start_ts = status_online_start_ts_old
                        short_offline_msg = f"Short offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}"
                        m_body_short_offline_msg = f"\n\n{short_offline_msg}"
                        print(short_offline_msg)
                    act_inact_flag = True

                m_body_played_games = ""

                # Player got offline
                if status_old and status_old != "offline" and status == "offline":
                    # Sync baseline with current title history to prevent false "appear offline" detection
                    if title_history_ts > 0:
                        title_history_ts_old = title_history_ts
                        title_history_game_old = title_history_game
                    if status_online_start_ts > 0:
                        m_subject_after = calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)
                        online_range = get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True, always_show_year=True)
                        online_since_msg = f"(after {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)}: {online_range})"
                        m_subject_was_since = f", was available: {online_range}"
                        m_body_was_since = f" ({status_range})\n\nUser was available for {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)} ({online_range})"
                    else:
                        online_since_msg = ""
                    if games_number > 0:
                        if game_name_old and not game_name:
                            game_total_ts += (int(game_ts) - int(game_ts_old))
                            game_total_after_offline_counted = True
                        games_word = "game" if games_number == 1 else "games"
                        m_body_played_games = f"\n\nUser played {games_number} {games_word} for total time of {display_time(game_total_ts)}"
                        print(f"User played {games_number} {games_word} for total time of {display_time(game_total_ts)}")
                    print(f"*** User got OFFLINE ! {online_since_msg}")
                    status_online_start_ts_old = status_online_start_ts
                    status_online_start_ts = 0
                    act_inact_flag = True

                m_body_user_in_game = ""
                if status != "offline" and game_name:
                    print(f"User is currently in-game: {game_name}{platform_str}")
                    m_body_user_in_game = f"\n\nUser is currently in-game: {game_name}{platform_str}"

                change = True

                m_body = f"Xbox user {xbox_gamertag} changed status from {status_old} to {status}{platform_str}\n\nUser was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{m_body_short_offline_msg}{m_body_user_in_game}{m_body_played_games}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                if platform:
                    platform_str = f"{platform}, "
                m_subject = f"Xbox user {xbox_gamertag} is now {status} ({platform_str}after {m_subject_after}{m_subject_was_since})"
                email_status_enabled = STATUS_NOTIFICATION or (ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag)
                webhook_status_enabled = webhook_event_enabled("all_status") or (webhook_event_enabled("status") and act_inact_flag)
                if email_status_enabled or webhook_status_enabled:
                    send_notification_channels("status", m_subject, m_body, email_enabled=email_status_enabled, webhook_enabled=webhook_status_enabled)

                status_ts_old = status_ts
                print_cur_ts("Timestamp:\t\t\t")

            # Player started/stopped/changed the game
            if game_name != game_name_old:

                platform_str = ""
                if platform:
                    platform_str = f" ({platform})"

                # User changed the game
                if game_name_old and game_name:
                    print(f"Xbox user {xbox_gamertag} changed game from '{game_name_old}' to '{game_name}'{platform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                    game_range = get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, always_show_year=True, between_sep=' to ')
                    print(f"User played game from {game_range}")
                    game_total_ts += (int(game_ts) - int(game_ts_old))
                    games_number += 1
                    m_body = f"Xbox user {xbox_gamertag} changed game from '{game_name_old}' to '{game_name}'{platform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {game_range}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    if platform:
                        platform_str = f"{platform}, "
                    m_subject = f"Xbox user {xbox_gamertag} changed game to '{game_name}' ({platform_str}after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, always_show_year=True)})"

                # User started playing new game
                elif not game_name_old and game_name:
                    print(f"Xbox user {xbox_gamertag} started playing '{game_name}'{platform_str}")
                    games_number += 1
                    m_subject = f"Xbox user {xbox_gamertag} now plays '{game_name}'{platform_str}"
                    m_body = f"Xbox user {xbox_gamertag} now plays '{game_name}'{platform_str}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

                # User stopped playing the game
                elif game_name_old and not game_name:
                    print(f"Xbox user {xbox_gamertag} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                    game_range = get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, always_show_year=True, between_sep=' to ')
                    print(f"User played game from {game_range}")
                    if not game_total_after_offline_counted:
                        game_total_ts += (int(game_ts) - int(game_ts_old))
                    m_subject = f"Xbox user {xbox_gamertag} stopped playing '{game_name_old}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, always_show_year=True)})"
                    m_body = f"Xbox user {xbox_gamertag} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {game_range}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

                change = True

                if m_subject and m_body and (GAME_CHANGE_NOTIFICATION or webhook_event_enabled("game")):
                    send_notification_channels("game", m_subject, m_body, email_enabled=GAME_CHANGE_NOTIFICATION)

                game_ts_old = game_ts
                print_cur_ts("Timestamp:\t\t\t")

            # Detect newer activity without treating system surfaces as games
            if status == "offline" and title_history_ts > 0 and title_history_ts_old > 0 and title_history_ts > title_history_ts_old:
                activity_detected_ts = get_date_from_ts(title_history_ts)
                game_info = f" '{title_history_game}'" if title_history_game else ""
                if title_history_game:
                    print(f"User detected playing a game{game_info} (via title history)! Started: {activity_detected_ts}")
                    m_subject = f"Xbox user {xbox_gamertag} detected playing{game_info} (via title history)"
                    m_body = f"Xbox user {xbox_gamertag} appears offline but was detected starting a game{game_info}.\n\nGame session started: {activity_detected_ts}\n\nNote: This was detected via title history. We cannot detect when the user stops playing via this method.{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                else:
                    print(f"User activity detected (via title history)! Last active: {activity_detected_ts}")
                    m_subject = f"Xbox user {xbox_gamertag} activity detected (via title history)"
                    m_body = f"Xbox user {xbox_gamertag} appears offline but has newer activity in title history.\n\nLast active: {activity_detected_ts}\n\nThis record does not identify a game session.{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

                email_activity_enabled = ACTIVE_INACTIVE_NOTIFICATION or STATUS_NOTIFICATION
                webhook_activity_enabled = webhook_event_enabled("status") or webhook_event_enabled("all_status")
                if email_activity_enabled or webhook_activity_enabled:
                    send_notification_channels("status", m_subject, m_body, email_enabled=email_activity_enabled, webhook_enabled=webhook_activity_enabled)

                print_cur_ts("Timestamp:\t\t\t")
                title_history_ts_old = title_history_ts
                change = True

            if change:
                alive_since = int(time.time())

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
                except Exception as e:
                    print_recovery_error(e, context="file.unwritable", detail=f"The CSV entry could not be written to '{csv_file_name}': {e}")

            status_old = status
            game_name_old = game_name

            # The banner speaks for a quiet check, so anything this one reported restarts the clock instead of being contradicted by it
            if REPORTS_PRINTED != reports_before_check:
                alive_since = int(time.time())
            elif LIVENESS_REMINDER_SECONDS and int(time.time()) - alive_since >= LIVENESS_REMINDER_SECONDS:
                print_liveness_banner(f"Monitoring healthy for {xbox_gamertag}. The user is {status or 'unknown'} with no activity change since the last check")
                alive_since = int(time.time())

            debug_print("Completed check", check=f"#{check_count}", user=xbox_gamertag, outcome="OK", status=status or "unknown", game=game_name or None)

            if status and status != "offline":
                debug_print("Sleep", seconds=XBOX_ACTIVE_CHECK_INTERVAL, reason="the user is online")
                await asyncio.sleep(XBOX_ACTIVE_CHECK_INTERVAL)
            else:
                debug_print("Sleep", seconds=XBOX_CHECK_INTERVAL, reason="the user is offline")
                await asyncio.sleep(XBOX_CHECK_INTERVAL)


# Resolves command-line actions and initializes the selected runtime mode
def main():
    global CHECK_INTERNET_TIMEOUT, CLI_CONFIG_PATH, CONFIG_DISCOVERY_DISABLED, DOTENV_FILE, LOCAL_TIMEZONE, LOCAL_TIMEZONE_STATE, LIVENESS_REMINDER_SECONDS, LIVENESS_CHECK_INTERVAL, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, CSV_FILE, XBOX_STATUS_FILE, DISABLE_LOGGING, XBOX_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, STATUS_NOTIFICATION, ERROR_NOTIFICATION, WEBHOOK_ENABLED, WEBHOOK_PROVIDER, WEBHOOK_URL, WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION, WEBHOOK_GAME_CHANGE_NOTIFICATION, WEBHOOK_STATUS_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION, NTFY_ACCESS_TOKEN, XBOX_CHECK_INTERVAL, XBOX_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, stdout_bck, MS_AUTH_TOKENS_FILE, VERBOSE_MODE, DEBUG_MODE, EXPORTED_SECRET_KEYS, COLORED_OUTPUT, COLOR_THEME, TRUNCATE_CHARS

    if "--generate-config" in sys.argv and not any(flag in sys.argv for flag in SECRET_ACTION_FLAGS):
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        # A filename after the flag writes the file directly, which sidesteps the UTF-16 redirect PowerShell
        # produces for a piped template
        idx = sys.argv.index("--generate-config")
        output_file = sys.argv[idx + 1] if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-") else ""
        if output_file:
            try:
                backup_path, written = write_generated_config(output_file, config_content, force="--force" in sys.argv)
            except ConfigExistsError as exc:
                # Built here rather than from the context, so the fix names the file the user actually asked for
                print_recovery_advice(make_recovery_advice("file.exists", str(exc), recovery_fix_with_guide(f"Re-run with: {render_command(['--generate-config', output_file, '--force'], include_paths=False)}. The existing file is backed up with a timestamp first, or write to a different path", CONFIG_GUIDE_URL), False, str(exc)))
                sys.exit(1)
            except OSError as exc:
                print_recovery_error(exc, context="file.unwritable", detail=f"Config file '{output_file}' cannot be written: {exc}")
                sys.exit(1)
            if not written:
                print("Config was not replaced. The existing file is unchanged")
                sys.exit(1)
            print(f"Config written to: {output_file}")
            if backup_path:
                print(f"Previous config backed up to: {backup_path}")
            sys.exit(0)
        # No filename provided - write to stdout using buffer to ensure UTF-8
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # The screen clear and the startup banner both run before the arguments are parsed, so the few settings
    # that decide them are read here too
    apply_early_output_config()

    # Read straight from sys.argv because argparse has not run yet and the banner is printed before it does
    if "--no-color" in sys.argv:
        COLORED_OUTPUT = False

    init_color_output(stdout_bck)

    if not isinstance(sys.stdout, TerminalStream):
        sys.stdout = TerminalStream(sys.stdout)

    # Read straight from sys.argv because argparse has not run yet and the screen is cleared before it does
    if "--debug" in sys.argv:
        DEBUG_MODE = True
    if CLEAR_SCREEN and DEBUG_MODE:
        debug_print("Terminal screen clear", outcome="skipped", reason="debug mode is active")
    clear_screen(CLEAR_SCREEN and not keep_terminal_history() and not DEBUG_MODE)

    print_startup_banner()

    parser = ColoredHelpParser(
        prog="xbox_monitor",
        description=("Monitor an Xbox user's playing status and send customizable email alerts [ https://github.com/misiektoja/xbox_monitor/ ]"), epilog=help_examples(), formatter_class=argparse.RawTextHelpFormatter, **argparse_color_kwargs()
    )

    # Positional
    parser.add_argument(
        "xbox_gamertag",
        nargs="?",
        metavar="XBOX_GAMERTAG",
        help="User's Xbox gamer tag",
        type=str
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--generate-config",
        dest="generate_config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Let --generate-config replace an existing file, after a timestamped backup"
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--setup",
        dest="setup",
        action="store_true",
        help="Run the guided setup and write a ready-to-run configuration"
    )
    conf.add_argument(
        "--set-ms-app-credentials",
        dest="set_ms_app_credentials",
        action="store_true",
        help="Enter the Microsoft application credentials privately, authorize once and save them to the dotenv file",
    )
    conf.add_argument(
        "--set-smtp-password",
        dest="set_smtp_password",
        action="store_true",
        help="Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Save a Discord or ntfy webhook URL through a hidden prompt",
    )
    conf.add_argument(
        "--doctor",
        dest="doctor",
        action="store_true",
        help="Run read-only preflight checks and report what is ready and what is not",
    )

    # API credentials
    creds = parser.add_argument_group("API credentials")
    creds.add_argument(
        "-u", "--ms-app-client-id",
        dest="ms_app_client_id",
        metavar="MS_APP_CLIENT_ID",
        help="Microsoft Azure application client ID",
        type=str
    )
    creds.add_argument(
        "-w", "--ms-app-client-secret",
        dest="ms_app_client_secret",
        metavar="MS_APP_CLIENT_SECRET",
        help="Microsoft Azure application client secret",
        type=str
    )

    # Email notifications
    notify = parser.add_argument_group("Email notifications")
    notify.add_argument(
        "-a", "--notify-active-inactive",
        dest="notify_active_inactive",
        action="store_true",
        default=None,
        help="Email when user goes online/offline"
    )
    notify.add_argument(
        "-g", "--notify-game-change",
        dest="notify_game_change",
        action="store_true",
        default=None,
        help="Email on game start/change/stop"
    )
    notify.add_argument(
        "-s", "--notify-status",
        dest="notify_status",
        action="store_true",
        default=None,
        help="Email on all status changes"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="notify_errors",
        action="store_false",
        default=None,
        help="Do not email on errors"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    webhook = parser.add_argument_group("Webhook notifications")
    webhook_toggle = webhook.add_mutually_exclusive_group()
    webhook_toggle.add_argument(
        "--webhook",
        dest="webhook_enabled",
        action="store_true",
        default=None,
        help="Enable the configured webhook alerts"
    )
    webhook_toggle.add_argument(
        "--no-webhook",
        dest="webhook_enabled",
        action="store_false",
        default=None,
        help="Disable the configured webhook alerts"
    )
    webhook.add_argument(
        "--webhook-url",
        dest="webhook_url",
        metavar="URL",
        type=str,
        help="Discord webhook or ntfy topic URL for this run (may stay in shell history, prefer --set-webhook-url)"
    )
    webhook.add_argument(
        "--webhook-provider",
        dest="webhook_provider",
        choices=("discord", "ntfy"),
        help="Webhook request format for this run (default: configured provider)"
    )
    webhook.add_argument(
        "--webhook-active-inactive",
        dest="webhook_active_inactive",
        action="store_true",
        default=None,
        help="Send a webhook alert when user goes online/offline"
    )
    webhook.add_argument(
        "--webhook-game-change",
        dest="webhook_game_change",
        action="store_true",
        default=None,
        help="Send a webhook alert on game start/change/stop"
    )
    webhook.add_argument(
        "--webhook-status",
        dest="webhook_status",
        action="store_true",
        default=None,
        help="Send a webhook alert on all status changes"
    )
    webhook_error_toggle = webhook.add_mutually_exclusive_group()
    webhook_error_toggle.add_argument(
        "--webhook-errors",
        dest="webhook_errors",
        action="store_true",
        default=None,
        help="Send a webhook alert on errors"
    )
    webhook_error_toggle.add_argument(
        "--no-webhook-error-notify",
        dest="webhook_errors",
        action="store_false",
        default=None,
        help="Disable webhook alerts on errors"
    )
    webhook.add_argument(
        "--send-test-webhook",
        dest="send_test_webhook",
        action="store_true",
        help="Send one test webhook without starting monitoring"
    )

    # Intervals & timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=positive_interval_arg,
        help="Polling interval when user is offline"
    )
    times.add_argument(
        "-k", "--active-interval",
        dest="active_interval",
        metavar="SECONDS",
        type=positive_interval_arg,
        help="Polling interval when user is online"
    )

    # User information & listing
    info = parser.add_argument_group("User information & listing")
    info.add_argument(
        "-i", "--info",
        dest="info_mode",
        action="store_true",
        default=None,
        help="Show detailed user info and exit"
    )
    info.add_argument(
        "-f", "--friends",
        dest="show_friends",
        action="store_true",
        default=None,
        help="Show friends list (only works with -i/--info)"
    )
    info.add_argument(
        "-r", "--recent-achievements",
        dest="show_recent_achievements",
        action="store_true",
        default=None,
        help="Show recent achievements (only works with -i/--info)"
    )
    info.add_argument(
        "-n", "--achievements-count",
        dest="achievements_count",
        metavar="NUMBER",
        type=int,
        default=5,
        help="Limit number of recent achievements to display (default: 5)"
    )
    info.add_argument(
        "-m", "--games-count",
        dest="games_count",
        metavar="NUMBER",
        type=int,
        default=10,
        help="Limit number of recently played games to display (default: 10)"
    )

    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write status & game changes to CSV"
    )
    opts.add_argument(
        "--status-file",
        dest="status_file",
        metavar="PATH",
        type=str,
        help="File to save the last seen status to (default: xbox_<xbox_gamertag>_last_status.json)"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to xbox_monitor_<xbox_gamertag>.log"
    )
    opts.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=None,
        help="Disable coloured output in the terminal"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose_mode",
        action="store_true",
        default=None,
        help="Report rare operational events such as recoveries and degraded features"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode for technical logging"
    )

    args = parser.parse_args()
    DOTENV_STARTUP_ERRORS.clear()
    env_path = None

    selected_secret_actions = [flag for flag, selected in zip(SECRET_ACTION_FLAGS, (args.set_ms_app_credentials, args.set_smtp_password, args.set_webhook_url), strict=True) if selected]
    if len(selected_secret_actions) > 1:
        parser.error(f"{selected_secret_actions[0]} cannot be combined with {selected_secret_actions[1]}")

    # Applied before the config file is read so a failing load is already visible and again after it so a saved
    # DEBUG_MODE = False cannot switch off what the command line asked for
    apply_diagnostic_cli_flags(args)

    # "none" is the documented sentinel that switches discovery off, so it is a selection rather than a missing file
    CONFIG_DISCOVERY_DISABLED = args.config_file is not None and str(args.config_file).casefold() == "none"
    if CONFIG_DISCOVERY_DISABLED:
        CLI_CONFIG_PATH = None
    elif args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = None if CONFIG_DISCOVERY_DISABLED else find_config_file(CLI_CONFIG_PATH)

    # Doctor reports a broken setup instead of exiting on the first thing it finds, so the whole report is usable
    doctor_mode = bool(args.doctor)
    config_advice = None

    if not cfg_path and CLI_CONFIG_PATH and not args.setup:
        config_advice = classify_recovery_error(context="config.missing", detail=f"Config file '{CLI_CONFIG_PATH}' does not exist")
        if not doctor_mode:
            print_recovery_advice(config_advice)
            sys.exit(1)

    if cfg_path:
        reported_advice = []
        if not load_config_file(cfg_path, report_errors=not doctor_mode, advice_out=reported_advice):
            if not doctor_mode:
                sys.exit(1)
            config_advice = reported_advice[0]
            cfg_path = None

    # Applied again, so a saved DEBUG_MODE cannot switch off a flag the user just typed
    apply_diagnostic_cli_flags(args)

    # Re-initialised so a COLORED_OUTPUT or COLOR_THEME from the config file takes effect before the welcome
    # screen, the setup wizard or doctor print anything, with --no-color still winning over both
    if args.no_color:
        COLORED_OUTPUT = False
    init_color_output(stdout_bck)

    # A gamertag given on the command line always wins over the saved one
    if not args.xbox_gamertag and XBOX_GAMERTAG:
        args.xbox_gamertag = XBOX_GAMERTAG
        debug_print("Gamertag resolved", source="configuration file", value=args.xbox_gamertag)

    # Evaluated after the config file is read, so a saved gamertag starts monitoring instead of being welcomed
    if len(sys.argv) == 1 and not args.xbox_gamertag:
        sys.exit(print_welcome_screen(config_file=args.config_file, env_file=args.env_file))

    prepare_configured_paths(args)

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    # Which secrets were already exported has to be captured before load_dotenv copies the file's values into
    # os.environ, because afterwards the two sources are indistinguishable
    # An empty export is a shell-profile leftover rather than a value, so it is dropped before the dotenv load,
    # which would otherwise keep it and leave the file's value unused
    for secret in SECRET_KEYS:
        if os.environ.get(secret) == "":
            os.environ.pop(secret)
    EXPORTED_SECRET_KEYS = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret))
    SECRET_SOURCES.clear()
    for secret in SECRET_KEYS:
        if secret_is_set(globals().get(secret)):
            record_secret_source(secret, "configuration file")

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import find_dotenv

            # Startup exports retain priority over file entries at startup and reload
            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    # A command that is about to write this file is not warned that it is missing
                    if not command_writes_dotenv(sys.argv[1:]):
                        print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_managed_dotenv(env_path, override=False)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_managed_dotenv(env_path, override=False)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print_recovery_advice(missing_dependency_advice("python-dotenv", f"The dotenv file '{env_path}' cannot be read", "Or export the secrets as environment variables"), label="Warning")
            print()
        except (OSError, UnicodeError, ValueError) as exc:
            detail, fix = dotenv_load_problem(env_path, exc)
            DOTENV_STARTUP_ERRORS[str(env_path)] = (detail, fix)
            if not args.doctor:
                print_recovery_advice(make_recovery_advice("file.unreadable", detail, recovery_fix_with_guide(fix, CONFIG_GUIDE_URL), False))
                if not command_reports_configuration(args):
                    sys.exit(1)

    apply_environment_secrets()

    try:
        validate_connectivity_timer()
    except ValueError as e:
        advice = classify_recovery_error(context="config.invalid", detail=str(e))
        if not doctor_mode:
            print_recovery_advice(advice)
            sys.exit(1)
        if config_advice is None:
            config_advice = advice

    timezone_advice = resolve_local_timezone()

    if timezone_advice is not None:
        if not doctor_mode:
            print_recovery_advice(timezone_advice)
            sys.exit(1)
        # The report still stamps timestamps, so it falls back rather than stopping before the diagnosis
        LOCAL_TIMEZONE = "UTC"

    # The command-line credentials have to be in effect before the report checks them
    if args.ms_app_client_id:
        MS_APP_CLIENT_ID = args.ms_app_client_id
        record_secret_source("MS_APP_CLIENT_ID", "command line", MS_APP_CLIENT_ID)

    if args.ms_app_client_secret:
        MS_APP_CLIENT_SECRET = args.ms_app_client_secret
        record_secret_source("MS_APP_CLIENT_SECRET", "command line", MS_APP_CLIENT_SECRET)

    if args.check_interval is not None:
        XBOX_CHECK_INTERVAL = args.check_interval

    if args.active_interval is not None:
        XBOX_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    elif CSV_FILE:
        CSV_FILE = os.path.expanduser(CSV_FILE)

    if args.status_file:
        XBOX_STATUS_FILE = os.path.expanduser(args.status_file)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    # Resolved after DISABLE_LOGGING, because truncation only applies to what the terminal shows and a run
    # with no log file would otherwise lose the cut text for good
    TRUNCATE_CHARS = resolve_truncate_chars(args.truncate, TRUNCATE_CHARS, DISABLE_LOGGING)

    if args.notify_active_inactive is True:
        ACTIVE_INACTIVE_NOTIFICATION = True

    if args.notify_game_change is True:
        GAME_CHANGE_NOTIFICATION = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    apply_webhook_cli_overrides(args, parser)

    # Traced here rather than at each layer, so the line reports the value that survived every later override
    resolved_secrets = {secret: SECRET_SOURCES[secret] for secret in SECRET_KEYS if secret in SECRET_SOURCES}
    for secret, source in resolved_secrets.items():
        debug_print("Secret resolution", name=secret, source=source, **secret_fields(globals().get(secret), secret))
    if not resolved_secrets:
        debug_print("No private settings were resolved from config, dotenv, environment or the command line")

    if doctor_mode:
        doctor_exit = run_doctor(args.xbox_gamertag, cfg_path, env_path, config_advice, timezone_advice)
        # A target the config file already carries is left out, so the command stays as short as the wizard's
        print_doctor_next_steps(args.xbox_gamertag, XBOX_GAMERTAG, doctor_exit)
        sys.exit(doctor_exit)

    if args.setup:
        sys.exit(run_setup_wizard(initial_target=args.xbox_gamertag, config_file=args.config_file, env_file=args.env_file))

    prepare_runtime_settings(runtime_configuration_errors() + runtime_boolean_errors(), args)

    if not check_internet():
        sys.exit(1)

    if args.set_ms_app_credentials:
        try:
            run_set_ms_app_credentials(env_file=env_path, config_path=cfg_path, xbox_gamertag=args.xbox_gamertag)
        except Exception as exc:
            print_recovery_error(exc, context="secret.entry")
            sys.exit(1)
        sys.exit(0)

    if args.set_smtp_password:
        try:
            run_set_smtp_password(env_file=env_path, config_path=cfg_path, xbox_gamertag=args.xbox_gamertag)
        except Exception as exc:
            print_recovery_error(exc, context="secret.entry")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        try:
            run_set_webhook_url(env_file=env_path, config_path=cfg_path, xbox_gamertag=args.xbox_gamertag, provider=args.webhook_provider)
        except Exception as exc:
            print_recovery_error(exc, context="secret.entry")
            sys.exit(1)
        sys.exit(0)

    if args.send_test_webhook:
        if not validate_webhook_url():
            print_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
            sys.exit(1)
        print(f"* Sending test webhook notification through {webhook_provider_display_name()} to {webhook_destination_host()} ...\n")
        # Forced past the alert settings, because the point of the test is the destination, not the choices
        if send_webhook("Xbox Monitor test webhook", "This test notification was sent by --send-test-webhook. Your webhook settings work.", "status", force=True, report_delivery=False) == 0:
            print("* Webhook sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.send_test_email:
        # Checked before the attempt is announced, so a mail server that was never usable is not reported as a failed send
        settings_advice = validate_smtp_settings()
        if settings_advice is not None:
            print_recovery_advice(settings_advice)
            sys.exit(1)
        print("* Sending test email notification ...\n")
        if send_email("Xbox Monitor test email", "This test email was sent by --send-test-email. Your SMTP settings work.", "", SMTP_SSL, smtp_timeout=5, report_delivery=False) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.xbox_gamertag:
        print_recovery_error(context="target.missing", detail="XBOX_GAMERTAG needs to be defined")
        sys.exit(1)

    missing_credentials = [name for name in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET") if not secret_is_set(globals()[name])]
    if missing_credentials:
        print_recovery_error(context="secret.missing", detail=f"{join_names(missing_credentials)} is empty or still set to a placeholder" if len(missing_credentials) == 1 else f"{join_names(missing_credentials)} are empty or still set to a placeholder")
        sys.exit(1)

    if not MS_AUTH_TOKENS_FILE:
        print_recovery_error(context="config.invalid", detail="MS_AUTH_TOKENS_FILE is empty, so authorized tokens cannot be saved")
        sys.exit(1)
    MS_AUTH_TOKENS_FILE = os.path.expanduser(MS_AUTH_TOKENS_FILE)

    if args.info_mode:
        asyncio.run(get_user_info(args.xbox_gamertag, client=None, show_friends=args.show_friends, show_recent_achievements=args.show_recent_achievements, show_recent_games=True, achievements_count=args.achievements_count, games_count=args.games_count))
        sys.exit(0)

    try:
        validate_monitor_timers()
    except ValueError as e:
        print_recovery_error(context="config.invalid", detail=str(e))
        sys.exit(1)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print_recovery_error(e, context="file.unwritable", detail=f"CSV file '{CSV_FILE}' cannot be opened for writing: {e}")
            sys.exit(1)

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        print_recovery_error(context="config.invalid", detail=str(e))
        sys.exit(1)

    if not DISABLE_LOGGING:
        log_path = Path(os.path.expanduser(XBOX_LOGFILE))
        if log_path.parent != Path('.'):
            if log_path.suffix == "":
                log_path = log_path.parent / f"{log_path.name}_{args.xbox_gamertag}.log"
        else:
            if log_path.suffix == "":
                log_path = Path(f"{log_path.name}_{args.xbox_gamertag}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None

    # Email cannot be delivered while the mail server, the user or the password is still a shipped placeholder
    unset_smtp = [name for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD") if not secret_is_set(globals()[name])]
    if unset_smtp:
        verbose_print(f"Email notifications are off because {join_names(unset_smtp)} is still empty or a shipped placeholder" if len(unset_smtp) == 1 else f"Email notifications are off because {join_names(unset_smtp)} are still empty or shipped placeholders")
        ACTIVE_INACTIVE_NOTIFICATION = False
        GAME_CHANGE_NOTIFICATION = False
        STATUS_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    if WEBHOOK_ENABLED and not validate_webhook_url():
        verbose_print("Webhook notifications are off because WEBHOOK_URL is not a complete HTTPS link")
        WEBHOOK_ENABLED = False

    emit_startup_summary(build_startup_summary(args.xbox_gamertag, cfg_path, env_path, FINAL_LOG_PATH), full_startup_summary_enabled())

    # The summary block already ended with one blank line, so this heading starts at the cursor
    out = f"Monitoring user with Xbox gamer tag {args.xbox_gamertag}"
    print(out)
    print("─" * len(out))
    mark_monitoring_started()

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    asyncio.run(xbox_monitor_user(args.xbox_gamertag, CSV_FILE, achievements_count=args.achievements_count, games_count=args.games_count))

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
