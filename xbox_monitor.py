#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.0

Tool implementing real-time tracking of Xbox Live players activities:
https://github.com/misiektoja/xbox_monitor/

Python pip3 requirements:

python-xbox
requests
python-dateutil
httpx
pytz
tzlocal (optional)
python-dotenv (optional)
"""

VERSION = "2.0"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
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
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

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

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Base name for the log file. Output will be saved to xbox_monitor_<gamer_tag>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/xbox_monitor
XBOX_LOGFILE = "xbox_monitor"

# Whether to disable logging to xbox_monitor_<gamer_tag>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Value used by signal handlers increasing/decreasing the check for player activity
# when user is online/away (XBOX_ACTIVE_CHECK_INTERVAL); in seconds
XBOX_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# Enable debug mode for technical logging (can also be enabled via --debug flag)
# Shows technical details, timestamps and internal state changes
DEBUG_MODE = False
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
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
DOTENV_FILE = ""
XBOX_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
XBOX_ACTIVE_CHECK_SIGNAL_VALUE = 0
DEBUG_MODE = False

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "xbox_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET", "SMTP_PASSWORD")

# Where each secret's effective value came from, recorded while precedence is applied so it can be reported later
SECRET_SOURCES = {}

# Secrets that were already exported before the dotenv file was loaded, captured at startup
EXPORTED_SECRET_KEYS = frozenset()

# Documentation the tool links to from errors, doctor rows and the welcome screen
DOCS_BASE_URL = "https://misiektoja.github.io/xbox_monitor"
INSTALLATION_GUIDE_URL = f"{DOCS_BASE_URL}/installation/"
QUICK_START_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#quick-start"
CONFIG_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#configuration-file"
CREDENTIALS_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#microsoft-entra-application-credentials"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
PRIVACY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#user-privacy-settings"
TIMEZONE_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#time-zone"
SMTP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#smtp-settings"
TLS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#tls-verification"
INTERVALS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#check-intervals"
DIAGNOSTICS_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#debug-output"
DOCTOR_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#doctor-preflight"

# How the positional target may be written. Reused by the recovery advice and every prompt, because three
# hand-written phrasings of the same list is what these tools drift into
XBOX_TARGET_FORMS = "Xbox gamertag, not the Microsoft account e-mail or the real name"

# How LOCAL_TIMEZONE was resolved, so the doctor reports the configured value rather than the resolved one
LOCAL_TIMEZONE_STATE = "config"

# Doctor label for each timezone outcome, kept identical to the sibling monitors
TIMEZONE_CHECK_LABELS = {"config": "Local timezone is valid", "auto": "Local timezone can be detected", "auto_unavailable": "Automatic timezone detection is unavailable", "auto_failed": "Automatic timezone detection failed", "invalid": "Local timezone is invalid"}

# Version incremented when SIGHUP reloads Xbox application credentials
XBOX_AUTH_REFRESH_VERSION = 0

LIVENESS_CHECK_COUNTER = 0

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

CLI_CONFIG_PATH = None

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"

# Global to track if we're at start of line (for debug_print to handle interleaving)
STDOUT_AT_START_OF_LINE = True


import sys

# Declared once so the startup gate, the packaging metadata and any later environment check cannot disagree
MINIMUM_PYTHON_VERSION = (3, 11)
MINIMUM_PYTHON_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

if sys.version_info < MINIMUM_PYTHON_VERSION:
    print(f"* Error: Python version {MINIMUM_PYTHON_VERSION_TEXT} or higher required !")
    sys.exit(1)


import time
import json
from typing import List, cast
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
import platform
import re
import ipaddress
import asyncio
import httpx
from httpx import HTTPStatusError
try:
    from pythonxbox.api.client import XboxLiveClient
    from pythonxbox.authentication.manager import AuthenticationManager
    from pythonxbox.authentication.models import OAuth2TokenResponse
    from pythonxbox.common.signed_session import SignedSession
    from pythonxbox.api.provider.presence.models import PresenceLevel
    from pythonxbox.api.provider.titlehub.models import TitleFields
    from pythonxbox.api.provider.userstats.models import GeneralStatsField
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Python-Xbox library !\n\nTo install it, run:\n    pip install python-xbox\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/tr4nt0r/python-xbox/")
import shutil
import shlex
import subprocess
import tempfile
from pathlib import Path


# The four shared status markers. A fifth neutral marker is the single biggest source of drift between these
# tools, because every state it would cover is a state the others already call PASS
DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# Doctor sections in the order they are printed
DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")

# Delivery results are printed as they happen rather than inside a section, but they still count in the summary
DOCTOR_DELIVERY_SECTION = "Optional delivery tests"

# Imported without a guard, so the tool cannot start when one of these is missing
DOCTOR_REQUIRED_DEPENDENCIES = (("pythonxbox", "python-xbox"), ("httpx", "httpx"), ("dateutil", "python-dateutil"), ("pytz", "pytz"))

# Guarded imports the tool degrades around, with what stops working and what to do instead
DOCTOR_OPTIONAL_DEPENDENCIES = (
    ("tzlocal", "tzlocal", "Used only to auto-detect the local time zone", "Automatic time zone detection is unavailable", "Or set LOCAL_TIMEZONE to a pytz timezone name in the config file"),
    ("dotenv", "python-dotenv", "Used only to read secrets from a dotenv file", "Secrets cannot be read from a dotenv file", "Or export them as environment variables"),
)

# An active check interval below this invites the Xbox Live rate limiter, which stops the tool seeing anything
DOCTOR_MIN_SAFE_ACTIVE_INTERVAL = 30

# Seconds the passive doctor sign-in waits, shorter than a real delivery so a dead host does not stall the report
DOCTOR_SMTP_TIMEOUT = 5

# Shared doctor label for the email channel, kept identical to the sibling monitors
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"

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


# Creates one doctor result, refusing a marker outside the shared four and redacting every field it shows
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    safe_label = sanitize_error_text(label)
    safe_detail = sanitize_error_text(detail)
    # Several advice objects carry the same text as their summary, and printing it twice reads as two problems
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
    while isinstance(stream, Logger):
        stream = stream.terminal
    return stream


# Shows one transient step only on an interactive terminal, erased by overwriting its own width
# The line stays uncoloured on purpose: it is erased by writing exactly len(line) spaces, and an escape
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
def render_doctor_notice():
    print("Running preflight checks. No files will be written. Interactive email tests run only after separate approval.\n")


# Checks the interpreter, the dependencies the tool needs and the ones it degrades around
def doctor_check_environment(version_info=None, spec_finder=None):
    checks = []
    selected = tuple(sys.version_info if version_info is None else version_info)
    version_text = ".".join(str(part) for part in selected[:3])
    if selected[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported"))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", recovery_fix_with_guide(f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", INSTALLATION_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, f"Minimum supported version: {MINIMUM_PYTHON_VERSION_TEXT}", advice))

    for module_name, package_name in DOCTOR_REQUIRED_DEPENDENCIES:
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", recovery_fix_with_guide(f"Install it with: {pip_install_command(package_name)}", INSTALLATION_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    for module_name, package_name, purpose, effect, alternative in DOCTOR_OPTIONAL_DEPENDENCIES:
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Optional dependency {package_name} is installed", purpose))
        else:
            advice = missing_dependency_advice(package_name, effect, alternative)
            checks.append(make_doctor_check("Environment", "WARN", f"Optional dependency {package_name} is not installed", f"{effect}. Monitoring is unaffected", advice))

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


# Reports the effective settings and the files the tool would write, without writing any of them
def doctor_check_configuration(config_path=None, env_path=None, config_advice=None, timezone_advice=None, xbox_gamertag=None):
    checks = []
    if config_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", config_advice.summary, advice=config_advice))
    elif config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))

    if env_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))

    checks.extend(doctor_secret_checks())

    timezone_label = TIMEZONE_CHECK_LABELS[LOCAL_TIMEZONE_STATE]
    if timezone_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", timezone_label, timezone_advice.detail, timezone_advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", timezone_label, LOCAL_TIMEZONE))

    intervals = f"{display_time(XBOX_CHECK_INTERVAL)} while offline, {display_time(XBOX_ACTIVE_CHECK_INTERVAL)} while online"
    if XBOX_ACTIVE_CHECK_INTERVAL < DOCTOR_MIN_SAFE_ACTIVE_INTERVAL:
        advice = make_recovery_advice("xbox.rate_limited", "Check intervals are short enough to be rate limited", recovery_fix_with_guide(f"Raise XBOX_ACTIVE_CHECK_INTERVAL to at least {DOCTOR_MIN_SAFE_ACTIVE_INTERVAL} seconds", INTERVALS_GUIDE_URL), True)
        checks.append(make_doctor_check("Configuration", "WARN", "Check intervals are short", intervals, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "Check intervals are set", intervals))

    if VERIFY_SSL:
        checks.append(make_doctor_check("Configuration", "PASS", "TLS certificate verification is on", "Every outbound request checks the server certificate"))
    else:
        advice = make_recovery_advice("config.insecure", "TLS certificate verification is off", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "WARN", "TLS certificate verification is off", "VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service", advice))

    try:
        checks.append(make_doctor_check("Configuration", "PASS", f"ASCII log separators are {'on' if ascii_log_separators_enabled() else 'off'}", f"Mode: {ASCII_LOG_SEPARATORS}"))
    except ValueError as exc:
        advice = classify_recovery_error(context="config.invalid", detail=str(exc))
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if MS_AUTH_TOKENS_FILE:
        tokens_path = os.path.expanduser(MS_AUTH_TOKENS_FILE)
        if path_is_writable(tokens_path):
            checks.append(make_doctor_check("Configuration", "PASS", "Xbox token cache is writable", f"Path: {tokens_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"Xbox token cache '{tokens_path}' cannot be written")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    else:
        advice = classify_recovery_error(context="config.invalid", detail="MS_AUTH_TOKENS_FILE is empty, so authorized tokens cannot be saved")
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if CSV_FILE:
        csv_path = os.path.expanduser(CSV_FILE)
        if path_is_writable(csv_path):
            checks.append(make_doctor_check("Configuration", "PASS", "CSV history file is writable", f"Path: {csv_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"CSV file '{csv_path}' cannot be written")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV history is disabled", "Set CSV_FILE or use -b to record every reported change"))

    status_path = resolve_status_file(xbox_gamertag or "<xbox_gamertag>")
    if path_is_writable(status_path):
        checks.append(make_doctor_check("Configuration", "PASS", "Status file is writable", f"Path: {status_path}"))
    else:
        advice = classify_recovery_error(context="file.unwritable", detail=f"Status file '{status_path}' cannot be written")
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Nothing is written to a log file"))
    else:
        log_path = resolve_log_path(xbox_gamertag or "<xbox_gamertag>")
        if path_is_writable(log_path):
            checks.append(make_doctor_check("Configuration", "PASS", "Log file is writable", f"Path: {log_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"Log file '{log_path}' cannot be written")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    return checks


# Reports whether the endpoint the tool checks at startup answers, using the configured URL, timeout and TLS setting
def doctor_check_connectivity():
    try:
        with httpx.Client(verify=tls_context(), timeout=CHECK_INTERNET_TIMEOUT) as client:
            client.get(CHECK_INTERNET_URL)
    except Exception as exc:
        advice = classify_recovery_error(exc, context="connectivity", detail=f"{CHECK_INTERNET_URL} could not be reached: {exc}")
        return [make_doctor_check("Connectivity", "FAIL", "The connectivity endpoint could not be reached", f"Endpoint: {CHECK_INTERNET_URL}", advice)]
    return [make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable", f"Endpoint: {CHECK_INTERNET_URL} (TLS verification: {VERIFY_SSL})")]


# Loads the cached tokens and refreshes them without writing anything, which is what the real run does first
# A real run answers an unreadable cache by starting the interactive sign-in, which writes a file, so here the
# same state has to become a diagnosis instead
async def doctor_refresh_tokens(auth_mgr):
    try:
        with open(MS_AUTH_TOKENS_FILE, encoding="utf-8") as tokens_file:
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
        advice = classify_recovery_error(context="secret.missing", detail=f"{' and '.join(credentials_missing)} is not set" if len(credentials_missing) == 1 else f"{' and '.join(credentials_missing)} are not set")
        checks.append(make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice))
        return checks + doctor_check_target_identity(report, xbox_gamertag)
    checks.append(make_doctor_check("Authentication", "PASS", "Microsoft application credentials are set", "MS_APP_CLIENT_ID and MS_APP_CLIENT_SECRET both hold a value"))

    tokens_path = Path(os.path.expanduser(MS_AUTH_TOKENS_FILE or ""))
    if not tokens_path.is_file():
        advice = make_recovery_advice("auth.token_cache", "No saved Xbox tokens were found", recovery_fix_with_guide(f"Authorize once by running: {tool_command('<xbox_gamertag>')}. Doctor writes no files, so it cannot run the sign-in flow for you", CREDENTIALS_GUIDE_URL), False, f"Expected the token cache at {tokens_path}")
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


# Reports whether a profile was even named, and stays silent once authentication has already explained itself
def doctor_check_target_identity(report, xbox_gamertag=None):
    if not xbox_gamertag:
        advice = classify_recovery_error(context="target.missing", detail="No Xbox gamertag was given")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice=advice)]
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
    except Exception as exc:
        advice = classify_recovery_error(exc, context="target", detail=f"Looking up the gamertag '{xbox_gamertag}' failed: {exc}")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    return [make_doctor_check("Target", "PASS", "The monitored profile is reachable", f"Gamertag: {xbox_gamertag}, XUID: {xuid}")]


# Returns advice for the first unusable SMTP server setting, or None when they are all present and valid
def validate_smtp_settings():
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')
    reason = ""

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            reason = "SMTP_HOST is not a valid IP address or hostname"

    if not reason:
        try:
            port = int(SMTP_PORT)
            if not (1 <= port <= 65535):
                raise ValueError
        except (TypeError, ValueError):
            reason = "SMTP_PORT is not a port number between 1 and 65535"

    if not reason and (not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL))):
        reason = "SENDER_EMAIL or RECEIVER_EMAIL is not an email address"

    if not reason and (not secret_is_set(SMTP_USER) or not secret_is_set(SMTP_PASSWORD)):
        reason = "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"

    return classify_recovery_error(context="smtp.settings", detail=reason) if reason else None


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
        debug_print(f"SMTP sign-in check against {SMTP_HOST}:{SMTP_PORT} as {SMTP_USER} (STARTTLS: {bool(SMTP_SSL)}, timeout: {timeout}s)")
        connection = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout)
        if SMTP_SSL:
            connection.starttls(context=tls_context())
        try:
            connection.login(SMTP_USER, candidate)
        finally:
            try:
                connection.quit()
            except Exception as quit_error:
                debug_print(f"Closing the SMTP connection failed: {type(quit_error).__name__}: {quit_error}")
    except RecoveryError:
        raise
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="smtp", detail=f"Signing in to {SMTP_HOST} as {SMTP_USER} failed: {exc}"), exc) from None
    finally:
        SMTP_PASSWORD = previous_password
    return SMTP_USER


# Reports whether email alerts can fire at all, then whether the settings they would use are usable
def doctor_check_email_notifications(report):
    settings_advice = validate_smtp_settings()
    # An error alert is on by default, so on its own it cannot make a fresh install look configured
    deliberate = ACTIVE_INACTIVE_NOTIFICATION or GAME_CHANGE_NOTIFICATION or STATUS_NOTIFICATION
    if not deliberate and not (ERROR_NOTIFICATION and settings_advice is None):
        return [make_doctor_check("Notifications", "PASS", "Email alerts are disabled", "Use -a, -g, -s or SMTP settings with ERROR_NOTIFICATION to turn them on")]
    if settings_advice is not None:
        return [make_doctor_check("Notifications", "WARN", "Email alerts are on but cannot be delivered", settings_advice.summary, settings_advice)]
    try:
        smtp_sign_in(SMTP_PASSWORD, timeout=DOCTOR_SMTP_TIMEOUT)
    except RecoveryError as exc:
        return [make_doctor_check("Notifications", "FAIL", exc.advice.summary, exc.advice.detail, exc.advice)]
    alerts = ", ".join(name for name, enabled in (("status changes", ACTIVE_INACTIVE_NOTIFICATION), ("game changes", GAME_CHANGE_NOTIFICATION), ("all status changes", STATUS_NOTIFICATION), ("errors", ERROR_NOTIFICATION)) if enabled)
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", SMTP_READY_CHECK_LABEL, f"Alerts: {alerts}. No email was sent during this passive check")]


# Asks one yes or no question, treating a closed or interrupted input as no
def ask_yes_no(question, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = read_interactively(input, f"{question} {hint}: ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers a real delivery test for each channel that already passed, approved separately from the report
def offer_doctor_delivery_tests(report):
    if not report.email_ready or not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    print("\nOptional delivery tests\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    offered = []
    if ask_yes_no("Send one test email now? This will deliver a real message"):
        delivered = send_email("xbox_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=DOCTOR_SMTP_TIMEOUT) == 0
        check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS" if delivered else "FAIL", "Doctor test email delivered" if delivered else "Doctor test email delivery failed", "One real test email was sent after confirmation" if delivered else "The approved test email could not be delivered")
    else:
        check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent")
    offered.append(check)
    # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
    for check in offered:
        report.checks.append(check)
        print(f"[{check.status}] {check.label}")
    return offered


# Runs every section in order, reporting each step while it is still running
def build_doctor_report(xbox_gamertag=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None, progress=None):
    report = DoctorReport()
    steps = (
        ("the environment", lambda: doctor_check_environment()),
        ("the configuration", lambda: doctor_check_configuration(config_path, env_path, config_advice, timezone_advice, xbox_gamertag)),
        ("connectivity", lambda: doctor_check_connectivity()),
        ("authentication", lambda: asyncio.run(doctor_check_xbox_live(report, xbox_gamertag, progress))),
        ("notifications", lambda: doctor_check_email_notifications(report)),
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
    lines = ["Doctor", f"Detected install method: {detect_install_method()}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", section))
        for check in section_checks:
            lines.append(f"[{check.status}] {check.label}")
            if check.detail:
                lines.append(f"  {check.detail}")
            if check.advice is not None and check.status in ("FAIL", "WARN"):
                lines.append(f"To fix: {check.advice.fix}")
    return sanitize_error_text("\n".join(lines))


# Renders the one sentence that says whether the setup is usable, and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        sentence = f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool."
    elif warnings:
        sentence = f"  All critical checks passed with {warnings} warning(s). Review the warnings above."
    else:
        sentence = "  All checks passed. You are good to go!"
    return "\n".join(("", "Summary", sentence, "", f"Guide: {DOCTOR_GUIDE_URL}"))


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


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        global STDOUT_AT_START_OF_LINE
        if message:
            STDOUT_AT_START_OF_LINE = message.endswith('\n')
        self.terminal.write(message)
        # Expand tabs for file output (stdout remains untouched)
        self.logfile.write(normalize_log_separators(message.expandtabs(8)))
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


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
        return True
    except Exception as e:
        report_recovery_error(e, context="connectivity", detail=f"The connectivity endpoint {check_url} could not be reached: {e}")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Returns whether this process was started from the packaged entry point or from a downloaded script
def detect_install_method():
    return "manual" if os.path.basename(sys.argv[0] or "").endswith(".py") else "pip"


# Returns a readable name for one install method
def install_method_display_name(method=None):
    return {"pip": "PyPI install", "manual": "downloaded script"}.get(method or detect_install_method(), "unknown install")


# Renders command arguments quoted for the shell of the host operating system
def render_command(arguments):
    values = [str(argument) for argument in arguments]
    return subprocess.list2cmdline(values) if platform.system() == "Windows" else shlex.join(values)


# Returns the bare command that starts this tool on the detected install, without arguments
def tool_command_prefix(method=None):
    if (method or detect_install_method()) == "manual":
        return render_command([("python" if platform.system() == "Windows" else "python3"), Path(__file__).name])
    return "xbox_monitor"


# Returns a complete, copy-pasteable command line for this tool with every argument quoted for the host shell
def tool_command(*arguments, method=None):
    return " ".join([tool_command_prefix(method), *[render_command([argument]) for argument in arguments]])


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


# Copies an existing file to a timestamped private backup before it is replaced, returning the backup path or None
def create_timestamped_backup(destination, attempts=100):
    destination_path = Path(destination).expanduser()
    if not destination_path.is_file():
        return None
    existing_bytes = destination_path.read_bytes()
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
        except Exception:
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
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return str(destination_path)


# Confirms replacing one existing generated config, or requires --force when there is nobody to ask
def confirm_generated_config_replacement(destination, force=False, interactive=None, input_func=input):
    destination_path = Path(destination).expanduser()
    if not destination_path.exists() or force:
        return True
    terminal_is_interactive = bool(sys.stdin.isatty()) if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise FileExistsError(f"Config file '{destination_path}' already exists and there is no terminal to confirm replacing it")
    try:
        answer = str(read_interactively(input_func, f"Config file '{destination_path}' exists. Replace it and keep a timestamped backup? [y/N]: ")).strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = ""
    return answer in {"y", "yes"}


# Writes one generated config atomically, backing up whatever was there first
def write_generated_config(output_file, content, force=False, interactive=None, input_func=input):
    destination = Path(os.path.expanduser(str(output_file)))
    if not confirm_generated_config_replacement(destination, force, interactive, input_func):
        return None, False
    backup_path = create_timestamped_backup(destination)
    write_file_atomically(destination, content)
    return backup_path, True


# Saves the last seen status atomically, so an interrupted write cannot strand a half-written status file
def save_last_status(status_file, status_ts, status):
    write_file_atomically(status_file, json.dumps([status_ts, status], indent=2) + "\n")


# Reports whether a setting holds a real value rather than being empty or one of the shipped placeholders
def secret_is_set(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("your_")


# Applies the diagnostic flags given on the command line, before and again after the config file is read
def apply_diagnostic_cli_flags(args):
    global DEBUG_MODE
    if getattr(args, "debug_mode", None):
        DEBUG_MODE = True



# The categories that mean the saved credentials themselves stopped working, which no retry can repair
AUTH_RECOVERY_CODES = frozenset({"auth.credentials_invalid", "auth.token_expired", "auth.token_cache"})


# Stable recovery categories. Every code here is produced somewhere in this file, and nothing else is accepted
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "config.insecure", "dependency.missing", "secret.missing",
    "auth.credentials_invalid", "auth.token_expired", "auth.token_cache", "auth.oauth_code",
    "network.unavailable", "network.timeout",
    "xbox.malformed_response", "xbox.rate_limited", "xbox.unavailable", "resource.exhausted",
    "target.missing", "target.not_found", "target.not_visible",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
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
    return sorted(set(values), key=len, reverse=True)


# Redacts credentials and secret-bearing assignments from arbitrary text before it is shown, logged or emailed
def sanitize_error_text(value):
    text = str(value or "")
    for secret in known_secret_values():
        text = text.replace(secret, "<redacted>")
    patterns = (
        (r"(?m)(\b(?:MS_APP_CLIENT_ID|MS_APP_CLIENT_SECRET|SMTP_PASSWORD)\b\s*=\s*).*$", r"\1<redacted>"),
        # An XBL3.0 header is 'XBL3.0 x=<userhash>;<token>', so stopping at the semicolon would leave the token
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?(?:bearer|basic|xbl3\.0)\s+)[^\s,'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:client_secret|client_id|access_token|refresh_token|id_token|smtp_password)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)([?&](?:access_token|refresh_token|client_secret|code)=)[^&#\s]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Returns a placeholder reporting only whether a secret is set, never any part of its value
def mask_secret(value):
    # Diagnostic output is meant to be pasted into public bug reports, so not even a prefix of a live key may
    # appear. Which secret is loaded is answered by its name and source instead, which SECRET_SOURCES reports
    if not secret_is_set(value):
        return "(not set)"
    return "<redacted>"


# Builds one piece of advice, rejecting any code outside the taxonomy and redacting every field
def make_recovery_advice(code, summary, fix, retryable, detail=""):
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), retryable, sanitize_error_text(detail))


# Appends the documentation link that matches the fix, on its own line
def recovery_fix_with_guide(fix, guide_url):
    return f"{fix}\nGuide: {guide_url}"


# Renders one piece of advice, adding the fix paragraph and the technical detail only where they help
def render_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error"):
    lines = [f"* {label}: {advice.summary}" + (f" ({retry_note})" if retry_note else "")]
    if with_fix:
        lines.append(f"To fix: {advice.fix}")
        if (DEBUG_MODE if debug is None else debug) and advice.detail:
            lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints advice in full the first time its category appears and as one line while the same category persists
def print_recovery_advice(advice, tracker=None, retry_note="", debug=None, label="Error"):
    print(render_recovery_advice(advice, debug, retry_note, tracker is None or tracker.should_render(advice), label))


# Classifies a failure and prints it, the shape every user-facing error site uses
def report_recovery_error(error=None, context="runtime", detail="", label="Error"):
    advice = classify_recovery_error(error, context, detail)
    print_recovery_advice(advice, label=label)
    return advice


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


# Reports whether any exception in the chain is the local file descriptor limit rather than a remote failure
def is_too_many_open_files(error):
    for current in iter_exc_chain(error):
        if isinstance(current, OSError) and getattr(current, "errno", None) == 24:
            return True
        message = str(current).lower()
        if "too many open files" in message or "errno 24" in message:
            return True
    return False


# Returns the HTTP status carried by any exception in the chain, or None when the failure was not a response
def http_status_from(error):
    for current in iter_exc_chain(error):
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
    return None


# Returns the fix for credentials the Microsoft sign-in endpoint would not accept
def credentials_recovery_fix():
    return f"Check MS_APP_CLIENT_ID and MS_APP_CLIENT_SECRET against the app registration in the Microsoft Entra admin center, then rerun: {tool_command('<xbox_gamertag>')}"


# Returns the fix for a refresh token the sign-in endpoint no longer accepts
def token_recovery_fix():
    return f"Delete the token cache file and authorize again by running: {tool_command('<xbox_gamertag>')}"


# Classifies a failure by context, exception type and message into one stable recovery category
def classify_recovery_error(error=None, context="runtime", detail=""):
    if isinstance(error, RecoveryError):
        return error.advice

    safe_detail = sanitize_error_text(detail or error or "")
    message = str(detail or error or "").lower()
    monitoring = context == "monitor"
    status = http_status_from(error)

    if error is not None and is_too_many_open_files(error):
        return make_recovery_advice("resource.exhausted", "This process ran out of file descriptors, which is a local limit and not an Xbox Live problem", recovery_fix_with_guide("Raise the file descriptor limit, for example with 'ulimit -n 4096', or set LimitNOFILE= if you run under systemd, then restart the tool", DIAGNOSTICS_GUIDE_URL), False, safe_detail)

    if context == "config.missing":
        return make_recovery_advice("config.missing", safe_detail or "The configuration file was not found", recovery_fix_with_guide(f"Check the --config-file path, or create one with: {tool_command('--generate-config', 'xbox_monitor.conf')}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "config.invalid":
        return make_recovery_advice("config.invalid", safe_detail or "The configuration file could not be loaded", recovery_fix_with_guide(f"Config files are read as data. Only documented SETTING = value lines with plain literal values are accepted. Correct the reported line, or write a fresh template to a different path with: {tool_command('--generate-config', '<new-file>')}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "secret.missing":
        return make_recovery_advice("secret.missing", safe_detail or "A required credential is missing", recovery_fix_with_guide(f"Register an application in the Microsoft Entra admin center, then put its client ID and secret in MS_APP_CLIENT_ID and MS_APP_CLIENT_SECRET in your dotenv file, or pass them directly: {tool_command('<xbox_gamertag>', '-u', '<client_id>', '-w', '<client_secret>')}", CREDENTIALS_GUIDE_URL), False, safe_detail)

    if context == "target.missing":
        return make_recovery_advice("target.missing", safe_detail or "No Xbox gamertag was given", recovery_fix_with_guide(f"Pass the account to watch: {tool_command_prefix()} <xbox_gamertag>. Use the {XBOX_TARGET_FORMS}", QUICK_START_GUIDE_URL), False, safe_detail)

    if context == "secret.entry":
        return make_recovery_advice("secret.entry", safe_detail or "The value was not entered, so nothing was written", recovery_fix_with_guide("Run the command again from an interactive terminal and enter the value when prompted", SECRETS_GUIDE_URL), False, safe_detail)

    if context == "file.exists":
        return make_recovery_advice("file.exists", safe_detail or "The destination file already exists", recovery_fix_with_guide("Re-run with --force to replace it after a timestamped backup, or write to a different path", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "file.unreadable":
        return make_recovery_advice("file.unreadable", safe_detail or "A file the tool needs could not be read", recovery_fix_with_guide("Check that the path exists and that this user can read it, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "file.unwritable":
        return make_recovery_advice("file.unwritable", safe_detail or "A file the tool needs could not be written", recovery_fix_with_guide("Check that the directory exists, that this user can write to it and that there is free space, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "smtp.settings":
        return make_recovery_advice("smtp.invalid", f"The SMTP settings are incorrect: {safe_detail}" if safe_detail else "The SMTP settings are incorrect", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL and RECEIVER_EMAIL then run: {tool_command('--send-test-email')}", SMTP_GUIDE_URL), False, safe_detail)

    if context.startswith("smtp"):
        for current in iter_exc_chain(error):
            if isinstance(current, smtplib.SMTPAuthenticationError):
                return make_recovery_advice("smtp.authentication", "The SMTP server rejected the login", recovery_fix_with_guide(f"Check SMTP_USER and SMTP_PASSWORD. Providers such as Gmail need an app password rather than the account password. Then run: {tool_command('--send-test-email')}", SMTP_GUIDE_URL), False, safe_detail)
            if isinstance(current, (smtplib.SMTPException, ssl.SSLError, OSError)):
                return make_recovery_advice("smtp.connection", "The SMTP server could not be reached", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT and SMTP_SSL, and that the port is not blocked. Then run: {tool_command('--send-test-email')}", SMTP_GUIDE_URL), True, safe_detail)

    if context == "auth.oauth_code":
        return make_recovery_advice("auth.oauth_code", safe_detail or "The authorization code was not accepted", recovery_fix_with_guide("Open the authorization URL again and copy the whole value after '?code=' from the address bar, without the trailing '&state=' part", CREDENTIALS_GUIDE_URL), False, safe_detail)

    if context == "auth.token_cache":
        return make_recovery_advice("auth.token_cache", safe_detail or "The saved Xbox tokens could not be read", recovery_fix_with_guide(f"Delete the token cache file named by MS_AUTH_TOKENS_FILE and authorize again by running: {tool_command('<xbox_gamertag>')}", CREDENTIALS_GUIDE_URL), False, safe_detail)

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

    return make_recovery_advice("unknown", "Something unexpected went wrong", recovery_fix_with_guide("Rerun with --debug and check the technical detail it prints. If the problem continues, open an issue with that output", DIAGNOSTICS_GUIDE_URL), True, safe_detail)


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
        return os.access(target, os.W_OK)
    parent = target.parent if str(target.parent) else Path(".")
    return parent.is_dir() and os.access(parent, os.W_OK)


# Returns the command that installs one library into the interpreter running this tool
def pip_install_command(requirement):
    return render_command([sys.executable or "python3", "-m", "pip", "install", requirement])


# Returns advice for an optional library that is missing, naming the exact install command for this interpreter
def missing_dependency_advice(package, effect, alternative=""):
    fix = f"Install it with: {pip_install_command(package)}"
    if alternative:
        fix = f"{fix}. {alternative}"
    return make_recovery_advice("dependency.missing", f"{effect} because the optional '{package}' library is missing", recovery_fix_with_guide(fix, INSTALLATION_GUIDE_URL), False)


# The ASCII startup banner, kept to plain ASCII so it renders on every console including Windows
STARTUP_BANNER = r"""
 .---------------.    __  __ ____    ___  __  __
|       (Y)      |    \ \/ /| __ )  / _ \ \ \/ /
|    (X)   (B)   |     \  / |  _ \ | | | | \  /
|       (A)      |     /  \ | |_) || |_| | /  \
|      o   o     |    /_/\_\|____/  \___/ /_/\_\
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


# Prints the ASCII startup banner with its separately aligned version
def print_startup_banner():
    print(STARTUP_BANNER)
    print(f"{'':21}v{VERSION}\n")


# Debug print helper - only prints if DEBUG_MODE is enabled
# Debug output exists to be pasted into a public bug report, so it is redacted here rather than at every call site
def debug_print(message):
    global STDOUT_AT_START_OF_LINE
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = ""
        if not STDOUT_AT_START_OF_LINE:
            prefix = "\n"
        print(f"{prefix}[DEBUG {timestamp}] {sanitize_error_text(message)}")
        STDOUT_AT_START_OF_LINE = True


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
            await asyncio.sleep(delay)
            delay *= 2


# Starts interactive OAuth flow and stores the new OAuth token on the auth manager
async def oauth_interactive_auth(auth_mgr):
    print("\nAuthorizing via OAuth ...")
    url = auth_mgr.generate_authorization_url()
    print(f"\nOpen this URL in your web browser to authorize:\n{url}")
    authorization_code = input("\nEnter authorization code (part after '?code=' in callback URL): ").strip()
    if not authorization_code:
        raise ValueError("Authorization code cannot be empty")
    auth_mgr.oauth = await auth_mgr.request_oauth_token(authorization_code)


# Loads cached OAuth tokens, refreshes them and falls back to interactive re-authentication when needed
async def authenticate_and_refresh_tokens(auth_mgr):
    token_file_loaded = False
    try:
        debug_print("Loading tokens from file...")
        with open(MS_AUTH_TOKENS_FILE) as f:
            tokens = f.read()
        auth_mgr.oauth = OAuth2TokenResponse.model_validate_json(tokens)
        token_file_loaded = True
        debug_print("Tokens loaded successfully.")
    except FileNotFoundError:
        print(f"\n* No saved Xbox tokens at '{MS_AUTH_TOKENS_FILE}' yet, so this run will ask you to authorize once")
    except Exception as e:
        print()
        report_recovery_error(e, context="auth.token_cache", detail=f"The Xbox token cache '{MS_AUTH_TOKENS_FILE}' could not be read: {e}", label="Warning")

    if not token_file_loaded:
        await oauth_interactive_auth(auth_mgr)

    try:
        debug_print("Refreshing tokens...")
        await refresh_tokens_with_retry(auth_mgr)
        debug_print("Tokens refreshed successfully.")
    except HTTPStatusError as e:
        # Temporary server-side errors are not a credential problem, so do not force interactive re-authentication
        if is_transient_auth_error(e):
            raise
        print()
        report_recovery_error(e, context="auth", detail=f"Refreshing the saved Xbox tokens failed: {format_exception(e)}", label="Warning")
        print("* Re-authorization is required")
        await oauth_interactive_auth(auth_mgr)
        debug_print("Refreshing tokens after interactive OAuth...")
        await refresh_tokens_with_retry(auth_mgr)
        debug_print("Tokens refreshed successfully after re-authentication.")

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
        except Exception:
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
        except Exception:
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


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    settings_advice = validate_smtp_settings()
    if settings_advice is not None:
        print_recovery_advice(settings_advice)
        return 1

    if not subject or not isinstance(subject, str):
        report_recovery_error(context="smtp.settings", detail="the message subject is empty")
        return 1

    if not body and not body_html:
        report_recovery_error(context="smtp.settings", detail="the message has no plain-text and no HTML body")
        return 1

    try:
        if use_ssl:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=tls_context())
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        report_recovery_error(e, context="smtp", detail=f"Sending the email through {SMTP_HOST} failed: {e}")
        return 1
    return 0


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, status, gamename):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': gamename})

    except Exception as e:
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
    except Exception:
        return None


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(now_local_naive()).weekday()]} {now_local_naive().strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
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
        except Exception:
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
        except Exception:
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


# Signal handler for SIGHUP allowing to reload secrets from .env
def reload_secrets_signal_handler(sig, frame):
    global XBOX_AUTH_REFRESH_VERSION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True)
            else:
                print("* No .env file found, skipping env-var reload")
        except ImportError:
            env_path = None
            print_recovery_advice(missing_dependency_advice("python-dotenv", "Secrets cannot be reloaded from a dotenv file", "Or export them as environment variables and restart"), label="Warning")

    auth_credentials_changed = False
    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                if secret_is_set(val):
                    SECRET_SOURCES[secret] = "dotenv file"
                else:
                    SECRET_SOURCES.pop(secret, None)
                if secret in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET"):
                    auth_credentials_changed = True
                print(f"* Reloaded {secret} from {env_path}")
    if auth_credentials_changed:
        XBOX_AUTH_REFRESH_VERSION += 1

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
                    if last_seen_class.title_name not in ("Online", "Home"):
                        title_name = last_seen_class.title_name
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
                    if title.name not in ("Online", "Home", "Xbox App") and title.placement != "Background":
                        game_name = title.name
                        break

    debug_print(f"Presence data: state={status}, title_name={title_name}, game_name={game_name}, platform={platform}, lastonline={get_debug_date_from_ts(lastonline_ts)}")
    debug_print(f"Presence raw: last_seen_title={last_seen_raw_title}, last_seen_device={last_seen_raw_device}, last_seen_timestamp={last_seen_raw_ts}")
    if presence_titles_dbg:
        debug_print(f"Presence device titles: {', '.join(presence_titles_dbg)}")
    else:
        debug_print("Presence device titles: none")

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
            debug_print(f"Fetched {len(history_response.titles)} history items:")
            best_ts = 0
            best_game = ""
            for i, title in enumerate(history_response.titles, 1):
                if title.title_history and title.title_history.last_time_played:
                    played_dt = convert_iso_str_to_datetime(title.title_history.last_time_played)
                    if played_dt:
                        ts = int(played_dt.timestamp())
                        game_name = title.name if hasattr(title, 'name') and title.name else "Unknown"
                        debug_print(f"  {i}. {game_name} played at {get_date_from_ts(ts)}")
                        if best_ts == 0:
                            best_ts = ts
                            best_game = game_name

            if best_ts > 0:
                debug_print(f"Selected title history: {best_game} at {get_date_from_ts(best_ts)}")
            return best_ts, best_game
    except Exception as e:
        debug_print(f"Error in xbox_get_latest_title_played_ts: {e}")
    return 0, ""


# Selects the best available last online timestamp (presence vs title history)
def xbox_get_best_lastonline_ts(lastonline_ts, title_history_ts):
    # Only use title history if it's significantly newer (20s jitter buffer) OR presence is missing (0)
    if title_history_ts > 0 and (title_history_ts > (lastonline_ts + 20) or lastonline_ts == 0):
        debug_print(f"Decision: Using Title History timestamp (history={get_debug_date_from_ts(title_history_ts)} > presence={get_debug_date_from_ts(lastonline_ts)})")
        return title_history_ts, True
    debug_print(f"Decision: Using Presence timestamp (presence={get_debug_date_from_ts(lastonline_ts)} >= history={get_debug_date_from_ts(title_history_ts)})")
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
            report_recovery_error(e, context="auth", detail=f"Signing in to Xbox Live failed: {format_exception(e)}")
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
            report_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned a profile for '{gamertag}' with no account in it")
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
        report_recovery_error(e, context="target", detail=f"The profile for '{gamertag}' could not be read: {e}")
        if session:
            await session.aclose()
        sys.exit(1)
    debug_print(f"Profile fetched: XUID={xuid}, Gamerscore={gamerscore}, Tier={tier}")
    print_ok()

    print_step("Fetching presence info...")
    try:
        presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
        status, title_name, game_name, platform, lastonline_ts = xbox_process_presence_class(presence, False)
    except Exception as e:
        print()
        report_recovery_error(e, context="target", detail=f"The presence for '{gamertag}' could not be read: {e}")
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
                debug_print(f"Friends fetched via library method: {friends_count}")
            elif len(friends_list_raw) == 1:
                # Response contains only the target user's profile
                # Check if this is the unfixed library bug or if user genuinely has 0 friends
                user_profile = friends_list_raw[0]
                detail = getattr(user_profile, 'detail', None)
                actual_friend_count = getattr(detail, 'friend_count', 0) if detail else 0

                if actual_friend_count > 0:
                    # Bug: Library returned user profile but they have friends - fallback needed
                    debug_print(f"Library bug detected: returned user profile with friend_count={actual_friend_count}, falling back to direct API")
                    raise ValueError("Unfixed library bug - response contains user profile instead of friends")
                else:
                    # User genuinely has 0 friends
                    friends_count = 0
                    friends_list = []
                    debug_print("User has 0 friends (confirmed via library method)")
            else:
                # Empty response - user has 0 friends
                friends_count = 0
                friends_list = []
                debug_print("Friends fetched via library method: 0")
        else:
            # Empty people list - user has 0 friends
            friends_count = 0
            friends_list = []
            debug_print("Friends fetched via library method: 0 (empty response)")

    except Exception as e:
        debug_print(f"Library method failed or unfixed: {e}")
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
                    debug_print(f"Friends fetched via direct API: {friends_count}")
            else:
                debug_print("Could not find HTTP session for direct API call")
                # Last fallback - get count from summary
                friends_summary = await xbl_client.people.get_friends_summary_by_xuid(str(xuid))
                if hasattr(friends_summary, 'target_following_count'):
                    friends_count = friends_summary.target_following_count
                    debug_print(f"Friends count from summary: {friends_count}")

        except Exception as e2:
            debug_print(f"Direct API and summary fallbacks failed: {e2}")
            print(f"Warning: Could not fetch friends: {e2}")

    if friends_list:
        debug_print(f"Friends list ({len(friends_list)}):")
        for i, friend in enumerate(friends_list, 1):
            f_gamertag = friend.get('gamertag', 'Unknown') if isinstance(friend, dict) else getattr(friend, 'gamertag', 'Unknown')
            f_state = friend.get('presenceState', 'Unknown') if isinstance(friend, dict) else getattr(friend, 'presence_state', 'Offline')
            debug_print(f"  {i}. {f_gamertag} ({f_state})")

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
            print(f"Warning: Could not fetch game history: {e}")

        if recent_games:
            debug_print(f"Game history titles fetched: {len(recent_games)}")
            for i, title in enumerate(recent_games, 1):
                played_val = "Unknown"
                if title.title_history and title.title_history.last_time_played:
                    dt = convert_iso_str_to_datetime(title.title_history.last_time_played)
                    if dt:
                        played_val = get_date_from_ts(int(dt.timestamp()))
                debug_print(f"  {i}. {title.name} (Last played: {played_val})")
        else:
            debug_print("Game history fetched: 0")

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
            print(f"Warning: Could not fetch achievements: {e}")

        if recent_achievements:
            debug_print(f"Method 1 (Fast Feed) - Recent achievements fetched: {len(recent_achievements)}")
            for i, ach in enumerate(recent_achievements, 1):
                name = ach.name if hasattr(ach, 'name') and ach.name else "Unknown"
                state = ach.progress_state if hasattr(ach, 'progress_state') else "Unknown"
                time_unlocked = "N/A"
                if hasattr(ach, 'progression') and ach.progression.time_unlocked:
                    dt = convert_iso_str_to_datetime(ach.progression.time_unlocked)
                    if dt:
                        time_unlocked = get_date_from_ts(int(dt.timestamp()))
                debug_print(f"  {i}. {name} ({state}, Unlocked: {time_unlocked})")
        else:
            debug_print("Method 1 (Fast Feed) - Recent achievements fetched: 0")

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
        except Exception:
            pass

        w_num = 3
        w_last = 24
        w_total = 14
        fixed = 47
        w_title = max(24, term_width - fixed - 1)

        hdr = f"{'#'.ljust(w_num)}  {'Title'.ljust(w_title)}  {'Last played'.ljust(w_last)}  {'Total'.ljust(w_total)}"
        sep = f"{'-' * w_num}  {'-' * w_title}  {'-' * w_last}  {'-' * w_total}"
        print(hdr)
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
                except Exception:
                    pass

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
        debug_print("Method 2 (Deep Scan) - Checking recent games for achievements...")

        all_recent_achievements = []

        # Process top recent games to get achievements
        for title_prog in recent_games:
            # print(f"DEBUG: Checking {title_prog.name}")
            try:
                game_achievements = await xbl_client.achievements.get_achievements_xboxone_gameprogress(xuid, title_prog.title_id)
                debug_print(f"Fetching detailed achievements for '{title_prog.name}'...")

                ach_list = []
                if isinstance(game_achievements, list):
                    ach_list = game_achievements
                elif hasattr(game_achievements, 'achievements'):
                    ach_list = game_achievements.achievements

                unlocked_achs = [a for a in ach_list if a.progress_state == "Achieved"]
                if unlocked_achs:
                    debug_print(f"  > Found {len(unlocked_achs)} unlocked achievements")
                # print(f"DEBUG: Unlocked {len(unlocked_achs)}")

                for ach in unlocked_achs:
                    # Store as tuple (achievement, title_name) since we cannot modify the model
                    all_recent_achievements.append((ach, title_prog.name))

            except Exception:
                pass

        # Sort ALL collected achievements by time_unlocked (descending)
        all_recent_achievements.sort(key=lambda x: x[0].progression.time_unlocked, reverse=True)

        # Determine column widths for achievements
        term_width = 100
        try:
            import shutil as sh
            term_width = sh.get_terminal_size(fallback=(100, 24)).columns
        except Exception:
            pass

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
        print(hdr)
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


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name))


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content, filename="<config>", retired_out=None, reference_values=None):
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
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
            parsed_values[name] = ast.literal_eval(statement.value)
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
        if retired_settings and report_errors:
            print(f"* Note: {describe_retired_settings(retired_settings, chr(39) + str(config_path) + chr(39))}")
        return True
    except SyntaxError as exc:
        detail = f"Config file '{config_path}' has invalid Python syntax"
        if exc.lineno is not None:
            detail += f" at line {exc.lineno}"
        if exc.text:
            detail += f" | Source: {exc.text.rstrip()}"
        detail += f" | Parser: {exc.msg}"
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}"
    advice = classify_recovery_error(context="config.invalid", detail=detail)
    if advice_out is not None:
        advice_out.append(advice)
    if report_errors:
        print_recovery_advice(advice)
    return False


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


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
    except (TypeError, ValueError) as e:
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
    global LIVENESS_CHECK_COUNTER, LIVENESS_CHECK_INTERVAL, XBOX_ACTIVE_CHECK_INTERVAL, XBOX_CHECK_INTERVAL
    XBOX_CHECK_INTERVAL = normalize_timer_setting("XBOX_CHECK_INTERVAL", XBOX_CHECK_INTERVAL)
    XBOX_ACTIVE_CHECK_INTERVAL = normalize_timer_setting("XBOX_ACTIVE_CHECK_INTERVAL", XBOX_ACTIVE_CHECK_INTERVAL)
    LIVENESS_CHECK_INTERVAL = normalize_timer_setting("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL, allow_zero=True)
    LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / XBOX_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0


# Main function that monitors activity of the specified Xbox user
async def xbox_monitor_user(xbox_gamertag, csv_file_name, achievements_count=5, games_count=10):

    alive_counter = 0
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
        report_recovery_error(e, context="file.unwritable", detail=f"The CSV file '{csv_file_name}' could not be prepared: {e}")

    # Create a XBOX HTTP client session
    async with create_signed_session() as session:

        # Initialize with global OAUTH config options (MS_APP_CLIENT_ID & MS_APP_CLIENT_SECRET)
        auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, "")

        # Print detailed user info on startup
        print("* Fetching details for Xbox user '{}'...\n".format(xbox_gamertag))

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
            report_recovery_error(e, context="auth", detail=f"Signing in to Xbox Live failed: {format_exception(e)}")
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
            report_recovery_error(e, context="target", detail=f"The profile for '{xbox_gamertag}' could not be read: {e}")
            sys.exit(1)

        if 'profile_users' in dir(profile):

            try:
                xuid = int(profile.profile_users[0].id)
            except IndexError:
                report_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned a profile for '{xbox_gamertag}' with no account in it")
                sys.exit(1)


        if xuid == 0:
            report_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned no XUID for '{xbox_gamertag}'")
            sys.exit(1)

        # Get presence status (by XUID)
        try:
            presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
        except Exception as e:
            report_recovery_error(e, context="target", detail=f"The presence for '{xbox_gamertag}' could not be read: {e}")
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
            debug_print("User is offline, using already fetched title history fallback data...")
            lastonline_ts, fallback_used = xbox_get_best_lastonline_ts(lastonline_ts, title_history_ts)
            if fallback_used:
                lastonline_ts = title_history_ts
        if not status:
            report_recovery_error(context="xbox.malformed_response", detail=f"Xbox Live returned no online status for '{xbox_gamertag}'")
            sys.exit(1)

        status_ts_old = int(time.time())
        status_ts_old_bck = status_ts_old

        if status and status != "offline":
            status_online_start_ts = status_ts_old
            status_online_start_ts_old = status_online_start_ts

        xbox_last_status_file = f"xbox_{xbox_gamertag}_last_status.json"
        last_status_read = []
        last_status_ts = 0
        last_status = ""

        if os.path.isfile(xbox_last_status_file):
            try:
                with open(xbox_last_status_file, 'r', encoding="utf-8") as f:
                    last_status_read = json.load(f)
            except Exception as e:
                print()
                report_recovery_error(e, context="file.unreadable", detail=f"The last status could not be read from '{xbox_last_status_file}': {e}", label="Warning")
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
                report_recovery_error(e, context="file.unwritable", detail=f"The last status could not be saved to '{xbox_last_status_file}': {e}")

        if status != "offline" and game_name:
            print(f"\nUser is currently in-game:\t{game_name}")
            game_ts_old = int(time.time())
            games_number += 1

        try:
            if csv_file_name and (status != last_status):
                write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
        except Exception as e:
            report_recovery_error(e, context="file.unwritable", detail=f"The CSV entry could not be written to '{csv_file_name}': {e}")

        if last_status_ts == 0:
            if lastonline_ts and status == "offline":
                status_ts_old = lastonline_ts
            try:
                save_last_status(xbox_last_status_file, status_ts_old, status)
            except Exception as e:
                report_recovery_error(e, context="file.unwritable", detail=f"The last status could not be saved to '{xbox_last_status_file}': {e}")

        if status_ts_old != status_ts_old_bck:
            if status == "offline":
                last_status_dt_str = get_date_from_ts(status_ts_old)
                print(f"\n* Last time user was available:\t{last_status_dt_str}")
            print(f"\n* User is {str(status).upper()} for:\t\t{calculate_timespan(now_local(), int(status_ts_old), show_seconds=False)}")

        status_old = status
        game_name_old = game_name

        print_cur_ts("\nTimestamp:\t\t\t")

        alive_counter = 0
        email_sent = False
        # A poll that keeps failing for the same reason repeats the fix paragraph on every cycle without it
        recovery_hints = RecoveryHintTracker()

        m_subject = m_body = ""

        if status and status != "offline":
            sleep_interval = XBOX_ACTIVE_CHECK_INTERVAL
        else:
            sleep_interval = XBOX_CHECK_INTERVAL

        await asyncio.sleep(sleep_interval)

        # Main loop
        while True:
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
                        debug_print(f"Offline transition with missing presence timestamp, retrying presence up to {offline_grace_attempts}x every {offline_grace_delay_seconds}s...")
                        for retry_num in range(1, offline_grace_attempts + 1):
                            await asyncio.sleep(offline_grace_delay_seconds)
                            retry_presence = await xbl_client.presence.get_presence(str(xuid), PresenceLevel.ALL)
                            retry_status, retry_title_name, retry_game_name, retry_platform, retry_lastonline_ts = xbox_process_presence_class(retry_presence)
                            debug_print(f"Grace retry {retry_num}/{offline_grace_attempts}: state={retry_status}, lastonline={get_debug_date_from_ts(retry_lastonline_ts)}")

                            # Use refreshed offline payload if it now includes last_seen
                            if retry_status == "offline" and retry_lastonline_ts > 0:
                                status = retry_status
                                game_name = retry_game_name
                                platform = retry_platform
                                lastonline_ts = retry_lastonline_ts
                                presence_lastonline_cache_ts = retry_lastonline_ts
                                debug_print("Grace retry succeeded: using refreshed offline presence last_seen timestamp.")
                                break

                            # If status bounced back online, stop offline fallback for this poll.
                            if retry_status and retry_status != "offline":
                                status = retry_status
                                game_name = retry_game_name
                                platform = retry_platform
                                lastonline_ts = retry_lastonline_ts
                                if retry_lastonline_ts > 0:
                                    presence_lastonline_cache_ts = retry_lastonline_ts
                                debug_print("Grace retry indicates user is no longer offline; skipping offline fallback in this poll.")
                                break

                if status == "offline":
                    debug_print("User is offline, checking title history fallback...")
                    title_history_ts, title_history_game = await xbox_get_latest_title_played_ts(xbl_client, xuid)
                    presence_ts_for_decision = lastonline_ts
                    lastactive_source = "presence_last_seen_live"
                    lastactive_confidence = "high"

                    if presence_ts_for_decision <= 0 and presence_lastonline_cache_ts > 0:
                        presence_ts_for_decision = presence_lastonline_cache_ts
                        lastactive_source = "presence_last_seen_cached"
                        lastactive_confidence = "medium"
                        debug_print(f"Using cached presence last_seen for decision: {get_debug_date_from_ts(presence_ts_for_decision)}")
                    elif presence_ts_for_decision <= 0:
                        lastactive_source = "presence_last_seen_missing"
                        lastactive_confidence = "none"

                    effective_lastactive_ts, source_is_history = xbox_get_best_lastonline_ts(presence_ts_for_decision, title_history_ts)
                    if source_is_history:
                        lastactive_source = "title_history_fallback"
                        lastactive_confidence = "low"

                    debug_print(f"Current status: {status}")
                    debug_print(f"Title history: {title_history_ts} ('{title_history_game}')")
                    debug_print(f"Baseline:      {title_history_ts_old} ('{title_history_game_old}')")
                    debug_print(f"Last active chosen: source={lastactive_source}, confidence={lastactive_confidence}, ts={get_debug_date_from_ts(effective_lastactive_ts)}")

                if not status:
                    raise ValueError('Xbox user status is empty')
                email_sent = False
                recovery_hints.reset()
            except Exception as e:
                if status and status != "offline":
                    sleep_interval = XBOX_ACTIVE_CHECK_INTERVAL
                else:
                    sleep_interval = XBOX_CHECK_INTERVAL
                advice = classify_recovery_error(e, context="monitor", detail=f"Reading the presence for '{xbox_gamertag}' failed: {e}")
                print_recovery_advice(advice, recovery_hints, retry_note=f"retrying in {display_time(sleep_interval)}")
                # Credentials do not recover on their own, so this is the one category worth an email
                if advice.code in AUTH_RECOVERY_CODES and ERROR_NOTIFICATION and not email_sent:
                    m_subject = f"xbox_monitor: Xbox authentication error! (user: {xbox_gamertag})"
                    m_body = f"{advice.summary}\n\nTo fix: {advice.fix}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)
                    email_sent = True
                print_cur_ts("Timestamp:\t\t\t")
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
                    report_recovery_error(e, context="file.unwritable", detail=f"The last status could not be saved to '{xbox_last_status_file}': {e}", label="Warning")

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
                        m_body_played_games = f"\n\nUser played {games_number} games for total time of {display_time(game_total_ts)}"
                        print(f"User played {games_number} games for total time of {display_time(game_total_ts)}")
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
                if STATUS_NOTIFICATION or (ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag):
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

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

                if GAME_CHANGE_NOTIFICATION and m_subject and m_body:
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                game_ts_old = game_ts
                print_cur_ts("Timestamp:\t\t\t")

            # Detect gaming activity for "appear offline" users via title history
            # This triggers when we detect a new game session started while user appears offline
            if status == "offline" and title_history_ts > 0 and title_history_ts_old > 0 and title_history_ts > title_history_ts_old:
                activity_detected_ts = get_date_from_ts(title_history_ts)
                game_info = f" '{title_history_game}'" if title_history_game else ""
                print(f"User detected playing a game{game_info} (via title history)! Started: {activity_detected_ts}")

                m_subject = f"Xbox user {xbox_gamertag} detected playing{game_info} (via title history)"
                m_body = f"Xbox user {xbox_gamertag} appears offline but was detected starting a game{game_info}.\n\nGame session started: {activity_detected_ts}\n\nNote: This was detected via title history. We cannot detect when the user stops playing via this method.{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

                if ACTIVE_INACTIVE_NOTIFICATION or STATUS_NOTIFICATION:
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                print_cur_ts("Timestamp:\t\t\t")
                title_history_ts_old = title_history_ts
                change = True

            if change:
                alive_counter = 0

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
                except Exception as e:
                    report_recovery_error(e, context="file.unwritable", detail=f"The CSV entry could not be written to '{csv_file_name}': {e}")

            status_old = status
            game_name_old = game_name

            alive_counter += 1

            if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER and (status == "offline" or not status):
                print_cur_ts("Liveness check, timestamp:\t")
                alive_counter = 0

            if status and status != "offline":
                await asyncio.sleep(XBOX_ACTIVE_CHECK_INTERVAL)
            else:
                await asyncio.sleep(XBOX_CHECK_INTERVAL)


def main():
    global CHECK_INTERNET_TIMEOUT, CLI_CONFIG_PATH, DOTENV_FILE, LOCAL_TIMEZONE, LOCAL_TIMEZONE_STATE, LIVENESS_CHECK_COUNTER, LIVENESS_CHECK_INTERVAL, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, CSV_FILE, DISABLE_LOGGING, XBOX_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, STATUS_NOTIFICATION, ERROR_NOTIFICATION, XBOX_CHECK_INTERVAL, XBOX_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, stdout_bck, MS_AUTH_TOKENS_FILE, DEBUG_MODE, EXPORTED_SECRET_KEYS

    if "--generate-config" in sys.argv:
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        # A filename after the flag writes the file directly, which sidesteps the UTF-16 redirect PowerShell
        # produces for a piped template
        idx = sys.argv.index("--generate-config")
        output_file = sys.argv[idx + 1] if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-") else ""
        if output_file:
            try:
                backup_path, written = write_generated_config(output_file, config_content, force="--force" in sys.argv)
            except FileExistsError as exc:
                # Built here rather than from the context, so the fix names the file the user actually asked for
                print_recovery_advice(make_recovery_advice("file.exists", str(exc), recovery_fix_with_guide(f"Re-run with: {tool_command('--generate-config', output_file, '--force')}. The existing file is backed up with a timestamp first, or write to a different path", CONFIG_GUIDE_URL), False, str(exc)))
                sys.exit(1)
            except OSError as exc:
                report_recovery_error(exc, context="file.unwritable", detail=f"Config file '{output_file}' cannot be written: {exc}")
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

    # Read straight from sys.argv because argparse has not run yet, and the screen is cleared before it does
    if "--debug" in sys.argv:
        DEBUG_MODE = True
    if CLEAR_SCREEN and DEBUG_MODE:
        debug_print("Terminal screen clear skipped because debug mode is active")
    clear_screen(CLEAR_SCREEN and not DEBUG_MODE)

    print_startup_banner()

    parser = argparse.ArgumentParser(
        prog="xbox_monitor",
        description=("Monitor an Xbox user's playing status and send customizable email alerts [ https://github.com/misiektoja/xbox_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter
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
        help="Location of the optional config file",
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
        "--doctor",
        dest="doctor",
        action="store_true",
        help="Run preflight checks on this setup and exit",
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

    # Notifications
    notify = parser.add_argument_group("Notifications")
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

    # User information
    info = parser.add_argument_group("User information")
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

    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write status & game changes to CSV"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to xbox_monitor_<gamertag>.log"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode for technical technical logging"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Applied before the config file is read so a failing load is already visible, and again after it so a saved
    # DEBUG_MODE = False cannot switch off what the command line asked for
    apply_diagnostic_cli_flags(args)

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    # Doctor reports a broken setup instead of exiting on the first thing it finds, so the whole report is usable
    doctor_mode = bool(args.doctor)
    config_advice = None
    timezone_advice = None

    if not cfg_path and CLI_CONFIG_PATH:
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

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    # Which secrets were already exported has to be captured before load_dotenv copies the file's values into
    # os.environ, because afterwards the two sources are indistinguishable
    EXPORTED_SECRET_KEYS = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret) is not None)
    SECRET_SOURCES.clear()
    for secret in SECRET_KEYS:
        if secret_is_set(globals().get(secret)):
            SECRET_SOURCES[secret] = "configuration file"

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            # An exported variable wins over the file at startup, matching python-dotenv's own default, so a
            # one-off secret or one injected by systemd or a container is not silently shadowed by the dotenv.
            # The SIGHUP reload still overrides, because there the edited file is exactly what must take effect.
            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=False)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=False)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print_recovery_advice(missing_dependency_advice("python-dotenv", f"The dotenv file '{env_path}' cannot be read", "Or export the secrets as environment variables"), label="Warning")
            print()

    # Environment variables are a documented alternative to a dotenv file, so they apply even when no file was loaded
    for secret in SECRET_KEYS:
        val = os.getenv(secret)
        if val is not None:
            globals()[secret] = val
            # A shipped placeholder is not a value, so it never counts as a source
            if secret_is_set(val):
                SECRET_SOURCES[secret] = "environment" if secret in EXPORTED_SECRET_KEYS else "dotenv file"
            else:
                SECRET_SOURCES.pop(secret, None)

    for secret in SECRET_KEYS:
        debug_print(f"Secret {secret} resolved from {SECRET_SOURCES.get(secret, 'nowhere')}")

    try:
        validate_connectivity_timer()
    except ValueError as e:
        advice = classify_recovery_error(context="config.invalid", detail=str(e))
        if not doctor_mode:
            print_recovery_advice(advice)
            sys.exit(1)
        if config_advice is None:
            config_advice = advice

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        if get_localzone is not None:
            try:
                local_tz = get_localzone()
            except Exception:
                pass
        if local_tz and is_valid_timezone(str(local_tz)):
            LOCAL_TIMEZONE = str(local_tz)
            LOCAL_TIMEZONE_STATE = "auto"
        elif get_localzone is None:
            LOCAL_TIMEZONE_STATE = "auto_unavailable"
            timezone_advice = make_recovery_advice("dependency.missing", "The local timezone could not be detected", recovery_fix_with_guide(f"Install tzlocal with: {pip_install_command('tzlocal')} or set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, "LOCAL_TIMEZONE is Auto but tzlocal is unavailable")
        else:
            LOCAL_TIMEZONE_STATE = "auto_failed"
            timezone_advice = make_recovery_advice("config.invalid", "The local timezone could not be detected", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, "tzlocal did not return a supported timezone")
    elif not is_valid_timezone(LOCAL_TIMEZONE):
        LOCAL_TIMEZONE_STATE = "invalid"
        timezone_advice = make_recovery_advice("config.invalid", f"Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, str(LOCAL_TIMEZONE))

    if timezone_advice is not None:
        if not doctor_mode:
            print_recovery_advice(timezone_advice)
            sys.exit(1)
        # The report still stamps timestamps, so it falls back rather than stopping before the diagnosis
        LOCAL_TIMEZONE = "UTC"

    # The command-line credentials have to be in effect before the report checks them
    if args.ms_app_client_id:
        MS_APP_CLIENT_ID = args.ms_app_client_id
        if secret_is_set(MS_APP_CLIENT_ID):
            SECRET_SOURCES["MS_APP_CLIENT_ID"] = "command line"

    if args.ms_app_client_secret:
        MS_APP_CLIENT_SECRET = args.ms_app_client_secret
        if secret_is_set(MS_APP_CLIENT_SECRET):
            SECRET_SOURCES["MS_APP_CLIENT_SECRET"] = "command line"

    if args.check_interval is not None:
        XBOX_CHECK_INTERVAL = args.check_interval

    if args.active_interval is not None:
        XBOX_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    elif CSV_FILE:
        CSV_FILE = os.path.expanduser(CSV_FILE)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if args.notify_active_inactive is True:
        ACTIVE_INACTIVE_NOTIFICATION = True

    if args.notify_game_change is True:
        GAME_CHANGE_NOTIFICATION = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if doctor_mode:
        sys.exit(run_doctor(args.xbox_gamertag, cfg_path, env_path, config_advice, timezone_advice))

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("xbox_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.xbox_gamertag:
        report_recovery_error(context="target.missing", detail="XBOX_GAMERTAG needs to be defined")
        sys.exit(1)

    missing_credentials = [name for name in ("MS_APP_CLIENT_ID", "MS_APP_CLIENT_SECRET") if not secret_is_set(globals()[name])]
    if missing_credentials:
        report_recovery_error(context="secret.missing", detail=f"{' and '.join(missing_credentials)} is empty or still set to a placeholder" if len(missing_credentials) == 1 else f"{' and '.join(missing_credentials)} are empty or still set to a placeholder")
        sys.exit(1)

    if not MS_AUTH_TOKENS_FILE:
        report_recovery_error(context="config.invalid", detail="MS_AUTH_TOKENS_FILE is empty, so authorized tokens cannot be saved")
        sys.exit(1)
    MS_AUTH_TOKENS_FILE = os.path.expanduser(MS_AUTH_TOKENS_FILE)

    if args.info_mode:
        asyncio.run(get_user_info(args.xbox_gamertag, client=None, show_friends=args.show_friends, show_recent_achievements=args.show_recent_achievements, show_recent_games=True, achievements_count=args.achievements_count, games_count=args.games_count))
        sys.exit(0)

    try:
        validate_monitor_timers()
    except ValueError as e:
        report_recovery_error(context="config.invalid", detail=str(e))
        sys.exit(1)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            report_recovery_error(e, context="file.unwritable", detail=f"CSV file '{CSV_FILE}' cannot be opened for writing: {e}")
            sys.exit(1)

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        report_recovery_error(context="config.invalid", detail=str(e))
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
    if not (secret_is_set(SMTP_HOST) and secret_is_set(SMTP_USER) and secret_is_set(SMTP_PASSWORD)):
        ACTIVE_INACTIVE_NOTIFICATION = False
        GAME_CHANGE_NOTIFICATION = False
        STATUS_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    print(f"* Xbox polling intervals:\t[offline: {display_time(XBOX_CHECK_INTERVAL)}] [online: {display_time(XBOX_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[online/offline status changes = {ACTIVE_INACTIVE_NOTIFICATION}] [game changes = {GAME_CHANGE_NOTIFICATION}]\n*\t\t\t\t[all status changes = {STATUS_NOTIFICATION}] [errors = {ERROR_NOTIFICATION}]")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* ASCII log separators:\t\t{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})")
    print(f"* Xbox token cache file:\t{MS_AUTH_TOKENS_FILE or 'None'}")
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}")
    print(f"* Debug mode:\t\t\t{DEBUG_MODE}")
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}")
    print(f"* Install method:\t\t{install_method_display_name()}")

    out = f"\nMonitoring user with Xbox gamer tag {args.xbox_gamertag}"
    print(out)
    print("─" * len(out))

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
