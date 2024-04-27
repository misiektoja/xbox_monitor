#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.0

Script implementing real-time monitoring of Xbox Live players activity:
https://github.com/misiektoja/xbox_monitor/

Python pip3 requirements:

xbox-webapi
httpx
python-dateutil
pytz
requests
"""

VERSION=1.0

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Register new app in Azure AD: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
# - name your app (e.g. xbox_monitor)
# - for account type select "Personal Microsoft accounts only"
# - for redirect URL select "Web" type and put: http://localhost/auth/callback
# Copy value of 'Application (client) ID' to MS_APP_CLIENT_ID below
MS_APP_CLIENT_ID="your_ms_application_client_id"

# Next to 'Client credentials' click 'Add a certificate or secret'
# Add a new client secret with long expiration date (like 2 years) and some description (e.g. xbox_monitor_secret)
# Copy the contents from 'Value' column to MS_APP_CLIENT_SECRET_VALUE below
MS_APP_CLIENT_SECRET_VALUE="your_ms_application_secret_value"

# After performing authentication the token will be saved into a file, type its location and name below
MS_AUTH_TOKENS_FILE="xbox_tokens.json"

# How often do we perform checks for player activity when user is offline; in seconds
XBOX_CHECK_INTERVAL=150 # 2.5 min

# How often do we perform checks for player activity when user is online; in seconds
XBOX_ACTIVE_CHECK_INTERVAL=60 # 1 min

# Specify your local time zone so we convert Xbox API timestamps to your time
LOCAL_TIMEZONE='Europe/Warsaw'

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL=21600 # 6 hours

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL='http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT=5

# SMTP settings for sending email notifications
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
#SMTP_HOST = "your_smtp_server_plaintext"
#SMTP_PORT = 25
#SMTP_USER = "your_smtp_user"
#SMTP_PASSWORD = "your_smtp_password"
#SMTP_SSL = False
#SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# The name of the .log file; the tool by default will output its messages to xbox_monitor_gamertag.log file
xbox_logfile="xbox_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is online; in seconds
XBOX_ACTIVE_CHECK_SIGNAL_VALUE=30 # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/XBOX_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status']

active_inactive_notification=False

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
import smtplib, ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pytz
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
        self.logfile = open(filename, "a", buffering=1)

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
    url=CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print("No connectivity, please check your network -", e)
        sys.exit(1)
    return False

# Function to convert absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952), # approximation
        ('months', 2629746), # approximation
        ('weeks', 604800),  # 60 * 60 * 24 * 7
        ('days', 86400),    # 60 * 60 * 24
        ('hours', 3600),    # 60 * 60
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
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals=['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1=timestamp1
    ts2=timestamp2

    if type(timestamp1) is int:
        dt1=datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1=timestamp1
        ts1=int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2=datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is datetime:
        dt2=timestamp2
        ts2=int(round(dt2.timestamp()))
    else:
        return ""

    if ts1>=ts2:
        ts_diff=ts1-ts2
    else:
        ts_diff=ts2-ts1
        dt1, dt2 = dt2, dt1

    if ts_diff>0:
        date_diff=relativedelta.relativedelta(dt1, dt2)
        years=date_diff.years
        months=date_diff.months
        weeks=date_diff.weeks
        if not show_weeks:
            weeks=0
        days=date_diff.days
        if weeks > 0:
            days=days-(weeks*7)
        hours=date_diff.hours
        if (not show_hours and ts_diff>86400):
            hours=0
        minutes=date_diff.minutes
        if (not show_minutes and ts_diff>3600):
            minutes=0
        seconds=date_diff.seconds
        if (not show_seconds and ts_diff>60):
            seconds=0
        date_list=[years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval>0:
                name=intervals[index]
                if interval==1:
                    name = name.rstrip('s')
                result.append("{} {}".format(interval, name))
#        return ', '.join(result)
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to send email notification
def send_email(subject,body,body_html,use_ssl):

    try:     
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
        smtpObj.login(SMTP_USER,SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] =  Header(subject, 'utf-8')

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
        print("Error sending email -", e)
        return 1
    return 0

# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, status):
    try:
        csv_file=open(csv_file_name, 'a', newline='', buffering=1)
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Status': status})
        csv_file.close()
    except Exception as e:
        raise

# Function to convert UTC string returned by XBOX API to datetime object in specified timezone
def convert_utc_str_to_tz_datetime(utc_string, timezone):
    utc_string_sanitize=utc_string.split('.', 1)[0]
    dt_utc = datetime.strptime(utc_string_sanitize, '%Y-%m-%dT%H:%M:%S')

    old_tz = pytz.timezone("UTC")
    new_tz = pytz.timezone(timezone)
    dt_new_tz = old_tz.localize(dt_utc).astimezone(new_tz)
    return dt_new_tz

# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (str(ts_str) + str(calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]) + ", " + str(datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")))

# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("-----------------------------------------------------------------------------------")

# Function to return the timestamp in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M:%S")))

# Function to return the timestamp in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %H:%M")))

# Function to return the timestamp in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts,show_seconds=False):
    if show_seconds:
        out_strf="%H:%M:%S"
    else:
        out_strf="%H:%M"
    return (str(datetime.fromtimestamp(ts).strftime(out_strf)))

# Function to return the range between two timestamps; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1,ts2,between_sep=" - ", short=False):
    ts1_strf=datetime.fromtimestamp(ts1).strftime("%Y%m%d")
    ts2_strf=datetime.fromtimestamp(ts2).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2,show_seconds=True)
    else:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_short_date_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_date_from_ts(ts2)       
    return (str(out_str))

# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_inactive_notification
    active_inactive_notification=not active_inactive_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {active_inactive_notification}]")
    print_cur_ts("Timestamp:\t\t\t")

# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is online by XBOX_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global XBOX_ACTIVE_CHECK_INTERVAL
    XBOX_ACTIVE_CHECK_INTERVAL=XBOX_ACTIVE_CHECK_INTERVAL+XBOX_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* Xbox timers: [active check interval: " + display_time(XBOX_ACTIVE_CHECK_INTERVAL) + "]")
    print_cur_ts("Timestamp:\t\t\t")

# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is online by XBOX_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global XBOX_ACTIVE_CHECK_INTERVAL
    if XBOX_ACTIVE_CHECK_INTERVAL-XBOX_ACTIVE_CHECK_SIGNAL_VALUE>0:
        XBOX_ACTIVE_CHECK_INTERVAL=XBOX_ACTIVE_CHECK_INTERVAL-XBOX_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* Xbox timers: [active check interval: " + display_time(XBOX_ACTIVE_CHECK_INTERVAL) + "]")
    print_cur_ts("Timestamp:\t\t\t")

# Main function monitoring activity of the specified Xbox user
async def xbox_monitor_user(xbox_gamertag,error_notification,csv_file_name,csv_exists):

    alive_counter = 0
    status_ts = 0
    status_old_ts = 0
    status_online_start_ts = 0
    lastonline=""
    lastonline_ts = 0
    status = ""
    xuid = 0
    location = ""
    bio = ""
    realname = ""
    title_name=""
    platform=""

    try:
        if csv_file_name:
            csv_file=open(csv_file_name, 'a', newline='', buffering=1)
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print("* Error -", e)
 
    # Create a XBOX HTTP client session
    async with SignedSession() as session:

        # Initialize with global OAUTH parameters (MS_APP_CLIENT_ID & MS_APP_CLIENT_SECRET_VALUE)
        auth_mgr = AuthenticationManager(session, MS_APP_CLIENT_ID, MS_APP_CLIENT_SECRET_VALUE, "")

        # Read in tokens that you received from the xbox-authenticate script
        try:
            with open(MS_AUTH_TOKENS_FILE) as f:
                tokens = f.read()
            auth_mgr.oauth = OAuth2TokenResponse.model_validate_json(tokens)
        except FileNotFoundError as e:
            print(f"File {MS_AUTH_TOKENS_FILE} isn`t found or doesn`t contain tokens! Error: {e}")
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
        #print(f"Refreshed tokens in {MS_AUTH_TOKENS_FILE}!")

        # Construct the Xbox API client from AuthenticationManager instance
        xbl_client = XboxLiveClient(auth_mgr)

        # Get profile for user with specified gamertag to grab some details like XUID
        try:
            profile = await xbl_client.profile.get_profile_by_gamertag(xbox_gamertag)
        except Exception as e:
            print("Error - cannot get profile for user " + xbox_gamertag + ":", e)
            sys.exit(1)

        if 'profile_users' in dir(profile):
            xuid=int(profile.profile_users[0].id)

            location_tmp=next((x for x in profile.profile_users[0].settings if x.id == "Location"), None)
            if location_tmp.value:
                location=location_tmp.value           
            bio_tmp=next((x for x in profile.profile_users[0].settings if x.id == "Bio"), None)
            if bio_tmp.value:
                bio=bio_tmp.value
            realname_tmp=next((x for x in profile.profile_users[0].settings if x.id == "RealNameOverride"), None)
            if realname_tmp.value:
                realname=realname_tmp.value

        # Get presence status (by XUID)
        try:        
            presence = await xbl_client.presence.get_presence(str(xuid))
        except Exception as e:            
            print("Error - cannot get presence for user " + xbox_gamertag + ":", e)
            sys.exit(1)

        if 'state' in dir(presence):
            if presence.state:
                status=str(presence.state).lower()

        last_seen_class=""

        if 'last_seen' in dir(presence):
            if presence.last_seen:
                last_seen_class=presence.last_seen
                if 'title_name' in dir(last_seen_class):
                    if last_seen_class.title_name:
                        title_name=last_seen_class.title_name
                if 'device_type' in dir(last_seen_class):
                    if last_seen_class.device_type:
                        platform=last_seen_class.device_type
                if 'timestamp' in dir(last_seen_class):
                    if last_seen_class.timestamp:
                        lastonline=last_seen_class.timestamp                                           

        if xuid==0:
            print("Error - cannot get XUID for user " + xbox_gamertag)
            sys.exit(1)

        if not status:
            print("Error - cannot get status for user " + xbox_gamertag)
            sys.exit(1)

        if lastonline and status=="offline":
            lastonline_dt=convert_utc_str_to_tz_datetime(str(lastonline),LOCAL_TIMEZONE)
            lastonline_ts=int(lastonline_dt.timestamp())
            lastonline_str=get_date_from_ts(int(lastonline_ts))
        else:
            lastonline_str=get_cur_ts()

        status_old_ts = int(time.time())
        status_old_ts_bck = status_old_ts

        if status and status != "offline":
            status_online_start_ts=status_old_ts

        xbox_last_status_file = "xbox_" + str(xbox_gamertag) + "_last_status.json"
        last_status_read = []
        last_status_ts = 0
        last_status = ""

        try:
            if os.path.isfile(xbox_last_status_file):
                with open(xbox_last_status_file, 'r') as f:
                    last_status_read = json.load(f)
                if last_status_read:
                    last_status_ts=last_status_read[0]
                    last_status=last_status_read[1]
                    xbox_last_status_file_mdate_dt=datetime.fromtimestamp(int(os.path.getmtime(xbox_last_status_file)))
                    xbox_last_status_file_mdate=xbox_last_status_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
                    xbox_last_status_file_mdate_weekday=str(calendar.day_abbr[(xbox_last_status_file_mdate_dt).weekday()])

                    print(f"* Last status loaded from file '{xbox_last_status_file}' ({xbox_last_status_file_mdate_weekday} {xbox_last_status_file_mdate})")

                    if last_status_ts>0:
                        last_status_dt_str=datetime.fromtimestamp(last_status_ts).strftime("%d %b %Y, %H:%M:%S")
                        last_status_str=str(last_status.upper())
                        last_status_ts_weekday=str(calendar.day_abbr[(datetime.fromtimestamp(last_status_ts)).weekday()])
                        print(f"* Last status read from file: {last_status_str} ({last_status_ts_weekday} {last_status_dt_str})")   

                        if lastonline_ts and status=="offline":
                            if lastonline_ts>=last_status_ts:
                                status_old_ts=lastonline_ts
                            else:
                                status_old_ts=last_status_ts
                        if not lastonline_ts and status == "offline":
                            status_old_ts=last_status_ts
                        if status and status != "offline" and status==last_status:
                            status_online_start_ts=last_status_ts
                            status_old_ts=last_status_ts
                    
                    if last_status_ts>0 and status!=last_status:
                        last_status_to_save=[]
                        last_status_to_save.append(status_old_ts)
                        last_status_to_save.append(status)
                        with open(xbox_last_status_file, 'w') as f:
                            json.dump(last_status_to_save, f, indent=2)                    

        except Exception as e:
            print("Error -", e)

        try: 
            if csv_file_name and (status!=last_status):
                write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status)
        except Exception as e:
            print("* Cannot write CSV entry -", e)

        print(f"\nXbox user gamertag:\t\t{xbox_gamertag}")
        print(f"Xbox XUID:\t\t\t{xuid}")
        if realname:
            print(f"Real name:\t\t\t{realname}")
        if location:
            print(f"Location:\t\t\t{location}") 
        if bio:
            print(f"Bio:\t\t\t\t{bio}")

        print("\nLast seen:\t\t\t" + str(lastonline_str))    
        print("Status:\t\t\t\t" + str(status).upper())
        if platform:
            print("Platform:\t\t\t" + str(platform)) 

        if last_status_ts==0:
            if lastonline_ts and status=="offline":
                status_old_ts = lastonline_ts
            last_status_to_save=[]
            last_status_to_save.append(status_old_ts)
            last_status_to_save.append(status)
            with open(xbox_last_status_file, 'w') as f:
                json.dump(last_status_to_save, f, indent=2)   

        if status_old_ts!=status_old_ts_bck:
            if status=="offline":
                last_status_dt_str=datetime.fromtimestamp(status_old_ts).strftime("%d %b %Y, %H:%M:%S")
                last_status_str=str(last_status).upper()
                last_status_ts_weekday=str(calendar.day_abbr[(datetime.fromtimestamp(status_old_ts)).weekday()])
                print(f"\n* Last time user was available:\t{last_status_ts_weekday} {last_status_dt_str}")          
            status_str=str(status).upper()
            status_for=calculate_timespan(int(time.time()),int(status_old_ts),show_seconds=False)
            print(f"\n* User is {status_str} for:\t\t{status_for}")       

        status_old=status

        print_cur_ts("\nTimestamp:\t\t\t")

        alive_counter=0

        # Main loop
        while True:      
            try:
                presence = await xbl_client.presence.get_presence(str(xuid))
                status=""
                if 'state' in dir(presence):
                    if presence.state:
                        status=str(presence.state).lower()
                email_sent = False
                if not status:
                    raise ValueError('Xbox user status is empty')                   
            except Exception as e:
                if status and status != "offline":
                    sleep_interval=XBOX_ACTIVE_CHECK_INTERVAL
                else:
                    sleep_interval=XBOX_CHECK_INTERVAL          
                print("Error getting presence, retrying in", display_time(sleep_interval), ", error -", e)
                if 'auth' in str(e):
                    print("* Xbox auth key might not be valid anymore!")
                    if error_notification and not email_sent:
                        m_subject="xbox_monitor: Xbox auth key error! (user: " + str(xbox_gamertag) + ")"
                        m_body="Xbox auth key might not be valid anymore: " + str(e) + get_cur_ts("\n\nTimestamp: ")
                        print("Sending email notification to",RECEIVER_EMAIL)
                        send_email(m_subject,m_body,"",SMTP_SSL)
                        email_sent=True
                print_cur_ts("Timestamp:\t\t\t")
                time.sleep(sleep_interval)
                continue

            change = False
            act_inact_flag=False

            # Player status changed
            if status != status_old:
                status_ts = int(time.time())

                last_status_to_save=[]
                last_status_to_save.append(status_ts)
                last_status_to_save.append(status)
                with open(xbox_last_status_file, 'w') as f:
                    json.dump(last_status_to_save, f, indent=2)                   

                print("Xbox user " + xbox_gamertag + " changed status from " + status_old + " to " + status)
                print("User was " + status_old + " for " + calculate_timespan(int(status_ts),int(status_old_ts)) + " (" + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True) + ")")

                m_subject_was_since=", was " + status_old + ": " + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True)
                m_subject_after=calculate_timespan(int(status_ts),int(status_old_ts),show_seconds=False)
                m_body_was_since=" (" + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True) + ")"
                if status_old=="offline" and status and status != "offline":
                    print("*** User got ACTIVE ! (was offline since " + get_date_from_ts(status_old_ts) + ")")
                    status_online_start_ts=status_ts
                    act_inact_flag=True
                if status_old and status_old != "offline" and status=="offline":
                    if status_online_start_ts>0:
                        m_subject_after=calculate_timespan(int(status_ts),int(status_online_start_ts),show_seconds=False)
                        online_since_msg="(after " + calculate_timespan(int(status_ts),int(status_online_start_ts),show_seconds=False) + ": " + get_range_of_dates_from_tss(int(status_online_start_ts),int(status_ts),short=True) + ")"
                        m_subject_was_since=", was available: " + get_range_of_dates_from_tss(int(status_online_start_ts),int(status_ts),short=True)
                        m_body_was_since=" (" + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True) + ")" + "\n\nUser was available for " + calculate_timespan(int(status_ts),int(status_online_start_ts),show_seconds=False) + " (" + get_range_of_dates_from_tss(int(status_online_start_ts),int(status_ts),short=True) + ")"
                    else:
                        online_since_msg=""
                    print(f"*** User got OFFLINE ! {online_since_msg}")
                    status_online_start_ts=0
                    act_inact_flag=True

                change=True

                m_subject="Xbox user " + xbox_gamertag + " is now " + str(status) + " (after " + m_subject_after + m_subject_was_since + ")"
                m_body="Xbox user " + xbox_gamertag + " changed status from " + str(status_old) + " to " + str(status) + "\n\nUser was " + status_old + " for " + calculate_timespan(int(status_ts),int(status_old_ts)) + m_body_was_since + get_cur_ts("\n\nTimestamp: ")
                if active_inactive_notification and act_inact_flag:
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body,"",SMTP_SSL)
                status_old_ts = status_ts
                       
            if change:
                alive_counter = 0

                try: 
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status)
                except Exception as e:
                        print("* Cannot write CSV entry -", e)

                print_cur_ts("Timestamp:\t\t\t")

            status_old=status
            alive_counter+=1

            if alive_counter >= TOOL_ALIVE_COUNTER and (status=="offline" or not status):
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
        os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print("Xbox Monitoring Tool",VERSION,"\n")

    parser = argparse.ArgumentParser("xbox_monitor")
    parser.add_argument("xbox_gamertag", nargs="?", default="misiektoja", help="User's Xbox gamertag", type=str)
    parser.add_argument("-b", "--csv_file", help="Write all status changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-a","--active_inactive_notification", help="Send email notification once user changes status from active to inactive and vice versa", action='store_true')
    parser.add_argument("-e","--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is not offline, in seconds", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'xbox_monitor_user.log' file", action='store_true')
    args = parser.parse_args()

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.check_interval:
        XBOX_CHECK_INTERVAL=args.check_interval
        TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/XBOX_CHECK_INTERVAL

    if args.active_check_interval:
        XBOX_ACTIVE_CHECK_INTERVAL=args.active_check_interval

    if args.csv_file:
        csv_enabled=True
        csv_exists=os.path.isfile(args.csv_file)
        try:
            csv_file=open(args.csv_file, 'a', newline='', buffering=1)
        except Exception as e:
            print("\n* Error, CSV file cannot be opened for writing -", e)
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled=False
        csv_file=None
        csv_exists=False

    if not args.disable_logging:
        xbox_logfile = xbox_logfile + "_" + str(args.xbox_gamertag) + ".log"
        sys.stdout = Logger(xbox_logfile)

    active_inactive_notification=args.active_inactive_notification

    print("* Xbox timers: [check interval: " + display_time(XBOX_CHECK_INTERVAL) + "] [active check interval: " + display_time(XBOX_ACTIVE_CHECK_INTERVAL) + "]")
    print("* Email notifications: [active/inactive status changes = " + str(active_inactive_notification) + "] [errors = " + str(args.error_notification) + "]")
    print("* Output logging disabled:",str(args.disable_logging))
    print("* CSV logging enabled:",str(csv_enabled))

    out = "\nMonitoring user with Xbox gamertag %s" % args.xbox_gamertag
    print(out)
    print("-" * len(out))

    signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
    signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
    signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    asyncio.run(xbox_monitor_user(args.xbox_gamertag,args.error_notification,args.csv_file,csv_exists))

    sys.stdout = stdout_bck
    sys.exit(0)

