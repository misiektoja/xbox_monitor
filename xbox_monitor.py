#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.4

Script implementing real-time monitoring of Xbox Live players activity:
https://github.com/misiektoja/xbox_monitor/

Python pip3 requirements:

xbox-webapi
httpx
python-dateutil
pytz
tzlocal
requests
"""

VERSION = 1.4

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Register new app in Azure AD: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
# - name your app (e.g. xbox_monitor)
# - for account type select "Personal Microsoft accounts only"
# - for redirect URL select "Web" type and put: http://localhost/auth/callback
# Copy value of 'Application (client) ID' to MS_APP_CLIENT_ID below (or use -u parameter)
MS_APP_CLIENT_ID = "your_ms_application_client_id"

# Next to 'Client credentials' click 'Add a certificate or secret'
# Add a new client secret with long expiration date (like 2 years) and some description (e.g. xbox_monitor_secret)
# Copy the contents from 'Value' column to MS_APP_CLIENT_SECRET below (or use -w parameter)
MS_APP_CLIENT_SECRET = "your_ms_application_secret_value"

# SMTP settings for sending email notifications, you can leave it as it is below and no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
# SMTP_HOST = "your_smtp_server_plaintext"
# SMTP_PORT = 25
# SMTP_USER = "your_smtp_user"
# SMTP_PASSWORD = "your_smtp_password"
# SMTP_SSL = False
# SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often do we perform checks for player activity when user is offline, you can also use -c parameter; in seconds
XBOX_CHECK_INTERVAL = 300  # 5 min

# How often do we perform checks for player activity when user is online, you can also use -k parameter; in seconds
XBOX_ACTIVE_CHECK_INTERVAL = 90  # 1,5 min

# Specify your local time zone so we convert Xbox API timestamps to your time (for example: 'Europe/Warsaw')
# If you leave it as 'Auto' we will try to automatically detect the local timezone
LOCAL_TIMEZONE = 'Auto'

# If user gets offline and online again (for example due to rebooting the console) during the next OFFLINE_INTERRUPT seconds then we set online start timestamp back to the previous one (so called short offline interruption) + we also keep stats from the previous session (like total time and number of played games)
OFFLINE_INTERRUPT = 420  # 7 mins

# After performing authentication the token will be saved into a file, type its location and name below
MS_AUTH_TOKENS_FILE = "xbox_tokens.json"

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL = 'http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# The name of the .log file; the tool by default will output its messages to xbox_monitor_gamertag.log file
XBOX_LOGFILE = "xbox_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is online; in seconds
XBOX_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / XBOX_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

active_inactive_notification = False
game_change_notification = False
status_notification = False


import sys
import time
import string
import json
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pytz
try:
    from tzlocal import get_localzone
except ImportError:
    pass
import platform
import re
import ipaddress
import asyncio
from httpx import HTTPStatusError
from xbox.webapi.api.client import XboxLiveClient
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox.webapi.common.signed_session import SignedSession


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Function to check internet connectivity
def check_internet():
    url = CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print(f"No connectivity, please check your network - {e}")
        sys.exit(1)
    return False


# Function to convert absolute value of seconds to human readable format
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


# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
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
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
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


# Function to send email notification
def send_email(subject, body, body_html, use_ssl):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        is_ip = ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = Header(subject, 'utf-8')

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
        print(f"Error sending email - {e}")
        return 1
    return 0


# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, status, gamename):
    try:
        csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': gamename})
        csv_file.close()
    except Exception as e:
        raise


# Function to convert UTC string returned by XBOX API to datetime object in specified timezone
def convert_utc_str_to_tz_datetime(utc_string, timezone):
    try:
        utc_string_sanitize = utc_string.split('.', 1)[0]
        dt_utc = datetime.strptime(utc_string_sanitize, '%Y-%m-%dT%H:%M:%S')

        old_tz = pytz.timezone("UTC")
        new_tz = pytz.timezone(timezone)
        dt_new_tz = old_tz.localize(dt_utc).astimezone(new_tz)
        return dt_new_tz
    except Exception as e:
        return datetime.fromtimestamp(0)


# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f"{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}")


# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("---------------------------------------------------------------------------------------------------------")


# Function to return the timestamp/datetime object in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    else:
        return ""

    return (f"{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}")


# Function to return the timestamp/datetime object in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    else:
        return ""

    return (f"{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %H:%M")}")


# Function to return the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Function to return the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_inactive_notification
    active_inactive_notification = not active_inactive_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {active_inactive_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global game_change_notification
    game_change_notification = not game_change_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {game_change_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch all status changes notifications
def toggle_all_status_changes_notifications_signal_handler(sig, frame):
    global status_notification
    status_notification = not status_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [all status changes = {status_notification}]")
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


def xbox_get_platform_mapping(platform, short=True):
    if ("scarlett" or "anaconda" or "starkville" or "lockhart" or "edith") in str(platform).lower():
        if short:
            platform = "XSX"
        else:
            platform = "Xbox One Series X/S"
    elif ("scorpio" or "edmonton") in str(platform).lower():
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

    if 'last_seen' in dir(presence):
        if presence.last_seen:
            last_seen_class = presence.last_seen
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
                    lastonline_dt = convert_utc_str_to_tz_datetime(str(last_seen_class.timestamp), LOCAL_TIMEZONE)
                    lastonline_ts = int(lastonline_dt.timestamp())
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
                    if title.name not in ("Online", "Home", "Xbox App") and title.placement != "Background":
                        game_name = title.name
                        break

    return status, title_name, game_name, platform, lastonline_ts


# Main function monitoring activity of the specified Xbox user
async def xbox_monitor_user(xbox_gamertag, error_notification, csv_file_name, csv_exists):

    alive_counter = 0
    status_ts = 0
    status_ts_old = 0
    status_online_start_ts = 0
    status_online_start_ts_old = 0
    lastonline_ts = 0
    status = ""
    xuid = 0
    location = ""
    bio = ""
    realname = ""
    title_name = ""
    game_name = ""
    platform = ""
    game_ts = 0
    game_ts_old = 0
    game_total_ts = 0
    games_number = 0
    game_total_after_offline_counted = False

    try:
        if csv_file_name:
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    # Create a XBOX HTTP client session
    async with SignedSession() as session:

        # Initialize with global OAUTH parameters (MS_APP_CLIENT_ID & MS_APP_CLIENT_SECRET)
        auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET, "")

        # Read in tokens that we received from the xbox-authenticate script
        try:
            with open(MS_AUTH_TOKENS_FILE) as f:
                tokens = f.read()
            auth_mgr.oauth = OAuth2TokenResponse.model_validate_json(tokens)
        except FileNotFoundError as e:
            print(f"File {MS_AUTH_TOKENS_FILE} not found or doesn't contain tokens! Error: {e}")
            print("\nAuthorizing via OAUTH ...")
            url = auth_mgr.generate_authorization_url()
            print(f"\nAuth via URL (paste in your web browser):\n{url}")
            authorization_code = input("\nEnter authorization code (part after '?code=' in callback URL): ")
            tokens = await auth_mgr.request_oauth_token(authorization_code)
            auth_mgr.oauth = tokens

        # Refresh tokens, just in case
        try:
            await auth_mgr.refresh_tokens()
        except HTTPStatusError as e:
            print(f"Could not refresh tokens from {MS_AUTH_TOKENS_FILE}! Error: {e}\nYou might have to delete the tokens file and re-authenticate if refresh token is expired")
            sys.exit(1)

        # Save the refreshed/updated tokens
        with open(MS_AUTH_TOKENS_FILE, mode="w") as f:
            f.write(auth_mgr.oauth.json())

        # Construct the Xbox API client from AuthenticationManager instance
        xbl_client = XboxLiveClient(auth_mgr)

        # Get profile for user with specified gamertag to grab some details like XUID
        try:
            profile = await xbl_client.profile.get_profile_by_gamertag(xbox_gamertag)
        except Exception as e:
            print(f"Error - cannot get profile for user {xbox_gamertag}: {e}")
            sys.exit(1)

        if 'profile_users' in dir(profile):

            try:
                xuid = int(profile.profile_users[0].id)
            except IndexError:
                print(f"Error - cannot get XUID for user {xbox_gamertag}")
                sys.exit(1)

            location_tmp = next((x for x in profile.profile_users[0].settings if x.id == "Location"), None)
            if location_tmp.value:
                location = location_tmp.value
            bio_tmp = next((x for x in profile.profile_users[0].settings if x.id == "Bio"), None)
            if bio_tmp.value:
                bio = bio_tmp.value
            realname_tmp = next((x for x in profile.profile_users[0].settings if x.id == "RealNameOverride"), None)
            if realname_tmp.value:
                realname = realname_tmp.value

        if xuid == 0:
            print(f"Error - cannot get XUID for user {xbox_gamertag}")
            sys.exit(1)

        # Get presence status (by XUID)
        try:
            presence = await xbl_client.presence.get_presence(str(xuid), "ALL")
        except Exception as e:
            print(f"Error - cannot get presence for user {xbox_gamertag}: {e}")
            sys.exit(1)

        status, title_name, game_name, platform, lastonline_ts = xbox_process_presence_class(presence, False)

        if not status:
            print(f"Error - cannot get status for user {xbox_gamertag}")
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
                print(f"* Cannot load last status from '{xbox_last_status_file}' file - {e}")
            if last_status_read:
                last_status_ts = last_status_read[0]
                last_status = last_status_read[1]
                xbox_last_status_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(xbox_last_status_file)))
                xbox_last_status_file_mdate = xbox_last_status_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
                xbox_last_status_file_mdate_weekday = str(calendar.day_abbr[(xbox_last_status_file_mdate_dt).weekday()])

                print(f"* Last status loaded from file '{xbox_last_status_file}' ({xbox_last_status_file_mdate_weekday} {xbox_last_status_file_mdate})")

                if last_status_ts > 0:
                    last_status_dt_str = datetime.fromtimestamp(last_status_ts).strftime("%d %b %Y, %H:%M:%S")
                    last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(last_status_ts)).weekday()])
                    print(f"* Last status read from file: {str(last_status.upper())} ({last_status_ts_weekday} {last_status_dt_str})")

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
            last_status_to_save = []
            last_status_to_save.append(status_ts_old)
            last_status_to_save.append(status)
            try:
                with open(xbox_last_status_file, 'w', encoding="utf-8") as f:
                    json.dump(last_status_to_save, f, indent=2)
            except Exception as e:
                print(f"* Cannot save last status to '{xbox_last_status_file}' file - {e}")

        print(f"\nXbox user gamertag:\t\t{xbox_gamertag}")
        print(f"Xbox XUID:\t\t\t{xuid}")
        if realname:
            print(f"Real name:\t\t\t{realname}")
        if location:
            print(f"Location:\t\t\t{location}")
        if bio:
            print(f"Bio:\t\t\t\t{bio}")

        print("\nStatus:\t\t\t\t" + str(status).upper())

        if platform:
            print("Platform:\t\t\t" + str(platform))

        if title_name and status == "offline":
            print(f"Title name:\t\t\t{title_name}")

        if status != "offline" and game_name:
            print(f"\nUser is currently in-game:\t{game_name}")
            game_ts_old = int(time.time())
            games_number += 1

        try:
            if csv_file_name and (status != last_status):
                write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status, game_name)
        except Exception as e:
            print(f"* Error: cannot write CSV entry - {e}")

        if last_status_ts == 0:
            if lastonline_ts and status == "offline":
                status_ts_old = lastonline_ts
            last_status_to_save = []
            last_status_to_save.append(status_ts_old)
            last_status_to_save.append(status)
            try:
                with open(xbox_last_status_file, 'w', encoding="utf-8") as f:
                    json.dump(last_status_to_save, f, indent=2)
            except Exception as e:
                print(f"* Cannot save last status to '{xbox_last_status_file}' file - {e}")

        if status_ts_old != status_ts_old_bck:
            if status == "offline":
                last_status_dt_str = datetime.fromtimestamp(status_ts_old).strftime("%d %b %Y, %H:%M:%S")
                last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(status_ts_old)).weekday()])
                print(f"\n* Last time user was available:\t{last_status_ts_weekday} {last_status_dt_str}")
            print(f"\n* User is {str(status).upper()} for:\t\t{calculate_timespan(int(time.time()), int(status_ts_old), show_seconds=False)}")

        status_old = status
        game_name_old = game_name

        print_cur_ts("\nTimestamp:\t\t\t")

        alive_counter = 0
        email_sent = False

        # Main loop
        while True:
            try:
                presence = await xbl_client.presence.get_presence(str(xuid), "ALL")
                status, title_name, game_name, platform, lastonline_ts = xbox_process_presence_class(presence)
                if not status:
                    raise ValueError('Xbox user status is empty')
                email_sent = False
            except Exception as e:
                if status and status != "offline":
                    sleep_interval = XBOX_ACTIVE_CHECK_INTERVAL
                else:
                    sleep_interval = XBOX_CHECK_INTERVAL
                print(f"Error getting presence, retrying in {display_time(sleep_interval)} - {e}")
                if 'validation' in str(e) or 'auth' in str(e) or 'token' in str(e):
                    print("* Xbox auth key might not be valid anymore!")
                    if error_notification and not email_sent:
                        m_subject = f"xbox_monitor: Xbox auth key error! (user: {xbox_gamertag})"
                        m_body = f"Xbox auth key might not be valid anymore: {e}{get_cur_ts("\n\nTimestamp: ")}"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, "", SMTP_SSL)
                        email_sent = True
                print_cur_ts("Timestamp:\t\t\t")
                time.sleep(sleep_interval)
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

                last_status_to_save = []
                last_status_to_save.append(status_ts)
                last_status_to_save.append(status)
                try:
                    with open(xbox_last_status_file, 'w', encoding="utf-8") as f:
                        json.dump(last_status_to_save, f, indent=2)
                except Exception as e:
                    print(f"* Cannot save last status to '{xbox_last_status_file}' file - {e}")

                print(f"Xbox user {xbox_gamertag} changed status from {status_old} to {status}{platform_str}")
                print(f"User was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))} ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})")

                m_subject_was_since = f", was {status_old}: {get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)}"
                m_subject_after = calculate_timespan(int(status_ts), int(status_ts_old), show_seconds=False)
                m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})"

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
                        m_body_short_offline_msg = f"\n\nShort offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}"
                        print(f"Short offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}")
                    act_inact_flag = True

                m_body_played_games = ""

                # Player got offline
                if status_old and status_old != "offline" and status == "offline":
                    if status_online_start_ts > 0:
                        m_subject_after = calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)
                        online_since_msg = f"(after {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)}: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                        m_subject_was_since = f", was available: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)}"
                        m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})\n\nUser was available for {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)} ({get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
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

                m_body = f"Xbox user {xbox_gamertag} changed status from {status_old} to {status}{platform_str}\n\nUser was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{m_body_short_offline_msg}{m_body_user_in_game}{m_body_played_games}{get_cur_ts("\n\nTimestamp: ")}"
                if platform:
                    platform_str = f"{platform}, "
                m_subject = f"Xbox user {xbox_gamertag} is now {status} ({platform_str}after {m_subject_after}{m_subject_was_since})"
                if status_notification or (active_inactive_notification and act_inact_flag):
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
                    print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}")
                    game_total_ts += (int(game_ts) - int(game_ts_old))
                    games_number += 1                    
                    m_body = f"Xbox user {xbox_gamertag} changed game from '{game_name_old}' to '{game_name}'{platform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}{get_cur_ts("\n\nTimestamp: ")}"
                    if platform:
                        platform_str = f"{platform}, "
                    m_subject = f"Xbox user {xbox_gamertag} changed game to '{game_name}' ({platform_str}after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"

                # User started playing new game
                elif not game_name_old and game_name:
                    print(f"Xbox user {xbox_gamertag} started playing '{game_name}'{platform_str}")
                    games_number += 1
                    m_subject = f"Xbox user {xbox_gamertag} now plays '{game_name}'{platform_str}"
                    m_body = f"Xbox user {xbox_gamertag} now plays '{game_name}'{platform_str}{get_cur_ts("\n\nTimestamp: ")}"

                # User stopped playing the game
                elif game_name_old and not game_name:
                    print(f"Xbox user {xbox_gamertag} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                    print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}")
                    if not game_total_after_offline_counted:
                        game_total_ts += (int(game_ts) - int(game_ts_old))
                    m_subject = f"Xbox user {xbox_gamertag} stopped playing '{game_name_old}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                    m_body = f"Xbox user {xbox_gamertag} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}{get_cur_ts("\n\nTimestamp: ")}"

                change = True

                if game_change_notification:
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                game_ts_old = game_ts
                print_cur_ts("Timestamp:\t\t\t")

            if change:
                alive_counter = 0

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status, game_name)
                except Exception as e:
                    print(f"* Error: cannot write CSV entry - {e}")

            status_old = status
            game_name_old = game_name

            alive_counter += 1

            if alive_counter >= TOOL_ALIVE_COUNTER and (status == "offline" or not status):
                print_cur_ts("Alive check, timestamp:\t\t")
                alive_counter = 0

            if status and status != "offline":
                time.sleep(XBOX_ACTIVE_CHECK_INTERVAL)
            else:
                time.sleep(XBOX_CHECK_INTERVAL)

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print(f"Xbox Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser("xbox_monitor")
    parser.add_argument("XBOX_GAMERTAG", nargs="?", help="User's Xbox gamertag", type=str)
    parser.add_argument("-u", "--ms_app_client_id", help="Microsoft Azure application client ID to override the value defined within the script (MS_APP_CLIENT_ID)", type=str)
    parser.add_argument("-w", "--ms_app_client_secret", help="Microsoft Azure application client secret to override the value defined within the script (MS_APP_CLIENT_SECRET)", type=str)
    parser.add_argument("-a", "--active_inactive_notification", help="Send email notification once user changes status from active to inactive and vice versa (online/offline)", action='store_true')
    parser.add_argument("-g", "--game_change_notification", help="Send email notification once user starts/changes/stops playing the game", action='store_true')
    parser.add_argument("-s", "--status_notification", help="Send email notification for all player status changes (online/away/offline)", action='store_true')
    parser.add_argument("-e", "--error_notification", help="Disable sending email notifications in case of errors like oauth issues", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is NOT offline, in seconds", type=int)
    parser.add_argument("-b", "--csv_file", help="Write all status & game changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'xbox_monitor_user.log' file", action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        try:
            local_tz = get_localzone()
        except NameError:
            pass
        if local_tz:
            LOCAL_TIMEZONE = str(local_tz)
        else:
            print("* Error: Cannot detect local timezone, consider setting LOCAL_TIMEZONE to your local timezone manually !")
            sys.exit(1)

    if not args.XBOX_GAMERTAG:
        print("* Error: XBOX_GAMERTAG needs to be defined !")
        sys.exit(1)

    if args.ms_app_client_id:
        MS_APP_CLIENT_ID = args.ms_app_client_id

    if args.ms_app_client_secret:
        MS_APP_CLIENT_SECRET = args.ms_app_client_secret

    if not MS_APP_CLIENT_ID or MS_APP_CLIENT_ID == "your_ms_application_client_id":
        print("* Error: MS_APP_CLIENT_ID (-u / --ms_app_client_id) value is empty or incorrect")
        sys.exit(1)

    if not MS_APP_CLIENT_SECRET or MS_APP_CLIENT_SECRET == "your_ms_application_secret_value":
        print("* Error: MS_APP_CLIENT_SECRET (-w / --ms_app_client_secret) value is empty or incorrect")
        sys.exit(1)

    if args.check_interval:
        XBOX_CHECK_INTERVAL = args.check_interval
        TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / XBOX_CHECK_INTERVAL

    if args.active_check_interval:
        XBOX_ACTIVE_CHECK_INTERVAL = args.active_check_interval

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.csv_file:
        csv_enabled = True
        csv_exists = os.path.isfile(args.csv_file)
        try:
            csv_file = open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8")
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing - {e}")
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled = False
        csv_file = None
        csv_exists = False

    if not args.disable_logging:
        XBOX_LOGFILE = f"{XBOX_LOGFILE}_{args.XBOX_GAMERTAG}.log"
        sys.stdout = Logger(XBOX_LOGFILE)

    active_inactive_notification = args.active_inactive_notification
    game_change_notification = args.game_change_notification
    status_notification = args.status_notification

    print(f"* Xbox timers:\t\t\t[check interval: {display_time(XBOX_CHECK_INTERVAL)}] [active check interval: {display_time(XBOX_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[active/inactive status changes = {active_inactive_notification}] [game changes = {game_change_notification}]\n*\t\t\t\t[all status changes = {status_notification}] [errors = {args.error_notification}]")
    if not args.disable_logging:
        print(f"* Output logging enabled:\t{not args.disable_logging} ({XBOX_LOGFILE})")
    else:
        print(f"* Output logging enabled:\t{not args.disable_logging}")
    if csv_enabled:
        print(f"* CSV logging enabled:\t\t{csv_enabled} ({args.csv_file})")
    else:
        print(f"* CSV logging enabled:\t\t{csv_enabled}")
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}")

    out = f"\nMonitoring user with Xbox gamertag {args.XBOX_GAMERTAG}"
    print(out)
    print("-" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    asyncio.run(xbox_monitor_user(args.XBOX_GAMERTAG, args.error_notification, args.csv_file, csv_exists))

    sys.stdout = stdout_bck
    sys.exit(0)
