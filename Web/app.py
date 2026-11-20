from __future__ import annotations

import base64
import binascii
import csv
import hmac
import hashlib
import io
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
from pywebpush import WebPushException, webpush
from fcm import FcmClient, FcmError
from werkzeug.security import check_password_hash, generate_password_hash


load_dotenv(Path(__file__).with_name(".env"))


LANGUAGES = {"en-us", "zh-tw"}
TIME_FORMATS = {"12h", "24h"}
PIN_PATTERN = re.compile(r"^\d{6}$")
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
ACCOUNT_USERNAME_PATTERN = re.compile(r"^[^\s<>]{3,40}$")
AVATAR_FILENAME_PATTERN = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png|webp)$")
COURT_MEDIA_FILENAME_PATTERN = re.compile(
    r"^[a-f0-9]{32}\.(?:jpg|png|webp|mp4|webm)$"
)
SOCIAL_THUMBNAIL_VERSION_PATTERN = re.compile(r"^[a-f0-9]{16}$")
WEB_PUSH_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")
FCM_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_:-]{20,4096}$")
TRUSTED_PUSH_HOST_SUFFIXES = (
    "fcm.googleapis.com",
    "push.services.mozilla.com",
    "notify.windows.com",
    "web.push.apple.com",
)
MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_COURT_IMAGE_BYTES = 8 * 1024 * 1024
MAX_COURT_VIDEO_BYTES = 50 * 1024 * 1024
MAX_COURT_MEDIA_FILES = 12
MAX_COURT_INFO_BYTES = 64 * 1024
MAX_CONTACT_NAME_LENGTH = 100
MAX_CONTACT_REPLY_LENGTH = 200
MAX_CONTACT_SUBJECT_LENGTH = 150
MAX_CONTACT_MESSAGE_LENGTH = 4000
COURT_INFO_FORMAT = "badminton-court-control-panel/court-info"
COURT_INFO_VERSION = 1
COURT_INFO_MARKER = (
    f"<!-- {COURT_INFO_FORMAT}:v{COURT_INFO_VERSION} -->"
)
SOCIAL_THUMBNAIL_WIDTH = 1200
SOCIAL_THUMBNAIL_HEIGHT = 630
SOCIAL_THUMBNAIL_MAX_SOURCE_PIXELS = 40_000_000
SOCIAL_THUMBNAIL_RENDER_VERSION = 2
ACCOUNT_ROLES = {"member", "sub_admin", "admin", "super_admin"}
ADMIN_ROLES = {"sub_admin", "admin", "super_admin"}
PUBLIC_CONTACT_ID_PATTERNS = {
    "discord": re.compile(r"^[A-Za-z0-9_-]{1,100}$"),
    "line": re.compile(r"^[A-Za-z0-9._-]{1,100}$"),
    "telegram": re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$"),
}
CONTACT_METHOD_SORT_ORDER = {
    method_id: index
    for index, method_id in enumerate(
        ("discord", "email", "line", "telegram", "website")
    )
}
COURT_EXPIRED_SQL = (
    "(c.court_date || ' ' || c.end_time || ':00') "
    "< strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')"
)
LEAVE_DEADLINE_PASSED_SQL = (
    "(c.leave_deadline_enabled = 1 AND c.leave_deadline_at != '' AND "
    "c.leave_deadline_at <= strftime('%Y-%m-%dT%H:%M', 'now', 'localtime'))"
)

TRANSLATIONS = {
    "en-us": {
        "brand": "Badminton Court Control Panel",
        "home": "Courts",
        "introduction": "Introduction",
        "android_page_nav": "Android app",
        "android_page_eyebrow": "Android app",
        "android_page_title": "Your courts, in your pocket.",
        "android_page_body": "The Android app does everything the website does, in a native app: find a court, join with your PIN, and run your own events. It can also notify you when something changes.",
        "android_page_download": "Get the Android app",
        "android_page_unavailable": "The Android app is in testing. Contact us if you want to try it.",
        "android_page_contact": "Contact us",
        "android_page_requirements": "Requires Android 8.0 or later",
        "android_page_features_eyebrow": "What's in the app",
        "android_page_features_title": "Built for the court, not the desk.",
        "android_page_features_body": "The app uses the same server and the same accounts as the website. Courts you create or join appear in both.",
        "android_page_find_title": "Find a court fast",
        "android_page_find_body": "Browse and search courts, then filter by date, level, gender, or status. Court links shared with you open straight in the app.",
        "android_page_join_title": "Join in seconds",
        "android_page_join_body": "Join or leave with a name and a 6-digit PIN. You don't need an account. If a court is full, the app adds you to the waiting list.",
        "android_page_follow_title": "Follow the courts you play",
        "android_page_follow_body": "Turn on change notifications for any court. After you join or leave, the app asks whether to turn them on or off for that court.",
        "android_page_organizer_title": "Run your events",
        "android_page_organizer_body": "Create, edit, and copy courts with photos, videos, and saved venues. Run roll call and clearing from your phone.",
        "android_page_owner_title": "Hear about your courts",
        "android_page_owner_body": "When players join or leave your court, or an administrator changes it, the app notifies you. You can turn this off for each court in its settings.",
        "android_page_style_title": "Make it yours",
        "android_page_style_body": "Use it in English or Traditional Chinese, in a light or dark theme, with the website's color palettes or your device colors, and with 12- or 24-hour time.",
        "android_page_steps_title": "Get started in three steps",
        "android_page_step_one_title": "Install the app",
        "android_page_step_one_body": "Install the app on your Android phone. It connects to this website's server.",
        "android_page_step_two_title": "Sign in if you organize",
        "android_page_step_two_body": "Players can join courts without an account. Organizers sign in with their website account to manage courts and get notifications about them.",
        "android_page_step_three_title": "Allow notifications",
        "android_page_step_three_body": "Allow notifications when the app asks, so you hear about the courts you follow and the ones you run.",
        "updates": "Update history",
        "contact": "Contact",
        "contact_admin": "Contact administrator",
        "contact_eyebrow": "Support",
        "contact_title": "Contact the site administrator.",
        "contact_body": "Get help with account access, technical problems, security, privacy, or using this website.",
        "contact_operator": "Site operator",
        "contact_method": "Public contact methods",
        "contact_method_email_group": "Email",
        "contact_method_messaging_group": "Messaging",
        "contact_method_other_group": "Other methods",
        "contact_unconfigured": "The site administrator has not configured a public contact method yet.",
        "contact_email": "Email",
        "contact_website": "Website",
        "contact_discord": "Discord",
        "contact_line": "LINE",
        "contact_telegram": "Telegram",
        "contact_help_title": "What we can help with",
        "contact_account_title": "Accounts and access",
        "contact_account_body": "Report trouble signing in, creating an account, managing your profile, or accessing an event you organize.",
        "contact_technical_title": "Technical problems",
        "contact_technical_body": "Tell us about broken pages, unexpected errors, notifications, uploads, or other website behavior.",
        "contact_privacy_title": "Security and privacy",
        "contact_privacy_body": "Report a security concern or ask about personal information, access, correction, or deletion.",
        "contact_event_title": "Questions about a specific event",
        "contact_event_body": "For schedules, fees, levels, attendance, or roster decisions, contact the event organizer when possible. If you need the site administrator, include the public event link so we can identify it.",
        "contact_prepare_title": "Help us understand the issue",
        "contact_prepare_body": "Include the page or event link, what you expected, what happened, and the approximate date and time. A screenshot can help, but remove unrelated personal information first.",
        "contact_security_title": "Keep private credentials private",
        "contact_security_body": "Never send your password, administrator credentials, or a player’s 6-digit PIN. The administrator does not need them to investigate a problem.",
        "contact_form_title": "Leave a message",
        "contact_form_body": "Your message is stored securely for this site’s administrators to review.",
        "contact_sender_name": "Your name",
        "contact_sender_name_placeholder": "How should the administrator address you?",
        "contact_reply": "Reply contact",
        "contact_reply_placeholder": "Email address or messaging username",
        "contact_reply_help": "Optional. Add a way to reach you if you would like a reply.",
        "contact_subject": "Subject",
        "contact_subject_placeholder": "A short summary of your request",
        "contact_message_label": "Message",
        "contact_message_placeholder": "Describe what you need help with…",
        "contact_submit": "Send message",
        "contact_form_privacy": "The site administrators can read this message. Do not include passwords or player PINs.",
        "contact_message_sent": "Your message has been sent to the site administrator.",
        "contact_form_required": "Complete all required fields.",
        "contact_form_invalid": "Check the highlighted fields and try again.",
        "contact_name_too_long": "Your name must be 100 characters or fewer.",
        "contact_reply_too_long": "Reply contact must be 200 characters or fewer.",
        "contact_subject_too_long": "Subject must be 150 characters or fewer.",
        "contact_message_too_long": "Message must be 4,000 characters or fewer.",
        "contact_messages": "Messages",
        "contact_messages_title": "Contact messages",
        "contact_messages_body": "Review messages submitted through the public administrator-contact page.",
        "contact_messages_empty": "No contact messages match this view.",
        "contact_messages_unread": "Unread messages",
        "contact_message_from": "From",
        "contact_message_reply": "Reply contact",
        "contact_message_submitted": "Submitted",
        "contact_message_read": "Read",
        "contact_message_unread": "Unread",
        "contact_mark_read": "Mark as read",
        "contact_mark_unread": "Mark as unread",
        "contact_message_status_updated": "Message status updated.",
        "contact_filter_all": "All messages",
        "contact_filter_unread": "Unread",
        "contact_filter_read": "Read",
        "contact_notification_settings": "Message notifications",
        "contact_notification_settings_body": "Every new message is reported to the Telegram chat whenever a Telegram bot and chat are configured. The switch below also sends it to Discord. Messages are always stored in the inbox, even if delivery fails.",
        "contact_notification_enable": "Also notify Discord",
        "contact_notification_discord_ready": "Discord webhook configured",
        "contact_notification_discord_missing": "Discord webhook not configured",
        "contact_notification_telegram_ready": "Telegram bot and chat configured",
        "contact_notification_telegram_missing": "Telegram bot or chat not configured",
        "contact_notification_saved": "Message notification settings saved.",
        "contact_notification_unavailable": "Configure a valid Discord webhook before enabling Discord notifications.",
        "previous_page": "Previous",
        "next_page": "Next",
        "privacy": "Privacy",
        "privacy_title": "Privacy policy",
        "privacy_body": "How this deployment handles account, court, registration, security, and browser data.",
        "privacy_last_updated": "Last updated",
        "privacy_last_updated_value": "July 30, 2026",
        "privacy_contents": "On this page",
        "privacy_operator_notice_title": "A note for this deployment",
        "privacy_operator_notice_body": "Badminton Court Control Panel is self-hosted software. This policy describes the application’s built-in behavior. The operator of this deployment is responsible for its hosting logs, backups, configuration, legal basis, contact details, and any additional processing.",
        "privacy_deployment_details": "Deployment details",
        "privacy_operator_name": "Operator",
        "privacy_operator_unconfigured": "Not configured",
        "privacy_data_region": "Primary data region",
        "privacy_data_region_unconfigured": "Not configured",
        "privacy_contact": "Privacy contact",
        "privacy_contact_unconfigured": "The deployment operator has not configured a dedicated privacy contact. Use the operator contact method published for this website.",
        "updates_eyebrow": "What’s new",
        "updates_title": "The control panel keeps getting better.",
        "updates_body": "Follow the newest features, security improvements, and experience updates added to Badminton Court Control Panel.",
        "update_latest": "Latest",
        "update_details": "Changes in this update",
        "first_visit_intro_title": "New here? Take a quick tour.",
        "first_visit_intro_body": "Would you like to visit the introduction page and see how the control panel works?",
        "first_visit_intro_accept": "View introduction",
        "first_visit_intro_decline": "Not now",
        "intro_eyebrow": "One place for every badminton event",
        "intro_title": "Organize the court. Bring players together.",
        "intro_body": "Badminton Court Control Panel helps organizers publish badminton events and gives players a simple way to discover, review, and join the right game.",
        "intro_browse": "Find a court",
        "intro_start": "Create an event",
        "intro_features_eyebrow": "Built for the whole game",
        "intro_features_title": "Everything around the court, under control.",
        "intro_features_body": "From the first invitation to the final clearing check, each tool keeps the event clear for organizers and players.",
        "intro_discover_title": "Find the right game",
        "intro_discover_body": "Filter events by date, level, gender range, availability, venue, group, or organizer.",
        "intro_join_title": "Join without an account",
        "intro_join_feature_body": "Players register with a nickname and private 6-digit PIN. Full events automatically form a waiting list.",
        "intro_create_title": "Publish and share",
        "intro_create_feature_body": "Members create detailed events with a permanent GUID link, venue information, pricing, levels, notes, photos, and videos.",
        "intro_manage_title": "Manage every place",
        "intro_manage_body": "Track online registrations, reserved players, hidden nicknames, capacity changes, and automatic waitlist promotion.",
        "intro_finish_title": "Roll call and clearing",
        "intro_finish_body": "Lock an event when play begins, record attendance, and mark each confirmed player as cleared.",
        "intro_preferences_title": "Made for every player",
        "intro_preferences_body": "Use English or Traditional Chinese, choose a color palette and light or dark mode, and browse comfortably on desktop or mobile.",
        "intro_how_title": "From search to court in three steps.",
        "intro_step_one_title": "Explore",
        "intro_step_one_body": "Browse upcoming events and compare the schedule, location, player level, price, capacity, and organizer.",
        "intro_step_two_title": "Join",
        "intro_step_two_body": "Choose a nickname and 6-digit PIN. No account is required to join or leave a court.",
        "intro_step_three_title": "Play",
        "intro_step_three_body": "Open the shared event link for updates, participant status, media, and everything needed before the game.",
        "intro_trust_eyebrow": "Simple by design",
        "intro_trust_title": "Useful details, protected credentials.",
        "intro_trust_body": "Member passwords and player PINs are stored as secure hashes. Public registration asks only for a nickname and PIN, while language and appearance choices stay under the visitor’s control.",
        "intro_ready_title": "Ready for your next game?",
        "intro_ready_body": "Find an event that fits—or publish one for your badminton community.",
        "admin": "Admin",
        "admin_console": "Admin console",
        "hero_eyebrow": "Badminton, made simple",
        "hero_title": "Find your next game.",
        "hero_body": "See open courts, check the level, and save your spot in seconds.",
        "browse_courts": "Browse courts",
        "active_courts": "Upcoming courts",
        "active_courts_body": "Choose a session that fits your schedule and level.",
        "no_courts": "No courts are open yet.",
        "no_courts_body": "Check back soon—new sessions will appear here.",
        "date": "Date",
        "weekday_monday": "Monday",
        "weekday_tuesday": "Tuesday",
        "weekday_wednesday": "Wednesday",
        "weekday_thursday": "Thursday",
        "weekday_friday": "Friday",
        "weekday_saturday": "Saturday",
        "weekday_sunday": "Sunday",
        "time": "Time",
        "hall": "Badminton hall",
        "location": "Location",
        "court_id": "Court ID",
        "members": "Members",
        "member_range": "Member range",
        "level": "Level",
        "male": "Male",
        "female": "Female",
        "price_and_shuttlecock": "Price & shuttlecock",
        "male_price": "Male price",
        "female_price": "Female price",
        "price_hint": "TWD per player",
        "free": "Free",
        "shuttlecock": "Shuttlecock",
        "shuttlecock_placeholder": "Brand, model, grade, or quantity provided…",
        "spots_left": "spots left",
        "full": "Full",
        "view_court": "View court",
        "joined": "joined",
        "reserved": "pre-booked",
        "archived": "Archived",
        "open": "Open",
        "share": "Share",
        "copy_link": "Copy link",
        "copied": "Copied!",
        "download_thumbnail": "Download thumbnail",
        "close": "Close",
        "push_notifications": "System push notifications",
        "push_notifications_body": "Get a device notification when event information or the member list changes.",
        "push_notifications_toggle": "Notify me about court changes",
        "push_notifications_checking": "Checking notification status…",
        "push_notifications_enabled": "Notifications are on for this court.",
        "push_notifications_disabled": "Notifications are off for this court.",
        "push_notifications_enabling": "Turning on notifications…",
        "push_notifications_disabling": "Turning off notifications…",
        "push_notifications_denied": "Notifications are blocked in your browser settings.",
        "push_notifications_unsupported": "This browser does not support system push notifications.",
        "push_notifications_unavailable": "System push notifications are not configured for this site.",
        "push_notifications_error": "Unable to update notifications. Please try again.",
        "push_event_updated_title": "{name} updated",
        "push_owner_title": "Your court {name} changed",
        "push_event_updated_body": "The organizer changed this court event.",
        "push_event_archived_body": "The organizer archived this court event.",
        "push_event_restored_body": "The organizer reopened this court event.",
        "push_event_roll_started_body": "Roll call and clearing has started for this court event.",
        "push_event_editing_restored_body": "Registration and event editing are open again.",
        "push_event_deleted_body": "The organizer deleted this court event.",
        "push_members_changed_body": "The player or waiting list for this court event changed.",
        "join_title": "Join this court",
        "join_body": "Pick a username and a private 6-digit PIN.",
        "join_waitlist": "Join waiting list",
        "join_waitlist_body": "This court is full. Join the waiting list and you will be promoted automatically when a place opens.",
        "leave_title": "Leave this court",
        "leave_body": "Use the same username and PIN you joined with.",
        "leave_deadline": "Leave deadline",
        "leave_deadline_enable": "Stop players from leaving after a deadline",
        "leave_deadline_help": "After this local date and time, players can no longer leave this court themselves.",
        "leave_deadline_notice": "You can leave until {deadline}.",
        "leave_deadline_passed_title": "The leave deadline has passed",
        "leave_deadline_passed_body": "Players can no longer leave this court themselves. Contact the event organizer if you need help.",
        "leave_deadline_passed": "The deadline for leaving this court has passed.",
        "username": "Username",
        "pin": "6-digit PIN",
        "join": "Join court",
        "leave": "Leave court",
        "participants": "Players",
        "no_participants": "No online sign-ups yet.",
        "manage_participant": "Manage player",
        "rename_participant": "Rename player",
        "participant_new_name": "New username",
        "participant_renamed": "Player renamed.",
        "reset_participant_pin": "Reset PIN",
        "participant_pin_reset": "Player PIN reset.",
        "remove_participant": "Remove player",
        "remove_participant_confirm": "Remove this player from the court?",
        "participant_removed": "Player removed from the court.",
        "participation_history": "Join & leave history",
        "participation_history_eyebrow": "Activity",
        "no_participation_history": "No join or leave activity yet.",
        "history_action": "Action",
        "history_joined": "Joined",
        "history_left": "Left",
        "date_and_time": "Date & time",
        "device_information": "Device type",
        "device_ios": "iOS",
        "device_android": "Android",
        "device_mobile": "Mobile",
        "device_web": "Web",
        "waiting_list": "Waiting list",
        "waiting": "waiting",
        "waitlisted": "Waitlisted",
        "no_waiting": "No one is waiting.",
        "level_guide": "Level guide",
        "level_guide_text": "1–3 Beginner · 4–5 Elementary · 6–7 Pre-intermediate · 8–9 Intermediate · 10–12 Upper-intermediate · 13–15 Advanced · 16–18 Professional",
        "grading_chart_alt": "Taiwan badminton grading chart for levels 1 through 18",
        "grading_chart_caption": "Taiwan Badminton Promotion Association grading reference (Traditional Chinese)",
        "show_grading_chart": "Show grading chart",
        "view_full_chart": "View full-size chart",
        "level_beginner": "Beginner",
        "level_elementary": "Elementary",
        "level_preintermediate": "Pre-intermediate",
        "level_intermediate": "Intermediate",
        "level_upperintermediate": "Upper-intermediate",
        "level_advanced": "Advanced",
        "level_professional": "Professional",
        "theme": "Theme",
        "theme_system": "System",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "theme_mono": "Monochrome",
        "theme_green": "Green & lime",
        "theme_purple": "Purple",
        "theme_yellow": "Yellow",
        "language": "Language",
        "preferences": "Preferences",
        "sign_in": "Sign in",
        "sign_up": "Sign up",
        "sign_out": "Sign out",
        "account": "Account",
        "profile": "Profile",
        "profile_title": "Your profile",
        "profile_body": "Personalize how your account appears.",
        "datetime_format": "Date and time format",
        "datetime_format_help": "Choose how times are displayed when you are signed in.",
        "time_format_12h": "12-hour (AM/PM)",
        "time_format_24h": "24-hour",
        "profile_preferences_saved": "Your profile preferences have been saved.",
        "invalid_datetime_format": "Choose a valid date and time format.",
        "profile_picture": "Profile picture",
        "upload_picture": "Upload picture",
        "replace_picture": "Replace picture",
        "remove_picture": "Remove picture",
        "avatar_help": "JPEG, PNG, or WebP. Maximum 2 MB.",
        "avatar_updated": "Your profile picture has been updated.",
        "avatar_removed": "Your profile picture has been removed.",
        "saved_locations": "Saved locations",
        "saved_locations_body": "Reuse these halls when creating a court event.",
        "no_saved_locations": "You have not saved any locations yet.",
        "use_saved_location": "Use a saved location",
        "choose_saved_location": "Choose a saved location…",
        "save_this_location": "Save this location",
        "save_location_help": "Add this hall and address to your profile for future events.",
        "saved_location_added": "The location has been saved to your profile.",
        "saved_location_deleted": "The saved location has been deleted.",
        "delete_saved_location": "Delete saved location",
        "delete_saved_location_confirm": "Delete this saved location?",
        "invalid_avatar": "Choose a valid JPEG, PNG, or WebP image.",
        "avatar_too_large": "Profile pictures must be 2 MB or smaller.",
        "member_since": "Member since",
        "last_login": "Last login",
        "ip_address": "IP address",
        "never": "Never",
        "admin_account": "Administrator",
        "account_role": "Account role",
        "role_member": "Member",
        "role_sub_admin": "Sub-admin",
        "role_admin": "Admin",
        "role_super_admin": "Super admin",
        "change_role": "Change role",
        "role_updated": "The account role has been updated.",
        "invalid_role": "Choose a valid account role.",
        "cannot_change_own_role": "You cannot change your own administrator role.",
        "cannot_manage_super_admin": "This super-admin account cannot be modified.",
        "admin_account_delete_disabled": "Administrator accounts must be managed by a super-admin.",
        "delete_account": "Delete account",
        "delete_account_title": "Delete your account",
        "delete_account_warning": "This permanently removes your profile and sign-in access. Your published courts will remain available and can be managed by an administrator.",
        "delete_account_confirm": "Permanently delete your account?",
        "account_deleted": "Your account has been deleted.",
        "my_courts": "My courts",
        "my_courts_title": "Your court events",
        "my_courts_body": "Create and manage the badminton events you organize.",
        "users": "Users",
        "user_management": "User management",
        "user_management_body": "Manage member access and temporary passwords.",
        "member_login_title": "Sign in to your account",
        "member_login_body": "Manage your courts or create a new event.",
        "signup_title": "Create your account",
        "signup_body": "Start organizing and sharing your own court events.",
        "confirm_password": "Confirm password",
        "create_account": "Create account",
        "have_account": "Already have an account?",
        "need_account": "New to Badminton Court Control Panel?",
        "account_created": "Your account is ready.",
        "username_taken": "That username is already in use.",
        "account_username_help": "Use 3–40 characters without spaces.",
        "password_help": "Use at least 8 characters.",
        "password_too_short": "Password must contain at least 8 characters.",
        "password_mismatch": "The passwords do not match.",
        "change_password": "Change password",
        "change_password_title": "Change your password",
        "change_password_body": "Confirm your current password and choose a new one.",
        "current_password": "Current password",
        "new_password": "New password",
        "password_changed": "Your password has been changed.",
        "temporary_password_required": "You must change your temporary password before continuing.",
        "temporary_password": "Temporary password",
        "set_temporary_password": "Set temporary password",
        "temporary_password_set": "Temporary password set. The user must change it at the next login.",
        "account_archived": "This account has been archived.",
        "account_banned": "This account has been banned.",
        "account_archived_success": "User account archived.",
        "account_restored_success": "User account restored.",
        "account_banned_success": "User account banned.",
        "account_unbanned_success": "User account unbanned.",
        "active_account": "Active",
        "banned": "Banned",
        "ban_account": "Ban account",
        "ban_account_confirm": "Ban this user account? They will immediately lose access.",
        "unban_account": "Unban account",
        "archive_account": "Archive account",
        "archive_account_confirm": "Archive this user account?",
        "restore_account": "Restore account",
        "delete_user_account": "Delete account",
        "delete_user_account_confirm": "Permanently delete this archived account? Its published courts will remain available without an owner.",
        "user_account_deleted": "User account permanently deleted.",
        "account_must_be_archived": "Archive the account before deleting it.",
        "must_change_password": "Password change required",
        "reset_login_retries": "Reset failed logins",
        "reset_login_retries_confirm": "Reset all failed login attempts for this user across every IP address?",
        "login_retries_reset": "Failed login attempts have been reset.",
        "no_users": "No member accounts yet.",
        "password": "Password",
        "dashboard": "Dashboard",
        "dashboard_title": "Court management",
        "dashboard_body": "Create sessions and keep your public schedule current.",
        "roll_and_clearing": "Roll call & clearing",
        "start_roll_and_clearing": "Start roll call & clearing",
        "roll_and_clearing_confirm": "Start roll call and clearing? Court details and participant changes will become read-only.",
        "roll_and_clearing_started": "Roll call and clearing started. This court is now read-only.",
        "editing_mode_restored": "Editing mode restored. Registration and court details are open again.",
        "roll_and_clearing_body": "Record attendance and clearing for each confirmed member.",
        "check_uncheck_all": "Check/uncheck all",
        "all": "All",
        "roll_call": "Roll call",
        "cleared": "Cleared",
        "save_member_statuses": "Save member statuses",
        "member_statuses_saved": "Member statuses saved.",
        "read_only": "Read-only",
        "court_read_only": "This court is read-only.",
        "court_read_only_body": "Registration and participant changes are closed.",
        "member_source": "Source",
        "unnamed_reserved_member": "Reserved member",
        "new_court": "New court",
        "event_information": "Event information",
        "event_name": "Event name",
        "event_name_placeholder": "For example: Friday evening games",
        "badminton_name": "Badminton group name",
        "badminton_name_placeholder": "Club, team, or group name",
        "optional": "Optional",
        "all_courts": "All courts",
        "all_courts_body": "Browse every active badminton session.",
        "creator": "Event creator",
        "filter_courts": "Filter courts",
        "filter_search": "Event, group, hall, location, court ID, or creator",
        "filter_date": "Event date",
        "date_from": "From date",
        "date_to": "To date",
        "filter_level": "Player level",
        "filter_gender": "Level gender",
        "both_genders": "Male & female",
        "filter_status": "Court status",
        "show_expired": "Show expired",
        "any_level": "Any level",
        "any_status": "Any status",
        "apply_filters": "Apply filters",
        "clear_filters": "Clear",
        "filter_results": "results",
        "homepage_settings": "Homepage settings",
        "homepage_settings_body": "Choose how many upcoming courts appear on the homepage.",
        "homepage_court_limit": "Maximum homepage courts",
        "homepage_court_limit_help": "Enter a number from 1 to 100.",
        "save_settings": "Save settings",
        "settings_saved": "Homepage settings saved.",
        "invalid_homepage_court_limit": "Homepage court limit must be from 1 to 100.",
        "expired": "Expired",
        "court_expired": "This event has ended",
        "court_expired_body": "Registration and participant changes are closed.",
        "status": "Status",
        "actions": "Actions",
        "archive": "Archive",
        "restore": "Restore",
        "edit": "Edit",
        "duplicate": "Duplicate",
        "court_info": "Court information file",
        "court_info_help": "Import a court_info.md file to prefill this form. Court registrations, PINs, history, media files, ownership, and the public link are never imported.",
        "court_info_choose": "Choose court_info.md",
        "court_info_no_file": "Select a Markdown file (.md)",
        "court_info_import": "Import court_info.md",
        "court_info_export": "Export",
        "export_all_courts_csv": "Export all courts (CSV)",
        "court_info_imported": "Court information imported. Review the form, then save it to create the event.",
        "court_info_imported_review": "Court information imported. Review the highlighted fields before saving.",
        "court_info_invalid": "Choose a valid court_info.md file exported by this site.",
        "court_info_too_large": "court_info.md must be 64 KB or smaller.",
        "delete": "Delete",
        "delete_confirm": "Permanently delete this court and all of its sign-ups?",
        "archive_confirm": "Archive this court?",
        "create_title": "Create a court",
        "create_body": "Set the schedule, capacity, and player level.",
        "edit_title": "Edit court",
        "edit_body": "Update the schedule, capacity, or player level without changing the public link.",
        "start_time": "Start time",
        "end_time": "End time",
        "time_hint": "24-hour · HH:MM",
        "hall_name": "Hall name",
        "hall_search": "Search for a hall",
        "selected_hall": "Selected hall",
        "hall_placeholder": "Start typing a badminton hall…",
        "hall_search_help": "Choose a Google suggestion to fill the address automatically.",
        "hall_search_setup": "Live Google suggestions require GOOGLE_MAPS_API_KEY; the Maps search link remains available.",
        "hall_search_error": "Could not load this place. Please choose another suggestion.",
        "hall_api_error": "Google Places rejected the request. Check billing, enable Maps JavaScript API and Places API (New), and allow this website in the API key restrictions. Manual entry is now enabled.",
        "location_placeholder": "Full address or Google Maps location",
        "remark": "Remark",
        "remark_placeholder": "Add meetup notes or other details…",
        "event_media": "Event photos & videos",
        "event_media_body": "Show players the venue, courts, or event atmosphere.",
        "media_upload": "Add photos or videos",
        "current_section": "Current section",
        "jump_to_section": "Jump to section",
        "media_browse_files": "Browse files",
        "media_choose_multiple": "Select multiple files at once",
        "media_files_selected": "{count} files selected",
        "media_upload_help": "JPEG, PNG, or WebP up to 8 MB; MP4 or WebM up to 50 MB. Up to 12 files per event.",
        "current_media": "Current media",
        "remove_media": "Remove when changes are saved",
        "media_invalid": "Choose a valid JPEG, PNG, WebP, MP4, or WebM file.",
        "media_too_large": "An image exceeds 8 MB or a video exceeds 50 MB.",
        "media_too_many": "Each event can contain up to 12 photos and videos.",
        "event_gallery": "Event gallery",
        "court_media_alt": "Event photo from {hall}",
        "search_maps": "Search on Google Maps",
        "member_min": "Minimum members",
        "member_max": "Maximum members",
        "ordered_count": "Already booked",
        "ordered_help": "Players already confirmed outside this website.",
        "reserved_nicknames": "Reserved player nicknames",
        "reserved_nicknames_help": "Optionally record one nickname for each pre-booked place. Drag players or use the arrow buttons to reorder them.",
        "reserved_nickname": "Reserved nickname",
        "reserved_nickname_placeholder": "Nickname (optional)",
        "drag_to_reorder": "Drag to reorder",
        "move_up": "Move up",
        "move_down": "Move down",
        "reserved_players": "Reserved players",
        "reserved_name_visibility": "Nickname visibility",
        "show_reserved_names": "Show on public page",
        "hide_reserved_names": "Hide from public page",
        "hidden_from_viewers": "Hidden from viewers",
        "nickname_too_long": "Each nickname must be 40 characters or fewer.",
        "male_min": "Male minimum",
        "male_max": "Male maximum",
        "female_min": "Female minimum",
        "female_max": "Female maximum",
        "create_court": "Create court",
        "save_changes": "Save changes",
        "cancel": "Cancel",
        "public_link": "Public link",
        "created": "Created",
        "court_not_found": "Court not found",
        "court_not_found_body": "This link may be incorrect or the court may have been deleted.",
        "back_home": "Back to courts",
        "footer": "Create events, gather players, and keep every court organized.",
        "licenses": "Licenses",
        "license_title": "Asset licenses",
        "license_body": "Credits, license information, and development acknowledgments for Badminton Court Control Panel.",
        "shuttlecock_icon": "Shuttlecock website icon",
        "icon_attribution": "Shuttlecock icon designed by the contributor credited on the Flaticon source page, from Flaticon.",
        "icon_usage": "Used as the website favicon in PNG format.",
        "source_page": "Source page",
        "flaticon_license": "Flaticon license",
        "flaticon_terms": "Terms of use",
        "development_acknowledgment": "Development acknowledgment",
        "codex_support_title": "Developed with support from OpenAI Codex",
        "codex_support_body": "Badminton Court Control Panel was developed with assistance from Codex, OpenAI’s coding agent, for implementation, review, and testing.",
        "codex_responsibility": "The project owner remains responsible for this website, its operation, and its content. This acknowledgment does not imply OpenAI endorsement or ownership.",
        "codex_official_page": "Official Codex page",
        "noto_font": "Noto Sans Traditional Chinese font",
        "noto_font_attribution": "Noto Sans Traditional Chinese is provided by the Noto project and is licensed under the SIL Open Font License 1.1.",
        "noto_font_usage": "The bundled variable font renders English and Traditional Chinese text in generated social-sharing thumbnails.",
        "font_license": "Font license",
        "joined_success": "You joined the court.",
        "joined_waitlist_success": "The court is full, so you have been added to the waiting list.",
        "left_success": "You left the court.",
        "court_created": "Court created.",
        "court_updated": "Court updated.",
        "court_duplicated": "Court information copied. Save the form to create the new event.",
        "court_archived": "Court archived.",
        "court_restored": "Court restored.",
        "court_deleted": "Court deleted.",
        "invalid_login": "Incorrect username or password.",
        "login_attempts_remaining": "Incorrect username or password. {count} attempts remaining.",
        "login_locked": "Too many failed attempts. Try again in {minutes} minutes.",
        "leave_attempts_remaining": "The username or PIN is incorrect. Attempts remaining: {count}.",
        "leave_locked": "Too many failed leave attempts. Try again in {minutes} minutes.",
        "signed_out": "You are signed out.",
        "invalid_csrf": "Your session expired. Please try again.",
        "turnstile_required": "Complete the Cloudflare Turnstile verification and try again.",
        "invalid_username": "Use a username between 2 and 40 characters.",
        "invalid_pin": "PIN must contain exactly 6 digits.",
        "duplicate_username": "That username has already joined this court.",
        "invalid_credentials": "The username or PIN is incorrect.",
        "court_closed": "This court is not accepting players.",
        "court_full": "This court is full.",
        "invalid_form": "Please check the highlighted court details.",
        "joined_on_site": "Online",
    },
    "zh-tw": {
        "brand": "羽球場控面板",
        "home": "球場",
        "introduction": "網站介紹",
        "android_page_nav": "Android App",
        "android_page_eyebrow": "Android App",
        "android_page_title": "場次資訊，隨身掌握。",
        "android_page_body": "Android App 以原生介面提供網站的所有功能：搜尋場次、用 PIN 碼報名、管理自己的活動，場次有異動時還能通知你。",
        "android_page_download": "下載 Android App",
        "android_page_unavailable": "Android App 正在測試中，想試用的話歡迎與我們聯絡。",
        "android_page_contact": "聯絡我們",
        "android_page_requirements": "需要 Android 8.0 以上版本",
        "android_page_features_eyebrow": "App 功能",
        "android_page_features_title": "為球場設計，不只在電腦前用。",
        "android_page_features_body": "App 與網站使用同一個伺服器和同一組帳號，你建立或報名的場次在兩邊都看得到。",
        "android_page_find_title": "快速找到場次",
        "android_page_find_body": "瀏覽與搜尋場次，並依日期、程度、性別或狀態篩選。別人分享給你的場次連結會直接在 App 中開啟。",
        "android_page_join_title": "幾秒完成報名",
        "android_page_join_body": "輸入名稱與 6 位數 PIN 碼即可報名或退出，不需要帳號。場次額滿時，App 會幫你加入候補名單。",
        "android_page_follow_title": "追蹤你打的場次",
        "android_page_follow_body": "任何場次都能開啟異動通知。報名或退出後，App 會詢問你是否要開啟或關閉該場次的通知。",
        "android_page_organizer_title": "管理你的活動",
        "android_page_organizer_body": "建立、編輯與複製場次，可附上照片、影片與常用場館；點名與清場也能在手機上完成。",
        "android_page_owner_title": "掌握你開的場次",
        "android_page_owner_body": "球友報名或退出你的場次，或管理員修改場次時，App 都會通知你。每個場次都可以在場次設定中關閉此通知。",
        "android_page_style_title": "打造你的風格",
        "android_page_style_body": "支援英文與繁體中文、淺色與深色主題、網站配色或裝置配色，以及 12 或 24 小時制。",
        "android_page_steps_title": "三個步驟開始使用",
        "android_page_step_one_title": "安裝 App",
        "android_page_step_one_body": "在 Android 手機上安裝 App，它會連線到本網站的伺服器。",
        "android_page_step_two_title": "主揪請登入",
        "android_page_step_two_body": "球友不需要帳號即可報名。主揪使用網站帳號登入後，就能管理場次並收到場次通知。",
        "android_page_step_three_title": "允許通知",
        "android_page_step_three_body": "App 詢問時請允許通知，才能收到你追蹤和你開的場次的異動。",
        "updates": "更新紀錄",
        "contact": "聯絡我們",
        "contact_admin": "聯絡網站管理員",
        "contact_eyebrow": "支援服務",
        "contact_title": "聯絡網站管理員。",
        "contact_body": "如需帳號存取、技術問題、安全性、隱私權或網站使用協助，請透過此頁聯絡。",
        "contact_operator": "網站營運者",
        "contact_method": "公開聯絡方式",
        "contact_method_email_group": "電子郵件",
        "contact_method_messaging_group": "即時通訊",
        "contact_method_other_group": "其他聯絡方式",
        "contact_unconfigured": "網站管理員尚未設定公開聯絡方式。",
        "contact_email": "電子郵件",
        "contact_website": "網站",
        "contact_discord": "Discord",
        "contact_line": "LINE",
        "contact_telegram": "Telegram",
        "contact_help_title": "我們可以協助的事項",
        "contact_account_title": "帳號與存取",
        "contact_account_body": "回報登入、建立帳號、管理個人資料，或存取自己主辦場次時遇到的問題。",
        "contact_technical_title": "技術問題",
        "contact_technical_body": "告訴我們頁面故障、非預期錯誤、通知、上傳或其他網站功能異常。",
        "contact_privacy_title": "安全性與隱私權",
        "contact_privacy_body": "回報安全性疑慮，或詢問個人資料的查詢、更正與刪除事宜。",
        "contact_event_title": "特定活動的問題",
        "contact_event_body": "若問題與時間、費用、程度、出席或名單安排有關，請優先聯絡活動主辦者。如需網站管理員協助，請附上公開活動連結，方便辨識場次。",
        "contact_prepare_title": "協助我們了解問題",
        "contact_prepare_body": "請附上頁面或活動連結、預期結果、實際情況，以及大約發生日期與時間。螢幕截圖也能協助判斷，但請先移除無關的個人資訊。",
        "contact_security_title": "請妥善保護私人憑證",
        "contact_security_body": "請勿傳送密碼、管理員憑證或球友的 6 位數 PIN 碼；網站管理員不需要這些資料即可調查問題。",
        "contact_form_title": "留言給網站管理員",
        "contact_form_body": "你的留言會安全地儲存，供此網站的管理員查看。",
        "contact_sender_name": "你的名稱",
        "contact_sender_name_placeholder": "管理員應如何稱呼你？",
        "contact_reply": "回覆聯絡方式",
        "contact_reply_placeholder": "電子郵件地址或通訊軟體帳號",
        "contact_reply_help": "選填；如希望收到回覆，請提供可聯絡你的方式。",
        "contact_subject": "主旨",
        "contact_subject_placeholder": "簡短說明你的需求",
        "contact_message_label": "留言內容",
        "contact_message_placeholder": "請描述需要協助的事項…",
        "contact_submit": "送出留言",
        "contact_form_privacy": "網站管理員可以查看此留言。請勿填入密碼或球友 PIN 碼。",
        "contact_message_sent": "你的留言已送交網站管理員。",
        "contact_form_required": "請填寫所有必填欄位。",
        "contact_form_invalid": "請檢查標示的欄位後再試一次。",
        "contact_name_too_long": "名稱不可超過 100 個字元。",
        "contact_reply_too_long": "回覆聯絡方式不可超過 200 個字元。",
        "contact_subject_too_long": "主旨不可超過 150 個字元。",
        "contact_message_too_long": "留言內容不可超過 4,000 個字元。",
        "contact_messages": "留言",
        "contact_messages_title": "聯絡留言",
        "contact_messages_body": "查看訪客透過公開網站管理員聯絡頁面送出的留言。",
        "contact_messages_empty": "此檢視目前沒有聯絡留言。",
        "contact_messages_unread": "未讀留言",
        "contact_message_from": "留言者",
        "contact_message_reply": "回覆聯絡方式",
        "contact_message_submitted": "送出時間",
        "contact_message_read": "已讀",
        "contact_message_unread": "未讀",
        "contact_mark_read": "標示為已讀",
        "contact_mark_unread": "標示為未讀",
        "contact_message_status_updated": "留言狀態已更新。",
        "contact_filter_all": "全部留言",
        "contact_filter_unread": "未讀",
        "contact_filter_read": "已讀",
        "contact_notification_settings": "留言通知",
        "contact_notification_settings_body": "只要設定了 Telegram Bot 與聊天室，每則新留言都會回報到 Telegram 聊天室；下方開關可另外傳送到 Discord。即使外部通知傳送失敗，留言仍會保存在收件匣。",
        "contact_notification_enable": "同時通知 Discord",
        "contact_notification_discord_ready": "Discord Webhook 已設定",
        "contact_notification_discord_missing": "Discord Webhook 尚未設定",
        "contact_notification_telegram_ready": "Telegram Bot 與聊天室已設定",
        "contact_notification_telegram_missing": "Telegram Bot 或聊天室尚未設定",
        "contact_notification_saved": "留言通知設定已儲存。",
        "contact_notification_unavailable": "啟用 Discord 通知前，請先設定有效的 Discord Webhook。",
        "previous_page": "上一頁",
        "next_page": "下一頁",
        "privacy": "隱私權",
        "privacy_title": "隱私權政策",
        "privacy_body": "說明此網站如何處理帳號、場次、報名、安全性及瀏覽器資料。",
        "privacy_last_updated": "最後更新",
        "privacy_last_updated_value": "2026 年 7 月 30 日",
        "privacy_contents": "本頁內容",
        "privacy_operator_notice_title": "關於此部署網站",
        "privacy_operator_notice_body": "羽球場控面板是可自行架設的軟體。本政策說明應用程式內建的資料處理方式；此部署網站的營運者仍須負責主機紀錄、備份、設定、法律依據、聯絡資訊及任何額外的資料處理。",
        "privacy_deployment_details": "部署資訊",
        "privacy_operator_name": "營運者",
        "privacy_operator_unconfigured": "尚未設定",
        "privacy_data_region": "主要資料地區",
        "privacy_data_region_unconfigured": "尚未設定",
        "privacy_contact": "隱私權聯絡方式",
        "privacy_contact_unconfigured": "此部署網站的營運者尚未設定專用的隱私權聯絡方式；請使用本網站公布的營運者聯絡管道。",
        "updates_eyebrow": "最新消息",
        "updates_title": "羽球場控面板，持續變得更好。",
        "updates_body": "查看羽球場控面板新增的功能、安全性改善與使用體驗更新。",
        "update_latest": "最新",
        "update_details": "本次更新內容",
        "first_visit_intro_title": "第一次來嗎？先快速認識網站。",
        "first_visit_intro_body": "是否前往網站介紹頁，了解羽球場控面板的主要功能？",
        "first_visit_intro_accept": "查看網站介紹",
        "first_visit_intro_decline": "暫時不用",
        "intro_eyebrow": "每一場羽球活動，都在同一個地方",
        "intro_title": "管理場次，連結每一位球友。",
        "intro_body": "Badminton Court Control Panel 協助主辦者發布羽球活動，也讓球友能簡單地搜尋、了解並加入適合自己的場次。",
        "intro_browse": "尋找場次",
        "intro_start": "建立活動",
        "intro_features_eyebrow": "為整場活動而設計",
        "intro_features_title": "球場內外的大小事，一次掌握。",
        "intro_features_body": "從第一次邀請到最後結清，每項工具都讓主辦者與球友清楚掌握活動狀況。",
        "intro_discover_title": "找到適合的場次",
        "intro_discover_body": "依日期、程度、男女程度範圍、名額、場館、羽球團或主辦者篩選活動。",
        "intro_join_title": "免帳號快速報名",
        "intro_join_feature_body": "球友只需暱稱與私密 6 位數 PIN 碼即可報名；額滿時會自動加入候補名單。",
        "intro_create_title": "發布並分享活動",
        "intro_create_feature_body": "會員可建立完整場次，加入固定 GUID 連結、場館、費用、程度、備註、相片與影片。",
        "intro_manage_title": "管理每一個名額",
        "intro_manage_body": "掌握線上報名、預訂球友、隱藏暱稱、人數調整，以及候補自動遞補。",
        "intro_finish_title": "點名與結清",
        "intro_finish_body": "活動開始後可鎖定場次，記錄出席狀態，並逐一確認正式成員是否完成結清。",
        "intro_preferences_title": "符合每位球友的使用習慣",
        "intro_preferences_body": "支援英文與繁體中文、多種配色及明暗模式，並針對桌面與行動裝置提供舒適體驗。",
        "intro_how_title": "三個步驟，從搜尋到上場。",
        "intro_step_one_title": "探索",
        "intro_step_one_body": "瀏覽即將開始的活動，比較時間、地點、程度、費用、名額與主辦者。",
        "intro_step_two_title": "加入",
        "intro_step_two_body": "設定暱稱與 6 位數 PIN 碼，加入或退出場次都不需要註冊會員。",
        "intro_step_three_title": "上場",
        "intro_step_three_body": "透過分享連結查看最新資訊、參加狀態、活動媒體，以及上場前需要知道的一切。",
        "intro_trust_eyebrow": "簡單，也重視安全",
        "intro_trust_title": "公開實用資訊，妥善保護登入資料。",
        "intro_trust_body": "會員密碼與球友 PIN 碼皆以安全雜湊儲存。公開報名只需要暱稱與 PIN 碼，語言及外觀偏好則由訪客自行決定。",
        "intro_ready_title": "準備好迎接下一場球了嗎？",
        "intro_ready_body": "找到適合你的活動，或為自己的羽球社群發布新場次。",
        "admin": "管理",
        "admin_console": "管理後台",
        "hero_eyebrow": "輕鬆揪團，準時上場",
        "hero_title": "找到你的下一場球。",
        "hero_body": "查看開放場次、確認程度，幾秒內完成報名。",
        "browse_courts": "瀏覽場次",
        "active_courts": "即將開打",
        "active_courts_body": "選擇適合你時間與程度的場次。",
        "no_courts": "目前沒有開放場次",
        "no_courts_body": "請稍後再來，新場次會顯示在這裡。",
        "date": "日期",
        "weekday_monday": "星期一",
        "weekday_tuesday": "星期二",
        "weekday_wednesday": "星期三",
        "weekday_thursday": "星期四",
        "weekday_friday": "星期五",
        "weekday_saturday": "星期六",
        "weekday_sunday": "星期日",
        "time": "時間",
        "hall": "羽球館",
        "location": "地點",
        "court_id": "場地編號",
        "members": "人數",
        "member_range": "人數範圍",
        "level": "程度",
        "male": "男性",
        "female": "女性",
        "price_and_shuttlecock": "費用與用球",
        "male_price": "男性費用",
        "female_price": "女性費用",
        "price_hint": "每人新台幣",
        "free": "免費",
        "shuttlecock": "用球資訊",
        "shuttlecock_placeholder": "提供的羽球品牌、型號、等級或數量…",
        "spots_left": "個名額",
        "full": "已額滿",
        "view_court": "查看場次",
        "joined": "已報名",
        "reserved": "已預訂",
        "archived": "已封存",
        "open": "開放中",
        "share": "分享",
        "copy_link": "複製連結",
        "copied": "已複製！",
        "download_thumbnail": "下載縮圖",
        "close": "關閉",
        "push_notifications": "系統推播通知",
        "push_notifications_body": "場次資訊或球友名單變更時，在你的裝置上接收通知。",
        "push_notifications_toggle": "通知我場次變更",
        "push_notifications_checking": "正在確認通知狀態…",
        "push_notifications_enabled": "已開啟此場次的通知。",
        "push_notifications_disabled": "未開啟此場次的通知。",
        "push_notifications_enabling": "正在開啟通知…",
        "push_notifications_disabling": "正在關閉通知…",
        "push_notifications_denied": "瀏覽器設定已封鎖通知。",
        "push_notifications_unsupported": "此瀏覽器不支援系統推播通知。",
        "push_notifications_unavailable": "此網站尚未設定系統推播通知。",
        "push_notifications_error": "無法更新通知設定，請再試一次。",
        "push_event_updated_title": "{name} 已更新",
        "push_owner_title": "你的場次「{name}」有異動",
        "push_event_updated_body": "主辦者已變更此羽球場次。",
        "push_event_archived_body": "主辦者已封存此羽球場次。",
        "push_event_restored_body": "主辦者已重新開放此羽球場次。",
        "push_event_roll_started_body": "此場次已開始點名與結清。",
        "push_event_editing_restored_body": "此場次已重新開放報名與編輯。",
        "push_event_deleted_body": "主辦者已刪除此羽球場次。",
        "push_members_changed_body": "此場次的球友或候補名單已變更。",
        "join_title": "加入場次",
        "join_body": "設定使用者名稱與私密的 6 位數 PIN 碼。",
        "join_waitlist": "加入候補名單",
        "join_waitlist_body": "此場次已額滿。加入候補後，如有名額釋出，系統會自動依序遞補。",
        "leave_title": "離開場次",
        "leave_body": "請輸入報名時使用的名稱與 PIN 碼。",
        "leave_deadline": "最後退出期限",
        "leave_deadline_enable": "超過期限後不允許球友自行退出",
        "leave_deadline_help": "超過此本地日期與時間後，球友將無法自行退出此場次。",
        "leave_deadline_notice": "可於 {deadline} 前退出場次。",
        "leave_deadline_passed_title": "退出期限已過",
        "leave_deadline_passed_body": "球友已無法自行退出此場次；如需協助，請聯絡活動主辦者。",
        "leave_deadline_passed": "此場次的退出期限已過。",
        "username": "使用者名稱",
        "pin": "6 位數 PIN 碼",
        "join": "加入場次",
        "leave": "離開場次",
        "participants": "球友名單",
        "no_participants": "目前尚無線上報名。",
        "manage_participant": "管理球友",
        "rename_participant": "重新命名球友",
        "participant_new_name": "新的使用者名稱",
        "participant_renamed": "球友名稱已更新。",
        "reset_participant_pin": "重設 PIN 碼",
        "participant_pin_reset": "球友 PIN 碼已重設。",
        "remove_participant": "移除球友",
        "remove_participant_confirm": "確定要將此球友移出場次嗎？",
        "participant_removed": "球友已移出場次。",
        "participation_history": "加入與退出紀錄",
        "participation_history_eyebrow": "活動紀錄",
        "no_participation_history": "目前尚無加入或退出紀錄。",
        "history_action": "動作",
        "history_joined": "加入",
        "history_left": "退出",
        "date_and_time": "日期與時間",
        "device_information": "裝置類型",
        "device_ios": "iOS",
        "device_android": "Android",
        "device_mobile": "行動裝置",
        "device_web": "網頁",
        "waiting_list": "候補名單",
        "waiting": "人候補",
        "waitlisted": "候補",
        "no_waiting": "目前沒有人候補。",
        "level_guide": "程度說明",
        "level_guide_text": "1～3 新手階 · 4～5 初階 · 6～7 初中階 · 8～9 中階 · 10～12 中進階 · 13～15 高階 · 16～18 職業級",
        "grading_chart_alt": "台灣羽球一至十八級程度分級表",
        "grading_chart_caption": "台灣羽球推廣協會程度分級參考表",
        "show_grading_chart": "顯示程度分級表",
        "view_full_chart": "查看完整尺寸",
        "level_beginner": "新手階",
        "level_elementary": "初階",
        "level_preintermediate": "初中階",
        "level_intermediate": "中階",
        "level_upperintermediate": "中進階",
        "level_advanced": "高階",
        "level_professional": "職業級",
        "theme": "主題",
        "theme_system": "跟隨系統",
        "theme_light": "淺色",
        "theme_dark": "深色",
        "theme_mono": "黑白",
        "theme_green": "綠色與萊姆",
        "theme_purple": "紫色",
        "theme_yellow": "黃色",
        "language": "語言",
        "preferences": "偏好設定",
        "sign_in": "登入",
        "sign_up": "註冊",
        "sign_out": "登出",
        "account": "帳號",
        "profile": "個人資料",
        "profile_title": "你的個人資料",
        "profile_body": "設定會員帳號的顯示方式。",
        "datetime_format": "日期與時間格式",
        "datetime_format_help": "設定登入後顯示時間所使用的格式。",
        "time_format_12h": "12 小時制（AM/PM）",
        "time_format_24h": "24 小時制",
        "profile_preferences_saved": "個人偏好設定已儲存。",
        "invalid_datetime_format": "請選擇有效的日期與時間格式。",
        "profile_picture": "個人照片",
        "upload_picture": "上傳照片",
        "replace_picture": "更換照片",
        "remove_picture": "移除照片",
        "avatar_help": "支援 JPEG、PNG 或 WebP，檔案上限為 2 MB。",
        "avatar_updated": "個人照片已更新。",
        "avatar_removed": "個人照片已移除。",
        "saved_locations": "已儲存地點",
        "saved_locations_body": "建立球場活動時可直接重複使用這些球館。",
        "no_saved_locations": "你尚未儲存任何地點。",
        "use_saved_location": "使用已儲存地點",
        "choose_saved_location": "選擇已儲存地點…",
        "save_this_location": "儲存此地點",
        "save_location_help": "將此球館與地址加入個人資料，供日後建立活動使用。",
        "saved_location_added": "此地點已儲存至你的個人資料。",
        "saved_location_deleted": "已刪除儲存的地點。",
        "delete_saved_location": "刪除儲存地點",
        "delete_saved_location_confirm": "確定要刪除此儲存地點嗎？",
        "invalid_avatar": "請選擇有效的 JPEG、PNG 或 WebP 圖片。",
        "avatar_too_large": "個人照片不可超過 2 MB。",
        "member_since": "加入日期",
        "last_login": "上次登入",
        "ip_address": "IP 位址",
        "never": "尚未登入",
        "admin_account": "管理員",
        "account_role": "帳號角色",
        "role_member": "會員",
        "role_sub_admin": "副管理員",
        "role_admin": "管理員",
        "role_super_admin": "最高管理員",
        "change_role": "變更角色",
        "role_updated": "帳號角色已更新。",
        "invalid_role": "請選擇有效的帳號角色。",
        "cannot_change_own_role": "你不能變更自己的管理員角色。",
        "cannot_manage_super_admin": "無法修改此最高管理員帳號。",
        "admin_account_delete_disabled": "管理員帳號必須由最高管理員管理。",
        "delete_account": "刪除帳號",
        "delete_account_title": "刪除你的帳號",
        "delete_account_warning": "此操作會永久移除個人資料與登入權限。已發布的場次仍會保留，並可由管理員繼續管理。",
        "delete_account_confirm": "確定要永久刪除你的帳號嗎？",
        "account_deleted": "你的帳號已刪除。",
        "my_courts": "我的場次",
        "my_courts_title": "你的球場活動",
        "my_courts_body": "建立並管理由你主辦的羽球場次。",
        "users": "會員",
        "user_management": "會員管理",
        "user_management_body": "管理會員存取權限與臨時密碼。",
        "member_login_title": "登入會員帳號",
        "member_login_body": "管理你的場次或建立新的活動。",
        "signup_title": "建立會員帳號",
        "signup_body": "開始主辦並分享自己的羽球場次。",
        "confirm_password": "確認密碼",
        "create_account": "建立帳號",
        "have_account": "已經有帳號？",
        "need_account": "第一次使用羽球場控面板？",
        "account_created": "你的帳號已建立。",
        "username_taken": "此使用者名稱已被使用。",
        "account_username_help": "請使用 3～40 個字元，不可包含空格。",
        "password_help": "密碼至少需要 8 個字元。",
        "password_too_short": "密碼至少需要 8 個字元。",
        "password_mismatch": "兩次輸入的密碼不一致。",
        "change_password": "變更密碼",
        "change_password_title": "變更你的密碼",
        "change_password_body": "輸入目前密碼，並設定新的密碼。",
        "current_password": "目前密碼",
        "new_password": "新密碼",
        "password_changed": "密碼已變更。",
        "temporary_password_required": "使用臨時密碼登入後，必須先變更密碼。",
        "temporary_password": "臨時密碼",
        "set_temporary_password": "設定臨時密碼",
        "temporary_password_set": "臨時密碼已設定，會員下次登入時必須變更密碼。",
        "account_archived": "此帳號已被封存。",
        "account_banned": "此帳號已被停權。",
        "account_archived_success": "會員帳號已封存。",
        "account_restored_success": "會員帳號已恢復。",
        "account_banned_success": "會員帳號已停權。",
        "account_unbanned_success": "會員帳號已解除停權。",
        "active_account": "使用中",
        "banned": "已停權",
        "ban_account": "停權帳號",
        "ban_account_confirm": "確定要停權此會員帳號嗎？會員將立即失去存取權限。",
        "unban_account": "解除停權",
        "archive_account": "封存帳號",
        "archive_account_confirm": "確定要封存此會員帳號嗎？",
        "restore_account": "恢復帳號",
        "delete_user_account": "刪除帳號",
        "delete_user_account_confirm": "確定要永久刪除此已封存帳號嗎？其發布的場次將保留，但不再有擁有者。",
        "user_account_deleted": "會員帳號已永久刪除。",
        "account_must_be_archived": "刪除帳號前必須先封存。",
        "must_change_password": "需要變更密碼",
        "reset_login_retries": "重設登入失敗次數",
        "reset_login_retries_confirm": "確定要重設此會員在所有 IP 位址的登入失敗次數嗎？",
        "login_retries_reset": "登入失敗次數已重設。",
        "no_users": "目前尚無會員帳號。",
        "password": "密碼",
        "dashboard": "控制台",
        "dashboard_title": "球場管理",
        "dashboard_body": "建立場次並維護公開場次資訊。",
        "roll_and_clearing": "點名與結清",
        "start_roll_and_clearing": "開始點名與結清",
        "roll_and_clearing_confirm": "確定要開始點名與結清嗎？場次資料及報名名單將改為唯讀。",
        "roll_and_clearing_started": "已開始點名與結清，此場次目前為唯讀。",
        "editing_mode_restored": "已恢復編輯模式，場次資料及報名功能已重新開放。",
        "roll_and_clearing_body": "記錄每位正式成員的點名及結清狀態。",
        "check_uncheck_all": "全部勾選／取消勾選",
        "all": "全部",
        "roll_call": "點名",
        "cleared": "結清",
        "save_member_statuses": "儲存成員狀態",
        "member_statuses_saved": "成員狀態已儲存。",
        "read_only": "唯讀",
        "court_read_only": "此場次目前為唯讀。",
        "court_read_only_body": "報名及成員異動已關閉。",
        "member_source": "來源",
        "unnamed_reserved_member": "預訂球友",
        "new_court": "新增場次",
        "event_information": "活動資訊",
        "event_name": "活動名稱",
        "event_name_placeholder": "例如：週五晚間羽球場",
        "badminton_name": "羽球團名稱",
        "badminton_name_placeholder": "俱樂部、球隊或羽球團名稱",
        "optional": "選填",
        "all_courts": "所有場次",
        "all_courts_body": "瀏覽所有開放中的羽球場次。",
        "creator": "活動建立者",
        "filter_courts": "篩選場次",
        "filter_search": "活動、羽球團、球館、地點、場地編號或建立者",
        "filter_date": "活動日期",
        "date_from": "開始日期",
        "date_to": "結束日期",
        "filter_level": "球員程度",
        "filter_gender": "程度性別",
        "both_genders": "男性與女性",
        "filter_status": "場次狀態",
        "show_expired": "顯示已過期場次",
        "any_level": "不限程度",
        "any_status": "不限狀態",
        "apply_filters": "套用篩選",
        "clear_filters": "清除",
        "filter_results": "筆結果",
        "homepage_settings": "首頁設定",
        "homepage_settings_body": "設定首頁最多顯示幾個即將開始的場次。",
        "homepage_court_limit": "首頁場次顯示上限",
        "homepage_court_limit_help": "請輸入 1 至 100。",
        "save_settings": "儲存設定",
        "settings_saved": "首頁設定已儲存。",
        "invalid_homepage_court_limit": "首頁場次顯示上限必須介於 1 至 100。",
        "expired": "已過期",
        "court_expired": "此場次已結束",
        "court_expired_body": "報名與參加者異動已關閉。",
        "status": "狀態",
        "actions": "操作",
        "archive": "封存",
        "restore": "重新開放",
        "edit": "編輯",
        "duplicate": "複製",
        "court_info": "場次資訊檔",
        "court_info_help": "匯入 court_info.md 以預先填入此表單。報名資料、PIN 碼、歷程、媒體檔案、擁有者與公開連結都不會被匯入。",
        "court_info_choose": "選擇 court_info.md",
        "court_info_no_file": "請選擇 Markdown 檔案（.md）",
        "court_info_import": "匯入 court_info.md",
        "court_info_export": "匯出",
        "export_all_courts_csv": "匯出所有場次（CSV）",
        "court_info_imported": "場次資訊已匯入。請檢查表單，儲存後才會建立場次。",
        "court_info_imported_review": "場次資訊已匯入，請先檢查標示的欄位再儲存。",
        "court_info_invalid": "請選擇由本網站匯出的有效 court_info.md 檔案。",
        "court_info_too_large": "court_info.md 不可超過 64 KB。",
        "delete": "刪除",
        "delete_confirm": "確定要永久刪除此場次及所有報名資料嗎？",
        "archive_confirm": "確定要封存此場次嗎？",
        "create_title": "建立新場次",
        "create_body": "設定日期、容量與男女程度範圍。",
        "edit_title": "編輯場次",
        "edit_body": "更新日期、容量或程度設定，公開連結將保持不變。",
        "start_time": "開始時間",
        "end_time": "結束時間",
        "time_hint": "24 小時制 · HH:MM",
        "hall_name": "球館名稱",
        "hall_search": "搜尋球館",
        "selected_hall": "已選球館",
        "hall_placeholder": "輸入羽球館名稱開始搜尋…",
        "hall_search_help": "選擇 Google 搜尋建議後，地址會自動帶入。",
        "hall_search_setup": "即時 Google 搜尋建議需要設定 GOOGLE_MAPS_API_KEY；仍可使用下方 Maps 搜尋連結。",
        "hall_search_error": "無法取得此地點資料，請選擇其他搜尋建議。",
        "hall_api_error": "Google Places 拒絕了搜尋請求。請確認已啟用計費、Maps JavaScript API、Places API (New)，並在 API 金鑰限制中允許此網站。目前已開放手動輸入。",
        "location_placeholder": "完整地址或 Google Maps 地點",
        "remark": "備註",
        "remark_placeholder": "填寫集合方式或其他注意事項…",
        "event_media": "活動相片與影片",
        "event_media_body": "向球友展示場館、球場或活動氣氛。",
        "media_upload": "新增相片或影片",
        "current_section": "目前區塊",
        "jump_to_section": "跳至區塊",
        "media_browse_files": "選擇檔案",
        "media_choose_multiple": "可一次選擇多個檔案",
        "media_files_selected": "已選擇 {count} 個檔案",
        "media_upload_help": "JPEG、PNG、WebP 圖片上限 8 MB；MP4、WebM 影片上限 50 MB。每個場次最多 12 個檔案。",
        "current_media": "目前的媒體",
        "remove_media": "儲存變更時移除",
        "media_invalid": "請選擇有效的 JPEG、PNG、WebP、MP4 或 WebM 檔案。",
        "media_too_large": "圖片不可超過 8 MB，影片不可超過 50 MB。",
        "media_too_many": "每個場次最多可有 12 個相片與影片。",
        "event_gallery": "活動相簿",
        "court_media_alt": "{hall} 的活動相片",
        "search_maps": "在 Google Maps 搜尋",
        "member_min": "最少人數",
        "member_max": "最多人數",
        "ordered_count": "已預訂人數",
        "ordered_help": "已透過本網站以外方式確認的人數。",
        "reserved_nicknames": "預訂球友暱稱",
        "reserved_nicknames_help": "可為每個已預訂名額記錄一個暱稱，並可拖曳或使用箭頭按鈕調整順序。",
        "reserved_nickname": "預訂球友暱稱",
        "reserved_nickname_placeholder": "暱稱（選填）",
        "drag_to_reorder": "拖曳調整順序",
        "move_up": "向上移動",
        "move_down": "向下移動",
        "reserved_players": "預訂球友",
        "reserved_name_visibility": "暱稱顯示設定",
        "show_reserved_names": "在公開頁面顯示",
        "hide_reserved_names": "不在公開頁面顯示",
        "hidden_from_viewers": "已對訪客隱藏",
        "nickname_too_long": "每個暱稱最多 40 個字元。",
        "male_min": "男性最低程度",
        "male_max": "男性最高程度",
        "female_min": "女性最低程度",
        "female_max": "女性最高程度",
        "create_court": "建立場次",
        "save_changes": "儲存變更",
        "cancel": "取消",
        "public_link": "公開連結",
        "created": "建立時間",
        "court_not_found": "找不到此場次",
        "court_not_found_body": "連結可能不正確，或此場次已被刪除。",
        "back_home": "返回場次列表",
        "footer": "建立場次、招募球友，輕鬆管理每一場球。",
        "licenses": "授權資訊",
        "license_title": "素材授權",
        "license_body": "Badminton Court Control Panel 使用之素材授權、來源標示與開發協助說明。",
        "shuttlecock_icon": "羽球網站圖示",
        "icon_attribution": "羽球圖示由 Flaticon 來源頁面所列之創作者設計，素材來自 Flaticon。",
        "icon_usage": "以 PNG 格式用作本網站的瀏覽器圖示。",
        "source_page": "素材來源",
        "flaticon_license": "Flaticon 授權",
        "flaticon_terms": "使用條款",
        "development_acknowledgment": "開發協助說明",
        "codex_support_title": "本網站由 OpenAI Codex 協助開發",
        "codex_support_body": "Badminton Court Control Panel 在功能實作、程式碼檢查與測試過程中，使用了 OpenAI 的程式設計代理 Codex 提供協助。",
        "codex_responsibility": "本網站之內容、營運與最終成果仍由專案擁有者負責；此說明不代表 OpenAI 對本網站提供背書或擁有權。",
        "codex_official_page": "Codex 官方頁面",
        "noto_font": "Noto Sans 繁體中文字型",
        "noto_font_attribution": "Noto Sans 繁體中文由 Noto 專案提供，並採用 SIL Open Font License 1.1 授權。",
        "noto_font_usage": "專案內附的可變字型用於在社群分享縮圖中繪製英文及繁體中文。",
        "font_license": "字型授權",
        "joined_success": "你已加入此場次。",
        "joined_waitlist_success": "場次已額滿，你已加入候補名單。",
        "left_success": "你已離開此場次。",
        "court_created": "場次已建立。",
        "court_updated": "場次已更新。",
        "court_duplicated": "場次資訊已複製，請儲存表單以建立新場次。",
        "court_archived": "場次已封存。",
        "court_restored": "場次已重新開放。",
        "court_deleted": "場次已刪除。",
        "invalid_login": "使用者名稱或密碼錯誤。",
        "login_attempts_remaining": "使用者名稱或密碼錯誤，還可嘗試 {count} 次。",
        "login_locked": "登入失敗次數過多，請在 {minutes} 分鐘後再試。",
        "leave_attempts_remaining": "使用者名稱或 PIN 碼不正確，還可嘗試 {count} 次。",
        "leave_locked": "退出場次失敗次數過多，請在 {minutes} 分鐘後再試。",
        "signed_out": "你已登出。",
        "invalid_csrf": "工作階段已過期，請再試一次。",
        "turnstile_required": "請完成 Cloudflare Turnstile 人機驗證後再試一次。",
        "invalid_username": "使用者名稱需為 2 至 40 個字元。",
        "invalid_pin": "PIN 碼必須正好為 6 位數字。",
        "duplicate_username": "此使用者名稱已加入該場次。",
        "invalid_credentials": "使用者名稱或 PIN 碼不正確。",
        "court_closed": "此場次目前不接受報名。",
        "court_full": "此場次已額滿。",
        "invalid_form": "請檢查標示的場次資料。",
        "joined_on_site": "線上報名",
    },
}



SITE_UPDATE_HISTORY_PATH = (
    Path(__file__).with_name("data") / "update_history.json"
)


def load_site_update_history(
    path: Path = SITE_UPDATE_HISTORY_PATH,
) -> tuple[dict[str, Any], ...]:
    with path.open(encoding="utf-8") as history_file:
        history = json.load(history_file)
    if not isinstance(history, list) or not history:
        raise ValueError("Update history must be a non-empty JSON array.")

    required_fields = {"date", "date_label", "title", "summary", "items"}
    language_fields = {"en-us", "zh-tw"}
    previous_date = ""
    for index, entry in enumerate(history):
        if not isinstance(entry, dict) or set(entry) != required_fields:
            raise ValueError(
                f"Update history entry {index} has invalid fields."
            )
        date_value = entry["date"]
        if not isinstance(date_value, str) or not re.fullmatch(
            r"\d{4}-\d{2}(?:-\d{2})?", date_value
        ):
            raise ValueError(
                f"Update history entry {index} has an invalid date."
            )
        try:
            datetime.strptime(
                date_value,
                "%Y-%m-%d" if len(date_value) == 10 else "%Y-%m",
            )
        except ValueError as error:
            raise ValueError(
                f"Update history entry {index} has an invalid date."
            ) from error
        if previous_date and date_value > previous_date:
            raise ValueError("Update history must be newest first.")
        previous_date = date_value

        for field_name in ("date_label", "title", "summary"):
            localized = entry[field_name]
            if (
                not isinstance(localized, dict)
                or set(localized) != language_fields
                or not all(
                    isinstance(value, str) and value.strip()
                    for value in localized.values()
                )
            ):
                raise ValueError(
                    f"Update history entry {index} has invalid "
                    f"{field_name} translations."
                )
        localized_items = entry["items"]
        if (
            not isinstance(localized_items, dict)
            or set(localized_items) != language_fields
            or not all(
                isinstance(items, list)
                and items
                and all(
                    isinstance(item, str) and item.strip()
                    for item in items
                )
                for items in localized_items.values()
            )
        ):
            raise ValueError(
                f"Update history entry {index} has invalid item translations."
            )
    return tuple(history)


SITE_UPDATE_HISTORY = load_site_update_history()


PRIVACY_POLICY_SECTIONS = {
    "en-us": (
        {
            "id": "scope",
            "title": "Scope and responsibility",
            "paragraphs": (
                "This policy applies to this deployment of Badminton Court Control Panel and its built-in website features.",
                "The person or organization operating this deployment determines why and how information is processed. Because the software is self-hosted, hosting providers, reverse proxies, backups, custom changes, and operational practices may add processing that is not visible to the application.",
            ),
        },
        {
            "id": "information",
            "title": "Information the application handles",
            "paragraphs": (
                "The application handles only the information needed to run accounts, publish court events, accept registrations, protect access, and deliver optional notifications.",
            ),
            "items": (
                "Requests and security: validated IP address, request time, country signals supplied by supported proxies or an optional local GeoIP database, failed-attempt counters, lockout times, and derived attempt identifiers. A User-Agent is reduced to iOS, Android, Mobile, or Web for successful join/leave history; the complete User-Agent and device fingerprints are not stored by the application.",
                "Accounts: username, password hash, role and account status, creation time, optional avatar, saved hall locations, last successful sign-in time, and last successful sign-in IP address. Plain-text account passwords are not stored.",
                "Court events: organizer identity, event and group names, date and time, venue and coordinates, court ID, capacity, reserved-player nicknames, levels, prices, shuttlecock information, remarks, status, roll-call/clearing state, and uploaded photos or videos.",
                "Public registration: nickname, participant PIN hash, confirmed or waiting status, join time, roll-call/clearing state, and successful join/leave history. History contains nickname, action, time, validated IP address, and broad device category. Plain-text participant PINs are not stored.",
                "Push notifications: the selected court, browser push-service endpoint, encryption keys, language, and creation/update times after a visitor explicitly opts in. In the Android app, the device's Firebase Cloud Messaging registration token is stored instead of a browser endpoint.",
                "Contact messages: the name supplied by the visitor, optional reply contact, subject, message, interface language, submission time, and administrator read status.",
            ),
        },
        {
            "id": "visibility",
            "title": "What is public and what administrators can see",
            "paragraphs": (
                "Court links are public. Event details, organizer name, uploaded event media, confirmed and waiting nicknames, and join/leave nicknames with timestamps can be viewed without signing in.",
                "Reserved-player nicknames are public only when the organizer enables that setting. Administrators can see join/leave IP addresses and broad device categories, account sign-in information, and other controls needed to operate the service. Organizers and administrators can manage event and participant records within their permissions.",
                "Administrator CSV exports contain event configuration, public URLs, creator and lifecycle information, counts, reserved nicknames, and media counts. They exclude active participant names, participant PINs, join/leave history, IP addresses, and device information.",
                "Contact messages and optional reply details are visible only to administrator and super-administrator accounts through the protected message inbox.",
            ),
        },
        {
            "id": "purposes",
            "title": "Why information is used",
            "items": (
                "Create and authenticate accounts, enforce roles, and manage profiles.",
                "Publish, discover, share, duplicate, archive, and administer court events.",
                "Process registration, waiting-list promotion, leaving, roll call, and payment-clearing status.",
                "Prevent repeated credential guessing, investigate operational problems, and protect the service.",
                "Deliver court-specific notifications requested by the browser user.",
                "Receive and respond to support requests, track whether administrators have reviewed them, and optionally alert administrators to new messages.",
                "Select a language, generate social-sharing previews, and maintain the visitor’s chosen interface preferences.",
            ),
        },
        {
            "id": "browser-storage",
            "title": "Cookies and browser storage",
            "items": (
                "A signed session cookie supports sign-in state, role checks, and CSRF protection. Production operators should transmit it only over HTTPS.",
                "The court_lang cookie remembers the selected interface language for up to one year.",
                "Local storage remembers theme and palette choices and whether the first-visit introduction prompt has been handled.",
                "When notifications are enabled, the browser and its push service retain a push subscription. Turning notifications off removes this court’s server-side mapping.",
                "The built-in application does not include advertising or analytics trackers. A deployment operator may add services outside the application and must disclose them separately.",
            ),
        },
        {
            "id": "services",
            "title": "External services",
            "paragraphs": (
                "Some features contact other providers, which process technical information under their own terms and privacy policies.",
            ),
            "items": (
                "Google Fonts is requested by website pages. Google Maps links are available for venue searches, and Google Maps JavaScript/Places loads on the event form when the operator configures an API key.",
                "Cloudflare Turnstile loads on signup, sign-in, and contact-message forms and receives verification information when both Turnstile keys are configured.",
                "Opt-in Web Push sends encrypted notification payloads through the push service selected by the visitor’s browser, such as Apple, Google, Microsoft, or Mozilla. The Android app receives notifications through Google Firebase Cloud Messaging.",
                "Each contact message is reported to the operator’s Telegram bot chat when one is configured, and also to a Discord webhook when an administrator enables it. The report contains the submitted name, reply contact, subject, message, time, language, inbox link, the signed-in username if any, and where it was sent from (website with a broad device type, or the Android app with its version, Android version, and device model). A failed delivery does not remove the message from this website’s database.",
                "When a court link is shared, the chosen social or messaging platform may request its public metadata and generated preview image.",
                "Following any external link sends the request directly to that external website.",
            ),
        },
        {
            "id": "retention",
            "title": "Retention and deletion",
            "items": (
                "Account data remains until the account is deleted or an administrator deletes an eligible archived account. Member self-deletion removes the account, avatar, and saved locations, but already-published courts and their displayed creator label remain online without an owner.",
                "Leaving a court removes the active participant record. Successful join/leave history remains until the court itself is deleted.",
                "Archiving or expiration does not delete a court. Deleting a court removes its participants, reserved members, media records and files, participation history, push mappings, and generated social-preview cache.",
                "Turning off push notifications removes the matching court subscription mapping. Endpoints and app tokens rejected as expired by a push service are removed automatically.",
                "Successful authentication clears the matching failed-attempt record; administrators can reset member sign-in retries. Other security records remain as needed to enforce current lockouts.",
                "Contact messages remain in the deployment database until the operator removes them according to its support and retention practices or handles an applicable deletion request.",
                "Hosting logs and backups are controlled by the deployment operator and may follow different retention and deletion schedules.",
            ),
        },
        {
            "id": "security",
            "title": "Security",
            "paragraphs": (
                "The application uses password hashing, role and ownership checks, CSRF protection, optional Turnstile verification, upload validation, randomized stored filenames, rate limits, and scoped access to reduce risk. Sensitive push endpoints, Discord webhook URLs, and Telegram bot tokens are not displayed publicly or written to application logs.",
                "No system is completely secure. The deployment operator is responsible for HTTPS, strong secrets, access controls, updates, backups, proxy configuration, and incident response.",
            ),
        },
        {
            "id": "choices",
            "title": "Your choices and requests",
            "items": (
                "Members can change their password and avatar, delete saved locations, and permanently delete an eligible member account after password confirmation.",
                "Organizers can correct or delete courts they own. Public participants can leave an editable court using their nickname and PIN.",
                "Visitors can decline or disable push notifications, change language and appearance preferences, and clear this site’s cookies or local storage in their browser.",
                "A contact message requires a name, subject, and message. Reply contact is optional, but administrators may be unable to respond without it. Visitors may use a separately published contact method instead of the stored form.",
                "Required information is necessary for the related feature: without account credentials a person cannot create or sign in to an account; without a nickname and PIN a person cannot join or leave a court. Optional profile, venue-saving, media, reserved-nickname, reply-contact, and notification features may be left unused.",
                "Contact the deployment operator to request access, correction, deletion, restriction, or other rights available under applicable law. Some information may need to remain for security, record integrity, legal obligations, or because published court data is no longer attached to a deleted member account.",
            ),
        },
        {
            "id": "changes",
            "title": "Changes and contact",
            "paragraphs": (
                "This policy may be updated when the application or deployment practices change. The latest revision date appears at the top of this page.",
                "Questions and privacy requests should be sent to the operator of this deployment using the contact method shown below.",
            ),
        },
    ),
    "zh-tw": (
        {
            "id": "scope",
            "title": "適用範圍與責任",
            "paragraphs": (
                "本政策適用於此一羽球場控面板部署網站及其內建的網站功能。",
                "此部署網站的營運者決定處理資訊的目的與方式。由於本軟體可自行架設，主機供應商、反向代理、備份、自訂修改及營運方式可能產生應用程式本身無法得知的額外處理。",
            ),
        },
        {
            "id": "information",
            "title": "應用程式處理的資訊",
            "paragraphs": (
                "應用程式僅處理建立帳號、發布場次、接受報名、保護存取及傳送選用通知所需的資訊。",
            ),
            "items": (
                "請求與安全性：已驗證的 IP 位址、請求時間、支援的代理服務所提供或選用本機 GeoIP 資料庫判斷的國家訊號、失敗次數、鎖定時間及衍生的嘗試識別值。成功加入／退出時，User-Agent 只會轉換為 iOS、Android、行動裝置或網頁；應用程式不保存完整 User-Agent 或裝置指紋。",
                "帳號：使用者名稱、密碼雜湊、角色與帳號狀態、建立時間、選用頭像、已儲存球館地點，以及最近成功登入時間與 IP 位址。系統不儲存帳號明文密碼。",
                "場次活動：主辦者身分、活動與羽球團名稱、日期與時間、場館與座標、場地編號、名額、預訂球友暱稱、程度、費用、用球、備註、狀態、點名／結清狀態，以及上傳的相片或影片。",
                "公開報名：暱稱、參加者 PIN 雜湊、正取或候補狀態、加入時間、點名／結清狀態，以及成功加入／退出歷程。歷程包含暱稱、動作、時間、已驗證 IP 位址與概略裝置類型。系統不儲存參加者明文 PIN。",
                "推播通知：訪客明確同意後，儲存所選場次、瀏覽器推播服務端點、加密金鑰、語言及建立／更新時間。Android App 則以裝置的 Firebase 雲端通訊（FCM）註冊權杖取代瀏覽器端點。",
                "聯絡留言：訪客填寫的名稱、選填回覆聯絡方式、主旨、留言內容、介面語言、送出時間及管理員已讀狀態。",
            ),
        },
        {
            "id": "visibility",
            "title": "公開資訊與管理員可見資訊",
            "paragraphs": (
                "場次連結是公開的；未登入的訪客也能查看活動內容、主辦者名稱、活動媒體、正取與候補暱稱，以及包含暱稱與時間的加入／退出紀錄。",
                "預訂球友暱稱只會在主辦者開啟該設定時公開。管理員可查看加入／退出 IP 位址與概略裝置類型、帳號登入資訊，以及營運服務所需的其他控制項。主辦者與管理員可依權限管理活動與參加者紀錄。",
                "管理員 CSV 匯出包含活動設定、公開網址、建立者與生命週期資訊、人數、預訂球友暱稱及媒體數量；不包含現有參加者暱稱、參加者 PIN、加入／退出歷程、IP 位址或裝置資訊。",
                "聯絡留言及選填回覆資訊只會透過受保護的留言收件匣提供管理員與最高管理員查看。",
            ),
        },
        {
            "id": "purposes",
            "title": "資訊使用目的",
            "items": (
                "建立與驗證帳號、執行角色權限及管理個人資料。",
                "發布、搜尋、分享、複製、封存及管理場次活動。",
                "處理報名、候補遞補、退出、點名及費用結清狀態。",
                "防止重複猜測憑證、調查營運問題並保護服務。",
                "傳送瀏覽器使用者自行要求的個別場次通知。",
                "接收與回覆支援請求、記錄管理員是否已查看，並選擇性通知管理員有新留言。",
                "選擇語言、產生社群分享預覽，並維持訪客選擇的介面偏好。",
            ),
        },
        {
            "id": "browser-storage",
            "title": "Cookie 與瀏覽器儲存空間",
            "items": (
                "經簽章的工作階段 Cookie 用於登入狀態、角色檢查及 CSRF 防護；正式環境營運者應只透過 HTTPS 傳送。",
                "court_lang Cookie 會記住介面語言選擇，最長一年。",
                "本機儲存空間會記住主題、配色，以及是否已處理初次造訪的網站介紹提示。",
                "開啟通知後，瀏覽器及其推播服務會保留推播訂閱；關閉通知會移除此場次在伺服器端的對應關係。",
                "應用程式內建功能不含廣告或分析追蹤器；部署網站營運者若另外加入服務，必須另行揭露。",
            ),
        },
        {
            "id": "services",
            "title": "外部服務",
            "paragraphs": (
                "部分功能會連線至其他供應商；供應商會依其條款與隱私權政策處理技術資訊。",
            ),
            "items": (
                "網站頁面會向 Google Fonts 取得字型。場館搜尋提供 Google Maps 連結；營運者設定 API 金鑰後，活動表單會載入 Google Maps JavaScript／Places。",
                "同時設定兩個 Turnstile 金鑰後，註冊、登入及聯絡留言表單會載入 Cloudflare Turnstile，並傳送驗證資訊。",
                "選用 Web Push 會透過訪客瀏覽器指定的推播服務（例如 Apple、Google、Microsoft 或 Mozilla）傳送加密通知內容。Android App 則透過 Google Firebase 雲端通訊（FCM）接收通知。",
                "設定 Telegram Bot 聊天室後，每則聯絡留言都會回報至該聊天室；管理員啟用後，也會另外傳送至設定的 Discord Webhook。回報內容包含填寫的名稱、回覆聯絡方式、主旨、留言、時間、語言、收件匣連結、已登入的使用者名稱（若有），以及送出來源（網站與概略裝置類型，或 Android App 的版本、Android 版本與裝置型號）；外部傳送失敗不會移除網站資料庫中的留言。",
                "分享場次連結時，所選社群或通訊平台可能讀取公開中繼資料及產生的預覽圖片。",
                "開啟任何外部連結時，請求會直接傳送至該外部網站。",
            ),
        },
        {
            "id": "retention",
            "title": "保留與刪除",
            "items": (
                "帳號資料會保留至帳號被刪除，或管理員刪除符合條件的已封存帳號。會員自行刪除帳號會移除帳號、頭像及已儲存地點；已發布的場次及其顯示的建立者標示會保留，但不再有擁有者。",
                "退出場次會移除目前的參加者紀錄；成功加入／退出歷程會保留至該場次被刪除。",
                "封存或過期不等於刪除。刪除場次會移除參加者、預訂球友、媒體紀錄與檔案、參與歷程、推播對應關係及產生的社群預覽快取。",
                "關閉推播會移除相符的場次訂閱對應；推播服務判定已失效的端點與 App 權杖也會自動移除。",
                "成功驗證會清除相符的失敗嘗試紀錄；管理員也可重設會員登入重試。其他安全紀錄會在執行目前鎖定所需期間保留。",
                "聯絡留言會保留在此部署網站的資料庫中，直到營運者依支援與保留方式移除，或處理適用的刪除請求。",
                "主機紀錄與備份由部署網站營運者控制，可能採用不同的保留及刪除時程。",
            ),
        },
        {
            "id": "security",
            "title": "資訊安全",
            "paragraphs": (
                "應用程式使用密碼雜湊、角色與擁有權檢查、CSRF 防護、選用 Turnstile 驗證、上傳驗證、隨機儲存檔名、頻率限制及範圍化存取來降低風險。敏感的推播端點、Discord Webhook 網址及 Telegram Bot Token 不會公開顯示或寫入應用程式紀錄。",
                "沒有任何系統能保證絕對安全。部署網站營運者必須負責 HTTPS、高強度密鑰、存取控制、更新、備份、代理設定及事件應變。",
            ),
        },
        {
            "id": "choices",
            "title": "您的選擇與請求",
            "items": (
                "會員可變更密碼與頭像、刪除已儲存地點，並在確認密碼後永久刪除符合條件的會員帳號。",
                "主辦者可修正或刪除自己擁有的場次；公開參加者可使用暱稱與 PIN 退出仍可編輯的場次。",
                "訪客可拒絕或關閉推播、更改語言與外觀偏好，並在瀏覽器中清除此網站的 Cookie 或本機儲存資料。",
                "聯絡留言必須填寫名稱、主旨與留言內容；回覆聯絡方式為選填，但未提供時管理員可能無法回覆。訪客也可改用另外公布的聯絡方式，不使用儲存式表單。",
                "相關功能必須提供必要資訊：未提供帳號憑證便無法建立帳號或登入；未提供暱稱與 PIN 便無法加入或退出場次。個人資料選填項目、儲存場館、媒體、預訂暱稱、回覆聯絡方式及通知功能都可選擇不使用。",
                "如需行使適用法律提供的查詢、存取、更正、刪除、限制或其他權利，請聯絡部署網站營運者。基於安全、紀錄完整性、法律義務，或已發布場次不再附屬於已刪除會員帳號等原因，部分資訊可能需要保留。",
            ),
        },
        {
            "id": "changes",
            "title": "政策變更與聯絡",
            "paragraphs": (
                "應用程式或部署網站的處理方式變更時，本政策可能隨之更新；最新修訂日期會顯示於本頁頂端。",
                "如有問題或隱私權請求，請透過下方聯絡方式洽詢此部署網站的營運者。",
            ),
        },
    ),
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    username_key TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    avatar_filename TEXT NOT NULL DEFAULT '',
    time_format TEXT NOT NULL DEFAULT '24h' CHECK(time_format IN ('12h', '24h')),
    last_login_at TEXT,
    last_login_ip TEXT,
    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
    banned INTEGER NOT NULL DEFAULT 0 CHECK(banned IN (0, 1)),
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK(must_change_password IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL UNIQUE,
    event_name TEXT NOT NULL DEFAULT '',
    badminton_name TEXT NOT NULL DEFAULT '',
    court_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    hall_name TEXT NOT NULL,
    location TEXT NOT NULL,
    google_place_id TEXT NOT NULL DEFAULT '',
    latitude REAL,
    longitude REAL,
    owner_id INTEGER,
    creator_name TEXT NOT NULL DEFAULT '',
    remark TEXT NOT NULL DEFAULT '',
    court_id TEXT NOT NULL,
    male_price INTEGER NOT NULL DEFAULT 0 CHECK(male_price >= 0),
    female_price INTEGER NOT NULL DEFAULT 0 CHECK(female_price >= 0),
    shuttlecock_info TEXT NOT NULL DEFAULT '',
    reserved_names_visible INTEGER NOT NULL DEFAULT 1 CHECK(reserved_names_visible IN (0, 1)),
    member_min INTEGER NOT NULL CHECK(member_min >= 1),
    member_max INTEGER NOT NULL CHECK(member_max >= member_min),
    ordered_count INTEGER NOT NULL DEFAULT 0 CHECK(ordered_count >= 0),
    male_level_min INTEGER NOT NULL CHECK(male_level_min BETWEEN 1 AND 18),
    male_level_max INTEGER NOT NULL CHECK(male_level_max BETWEEN 1 AND 18),
    female_level_min INTEGER NOT NULL CHECK(female_level_min BETWEEN 1 AND 18),
    female_level_max INTEGER NOT NULL CHECK(female_level_max BETWEEN 1 AND 18),
    leave_deadline_enabled INTEGER NOT NULL DEFAULT 0 CHECK(leave_deadline_enabled IN (0, 1)),
    leave_deadline_at TEXT NOT NULL DEFAULT '',
    roll_clearing_locked INTEGER NOT NULL DEFAULT 0 CHECK(roll_clearing_locked IN (0, 1)),
    owner_notifications INTEGER NOT NULL DEFAULT 1 CHECK(owner_notifications IN (0, 1)),
    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS saved_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    hall_name TEXT NOT NULL,
    location TEXT NOT NULL,
    google_place_id TEXT NOT NULL DEFAULT '',
    latitude REAL,
    longitude REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, hall_name, location)
);

CREATE INDEX IF NOT EXISTS saved_locations_user_idx
ON saved_locations(user_id, hall_name, location);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    username_key TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    waitlisted INTEGER NOT NULL DEFAULT 0 CHECK(waitlisted IN (0, 1)),
    roll_called INTEGER NOT NULL DEFAULT 0 CHECK(roll_called IN (0, 1)),
    cleared INTEGER NOT NULL DEFAULT 0 CHECK(cleared IN (0, 1)),
    joined_at TEXT NOT NULL,
    FOREIGN KEY (court_id) REFERENCES courts(id) ON DELETE CASCADE,
    UNIQUE(court_id, username_key)
);

CREATE TABLE IF NOT EXISTS participation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('join', 'leave')),
    occurred_at TEXT NOT NULL,
    ip_address TEXT NOT NULL DEFAULT '',
    device_information TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (court_id) REFERENCES courts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS participation_history_court_time_idx
ON participation_history(court_id, occurred_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS reserved_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0),
    nickname TEXT NOT NULL,
    roll_called INTEGER NOT NULL DEFAULT 0 CHECK(roll_called IN (0, 1)),
    cleared INTEGER NOT NULL DEFAULT 0 CHECK(cleared IN (0, 1)),
    FOREIGN KEY (court_id) REFERENCES courts(id) ON DELETE CASCADE,
    UNIQUE(court_id, position)
);

CREATE TABLE IF NOT EXISTS court_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL CHECK(media_type IN ('image', 'video')),
    mime_type TEXT NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (court_id) REFERENCES courts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS court_media_court_position_idx
ON court_media(court_id, position);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL,
    endpoint TEXT NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en-us',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (court_id) REFERENCES courts(id) ON DELETE CASCADE,
    UNIQUE(court_id, endpoint)
);

CREATE INDEX IF NOT EXISTS push_subscriptions_court_idx
ON push_subscriptions(court_id);

CREATE TABLE IF NOT EXISTS fcm_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL,
    token TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en-us',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (court_id) REFERENCES courts(id) ON DELETE CASCADE,
    UNIQUE(court_id, token)
);

CREATE INDEX IF NOT EXISTS fcm_subscriptions_token_idx
ON fcm_subscriptions(token);

CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_key TEXT PRIMARY KEY,
    scope TEXT NOT NULL DEFAULT '',
    username_key TEXT NOT NULL DEFAULT '',
    failed_count INTEGER NOT NULL DEFAULT 0 CHECK(failed_count >= 0),
    locked_until TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_name TEXT NOT NULL,
    reply_contact TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en-us'
        CHECK(language IN ('en-us', 'zh-tw')),
    submitted_at TEXT NOT NULL,
    read_at TEXT
);

CREATE INDEX IF NOT EXISTS contact_messages_status_time_idx
ON contact_messages(read_at, submitted_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS api_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    expires_at TEXT NOT NULL,
    fcm_token TEXT,
    fcm_language TEXT NOT NULL DEFAULT 'en-us'
);

CREATE INDEX IF NOT EXISTS api_tokens_user_idx ON api_tokens(user_id);
"""


class CourtActionError(Exception):
    """A user-facing failure shared by the HTML views and the JSON API.

    ``code`` is a TRANSLATIONS key (or a stable API error code); ``message``
    overrides the translated text when it needs runtime values.
    """

    def __init__(
        self,
        code: str,
        status: int = 400,
        message: str | None = None,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.custom_message = message
        self.fields = fields or {}

    @property
    def message(self) -> str:
        if self.custom_message:
            return self.custom_message
        return TRANSLATIONS[current_language()].get(self.code, self.code)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get(
            "COURT_DATABASE", str(Path(app.instance_path) / "courts.sqlite")
        ),
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "change-me"),
        TURNSTILE_SITE_KEY=os.environ.get("TURNSTILE_SITE_KEY", ""),
        TURNSTILE_SECRET_KEY=os.environ.get("TURNSTILE_SECRET_KEY", ""),
        TURNSTILE_VERIFY_TIMEOUT=float(
            os.environ.get("TURNSTILE_VERIFY_TIMEOUT", "5")
        ),
        GOOGLE_MAPS_API_KEY=os.environ.get("GOOGLE_MAPS_API_KEY", ""),
        WEB_PUSH_PUBLIC_KEY=os.environ.get("WEB_PUSH_PUBLIC_KEY", ""),
        WEB_PUSH_PRIVATE_KEY=os.environ.get("WEB_PUSH_PRIVATE_KEY", ""),
        WEB_PUSH_SUBJECT=os.environ.get("WEB_PUSH_SUBJECT", ""),
        WEB_PUSH_TIMEOUT=float(os.environ.get("WEB_PUSH_TIMEOUT", "5")),
        FCM_SERVICE_ACCOUNT_FILE=os.environ.get("FCM_SERVICE_ACCOUNT_FILE", ""),
        FCM_TIMEOUT=float(os.environ.get("FCM_TIMEOUT", "5")),
        AVATAR_FOLDER=str(Path(app.instance_path) / "avatars"),
        COURT_MEDIA_FOLDER=str(Path(app.instance_path) / "court_media"),
        SOCIAL_THUMBNAIL_FOLDER=str(
            Path(app.instance_path) / "social_thumbnails"
        ),
        SOCIAL_THUMBNAIL_FFMPEG=os.environ.get(
            "SOCIAL_THUMBNAIL_FFMPEG", ""
        ),
        SOCIAL_THUMBNAIL_FONT=os.environ.get("SOCIAL_THUMBNAIL_FONT", ""),
        GEOIP_COUNTRY_DB=os.environ.get("GEOIP_COUNTRY_DB", ""),
        DEFAULT_COUNTRY_CODE=os.environ.get("DEFAULT_COUNTRY_CODE", "").upper(),
        PRIVACY_OPERATOR_NAME=os.environ.get("PRIVACY_OPERATOR_NAME", ""),
        PRIVACY_DATA_REGION=os.environ.get("PRIVACY_DATA_REGION", ""),
        PRIVACY_CONTACT=os.environ.get("PRIVACY_CONTACT", ""),
        ADMIN_CONTACT=os.environ.get("ADMIN_CONTACT", ""),
        ADMIN_CONTACT_DISCORD=os.environ.get("ADMIN_CONTACT_DISCORD", ""),
        ADMIN_CONTACT_LINE=os.environ.get("ADMIN_CONTACT_LINE", ""),
        ADMIN_CONTACT_TELEGRAM=os.environ.get("ADMIN_CONTACT_TELEGRAM", ""),
        CONTACT_DISCORD_WEBHOOK_URL=os.environ.get(
            "CONTACT_DISCORD_WEBHOOK_URL", ""
        ),
        CONTACT_TELEGRAM_BOT_TOKEN=os.environ.get(
            "CONTACT_TELEGRAM_BOT_TOKEN", ""
        ),
        CONTACT_TELEGRAM_CHAT_ID=os.environ.get(
            "CONTACT_TELEGRAM_CHAT_ID", ""
        ),
        CONTACT_NOTIFICATION_TIMEOUT=float(
            os.environ.get("CONTACT_NOTIFICATION_TIMEOUT", "5")
        ),
        ANDROID_APP_URL=os.environ.get("ANDROID_APP_URL", ""),
        TRUST_PROXY_HEADERS=os.environ.get("TRUST_PROXY_HEADERS", "0") == "1",
        LOGIN_MAX_ATTEMPTS=int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5")),
        LOGIN_LOCKOUT_SECONDS=int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "900")),
        LEAVE_MAX_ATTEMPTS=int(os.environ.get("LEAVE_MAX_ATTEMPTS", "5")),
        LEAVE_LOCKOUT_SECONDS=int(os.environ.get("LEAVE_LOCKOUT_SECONDS", "900")),
        API_TOKEN_TTL_DAYS=int(os.environ.get("API_TOKEN_TTL_DAYS", "90")),
        # Defaults to the newest update-history date so every deployment
        # reports something meaningful without extra configuration.
        APP_VERSION=os.environ.get("APP_VERSION", "").strip()
        or SITE_UPDATE_HISTORY[0]["date"],
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["AVATAR_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["COURT_MEDIA_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["SOCIAL_THUMBNAIL_FOLDER"]).mkdir(
        parents=True, exist_ok=True
    )
    app.extensions["geoip_country_reader"] = None
    if app.config["GEOIP_COUNTRY_DB"]:
        try:
            import geoip2.database

            app.extensions["geoip_country_reader"] = geoip2.database.Reader(
                app.config["GEOIP_COUNTRY_DB"]
            )
        except (OSError, ValueError) as error:
            app.logger.warning("Unable to open GeoIP country database: %s", error)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    from api import create_api_blueprint

    app.register_blueprint(create_api_blueprint(sys.modules[__name__]))

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        lang = current_language()
        member = current_member()
        g.time_format = (
            member["time_format"]
            if member is not None and member["time_format"] in TIME_FORMATS
            else "24h"
        )
        turnstile_is_enabled = turnstile_enabled()
        return {
            "lang": lang,
            "t": lambda key: TRANSLATIONS[lang].get(key, key),
            "csrf_token": csrf_token,
            "level_label": lambda number: level_label(number, lang),
            "court_info_export_filename": court_info_export_filename,
            "google_maps_api_key": app.config["GOOGLE_MAPS_API_KEY"],
            "web_push_enabled": web_push_enabled(),
            "web_push_public_key": app.config["WEB_PUSH_PUBLIC_KEY"],
            "is_admin": bool(member and member["role"] in ADMIN_ROLES),
            "current_user": member,
            "turnstile_enabled": turnstile_is_enabled,
            "turnstile_site_key": (
                app.config["TURNSTILE_SITE_KEY"] if turnstile_is_enabled else ""
            ),
        }

    @app.template_filter("court_date")
    def court_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y/%m/%d")
        except (TypeError, ValueError):
            return value

    @app.template_filter("court_weekday")
    def court_weekday(value: str) -> str:
        try:
            weekday_index = datetime.strptime(value, "%Y-%m-%d").weekday()
        except (TypeError, ValueError):
            return ""
        keys = (
            "weekday_monday",
            "weekday_tuesday",
            "weekday_wednesday",
            "weekday_thursday",
            "weekday_friday",
            "weekday_saturday",
            "weekday_sunday",
        )
        return TRANSLATIONS[current_language()][keys[weekday_index]]

    @app.template_filter("audit_datetime")
    def audit_datetime(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return value
        return f"{parsed:%Y/%m/%d} {format_clock_time(parsed, True)}"

    @app.template_filter("profile_datetime")
    def profile_datetime(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return value
        return f"{parsed:%Y-%m-%d} {format_clock_time(parsed)}"

    @app.template_filter("court_time")
    def court_time(value: str) -> str:
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except (TypeError, ValueError):
            return value
        return format_clock_time(parsed)

    @app.get("/")
    def index():
        court_limit = get_int_setting("homepage_court_limit", 12, 1, 100)
        courts = get_db().execute(
            court_query()
            + f" WHERE c.archived = 0 AND NOT {COURT_EXPIRED_SQL} "
            "ORDER BY c.court_date, c.start_time LIMIT ?",
            (court_limit,),
        ).fetchall()
        return render_template("index.html", courts=courts)

    @app.get("/healthz")
    def healthz():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok"}

    @app.get("/licenses")
    def licenses():
        return render_template("licenses.html")

    @app.get("/privacy")
    def privacy():
        lang = current_language()
        contact_uri = validated_contact_uri(
            app.config["PRIVACY_CONTACT"]
        )
        contact_label = (
            contact_uri.removeprefix("mailto:") if contact_uri else ""
        )
        return render_template(
            "privacy.html",
            policy_sections=PRIVACY_POLICY_SECTIONS[lang],
            privacy_operator_name=validated_privacy_label(
                app.config["PRIVACY_OPERATOR_NAME"]
            ),
            privacy_data_region=validated_privacy_label(
                app.config["PRIVACY_DATA_REGION"]
            ),
            privacy_contact_uri=contact_uri,
            privacy_contact_label=contact_label,
        )

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if (
            request.method == "POST"
            and request.content_length is not None
            and request.content_length > 16_384
        ):
            abort(413)
        lang = current_language()
        member = current_member()
        form_values = {
            "sender_name": (
                request.form.get("sender_name", "").strip()
                if request.method == "POST"
                else (member["username"] if member else "")
            ),
            "reply_contact": request.form.get("reply_contact", "").strip(),
            "subject": request.form.get("subject", "").strip(),
            "message": request.form.get("message", "").strip(),
        }
        form_errors: dict[str, str] = {}
        if request.method == "POST":
            verify_csrf()
            form_errors = validate_contact_message(form_values)
            if not form_errors and not verify_turnstile_response(
                "contact_message"
            ):
                form_errors["turnstile"] = "turnstile_required"
            if not form_errors:
                store_contact_message(form_values, lang)
                flash_t("contact_message_sent", "success")
                return redirect(url_for("contact") + "#contact-form")
            flash_t("contact_form_invalid", "error")
        response = render_template(
            "contact.html",
            contact_operator_name=validated_privacy_label(
                app.config["PRIVACY_OPERATOR_NAME"]
            ),
            contact_method_groups=configured_admin_contact_method_groups(
                lang
            ),
            contact_form_values=form_values,
            contact_form_errors=form_errors,
        )
        return (response, 400) if form_errors else response

    @app.get("/introduction")
    def introduction():
        return render_template("introduction.html")

    @app.get("/android")
    def android_app():
        download_url = str(app.config.get("ANDROID_APP_URL") or "").strip()
        parsed = urlparse(download_url)
        if parsed.scheme != "https" or not parsed.netloc:
            download_url = ""
        return render_template(
            "android.html", android_download_url=download_url
        )

    @app.get("/updates")
    def updates():
        lang = current_language()
        update_entries = tuple(
            {
                "date": entry["date"],
                "date_label": entry["date_label"][lang],
                "title": entry["title"][lang],
                "summary": entry["summary"][lang],
                "items": entry["items"][lang],
            }
            for entry in SITE_UPDATE_HISTORY
        )
        return render_template(
            "updates.html", update_entries=update_entries
        )

    @app.get("/courts")
    def public_courts():
        clauses, parameters, filters = build_court_filters(request.args)
        courts = get_db().execute(
            court_query()
            + court_where_sql(clauses)
            + " ORDER BY is_expired, c.court_date, c.start_time",
            parameters,
        ).fetchall()
        return render_template("courts.html", courts=courts, filters=filters)

    @app.route("/signup", methods=["GET", "POST"])
    def account_signup():
        signed_in_user = current_member()
        if signed_in_user is not None:
            return redirect(
                url_for(
                    "admin_dashboard"
                    if signed_in_user["role"] in ADMIN_ROLES
                    else "account_dashboard"
                )
            )
        if request.method == "POST":
            verify_csrf()
            if not verify_turnstile_response("signup"):
                flash_t("turnstile_required", "error")
                return render_template("account/auth.html", signup=True)
            username = request.form.get("username", "").strip()
            try:
                user_id = register_member(
                    username,
                    request.form.get("password", ""),
                    request.form.get("confirm_password", ""),
                )
            except CourtActionError as error:
                flash_action_error(error)
            else:
                session.clear()
                session["user_id"] = user_id
                session["user_username"] = username
                session["csrf_token"] = secrets.token_urlsafe(32)
                flash_t("account_created", "success")
                return redirect(url_for("account_dashboard"))
        return render_template("account/auth.html", signup=True)

    @app.route("/login", methods=["GET", "POST"])
    def account_login():
        signed_in_user = current_member()
        if signed_in_user is not None and signed_in_user["role"] in ADMIN_ROLES:
            return redirect(url_for("admin_dashboard"))
        if signed_in_user is not None:
            return redirect(url_for("account_dashboard"))
        if request.method == "POST":
            verify_csrf()
            if not verify_turnstile_response("login"):
                flash_t("turnstile_required", "error")
                return render_template("account/auth.html", signup=False)
            try:
                user = authenticate_member(
                    request.form.get("username", ""),
                    request.form.get("password", ""),
                )
            except CourtActionError as error:
                flash_action_error(error)
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["user_username"] = user["username"]
                if user["role"] in ADMIN_ROLES:
                    session["admin"] = True
                session["csrf_token"] = secrets.token_urlsafe(32)
                if user["must_change_password"]:
                    flash_t("temporary_password_required", "error")
                    return redirect(url_for("account_change_password"))
                return redirect(
                    url_for(
                        "admin_dashboard"
                        if user["role"] in ADMIN_ROLES
                        else "account_dashboard"
                    )
                )
        return render_template("account/auth.html", signup=False)

    @app.post("/logout")
    @member_required
    def account_logout():
        verify_csrf()
        session.clear()
        flash_t("signed_out", "success")
        return redirect(url_for("index"))

    @app.route("/account/password", methods=["GET", "POST"])
    @member_required
    def account_change_password():
        member = current_member()
        if request.method == "POST":
            verify_csrf()
            try:
                change_member_password(
                    member["id"],
                    request.form.get("current_password", ""),
                    request.form.get("new_password", ""),
                    request.form.get("confirm_password", ""),
                )
            except CourtActionError as error:
                flash_action_error(error)
            else:
                flash_t("password_changed", "success")
                return redirect(
                    url_for(
                        "admin_dashboard"
                        if member["role"] in ADMIN_ROLES
                        else "account_dashboard"
                    )
                )
        return render_template("account/change_password.html")

    @app.route("/account/profile", methods=["GET", "POST"])
    @member_required
    def account_profile():
        member = current_member()
        if request.method == "POST":
            verify_csrf()
            try:
                save_member_avatar(member, request.files.get("avatar"))
            except CourtActionError as error:
                flash_action_error(error)
            else:
                flash_t("avatar_updated", "success")
            return redirect(url_for("account_profile"))
        return render_template(
            "account/profile.html",
            saved_locations=fetch_saved_locations(member["id"]),
        )

    @app.post("/account/profile/avatar/remove")
    @member_required
    def account_remove_avatar():
        verify_csrf()
        remove_member_avatar(current_member())
        flash_t("avatar_removed", "success")
        return redirect(url_for("account_profile"))

    @app.post("/account/profile/preferences")
    @member_required
    def account_update_profile_preferences():
        verify_csrf()
        time_format = request.form.get("time_format", "").strip().lower()
        if time_format not in TIME_FORMATS:
            flash_t("invalid_datetime_format", "error")
            return redirect(url_for("account_profile"))
        member = current_member()
        db = get_db()
        db.execute(
            "UPDATE users SET time_format = ? WHERE id = ?",
            (time_format, member["id"]),
        )
        db.commit()
        flash_t("profile_preferences_saved", "success")
        return redirect(url_for("account_profile"))

    @app.post("/account/profile/saved-locations/<int:location_id>/delete")
    @member_required
    def account_delete_saved_location(location_id: int):
        verify_csrf()
        member = current_member()
        db = get_db()
        result = db.execute(
            "DELETE FROM saved_locations WHERE id = ? AND user_id = ?",
            (location_id, member["id"]),
        )
        if result.rowcount == 0:
            abort(404)
        db.commit()
        flash_t("saved_location_deleted", "success")
        return redirect(url_for("account_profile"))

    @app.post("/account/delete")
    @member_required
    def account_delete():
        verify_csrf()
        try:
            delete_member_account(
                current_member(), request.form.get("current_password", "")
            )
        except CourtActionError as error:
            flash_action_error(error)
            return redirect(url_for("account_profile"))
        session.clear()
        flash_t("account_deleted", "success")
        return redirect(url_for("index"))

    @app.get("/avatars/<filename>")
    def avatar_file(filename: str):
        if not AVATAR_FILENAME_PATTERN.fullmatch(filename):
            abort(404)
        exists = get_db().execute(
            "SELECT 1 FROM users WHERE avatar_filename = ?", (filename,)
        ).fetchone()
        if exists is None:
            abort(404)
        return send_from_directory(
            app.config["AVATAR_FOLDER"], filename, max_age=86400
        )

    @app.get("/court-media/<filename>")
    def court_media_file(filename: str):
        if not COURT_MEDIA_FILENAME_PATTERN.fullmatch(filename):
            abort(404)
        exists = get_db().execute(
            "SELECT 1 FROM court_media WHERE filename = ?", (filename,)
        ).fetchone()
        if exists is None:
            abort(404)
        return send_from_directory(
            app.config["COURT_MEDIA_FOLDER"],
            filename,
            conditional=True,
            max_age=86400,
        )

    @app.get("/<guid>/social-thumbnail/<version>/<lang>.jpg")
    def court_social_thumbnail(guid: str, version: str, lang: str):
        if (
            not SOCIAL_THUMBNAIL_VERSION_PATTERN.fullmatch(version)
            or lang not in LANGUAGES
        ):
            abort(404)
        court = fetch_court(guid)
        if court is None:
            abort(404)
        first_media = fetch_first_court_media(court["id"])
        expected_version = court_social_thumbnail_version(court, first_media)
        if version != expected_version:
            return redirect(
                url_for(
                    "court_social_thumbnail",
                    guid=guid,
                    version=expected_version,
                    lang=lang,
                ),
                code=302,
            )

        thumbnail_folder, filename = cached_court_social_thumbnail(
            court, first_media, version, lang
        )

        response = send_from_directory(
            thumbnail_folder,
            filename,
            mimetype="image/jpeg",
            conditional=True,
            max_age=31536000,
        )
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/<guid>/thumbnail.jpg")
    def download_court_thumbnail(guid: str):
        court = fetch_court(guid)
        if court is None:
            abort(404)
        first_media = fetch_first_court_media(court["id"])
        version = court_social_thumbnail_version(court, first_media)
        thumbnail_folder, filename = cached_court_social_thumbnail(
            court, first_media, version, current_language()
        )
        response = send_from_directory(
            thumbnail_folder,
            filename,
            mimetype="image/jpeg",
            as_attachment=True,
            download_name=court_thumbnail_download_filename(court),
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/service-worker.js")
    def service_worker():
        response = send_from_directory(
            Path(app.static_folder) / "js",
            "service-worker.js",
            mimetype="application/javascript",
            conditional=True,
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.post("/<guid>/push-subscription/status")
    def court_push_subscription_status(guid: str):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        payload = limited_json_payload()
        endpoint = validated_push_endpoint(payload.get("endpoint"))
        if endpoint is None:
            abort(400)
        subscribed = get_db().execute(
            "SELECT 1 FROM push_subscriptions "
            "WHERE court_id = ? AND endpoint = ?",
            (court["id"], endpoint),
        ).fetchone()
        return jsonify({"subscribed": subscribed is not None})

    @app.post("/<guid>/push-subscription")
    def subscribe_to_court_push(guid: str):
        verify_csrf()
        if not web_push_enabled():
            return jsonify({"error": "push_unavailable"}), 503
        court = fetch_court(guid)
        if court is None:
            abort(404)
        payload = limited_json_payload()
        subscription = validated_push_subscription(payload.get("subscription"))
        if subscription is None:
            abort(400)
        endpoint, p256dh, auth = subscription
        now = datetime.now().isoformat(timespec="seconds")
        db = get_db()
        db.execute(
            """
            INSERT INTO push_subscriptions (
                court_id, endpoint, p256dh, auth, language, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(court_id, endpoint) DO UPDATE SET
                p256dh = excluded.p256dh,
                auth = excluded.auth,
                language = excluded.language,
                updated_at = excluded.updated_at
            """,
            (
                court["id"],
                endpoint,
                p256dh,
                auth,
                current_language(),
                now,
                now,
            ),
        )
        db.commit()
        return jsonify({"subscribed": True})

    @app.delete("/<guid>/push-subscription")
    def unsubscribe_from_court_push(guid: str):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        payload = limited_json_payload()
        endpoint = validated_push_endpoint(payload.get("endpoint"))
        if endpoint is None:
            abort(400)
        db = get_db()
        db.execute(
            "DELETE FROM push_subscriptions "
            "WHERE court_id = ? AND endpoint = ?",
            (court["id"], endpoint),
        )
        db.commit()
        return jsonify({"subscribed": False})

    @app.get("/<guid>/court_info.md")
    @organizer_required
    def export_court_info(guid: str):
        court = fetch_managed_court(guid)
        content = render_court_info_markdown(court)
        response = send_file(
            io.BytesIO(content.encode("utf-8")),
            mimetype="text/markdown",
            as_attachment=True,
            download_name=court_info_export_filename(court),
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/<guid>")
    def court_detail(guid: str):
        court = fetch_court(guid)
        if court is None:
            abort(404)
        db = get_db()
        participants = db.execute(
            "SELECT id, username, joined_at, waitlisted, roll_called, cleared "
            "FROM participants WHERE court_id = ? "
            "ORDER BY joined_at, id",
            (court["id"],),
        ).fetchall()
        all_reserved_members = db.execute(
            "SELECT id, nickname, position, roll_called, cleared "
            "FROM reserved_members WHERE court_id = ? "
            "ORDER BY position, id",
            (court["id"],),
        ).fetchall()
        if current_user_is_admin():
            participation_history = db.execute(
                "SELECT id, username, event_type, occurred_at, "
                "ip_address, device_information "
                "FROM participation_history WHERE court_id = ? "
                "ORDER BY occurred_at DESC, id DESC",
                (court["id"],),
            ).fetchall()
        else:
            participation_history = db.execute(
                "SELECT id, username, event_type, occurred_at "
                "FROM participation_history WHERE court_id = ? "
                "ORDER BY occurred_at DESC, id DESC",
                (court["id"],),
            ).fetchall()
        court_media = fetch_court_media(court["id"])
        social_metadata = court_social_metadata(
            court, court_media[0] if court_media else None
        )
        return render_template(
            "court.html",
            court=court,
            participants=[p for p in participants if not p["waitlisted"]],
            waiting_participants=[p for p in participants if p["waitlisted"]],
            reserved_members=[member for member in all_reserved_members if member["nickname"]],
            all_reserved_members=all_reserved_members,
            court_media=court_media,
            participation_history=participation_history,
            social_metadata=social_metadata,
        )

    @app.post("/<guid>/roll-clearing/start")
    def start_roll_clearing(guid: str):
        verify_csrf()
        start_roll_clearing_mode(fetch_managed_court(guid))
        flash_t("roll_and_clearing_started", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.post("/<guid>/roll-clearing/status")
    def update_roll_clearing_status(guid: str):
        verify_csrf()
        court = fetch_managed_court(guid)
        if not court["roll_clearing_locked"]:
            abort(409)

        def checkbox_statuses(roll_field: str, cleared_field: str):
            roll = set(request.form.getlist(roll_field))
            cleared = set(request.form.getlist(cleared_field))
            return {
                int(value): (value in roll, value in cleared)
                for value in roll | cleared
                if value.isdigit()
            }

        save_roll_clearing_statuses(
            court,
            checkbox_statuses("participant_roll", "participant_cleared"),
            checkbox_statuses("reserved_roll", "reserved_cleared"),
            reset_unlisted=True,
        )
        flash_t("member_statuses_saved", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.post("/<guid>/roll-clearing/edit")
    def restore_court_editing(guid: str):
        verify_csrf()
        restore_court_editing_mode(fetch_managed_court(guid))
        flash_t("editing_mode_restored", "success")
        edit_endpoint = (
            "admin_edit_court"
            if current_user_is_admin()
            else "account_edit_court"
        )
        return redirect(url_for(edit_endpoint, guid=guid))

    @app.post("/<guid>/join")
    def join_court(guid: str):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        try:
            waitlisted = join_court_entry(
                court,
                request.form.get("username", ""),
                request.form.get("pin", ""),
            )
        except CourtActionError as error:
            flash_action_error(error)
        else:
            flash_t(
                "joined_waitlist_success" if waitlisted else "joined_success",
                "success",
            )
        return redirect(url_for("court_detail", guid=guid))

    @app.post("/<guid>/leave")
    def leave_court(guid: str):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        try:
            leave_court_entry(
                court,
                request.form.get("username", ""),
                request.form.get("pin", ""),
            )
        except CourtActionError as error:
            flash_action_error(error)
        else:
            flash_t("left_success", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        return redirect(
            url_for("account_login", **request.args),
            code=307 if request.method == "POST" else 302,
        )

    @app.post("/admin/logout")
    @admin_required
    def admin_logout():
        verify_csrf()
        session.clear()
        flash_t("signed_out", "success")
        return redirect(url_for("index"))

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        clauses, parameters, filters = build_court_filters(
            request.args, admin=True
        )
        courts = get_db().execute(
            court_query()
            + court_where_sql(clauses)
            + " ORDER BY c.archived, c.court_date DESC, c.start_time DESC",
            parameters,
        ).fetchall()
        return render_template(
            "admin/dashboard.html",
            courts=courts,
            admin_filters=filters,
            home_court_limit=get_int_setting(
                "homepage_court_limit", 12, 1, 100
            ),
        )

    @app.get("/admin/courts/export.csv")
    @admin_required
    def admin_export_all_courts_csv():
        content = render_all_courts_csv()
        response = send_file(
            io.BytesIO(content),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{date.today().isoformat()}_all_court_events.csv",
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/admin/messages")
    @account_admin_required
    def admin_messages():
        message_status = request.args.get("status", "all").strip().lower()
        if message_status not in {"all", "unread", "read"}:
            message_status = "all"
        try:
            page = max(1, int(request.args.get("page", "1")))
        except ValueError:
            page = 1
        message_page = fetch_contact_message_page(message_status, page)
        notification_channels = contact_notification_channels()
        return render_template(
            "admin/messages.html",
            contact_messages=message_page["messages"],
            message_status=message_status,
            total_count=message_page["total_count"],
            unread_count=message_page["unread_count"],
            page=message_page["page"],
            page_count=message_page["page_count"],
            contact_notifications_enabled=get_bool_setting(
                "contact_notifications_enabled"
            ),
            discord_notification_ready=notification_channels[
                "discord_ready"
            ],
            telegram_notification_ready=notification_channels[
                "telegram_ready"
            ],
        )

    @app.post("/admin/messages/<int:message_id>/status")
    @account_admin_required
    def admin_update_message_status(message_id: int):
        verify_csrf()
        if not set_contact_message_read(
            message_id, request.form.get("read") == "1"
        ):
            abort(404)
        flash_t("contact_message_status_updated", "success")
        message_status = request.form.get("status", "all")
        page = request.form.get("page", "1")
        return redirect(
            url_for(
                "admin_messages",
                status=(
                    message_status
                    if message_status in {"all", "unread", "read"}
                    else "all"
                ),
                page=page if page.isdigit() else "1",
            )
        )

    @app.post("/admin/settings/contact-notifications")
    @account_admin_required
    def admin_update_contact_notification_settings():
        verify_csrf()
        enabled = request.form.get("enabled") == "1"
        channels = contact_notification_channels()
        if enabled and not channels["discord_ready"]:
            flash_t("contact_notification_unavailable", "error")
            return redirect(url_for("admin_messages"))
        set_setting(
            "contact_notifications_enabled",
            "1" if enabled else "0",
        )
        flash_t("contact_notification_saved", "success")
        return redirect(url_for("admin_messages"))

    @app.post("/admin/settings/homepage")
    @account_admin_required
    def admin_update_homepage_settings():
        verify_csrf()
        raw_limit = request.form.get("homepage_court_limit", "").strip()
        try:
            court_limit = int(raw_limit)
        except ValueError:
            court_limit = 0
        if not 1 <= court_limit <= 100:
            flash_t("invalid_homepage_court_limit", "error")
            return redirect(url_for("admin_dashboard"))
        set_setting("homepage_court_limit", str(court_limit))
        flash_t("settings_saved", "success")
        return redirect(url_for("admin_dashboard"))

    @app.get("/admin/users")
    @account_admin_required
    def admin_users():
        return render_template("admin/users.html", users=fetch_admin_user_rows())

    @app.post("/admin/users/<int:user_id>/role")
    @super_admin_required
    def admin_update_user_role(user_id: int):
        verify_csrf()
        try:
            set_member_role(
                current_member(), user_id, request.form.get("role", "")
            )
        except CourtActionError as error:
            if error.status == 404:
                abort(404)
            flash_action_error(error)
            return redirect(url_for("admin_users"))
        flash_t("role_updated", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/archive")
    @account_admin_required
    def admin_archive_user(user_id: int):
        verify_csrf()
        reject_privileged_account_mutation(user_id)
        update_user_status(user_id, archived=1)
        flash_t("account_archived_success", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/restore")
    @account_admin_required
    def admin_restore_user(user_id: int):
        verify_csrf()
        reject_privileged_account_mutation(user_id)
        update_user_status(user_id, archived=0)
        flash_t("account_restored_success", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/delete")
    @account_admin_required
    def admin_delete_user(user_id: int):
        verify_csrf()
        try:
            delete_archived_member(user_id)
        except CourtActionError as error:
            flash_action_error(error)
            return redirect(url_for("admin_users"))
        flash_t("user_account_deleted", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/ban")
    @account_admin_required
    def admin_ban_user(user_id: int):
        verify_csrf()
        reject_privileged_account_mutation(user_id)
        update_user_ban(user_id, banned=1)
        flash_t("account_banned_success", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/unban")
    @account_admin_required
    def admin_unban_user(user_id: int):
        verify_csrf()
        reject_privileged_account_mutation(user_id)
        update_user_ban(user_id, banned=0)
        flash_t("account_unbanned_success", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/reset-login-retries")
    @account_admin_required
    def admin_reset_user_login_retries(user_id: int):
        verify_csrf()
        db = get_db()
        user = db.execute(
            "SELECT username_key FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None:
            abort(404)
        db.execute(
            "DELETE FROM login_attempts "
            "WHERE scope = 'member' AND username_key = ?",
            (user["username_key"],),
        )
        db.commit()
        flash_t("login_retries_reset", "success")
        return redirect(url_for("admin_users"))

    @app.post("/admin/users/<int:user_id>/temporary-password")
    @account_admin_required
    def admin_set_temporary_password(user_id: int):
        verify_csrf()
        reject_privileged_account_mutation(user_id)
        temporary_password = request.form.get("temporary_password", "")
        if len(temporary_password) < 8:
            flash_t("password_too_short", "error")
            return redirect(url_for("admin_users"))
        db = get_db()
        result = db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1 "
            "WHERE id = ?",
            (generate_password_hash(temporary_password), user_id),
        )
        if result.rowcount == 0:
            abort(404)
        db.commit()
        revoke_api_tokens(user_id)
        flash_t("temporary_password_set", "success")
        return redirect(url_for("admin_users"))

    @app.route("/admin/courts/new", methods=["GET", "POST"])
    def admin_new_court():
        return redirect(
            url_for("court_new", **request.args),
            code=307 if request.method == "POST" else 302,
        )

    @app.route("/admin/courts/<guid>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_court(guid: str):
        court = fetch_court(guid)
        if court is None:
            abort(404)
        if court["roll_clearing_locked"]:
            flash_t("court_read_only", "error")
            return redirect(url_for("court_detail", guid=guid))

        errors: dict[str, str] = {}
        field_names = default_court_values().keys()
        values = court_form_values(court)
        reserved_nicknames = reserved_nickname_values(
            court["id"], court["ordered_count"]
        )
        court_media = fetch_court_media(court["id"])
        selected_remove_media: set[int] = set()
        if request.method == "POST":
            verify_csrf()
            values = submitted_court_values(field_names)
            cleaned, errors = validate_court(values)
            reserved_nicknames = validate_reserved_nicknames(
                request.form.getlist("reserved_nickname"),
                cleaned.get("ordered_count") if "ordered_count" not in errors else None,
                errors,
            )
            submitted_remove_ids = {
                int(value)
                for value in request.form.getlist("remove_media")
                if value.isdigit()
            }
            available_media_ids = {item["id"] for item in court_media}
            selected_remove_media = submitted_remove_ids & available_media_ids
            media_uploads = validate_court_media_uploads(
                request.files.getlist("media"),
                len(court_media) - len(selected_remove_media),
                errors,
            )
            if not errors:
                update_court_record(
                    guid,
                    cleaned,
                    reserved_nicknames,
                    media_uploads,
                    selected_remove_media,
                )
                flash_t("court_updated", "success")
                return redirect(url_for("court_detail", guid=guid))
            flash_t("invalid_form", "error")

        return render_template(
            "admin/new_court.html",
            errors=errors,
            values=values,
            reserved_nicknames=reserved_nicknames,
            court_media=court_media,
            selected_remove_media=selected_remove_media,
            editing=True,
            court=court,
            registered_players=fetch_registered_players(court["id"]),
        )

    @app.post("/admin/courts/<guid>/duplicate")
    @admin_required
    def admin_duplicate_court(guid: str):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        flash_t("court_duplicated", "success")
        return redirect(url_for("court_new", duplicate=guid))

    @app.post("/admin/courts/<guid>/archive")
    @admin_required
    def admin_archive_court(guid: str):
        verify_csrf()
        update_court_status(guid, archived=1)
        flash_t("court_archived", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/courts/<guid>/restore")
    @admin_required
    def admin_restore_court(guid: str):
        verify_csrf()
        update_court_status(guid, archived=0)
        flash_t("court_restored", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/courts/<guid>/delete")
    @admin_required
    def admin_delete_court(guid: str):
        verify_csrf()
        if not delete_court_record(guid):
            abort(404)
        flash_t("court_deleted", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post(
        "/admin/courts/<guid>/participants/<int:participant_id>/rename"
    )
    @admin_required
    def admin_rename_participant(guid: str, participant_id: int):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        try:
            rename_court_participant(
                court, participant_id, request.form.get("username", "")
            )
        except CourtActionError as error:
            if error.status == 404:
                abort(404)
            flash_action_error(error)
        else:
            flash_t("participant_renamed", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.post(
        "/admin/courts/<guid>/participants/<int:participant_id>/reset-pin"
    )
    @admin_required
    def admin_reset_participant_pin(guid: str, participant_id: int):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        try:
            reset_court_participant_pin(
                court, participant_id, request.form.get("pin", "")
            )
        except CourtActionError as error:
            if error.status == 404:
                abort(404)
            flash_action_error(error)
        else:
            flash_t("participant_pin_reset", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.post(
        "/admin/courts/<guid>/participants/<int:participant_id>/delete"
    )
    @admin_required
    def admin_delete_participant(guid: str, participant_id: int):
        verify_csrf()
        court = fetch_court(guid)
        if court is None:
            abort(404)
        try:
            remove_court_participant(court, participant_id)
        except CourtActionError as error:
            if error.status == 404:
                abort(404)
            flash_action_error(error)
        else:
            flash_t("participant_removed", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.get("/my-courts")
    @member_required
    def account_dashboard():
        member = current_member()
        courts = get_db().execute(
            court_query()
            + " WHERE c.owner_id = ? "
            "ORDER BY c.archived, c.court_date DESC, c.start_time DESC",
            (member["id"],),
        ).fetchall()
        return render_template(
            "admin/dashboard.html",
            courts=courts,
            dashboard_mode="member",
            dashboard_title_key="my_courts_title",
            dashboard_body_key="my_courts_body",
            dashboard_label_key="my_courts",
            logout_endpoint="account_logout",
            new_endpoint="court_new",
            edit_endpoint="account_edit_court",
            duplicate_endpoint="account_duplicate_court",
            archive_endpoint="account_archive_court",
            restore_endpoint="account_restore_court",
            delete_endpoint="account_delete_court",
        )

    @app.route("/my-courts/new", methods=["GET", "POST"])
    def account_new_court():
        return redirect(
            url_for("court_new", **request.args),
            code=307 if request.method == "POST" else 302,
        )

    @app.route("/courts/new", methods=["GET", "POST"])
    @organizer_required
    def court_new():
        member = current_member()
        is_admin_actor = current_user_is_admin()
        errors: dict[str, str] = {}
        values = default_court_values()
        save_location = False
        reserved_nicknames: list[str] = []
        media_uploads: list[dict[str, Any]] = []
        source_guid = request.args.get("duplicate", "").strip()
        source_court = None
        if source_guid:
            source_court = (
                fetch_court(source_guid)
                if is_admin_actor
                else fetch_owned_court(source_guid, member["id"])
            )
            if source_court is None:
                abort(404)
            if request.method == "GET":
                values = court_form_values(source_court)
                reserved_nicknames = reserved_nickname_values(
                    source_court["id"], source_court["ordered_count"]
                )
        if request.method == "POST":
            verify_csrf()
            if request.form.get("form_action") == "import_court_info":
                try:
                    values, reserved_nicknames = parse_court_info_upload(
                        request.files.get("court_info_file")
                    )
                except ValueError as error:
                    error_key = str(error)
                    if error_key not in {
                        "court_info_invalid",
                        "court_info_too_large",
                    }:
                        error_key = "court_info_invalid"
                    errors["court_info_file"] = error_key
                    flash_t(error_key, "error")
                else:
                    cleaned, errors = validate_court(values)
                    reserved_nicknames = validate_reserved_nicknames(
                        reserved_nicknames,
                        (
                            cleaned.get("ordered_count")
                            if "ordered_count" not in errors
                            else None
                        ),
                        errors,
                    )
                    flash_t(
                        (
                            "court_info_imported_review"
                            if errors
                            else "court_info_imported"
                        ),
                        "error" if errors else "success",
                    )
            else:
                save_location = request.form.get("save_location") == "1"
                values = submitted_court_values(values)
                cleaned, errors = validate_court(values)
                reserved_nicknames = validate_reserved_nicknames(
                    request.form.getlist("reserved_nickname"),
                    (
                        cleaned.get("ordered_count")
                        if "ordered_count" not in errors
                        else None
                    ),
                    errors,
                )
                media_uploads = validate_court_media_uploads(
                    request.files.getlist("media"), 0, errors
                )
                if not errors:
                    guid = create_court_record(
                        cleaned,
                        owner_id=member["id"],
                        creator_name=member["username"],
                        reserved_nicknames=reserved_nicknames,
                        media_uploads=media_uploads,
                    )
                    if save_location:
                        save_member_location(member["id"], cleaned)
                    flash_t("court_created", "success")
                    return redirect(url_for("court_detail", guid=guid))
                flash_t("invalid_form", "error")
        return render_template(
            "admin/new_court.html",
            errors=errors,
            values=values,
            reserved_nicknames=reserved_nicknames,
            court_media=[],
            selected_remove_media=set(),
            editing=False,
            dashboard_endpoint=(
                "admin_dashboard" if is_admin_actor else "account_dashboard"
            ),
            console_key="admin_console" if is_admin_actor else "my_courts",
            saved_locations=fetch_saved_locations(member["id"]),
            allow_save_location=True,
            save_location=save_location,
        )

    @app.route("/my-courts/<guid>/edit", methods=["GET", "POST"])
    @member_required
    def account_edit_court(guid: str):
        member = current_member()
        court = fetch_owned_court(guid, member["id"])
        if court is None:
            abort(404)
        if court["roll_clearing_locked"]:
            flash_t("court_read_only", "error")
            return redirect(url_for("court_detail", guid=guid))

        errors: dict[str, str] = {}
        field_names = default_court_values().keys()
        values = court_form_values(court)
        reserved_nicknames = reserved_nickname_values(
            court["id"], court["ordered_count"]
        )
        court_media = fetch_court_media(court["id"])
        selected_remove_media: set[int] = set()
        if request.method == "POST":
            verify_csrf()
            values = submitted_court_values(field_names)
            cleaned, errors = validate_court(values)
            reserved_nicknames = validate_reserved_nicknames(
                request.form.getlist("reserved_nickname"),
                cleaned.get("ordered_count") if "ordered_count" not in errors else None,
                errors,
            )
            submitted_remove_ids = {
                int(value)
                for value in request.form.getlist("remove_media")
                if value.isdigit()
            }
            available_media_ids = {item["id"] for item in court_media}
            selected_remove_media = submitted_remove_ids & available_media_ids
            media_uploads = validate_court_media_uploads(
                request.files.getlist("media"),
                len(court_media) - len(selected_remove_media),
                errors,
            )
            if not errors:
                update_court_record(
                    guid,
                    cleaned,
                    reserved_nicknames,
                    media_uploads,
                    selected_remove_media,
                )
                flash_t("court_updated", "success")
                return redirect(url_for("court_detail", guid=guid))
            flash_t("invalid_form", "error")

        return render_template(
            "admin/new_court.html",
            errors=errors,
            values=values,
            reserved_nicknames=reserved_nicknames,
            court_media=court_media,
            selected_remove_media=selected_remove_media,
            editing=True,
            court=court,
            registered_players=fetch_registered_players(court["id"]),
            dashboard_endpoint="account_dashboard",
            console_key="my_courts",
        )

    @app.post("/my-courts/<guid>/duplicate")
    @member_required
    def account_duplicate_court(guid: str):
        member = current_member()
        verify_csrf()
        court = fetch_owned_court(guid, member["id"])
        if court is None:
            abort(404)
        flash_t("court_duplicated", "success")
        return redirect(url_for("court_new", duplicate=guid))

    @app.post("/my-courts/<guid>/archive")
    @member_required
    def account_archive_court(guid: str):
        verify_csrf()
        update_owned_court_status(guid, current_member()["id"], archived=1)
        flash_t("court_archived", "success")
        return redirect(url_for("account_dashboard"))

    @app.post("/my-courts/<guid>/restore")
    @member_required
    def account_restore_court(guid: str):
        verify_csrf()
        update_owned_court_status(guid, current_member()["id"], archived=0)
        flash_t("court_restored", "success")
        return redirect(url_for("account_dashboard"))

    @app.post("/my-courts/<guid>/delete")
    @member_required
    def account_delete_court(guid: str):
        verify_csrf()
        if not delete_court_record(guid, current_member()["id"]):
            abort(404)
        flash_t("court_deleted", "success")
        return redirect(url_for("account_dashboard"))

    @app.errorhandler(404)
    def not_found(_error):
        if request.path == "/api" or request.path.startswith("/api/"):
            return api_error_response("not_found", 404)
        return render_template("404.html"), 404

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app_config("DATABASE"), detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_int_setting(
    setting_key: str, default: int, minimum: int, maximum: int
) -> int:
    setting = get_db().execute(
        "SELECT setting_value FROM app_settings WHERE setting_key = ?",
        (setting_key,),
    ).fetchone()
    try:
        value = int(setting["setting_value"]) if setting is not None else default
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def get_bool_setting(setting_key: str, default: bool = False) -> bool:
    setting = get_db().execute(
        "SELECT setting_value FROM app_settings WHERE setting_key = ?",
        (setting_key,),
    ).fetchone()
    if setting is None:
        return default
    return str(setting["setting_value"]).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def set_setting(setting_key: str, setting_value: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    db = get_db()
    db.execute(
        """
        INSERT INTO app_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            updated_at = excluded.updated_at
        """,
        (setting_key, setting_value, now),
    )
    db.commit()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    columns = {
        row["name"] for row in db.execute("PRAGMA table_info(courts)").fetchall()
    }
    # Keep existing SQLite installations compatible as place metadata is added.
    if "event_name" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN event_name TEXT NOT NULL DEFAULT ''"
        )
    if "badminton_name" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN badminton_name TEXT NOT NULL DEFAULT ''"
        )
    if "google_place_id" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN google_place_id TEXT NOT NULL DEFAULT ''"
        )
    if "latitude" not in columns:
        db.execute("ALTER TABLE courts ADD COLUMN latitude REAL")
    if "longitude" not in columns:
        db.execute("ALTER TABLE courts ADD COLUMN longitude REAL")
    if "owner_id" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN owner_id INTEGER "
            "REFERENCES users(id) ON DELETE SET NULL"
        )
    if "creator_name" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN creator_name "
            "TEXT NOT NULL DEFAULT ''"
        )
    db.execute(
        """
        UPDATE courts
        SET creator_name = COALESCE(
            (SELECT username FROM users WHERE users.id = courts.owner_id),
            ?
        )
        WHERE creator_name = ''
        """,
        (current_app_config("ADMIN_USERNAME"),),
    )
    if "remark" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN remark TEXT NOT NULL DEFAULT ''"
        )
    if "male_price" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN male_price INTEGER NOT NULL DEFAULT 0"
        )
    if "female_price" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN female_price INTEGER NOT NULL DEFAULT 0"
        )
    if "shuttlecock_info" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN shuttlecock_info TEXT NOT NULL DEFAULT ''"
        )
    if "reserved_names_visible" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN reserved_names_visible "
            "INTEGER NOT NULL DEFAULT 1"
        )
    if "roll_clearing_locked" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN roll_clearing_locked "
            "INTEGER NOT NULL DEFAULT 0"
        )
    if "leave_deadline_enabled" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN leave_deadline_enabled "
            "INTEGER NOT NULL DEFAULT 0"
        )
    if "leave_deadline_at" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN leave_deadline_at "
            "TEXT NOT NULL DEFAULT ''"
        )
    if "owner_notifications" not in columns:
        db.execute(
            "ALTER TABLE courts ADD COLUMN owner_notifications "
            "INTEGER NOT NULL DEFAULT 1"
        )
    api_token_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(api_tokens)").fetchall()
    }
    # The Android app links its FCM registration token to its sign-in token
    # so organizers hear about changes to their own courts.
    if "fcm_token" not in api_token_columns:
        db.execute("ALTER TABLE api_tokens ADD COLUMN fcm_token TEXT")
    if "fcm_language" not in api_token_columns:
        db.execute(
            "ALTER TABLE api_tokens ADD COLUMN fcm_language "
            "TEXT NOT NULL DEFAULT 'en-us'"
        )
    db.execute(
        "CREATE INDEX IF NOT EXISTS api_tokens_fcm_token_idx "
        "ON api_tokens(fcm_token)"
    )
    participant_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(participants)").fetchall()
    }
    if "waitlisted" not in participant_columns:
        db.execute(
            "ALTER TABLE participants ADD COLUMN waitlisted "
            "INTEGER NOT NULL DEFAULT 0"
        )
    if "roll_called" not in participant_columns:
        db.execute(
            "ALTER TABLE participants ADD COLUMN roll_called "
            "INTEGER NOT NULL DEFAULT 0"
        )
    if "cleared" not in participant_columns:
        db.execute(
            "ALTER TABLE participants ADD COLUMN cleared "
            "INTEGER NOT NULL DEFAULT 0"
        )
    reserved_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(reserved_members)").fetchall()
    }
    if "roll_called" not in reserved_columns:
        db.execute(
            "ALTER TABLE reserved_members ADD COLUMN roll_called "
            "INTEGER NOT NULL DEFAULT 0"
        )
    if "cleared" not in reserved_columns:
        db.execute(
            "ALTER TABLE reserved_members ADD COLUMN cleared "
            "INTEGER NOT NULL DEFAULT 0"
        )
    user_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()
    }
    if "archived" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
        )
    if "banned" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN banned INTEGER NOT NULL DEFAULT 0"
        )
    if "must_change_password" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN must_change_password "
            "INTEGER NOT NULL DEFAULT 0"
        )
    if "avatar_filename" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN avatar_filename "
            "TEXT NOT NULL DEFAULT ''"
        )
    if "time_format" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN time_format "
            "TEXT NOT NULL DEFAULT '24h' CHECK(time_format IN ('12h', '24h'))"
        )
    if "last_login_at" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
    if "last_login_ip" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN last_login_ip TEXT")
    if "role" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'member'"
        )
    db.execute(
        "UPDATE users SET role = 'member' WHERE role NOT IN "
        "('member', 'sub_admin', 'admin', 'super_admin')"
    )
    admin_username = str(current_app_config("ADMIN_USERNAME")).strip()
    admin_username_key = admin_username.casefold()
    bootstrap_admin = db.execute(
        "SELECT id, role FROM users WHERE username_key = ?",
        (admin_username_key,),
    ).fetchone()
    has_super_admin = db.execute(
        "SELECT 1 FROM users WHERE role = 'super_admin' LIMIT 1"
    ).fetchone()
    if has_super_admin is None:
        admin_password_hash = generate_password_hash(
            str(current_app_config("ADMIN_PASSWORD"))
        )
        now = datetime.now().isoformat(timespec="seconds")
        if bootstrap_admin is None:
            db.execute(
                "INSERT INTO users "
                "(username, username_key, password_hash, role, created_at) "
                "VALUES (?, ?, ?, 'super_admin', ?)",
                (admin_username, admin_username_key, admin_password_hash, now),
            )
        else:
            db.execute(
                "UPDATE users SET password_hash = ?, role = 'super_admin', "
                "archived = 0, banned = 0 WHERE id = ?",
                (admin_password_hash, bootstrap_admin["id"]),
            )
    login_attempt_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(login_attempts)").fetchall()
    }
    if "scope" not in login_attempt_columns:
        db.execute(
            "ALTER TABLE login_attempts ADD COLUMN scope "
            "TEXT NOT NULL DEFAULT ''"
        )
    if "username_key" not in login_attempt_columns:
        db.execute(
            "ALTER TABLE login_attempts ADD COLUMN username_key "
            "TEXT NOT NULL DEFAULT ''"
        )
    # Previous hashed-only rows cannot be mapped back to a member account.
    # Clear them once so every remaining retry group can be reset by admin.
    db.execute(
        "DELETE FROM login_attempts WHERE scope = '' OR username_key = ''"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS login_attempts_member_idx "
        "ON login_attempts(scope, username_key)"
    )
    # Earlier releases stored the complete User-Agent string. Keep only a
    # broad device category so audit records do not retain browser details.
    db.execute(
        """
        UPDATE participation_history
        SET device_information = CASE
            WHEN lower(device_information) LIKE '%android%'
                THEN 'android'
            WHEN lower(device_information) LIKE '%iphone%'
              OR lower(device_information) LIKE '%ipad%'
              OR lower(device_information) LIKE '%ipod%'
              OR (
                  lower(device_information) LIKE '%mac os x%'
                  AND lower(device_information) LIKE '%mobile%'
              )
                THEN 'ios'
            WHEN lower(device_information) LIKE '%mobile%'
              OR lower(device_information) LIKE '%iemobile%'
              OR lower(device_information) LIKE '%opera mini%'
                THEN 'mobile'
            ELSE 'web'
        END
        WHERE device_information NOT IN ('ios', 'android', 'mobile', 'web')
        """
    )
    db.commit()


def current_app_config(key: str) -> Any:
    from flask import current_app

    return current_app.config[key]


def public_external_url(endpoint: str, **values: Any) -> str:
    generated_url = url_for(endpoint, _external=True, **values)
    if not current_app_config("TRUST_PROXY_HEADERS"):
        return generated_url
    forwarded_scheme = request.headers.get("X-Forwarded-Proto", "")
    forwarded_scheme = forwarded_scheme.split(",", 1)[0].strip().lower()
    if forwarded_scheme not in {"http", "https"}:
        return generated_url
    return urlparse(generated_url)._replace(scheme=forwarded_scheme).geturl()


def current_language() -> str:
    if api_request_active():
        requested = request.args.get("lang", "").strip().lower()
        if requested in LANGUAGES:
            return requested
        if request.accept_languages:
            matched = request.accept_languages.best_match(
                ("zh-TW", "zh-Hant", "zh", "en-US", "en")
            )
            if matched:
                return "zh-tw" if matched.lower().startswith("zh") else "en-us"
    saved_language = request.cookies.get("court_lang", "").lower()
    if saved_language in LANGUAGES:
        return saved_language
    return "zh-tw" if detected_country_code() == "TW" else "en-us"


def current_time_format() -> str:
    cached_format = getattr(g, "time_format", None)
    if cached_format in TIME_FORMATS:
        return cached_format
    member = current_member()
    selected_format = (
        member["time_format"]
        if member is not None and member["time_format"] in TIME_FORMATS
        else "24h"
    )
    g.time_format = selected_format
    return selected_format


def format_clock_time(value: datetime, include_seconds: bool = False) -> str:
    minute_second = f":{value.minute:02d}"
    if include_seconds:
        minute_second += f":{value.second:02d}"
    if current_time_format() == "12h":
        hour = value.hour % 12 or 12
        meridiem = "AM" if value.hour < 12 else "PM"
        return f"{hour}{minute_second} {meridiem}"
    return f"{value.hour:02d}{minute_second}"


def validated_privacy_label(value: Any) -> str:
    label = str(value or "").strip()
    if (
        not label
        or len(label) > 200
        or any(ord(character) < 32 for character in label)
    ):
        return ""
    return label


def validated_contact_uri(value: Any) -> str:
    contact = str(value or "").strip()
    if (
        not contact
        or len(contact) > 500
        or any(ord(character) < 32 for character in contact)
    ):
        return ""
    parsed = urlparse(contact)
    if (
        parsed.scheme == "mailto"
        and parsed.path
        and not parsed.netloc
    ):
        return contact
    if parsed.scheme in {"https", "http"} and parsed.netloc:
        return contact
    return ""


def configured_admin_contact_methods(lang: str) -> list[dict[str, str]]:
    contact_methods: list[dict[str, str]] = []
    general_contact = validated_contact_uri(
        current_app_config("ADMIN_CONTACT")
    )
    if general_contact:
        general_id = (
            "email"
            if urlparse(general_contact).scheme == "mailto"
            else "website"
        )
        contact_methods.append(
            {
                "id": general_id,
                "label": TRANSLATIONS[lang][f"contact_{general_id}"],
                "uri": general_contact,
                "display": contact_display_label(general_contact),
            }
        )
    for method_id in ("discord", "line", "telegram"):
        public_contact = configured_public_contact(
            method_id,
            current_app_config(f"ADMIN_CONTACT_{method_id.upper()}"),
        )
        if public_contact:
            method_uri, display = public_contact
            contact_methods.append(
                {
                    "id": method_id,
                    "label": TRANSLATIONS[lang][f"contact_{method_id}"],
                    "uri": method_uri,
                    "display": display,
                }
            )
    return sorted(
        {method["uri"]: method for method in contact_methods}.values(),
        key=lambda method: (
            CONTACT_METHOD_SORT_ORDER[method["id"]],
            method["id"],
        ),
    )


def configured_admin_contact_method_groups(
    lang: str,
) -> list[dict[str, Any]]:
    methods = configured_admin_contact_methods(lang)
    groups = (
        (
            "email",
            "contact_method_email_group",
            [method for method in methods if method["id"] == "email"],
        ),
        (
            "messaging",
            "contact_method_messaging_group",
            [
                method
                for method in methods
                if method["id"] in {"discord", "line", "telegram"}
            ],
        ),
        (
            "other",
            "contact_method_other_group",
            [
                method
                for method in methods
                if method["id"]
                not in {"email", "discord", "line", "telegram"}
            ],
        ),
    )
    return [
        {
            "id": group_id,
            "label": TRANSLATIONS[lang][label_key],
            "methods": grouped_methods,
        }
        for group_id, label_key, grouped_methods in groups
        if grouped_methods
    ]


def configured_public_contact(
    method_id: str, value: Any
) -> tuple[str, str] | None:
    contact_id = normalized_public_contact_id(method_id, value)
    if not contact_id:
        return None
    if method_id == "discord":
        return f"https://discord.gg/{contact_id}", contact_id
    if method_id == "line":
        display = f"@{contact_id}"
        return (
            f"https://line.me/R/ti/p/{quote(display, safe='')}",
            display,
        )
    if method_id == "telegram":
        return f"https://t.me/{contact_id}", f"@{contact_id}"
    return None


def normalized_public_contact_id(method_id: str, value: Any) -> str:
    contact = str(value or "").strip()
    if (
        method_id not in PUBLIC_CONTACT_ID_PATTERNS
        or not contact
        or len(contact) > 500
        or any(ord(character) < 32 for character in contact)
    ):
        return ""

    parsed = urlparse(contact)
    if parsed.scheme or parsed.netloc:
        contact = public_contact_id_from_url(method_id, parsed)
        if not contact:
            return ""

    contact = unquote(contact).strip()
    if method_id in {"line", "telegram"}:
        contact = contact.removeprefix("@")
    if not PUBLIC_CONTACT_ID_PATTERNS[method_id].fullmatch(contact):
        return ""
    return contact


def public_contact_id_from_url(method_id: str, parsed: Any) -> str:
    try:
        hostname = (parsed.hostname or "").rstrip(".").lower()
        has_port = parsed.port is not None
    except ValueError:
        return ""
    if (
        parsed.scheme.lower() != "https"
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or has_port
    ):
        return ""
    path_parts = [part for part in parsed.path.split("/") if part]
    if method_id == "discord":
        if hostname == "discord.gg" and len(path_parts) == 1:
            return path_parts[0]
        if (
            hostname in {"discord.com", "discordapp.com"}
            and len(path_parts) == 2
            and path_parts[0].lower() == "invite"
        ):
            return path_parts[1]
    elif method_id == "line":
        if (
            hostname == "line.me"
            and len(path_parts) == 4
            and [part.lower() for part in path_parts[:3]] == ["r", "ti", "p"]
        ):
            return path_parts[3]
    elif (
        method_id == "telegram"
        and hostname in {"t.me", "telegram.me"}
        and len(path_parts) == 1
    ):
        return path_parts[0]
    return ""


def contact_display_label(contact_uri: str) -> str:
    if contact_uri.startswith("mailto:"):
        return contact_uri.removeprefix("mailto:")
    return re.sub(r"^https?://", "", contact_uri, flags=re.IGNORECASE)


def contains_disallowed_control_characters(
    value: str, *, multiline: bool = False
) -> bool:
    allowed = {"\n", "\r", "\t"} if multiline else set()
    return any(
        ord(character) < 32 and character not in allowed
        for character in value
    )


def validated_discord_webhook_url(value: Any) -> str:
    webhook_url = str(value or "").strip()
    if (
        not webhook_url
        or len(webhook_url) > 1000
        or contains_disallowed_control_characters(webhook_url)
    ):
        return ""
    parsed = urlparse(webhook_url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not (
            hostname == "discord.com"
            or hostname.endswith(".discord.com")
            or hostname == "discordapp.com"
            or hostname.endswith(".discordapp.com")
        )
        or not re.fullmatch(
            r"/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9._-]+/?",
            parsed.path,
        )
    ):
        return ""
    return webhook_url


def validated_telegram_bot_token(value: Any) -> str:
    token = str(value or "").strip()
    if re.fullmatch(r"\d{5,20}:[A-Za-z0-9_-]{20,100}", token):
        return token
    return ""


def validated_telegram_chat_id(value: Any) -> str:
    chat_id = str(value or "").strip()
    if re.fullmatch(r"-?\d{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31}", chat_id):
        return chat_id
    return ""


def contact_notification_channels() -> dict[str, Any]:
    discord_webhook = validated_discord_webhook_url(
        current_app_config("CONTACT_DISCORD_WEBHOOK_URL")
    )
    telegram_token = validated_telegram_bot_token(
        current_app_config("CONTACT_TELEGRAM_BOT_TOKEN")
    )
    telegram_chat_id = validated_telegram_chat_id(
        current_app_config("CONTACT_TELEGRAM_CHAT_ID")
    )
    return {
        "discord_webhook": discord_webhook,
        "discord_ready": bool(discord_webhook),
        "telegram_token": telegram_token,
        "telegram_chat_id": telegram_chat_id,
        "telegram_ready": bool(telegram_token and telegram_chat_id),
    }


CONTACT_CLIENT_FIELDS = ("platform", "app_version", "os_version", "device_model")
WEB_DEVICE_LABELS = {
    "android": "Android browser",
    "ios": "iOS browser",
    "mobile": "Mobile browser",
    "web": "Desktop browser",
}


def clean_contact_client(value: Any) -> dict[str, str]:
    """Keep the short, printable client fields an app sends with a message."""
    if not isinstance(value, dict):
        return {}
    client: dict[str, str] = {}
    for field_name in CONTACT_CLIENT_FIELDS:
        field_value = value.get(field_name)
        if isinstance(field_value, (str, int, float)) and not isinstance(
            field_value, bool
        ):
            text = "".join(
                ch for ch in str(field_value).strip() if ch.isprintable()
            )[:60]
            if text:
                client[field_name] = text
    return client


def contact_message_context(client: dict[str, str] | None = None) -> dict[str, str]:
    """Where a contact message came from, for the delivered report."""
    member = current_member()
    account = (
        f"{member['username']} (#{member['id']})" if member else "Guest / 訪客"
    )
    client = client or {}
    if not api_request_active():
        source = "Website / 網站"
        device = WEB_DEVICE_LABELS[client_device_information()]
    elif client.get("platform", "").casefold() == "android":
        source = " ".join(
            part for part in ("Android app / App", client.get("app_version")) if part
        )
        os_version = client.get("os_version")
        device = " · ".join(
            part
            for part in (
                client.get("device_model"),
                f"Android {os_version}" if os_version else "",
            )
            if part
        ) or "—"
    else:
        source = "API"
        device = WEB_DEVICE_LABELS[client_device_information()]
    return {"source": source, "device": device, "account": account}


def format_contact_message_notification(message: dict[str, Any]) -> str:
    reply_contact = message["reply_contact"] or "—"
    body = message["message"]
    if len(body) > 1200:
        body = body[:1197].rstrip() + "…"
    notification = (
        f"📮 Contact report / 聯絡回報 #{message['id']}\n"
        f"Subject / 主旨: {message['subject']}\n\n"
        f"{body}\n\n"
        "— Sender / 寄件者 —\n"
        f"Name / 名稱: {message['sender_name']}\n"
        f"Reply / 回覆: {reply_contact}\n"
        f"Account / 帳號: {message.get('account') or '—'}\n\n"
        "— Environment / 環境 —\n"
        f"Source / 來源: {message.get('source') or '—'}\n"
        f"Device / 裝置: {message.get('device') or '—'}\n"
        f"Language / 語言: {message.get('language') or '—'}\n"
        f"Submitted / 送出: {message['submitted_at']}\n\n"
        f"Inbox / 收件匣: {public_external_url('admin_messages')}"
    )
    return notification[:1900]


def post_contact_notification(
    service: str,
    endpoint: str,
    payload: dict[str, Any],
    *,
    require_ok_response: bool = False,
) -> bool:
    notification_request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "badminton-court-control-panel/contact-notifier",
        },
        method="POST",
    )
    timeout = min(
        30.0,
        max(
            0.5,
            float(current_app_config("CONTACT_NOTIFICATION_TIMEOUT")),
        ),
    )
    try:
        with urlopen(notification_request, timeout=timeout) as response:
            response_body = response.read(65536)
            if require_ok_response:
                response_data = json.loads(response_body.decode("utf-8"))
                if response_data.get("ok") is not True:
                    raise ValueError("notification response was not successful")
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        current_app.logger.warning(
            "%s contact-message notification failed: %s",
            service,
            error.__class__.__name__,
        )
        return False
    return True


def send_contact_message_notifications(message: dict[str, Any]) -> None:
    """Report a new message: always to Telegram when it is configured, and to
    Discord when an administrator turned Discord notifications on."""
    channels = contact_notification_channels()
    discord_enabled = channels["discord_ready"] and get_bool_setting(
        "contact_notifications_enabled"
    )
    if not (discord_enabled or channels["telegram_ready"]):
        return
    notification = format_contact_message_notification(message)
    if discord_enabled:
        post_contact_notification(
            "Discord",
            channels["discord_webhook"],
            {
                "content": notification,
                "allowed_mentions": {"parse": []},
            },
        )
    if channels["telegram_ready"]:
        post_contact_notification(
            "Telegram",
            (
                "https://api.telegram.org/bot"
                f"{channels['telegram_token']}/sendMessage"
            ),
            {
                "chat_id": channels["telegram_chat_id"],
                "text": notification,
            },
            require_ok_response=True,
        )


def detected_country_code() -> str:
    if "detected_country_code" in g:
        return g.detected_country_code

    country_code = ""
    for header_name in (
        "CF-IPCountry",
        "CloudFront-Viewer-Country",
        "X-Vercel-IP-Country",
        "X-Country-Code",
    ):
        candidate = request.headers.get(header_name, "").strip().upper()
        if len(candidate) == 2 and candidate.isalpha():
            country_code = candidate
            break

    if not country_code:
        reader = current_app.extensions.get("geoip_country_reader")
        address = client_ip_address()
        if reader is not None and address:
            try:
                country_code = (reader.country(address).country.iso_code or "").upper()
            except (KeyError, ValueError):
                country_code = ""
            except Exception as error:
                if error.__class__.__name__ != "AddressNotFoundError":
                    current_app.logger.warning("GeoIP lookup failed: %s", error)

    if not country_code:
        fallback = str(current_app_config("DEFAULT_COUNTRY_CODE")).strip().upper()
        if len(fallback) == 2 and fallback.isalpha():
            country_code = fallback

    g.detected_country_code = country_code
    return country_code


def parse_filter_date(value: str) -> date | None:
    normalized = value.strip().replace("/", "-")
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def format_filter_date(value: date | None) -> str:
    return value.strftime("%Y/%m/%d") if value else ""


def client_ip_address() -> str:
    candidate = request.remote_addr or ""
    if current_app_config("TRUST_PROXY_HEADERS"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        return ""


def client_device_information() -> str:
    return classify_device(request.headers.get("User-Agent", ""))


def classify_device(user_agent: str) -> str:
    normalized = user_agent.casefold()
    if "android" in normalized:
        return "android"
    if (
        any(device in normalized for device in ("iphone", "ipad", "ipod"))
        or ("mac os x" in normalized and "mobile" in normalized)
    ):
        return "ios"
    if any(
        marker in normalized for marker in ("mobile", "iemobile", "opera mini")
    ):
        return "mobile"
    return "web"


def record_participation_event(
    db: sqlite3.Connection,
    court_id: int,
    username: str,
    event_type: str,
    occurred_at: str,
) -> None:
    db.execute(
        """
        INSERT INTO participation_history
            (court_id, username, event_type, occurred_at,
             ip_address, device_information)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            court_id,
            username,
            event_type,
            occurred_at,
            client_ip_address(),
            client_device_information(),
        ),
    )


def login_attempt_key(scope: str, username: str) -> str:
    identity = f"{scope}\0{username.casefold()}\0{client_ip_address()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def login_lock_minutes(scope: str, username: str) -> int:
    attempt_key = login_attempt_key(scope, username)
    db = get_db()
    attempt = db.execute(
        "SELECT locked_until FROM login_attempts WHERE attempt_key = ?",
        (attempt_key,),
    ).fetchone()
    if attempt is None or not attempt["locked_until"]:
        return 0
    try:
        locked_until = datetime.fromisoformat(attempt["locked_until"])
    except (TypeError, ValueError):
        locked_until = datetime.min
    now = datetime.now()
    if locked_until <= now:
        db.execute("DELETE FROM login_attempts WHERE attempt_key = ?", (attempt_key,))
        db.commit()
        return 0
    seconds = int((locked_until - now).total_seconds())
    return max(1, (seconds + 59) // 60)


def clear_login_failures(scope: str, username: str) -> None:
    db = get_db()
    db.execute(
        "DELETE FROM login_attempts WHERE attempt_key = ?",
        (login_attempt_key(scope, username),),
    )
    db.commit()


def record_failed_attempt(
    scope: str,
    username: str,
    *,
    max_attempts_config: str,
    lockout_seconds_config: str,
    remaining_translation: str,
    locked_translation: str,
    store_username_key: bool,
) -> str:
    """Count one failed attempt and return the user-facing message."""
    db = get_db()
    now = datetime.now()
    attempt_key = login_attempt_key(scope, username)
    attempt_window = max(
        60, int(current_app_config(lockout_seconds_config))
    )
    cutoff = now - timedelta(seconds=attempt_window)
    db.execute(
        """
        DELETE FROM login_attempts
        WHERE (locked_until IS NULL AND updated_at <= ?)
           OR (locked_until IS NOT NULL AND locked_until <= ?)
        """,
        (
            cutoff.isoformat(timespec="seconds"),
            now.isoformat(timespec="seconds"),
        ),
    )
    db.execute(
        """
        INSERT INTO login_attempts
            (attempt_key, scope, username_key,
             failed_count, locked_until, updated_at)
        VALUES (?, ?, ?, 1, NULL, ?)
        ON CONFLICT(attempt_key) DO UPDATE SET
            scope = excluded.scope,
            username_key = excluded.username_key,
            failed_count = login_attempts.failed_count + 1,
            updated_at = excluded.updated_at
        """,
        (
            attempt_key,
            scope,
            username.casefold() if store_username_key else attempt_key,
            now.isoformat(timespec="seconds"),
        ),
    )
    attempt = db.execute(
        "SELECT failed_count FROM login_attempts WHERE attempt_key = ?",
        (attempt_key,),
    ).fetchone()
    max_attempts = max(1, int(current_app_config(max_attempts_config)))
    failed_count = attempt["failed_count"]
    remaining = max(0, max_attempts - failed_count)
    if remaining:
        db.commit()
        return TRANSLATIONS[current_language()][remaining_translation].format(
            count=remaining,
        )

    lockout_seconds = attempt_window
    locked_until = now + timedelta(seconds=lockout_seconds)
    db.execute(
        "UPDATE login_attempts SET locked_until = ? WHERE attempt_key = ?",
        (locked_until.isoformat(timespec="seconds"), attempt_key),
    )
    db.commit()
    return attempt_locked_message(
        locked_translation,
        max(1, (lockout_seconds + 59) // 60),
    )


def record_login_failure(scope: str, username: str) -> str:
    return record_failed_attempt(
        scope,
        username,
        max_attempts_config="LOGIN_MAX_ATTEMPTS",
        lockout_seconds_config="LOGIN_LOCKOUT_SECONDS",
        remaining_translation="login_attempts_remaining",
        locked_translation="login_locked",
        store_username_key=True,
    )


def court_leave_attempt_scope(court_id: int) -> str:
    return f"court_leave:{court_id}"


def record_leave_failure(court_id: int, username: str) -> str:
    return record_failed_attempt(
        court_leave_attempt_scope(court_id),
        username,
        max_attempts_config="LEAVE_MAX_ATTEMPTS",
        lockout_seconds_config="LEAVE_LOCKOUT_SECONDS",
        remaining_translation="leave_attempts_remaining",
        locked_translation="leave_locked",
        store_username_key=False,
    )


def attempt_locked_message(translation_key: str, minutes: int) -> str:
    return TRANSLATIONS[current_language()][translation_key].format(
        minutes=minutes
    )


def flash_action_error(error: CourtActionError) -> None:
    flash_message(error.message, "error")


def api_request_active() -> bool:
    return bool(g.get("api_request"))


def api_error_response(
    code: str,
    status: int,
    message: str | None = None,
    fields: dict[str, str] | None = None,
):
    error: dict[str, Any] = {
        "code": code,
        "message": message
        or TRANSLATIONS[current_language()].get(code)
        or API_ERROR_MESSAGES.get(code, {}).get(current_language())
        or code,
    }
    if fields:
        error["fields"] = fields
    return jsonify({"error": error}), status


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def verify_csrf() -> None:
    expected = session.get("csrf_token", "")
    supplied = (
        request.form.get("csrf_token", "")
        or request.headers.get("X-CSRF-Token", "")
    )
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        flash_t("invalid_csrf", "error")
        abort(400)


def web_push_enabled() -> bool:
    public_key = str(current_app.config.get("WEB_PUSH_PUBLIC_KEY", "")).strip()
    subject = str(current_app.config.get("WEB_PUSH_SUBJECT", "")).strip()
    parsed_subject = urlparse(subject)
    return bool(
        valid_p256dh_key(public_key)
        and current_app.config.get("WEB_PUSH_PRIVATE_KEY")
        and (
            (parsed_subject.scheme == "mailto" and "@" in parsed_subject.path)
            or (parsed_subject.scheme == "https" and parsed_subject.hostname)
        )
    )


def limited_json_payload() -> dict[str, Any]:
    if request.content_length is not None and request.content_length > 16_384:
        abort(413)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400)
    return payload


def validated_push_endpoint(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    endpoint = value.strip()
    if not 20 <= len(endpoint) <= 2048:
        return None
    try:
        parsed = urlparse(endpoint)
        port = parsed.port
    except ValueError:
        return None
    hostname = (parsed.hostname or "").lower().rstrip(".")
    trusted_host = any(
        hostname == suffix or hostname.endswith(f".{suffix}")
        for suffix in TRUSTED_PUSH_HOST_SUFFIXES
    )
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or port not in (None, 443)
        or parsed.fragment
        or not trusted_host
    ):
        return None
    return endpoint


def fcm_client() -> FcmClient | None:
    """The FCM sender, created once per app; ``None`` when not configured."""
    extensions = current_app.extensions
    if "fcm_client" not in extensions:
        path = str(current_app.config.get("FCM_SERVICE_ACCOUNT_FILE", "")).strip()
        client = None
        if path:
            try:
                client = FcmClient(
                    path, timeout=float(current_app.config["FCM_TIMEOUT"])
                )
            except (OSError, ValueError, KeyError) as error:
                current_app.logger.warning(
                    "FCM disabled: cannot load the service account key (%s)",
                    type(error).__name__,
                )
        extensions["fcm_client"] = client
    return extensions["fcm_client"]


def fcm_enabled() -> bool:
    return fcm_client() is not None


def validated_fcm_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    return token if FCM_TOKEN_PATTERN.fullmatch(token) else None


def validated_push_subscription(value: Any) -> tuple[str, str, str] | None:
    if not isinstance(value, dict):
        return None
    endpoint = validated_push_endpoint(value.get("endpoint"))
    keys = value.get("keys")
    if endpoint is None or not isinstance(keys, dict):
        return None
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not isinstance(p256dh, str) or not isinstance(auth, str):
        return None
    p256dh = p256dh.strip()
    auth = auth.strip()
    if (
        not valid_p256dh_key(p256dh)
        or not valid_auth_secret(auth)
    ):
        return None
    return endpoint, p256dh, auth


def decode_base64url(value: str) -> bytes | None:
    if WEB_PUSH_KEY_PATTERN.fullmatch(value) is None:
        return None
    try:
        return base64.urlsafe_b64decode(
            value + ("=" * ((4 - len(value) % 4) % 4))
        )
    except (binascii.Error, ValueError):
        return None


def valid_p256dh_key(value: str) -> bool:
    decoded = decode_base64url(value)
    return bool(decoded and len(decoded) == 65 and decoded[0] == 4)


def valid_auth_secret(value: str) -> bool:
    decoded = decode_base64url(value)
    return bool(decoded and len(decoded) == 16)


def flash_message(message: str, category: str) -> None:
    # API clients receive results in the JSON body; flashing would only
    # create an unused session cookie.
    if not api_request_active():
        flash(message, category)


def flash_t(key: str, category: str) -> None:
    flash_message(TRANSLATIONS[current_language()].get(key, key), category)


def turnstile_enabled() -> bool:
    return bool(
        not current_app.debug
        and current_app.config.get("TURNSTILE_SITE_KEY")
        and current_app.config.get("TURNSTILE_SECRET_KEY")
    )


def verify_turnstile_response(
    expected_action: str, token: str | None = None
) -> bool:
    if not turnstile_enabled():
        return True
    if token is None:
        token = request.form.get("cf-turnstile-response", "")
    token = str(token).strip()
    if not token or len(token) > 2048:
        return False

    payload = {
        "secret": current_app.config["TURNSTILE_SECRET_KEY"],
        "response": token,
    }
    remote_ip = client_ip_address()
    if remote_ip:
        payload["remoteip"] = remote_ip
    verification_request = Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(
            verification_request,
            timeout=float(current_app.config["TURNSTILE_VERIFY_TIMEOUT"]),
        ) as response:
            result = json.loads(response.read(65536).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        current_app.logger.warning(
            "Turnstile verification request failed: %s",
            error.__class__.__name__,
        )
        return False
    return (
        result.get("success") is True
        and result.get("action") == expected_action
    )


def admin_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        member = current_member()
        if member is None or member["role"] not in ADMIN_ROLES:
            return redirect(url_for("account_login", next=request.path))
        if member["must_change_password"]:
            flash_t("temporary_password_required", "error")
            return redirect(url_for("account_change_password"))
        return view(*args, **kwargs)

    return wrapped


def account_admin_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        member = current_member()
        if member is None:
            return redirect(url_for("account_login", next=request.path))
        if member["role"] not in {"admin", "super_admin"}:
            abort(403)
        if member["must_change_password"]:
            flash_t("temporary_password_required", "error")
            return redirect(url_for("account_change_password"))
        return view(*args, **kwargs)

    return wrapped


def super_admin_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        member = current_member()
        if member is None:
            return redirect(url_for("account_login", next=request.path))
        if member["role"] != "super_admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def member_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        member = current_member()
        if member is None:
            return redirect(url_for("account_login", next=request.path))
        if (
            member["must_change_password"]
            and request.endpoint not in {"account_change_password", "account_logout"}
        ):
            flash_t("temporary_password_required", "error")
            return redirect(url_for("account_change_password"))
        return view(*args, **kwargs)

    return wrapped


def organizer_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        member = current_member()
        if member is None:
            return redirect(url_for("account_login", next=request.path))
        if member["must_change_password"]:
            flash_t("temporary_password_required", "error")
            return redirect(url_for("account_change_password"))
        return view(*args, **kwargs)

    return wrapped


def current_member() -> sqlite3.Row | None:
    api_request = api_request_active()
    # API requests never fall back to the session cookie, so cross-site
    # requests cannot ride a browser session without a CSRF token.
    user_id = g.get("api_user_id") if api_request else session.get("user_id")
    if not user_id:
        return None
    user = get_db().execute(
        "SELECT id, username, created_at, avatar_filename, time_format, last_login_at, "
        "archived, banned, must_change_password, role "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if api_request:
        if user is None or user["archived"] or user["banned"]:
            return None
        return user
    if user is None or user["archived"] or user["banned"]:
        session.pop("user_id", None)
        session.pop("user_username", None)
        session.pop("admin", None)
        return None
    if user["role"] in ADMIN_ROLES:
        session["admin"] = True
    else:
        session.pop("admin", None)
    return user


def current_user_is_admin() -> bool:
    member = current_member()
    return bool(member and member["role"] in ADMIN_ROLES)


def court_query() -> str:
    return f"""
        SELECT c.*,
               COALESCE(NULLIF(c.creator_name, ''), u.username)
                   AS creator_username,
               CASE WHEN {COURT_EXPIRED_SQL}
                    THEN 1 ELSE 0 END AS is_expired,
               CASE WHEN {LEAVE_DEADLINE_PASSED_SQL}
                    THEN 1 ELSE 0 END AS leave_deadline_passed,
               (SELECT COUNT(*) FROM participants p
                WHERE p.court_id = c.id AND p.waitlisted = 0)
                   AS online_count,
               (SELECT COUNT(*) FROM participants p
                WHERE p.court_id = c.id AND p.waitlisted = 1)
                   AS waiting_count,
               (SELECT cm.filename FROM court_media cm
                WHERE cm.court_id = c.id AND cm.media_type = 'image'
                ORDER BY cm.position, cm.id LIMIT 1)
                   AS cover_image,
               c.ordered_count +
               (SELECT COUNT(*) FROM participants p
                WHERE p.court_id = c.id AND p.waitlisted = 0)
                   AS total_count
        FROM courts c
        LEFT JOIN users u ON u.id = c.owner_id
    """


def spreadsheet_safe_csv_text(value: Any) -> str:
    text = "" if value is None else str(value)
    candidate = text.lstrip()
    if candidate.startswith(("=", "+", "-", "@")) or text.startswith(
        ("\t", "\r", "\n")
    ):
        return "'" + text
    return text


def court_csv_status(court: sqlite3.Row) -> str:
    if court["archived"]:
        return "archived"
    if court["is_expired"]:
        return "expired"
    if court["roll_clearing_locked"]:
        return "read_only"
    if court["total_count"] >= court["member_max"]:
        return "full"
    return "open"


def render_all_courts_csv() -> bytes:
    db = get_db()
    courts = db.execute(
        court_query()
        + " ORDER BY c.court_date DESC, c.start_time DESC, c.id DESC"
    ).fetchall()
    reserved_by_court: dict[int, list[str]] = {}
    for row in db.execute(
        "SELECT court_id, position, nickname FROM reserved_members "
        "ORDER BY court_id, position"
    ).fetchall():
        reserved_by_court.setdefault(row["court_id"], []).append(row["nickname"])
    media_counts = {
        row["court_id"]: row["media_count"]
        for row in db.execute(
            "SELECT court_id, COUNT(*) AS media_count FROM court_media "
            "GROUP BY court_id"
        ).fetchall()
    }

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(
        (
            "guid",
            "public_url",
            "event_name",
            "badminton_name",
            "court_date",
            "start_time",
            "end_time",
            "hall_name",
            "location",
            "google_place_id",
            "latitude",
            "longitude",
            "court_id",
            "creator_username",
            "created_at",
            "status",
            "archived",
            "expired",
            "roll_clearing_locked",
            "leave_deadline_enabled",
            "leave_deadline_at",
            "member_min",
            "member_max",
            "reserved_count",
            "reserved_names_visible",
            "reserved_nicknames",
            "confirmed_signup_count",
            "waiting_count",
            "total_confirmed_count",
            "male_level_min",
            "male_level_max",
            "female_level_min",
            "female_level_max",
            "male_price",
            "female_price",
            "shuttlecock_info",
            "remark",
            "media_count",
        )
    )
    for court in courts:
        writer.writerow(
            (
                court["guid"],
                url_for("court_detail", guid=court["guid"], _external=True),
                spreadsheet_safe_csv_text(court["event_name"]),
                spreadsheet_safe_csv_text(court["badminton_name"]),
                court["court_date"],
                court["start_time"],
                court["end_time"],
                spreadsheet_safe_csv_text(court["hall_name"]),
                spreadsheet_safe_csv_text(court["location"]),
                spreadsheet_safe_csv_text(court["google_place_id"]),
                court["latitude"] if court["latitude"] is not None else "",
                court["longitude"] if court["longitude"] is not None else "",
                spreadsheet_safe_csv_text(court["court_id"]),
                spreadsheet_safe_csv_text(court["creator_username"]),
                court["created_at"],
                court_csv_status(court),
                court["archived"],
                court["is_expired"],
                court["roll_clearing_locked"],
                court["leave_deadline_enabled"],
                court["leave_deadline_at"],
                court["member_min"],
                court["member_max"],
                court["ordered_count"],
                court["reserved_names_visible"],
                json.dumps(
                    reserved_by_court.get(court["id"], []),
                    ensure_ascii=False,
                ),
                court["online_count"],
                court["waiting_count"],
                court["total_count"],
                court["male_level_min"],
                court["male_level_max"],
                court["female_level_min"],
                court["female_level_max"],
                court["male_price"],
                court["female_price"],
                spreadsheet_safe_csv_text(court["shuttlecock_info"]),
                spreadsheet_safe_csv_text(court["remark"]),
                media_counts.get(court["id"], 0),
            )
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def fetch_court(guid: str) -> sqlite3.Row | None:
    return get_db().execute(
        court_query() + " WHERE c.guid = ?", (guid,)
    ).fetchone()


def fetch_owned_court(guid: str, owner_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        court_query() + " WHERE c.guid = ? AND c.owner_id = ?",
        (guid, owner_id),
    ).fetchone()


def fetch_managed_court(guid: str) -> sqlite3.Row:
    court = fetch_court(guid)
    if court is None:
        abort(404)
    if current_user_is_admin():
        return court
    member = current_member()
    if member is None or court["owner_id"] != member["id"]:
        abort(404)
    return court


def clean_username(value: str) -> str:
    return " ".join(value.strip().split())


def detect_image_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def detect_court_media(data: bytes) -> tuple[str, str, str] | None:
    image_extension = detect_image_extension(data)
    if image_extension:
        image_mimes = {
            "jpg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        return "image", image_extension, image_mimes[image_extension]
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "video", "mp4", "video/mp4"
    if data.startswith(b"\x1aE\xdf\xa3"):
        return "video", "webm", "video/webm"
    return None


def validate_court_media_uploads(
    uploads: list[Any],
    existing_count: int,
    errors: dict[str, str],
) -> list[dict[str, Any]]:
    files = [upload for upload in uploads if upload and upload.filename]
    if existing_count + len(files) > MAX_COURT_MEDIA_FILES:
        errors["media"] = "media_too_many"
        return []

    validated: list[dict[str, Any]] = []
    for upload in files:
        data = upload.stream.read(MAX_COURT_VIDEO_BYTES + 1)
        detected = detect_court_media(data)
        if detected is None:
            errors["media"] = "media_invalid"
            return []
        media_type, extension, mime_type = detected
        limit = (
            MAX_COURT_IMAGE_BYTES
            if media_type == "image"
            else MAX_COURT_VIDEO_BYTES
        )
        if len(data) > limit:
            errors["media"] = "media_too_large"
            return []
        original_name = Path(upload.filename).name
        original_name = "".join(
            character for character in original_name if character.isprintable()
        )[:255]
        validated.append(
            {
                "data": data,
                "extension": extension,
                "media_type": media_type,
                "mime_type": mime_type,
                "original_name": original_name,
            }
        )
    return validated


def fetch_court_media(court_id: int) -> list[sqlite3.Row]:
    return get_db().execute(
        "SELECT id, filename, original_name, media_type, mime_type, position "
        "FROM court_media WHERE court_id = ? ORDER BY position, id",
        (court_id,),
    ).fetchall()


def fetch_first_court_media(court_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT id, filename, original_name, media_type, mime_type, position "
        "FROM court_media WHERE court_id = ? ORDER BY position, id LIMIT 1",
        (court_id,),
    ).fetchone()


def court_social_thumbnail_cache_key(guid: str) -> str:
    return hashlib.sha256(guid.encode("utf-8")).hexdigest()[:32]


def court_social_thumbnail_version(
    court: sqlite3.Row, first_media: sqlite3.Row | None
) -> str:
    court_fields = (
        "event_name",
        "badminton_name",
        "court_date",
        "start_time",
        "end_time",
        "hall_name",
        "location",
        "court_id",
        "total_count",
        "member_max",
        "archived",
        "is_expired",
    )
    media_fields = ("id", "filename", "media_type", "mime_type", "position")
    fingerprint = {
        "renderer": SOCIAL_THUMBNAIL_RENDER_VERSION,
        "court": {field: court[field] for field in court_fields},
        "media": (
            {field: first_media[field] for field in media_fields}
            if first_media is not None
            else None
        ),
    }
    serialized = json.dumps(
        fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def court_social_metadata(
    court: sqlite3.Row, first_media: sqlite3.Row | None
) -> dict[str, str]:
    lang = current_language()
    translations = TRANSLATIONS[lang]
    title = court["event_name"] or court["hall_name"]
    date_text = str(court["court_date"]).replace("-", "/")
    time_text = f"{court['start_time']}–{court['end_time']}"
    description = " · ".join(
        (
            f"{date_text} {time_text}",
            court["hall_name"],
            court["location"],
            f"{translations['members']} {court['total_count']}/{court['member_max']}",
        )
    )
    version = court_social_thumbnail_version(court, first_media)
    return {
        "title": title,
        "description": description,
        "url": public_external_url("court_detail", guid=court["guid"]),
        "image_url": public_external_url(
            "court_social_thumbnail",
            guid=court["guid"],
            version=version,
            lang=lang,
        ),
        "image_alt": f"{title} · {translations['event_information']}",
        "locale": "zh_TW" if lang == "zh-tw" else "en_US",
        "alternate_locale": "en_US" if lang == "zh-tw" else "zh_TW",
    }


def render_court_social_thumbnail(
    court: sqlite3.Row,
    first_media: sqlite3.Row | None,
    lang: str,
) -> bytes:
    thumbnail: Image.Image | None = None
    if first_media is not None:
        try:
            thumbnail = render_court_media_social_thumbnail(first_media)
        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
            subprocess.SubprocessError,
        ) as error:
            current_app.logger.warning(
                "Unable to create social thumbnail from court media %s (%s)",
                first_media["id"],
                type(error).__name__,
            )
    if thumbnail is None:
        thumbnail = render_court_information_social_thumbnail(court, lang)

    output = io.BytesIO()
    thumbnail.save(
        output,
        format="JPEG",
        quality=88,
        optimize=True,
        progressive=True,
    )
    return output.getvalue()


def cached_court_social_thumbnail(
    court: sqlite3.Row,
    first_media: sqlite3.Row | None,
    version: str,
    lang: str,
) -> tuple[Path, str]:
    cache_key = court_social_thumbnail_cache_key(court["guid"])
    filename = f"{cache_key}-{version}-{lang}.jpg"
    thumbnail_folder = Path(current_app_config("SOCIAL_THUMBNAIL_FOLDER"))
    thumbnail_path = thumbnail_folder / filename
    if not thumbnail_path.is_file():
        thumbnail_data = render_court_social_thumbnail(
            court, first_media, lang
        )
        temporary_path = thumbnail_folder / (
            f".{filename}.{secrets.token_hex(8)}.tmp"
        )
        try:
            temporary_path.write_bytes(thumbnail_data)
            os.replace(temporary_path, thumbnail_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        remove_stale_court_social_thumbnails(cache_key, version)
    return thumbnail_folder, filename


def render_court_media_social_thumbnail(media: sqlite3.Row) -> Image.Image:
    media_path = (
        Path(current_app_config("COURT_MEDIA_FOLDER")) / media["filename"]
    )
    if media["media_type"] == "video":
        configured_ffmpeg = str(
            current_app_config("SOCIAL_THUMBNAIL_FFMPEG")
        ).strip()
        result = subprocess.run(
            [
                configured_ffmpeg or get_ffmpeg_exe(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(media_path),
                "-an",
                "-sn",
                "-dn",
                "-vf",
                (
                    "thumbnail=30,"
                    f"scale={SOCIAL_THUMBNAIL_WIDTH}:"
                    f"{SOCIAL_THUMBNAIL_HEIGHT}:"
                    "force_original_aspect_ratio=increase,"
                    f"crop={SOCIAL_THUMBNAIL_WIDTH}:"
                    f"{SOCIAL_THUMBNAIL_HEIGHT}"
                ),
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "pipe:1",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=12,
        )
        if not result.stdout or len(result.stdout) > 16 * 1024 * 1024:
            raise ValueError("Invalid video thumbnail output")
        source: str | io.BytesIO = io.BytesIO(result.stdout)
    else:
        source = str(media_path)

    with Image.open(source) as opened_image:
        if (
            opened_image.width * opened_image.height
            > SOCIAL_THUMBNAIL_MAX_SOURCE_PIXELS
        ):
            raise ValueError("Court media dimensions are too large")
        image = ImageOps.exif_transpose(opened_image).convert("RGB")
        return ImageOps.fit(
            image,
            (SOCIAL_THUMBNAIL_WIDTH, SOCIAL_THUMBNAIL_HEIGHT),
            method=Image.Resampling.LANCZOS,
        )


def social_thumbnail_font(
    size: int, *, bold: bool = False
) -> ImageFont.FreeTypeFont:
    configured_font = str(current_app_config("SOCIAL_THUMBNAIL_FONT")).strip()
    bundled_font = (
        Path(__file__).with_name("static")
        / "fonts"
        / "NotoSansTC-VF.ttf"
    )
    candidates = [
        configured_font,
        str(bundled_font),
        (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
            if bold
            else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        ),
        (
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
            if bold
            else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            font = ImageFont.truetype(candidate, size=size)
            try:
                variation_values = []
                for axis in font.get_variation_axes():
                    axis_name = axis.get("name", b"")
                    if isinstance(axis_name, bytes):
                        axis_name = axis_name.decode("ascii", errors="ignore")
                    if axis_name.lower() == "weight":
                        variation_values.append(700 if bold else 400)
                    else:
                        variation_values.append(axis["default"])
                if variation_values:
                    font.set_variation_by_axes(variation_values)
            except (AttributeError, OSError, ValueError):
                pass
            return font
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_social_thumbnail_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    normalized = " ".join(str(text).split())
    if not normalized:
        return []
    lines: list[str] = []
    current = ""
    consumed = 0
    for index, character in enumerate(normalized):
        candidate = current + character
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if current and width > max_width:
            lines.append(current.rstrip())
            consumed = index
            current = character.lstrip()
            if len(lines) == max_lines:
                break
        else:
            current = candidate
        consumed = index + 1
    if len(lines) < max_lines and current:
        lines.append(current.rstrip())
    if consumed < len(normalized) and lines:
        last_line = lines[-1].rstrip()
        while last_line:
            candidate = last_line.rstrip() + "…"
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                lines[-1] = candidate
                break
            last_line = last_line[:-1]
    return lines


def render_court_information_social_thumbnail(
    court: sqlite3.Row, lang: str
) -> Image.Image:
    translations = TRANSLATIONS[lang]
    image = Image.new(
        "RGB",
        (SOCIAL_THUMBNAIL_WIDTH, SOCIAL_THUMBNAIL_HEIGHT),
        "#f7f3e8",
    )
    draw = ImageDraw.Draw(image)
    accent = "#f2c94c"
    ink = "#171717"
    muted = "#605d55"
    white = "#ffffff"

    draw.rounded_rectangle((28, 28, 1172, 602), radius=34, fill=white)
    draw.rounded_rectangle((28, 28, 54, 602), radius=13, fill=accent)
    draw.ellipse((965, -120, 1265, 180), fill="#fbefd0")
    draw.rounded_rectangle(
        (900, 75, 1110, 315), radius=22, outline="#eadfbf", width=7
    )
    draw.line((1005, 75, 1005, 315), fill="#eadfbf", width=5)
    draw.line((900, 195, 1110, 195), fill="#eadfbf", width=5)
    draw.ellipse((980, 170, 1030, 220), outline=accent, width=6)

    brand_font = social_thumbnail_font(26, bold=True)
    title_font = social_thumbnail_font(62, bold=True)
    subtitle_font = social_thumbnail_font(30)
    label_font = social_thumbnail_font(22, bold=True)
    value_font = social_thumbnail_font(30, bold=True)

    brand = translations["brand"].upper()
    draw.text((82, 64), brand, font=brand_font, fill=muted)
    title = court["event_name"] or court["hall_name"]
    title_lines = wrap_social_thumbnail_text(
        draw, title, title_font, 790, 2
    )
    for line_index, line in enumerate(title_lines):
        draw.text(
            (78, 122 + line_index * 76),
            line,
            font=title_font,
            fill=ink,
        )

    subtitle_parts = []
    if court["event_name"]:
        subtitle_parts.append(court["hall_name"])
    if court["badminton_name"]:
        subtitle_parts.append(court["badminton_name"])
    subtitle = " · ".join(subtitle_parts) or court["location"]
    subtitle_line = wrap_social_thumbnail_text(
        draw, subtitle, subtitle_font, 970, 1
    )
    if subtitle_line:
        draw.text((82, 292), subtitle_line[0], font=subtitle_font, fill=muted)
    location_line = wrap_social_thumbnail_text(
        draw, court["location"], subtitle_font, 970, 1
    )
    if location_line and court["location"] != subtitle:
        draw.text((82, 340), location_line[0], font=subtitle_font, fill=muted)

    labels = (
        translations["date"],
        translations["time"],
        translations["court_id"],
        translations["members"],
    )
    values = (
        str(court["court_date"]).replace("-", "/"),
        f"{court['start_time']}–{court['end_time']}",
        str(court["court_id"]),
        f"{court['total_count']} / {court['member_max']}",
    )
    left_positions = (82, 358, 654, 900)
    widths = (240, 260, 210, 210)
    for left, column_width, label, value in zip(
        left_positions, widths, labels, values
    ):
        draw.text((left, 458), label, font=label_font, fill=muted)
        value_line = wrap_social_thumbnail_text(
            draw, value, value_font, column_width, 1
        )
        if value_line:
            draw.text((left, 500), value_line[0], font=value_font, fill=ink)

    draw.rounded_rectangle((82, 558, 235, 570), radius=6, fill=accent)
    return image


def remove_stale_court_social_thumbnails(
    cache_key: str, current_version: str
) -> None:
    thumbnail_folder = Path(current_app_config("SOCIAL_THUMBNAIL_FOLDER"))
    current_prefix = f"{cache_key}-{current_version}-"
    for thumbnail_path in thumbnail_folder.glob(f"{cache_key}-*.jpg"):
        if not thumbnail_path.name.startswith(current_prefix):
            thumbnail_path.unlink(missing_ok=True)


def remove_court_social_thumbnails(guid: str) -> None:
    thumbnail_folder = Path(current_app_config("SOCIAL_THUMBNAIL_FOLDER"))
    cache_key = court_social_thumbnail_cache_key(guid)
    for thumbnail_path in thumbnail_folder.glob(f"{cache_key}-*.jpg"):
        thumbnail_path.unlink(missing_ok=True)


def store_court_media(
    db: sqlite3.Connection,
    court_id: int,
    uploads: list[dict[str, Any]],
    start_position: int,
) -> list[str]:
    stored_filenames: list[str] = []
    try:
        for offset, upload in enumerate(uploads):
            filename = f"{secrets.token_hex(16)}.{upload['extension']}"
            media_path = Path(current_app_config("COURT_MEDIA_FOLDER")) / filename
            media_path.write_bytes(upload["data"])
            stored_filenames.append(filename)
            db.execute(
                "INSERT INTO court_media "
                "(court_id, filename, original_name, media_type, mime_type, "
                "position, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    court_id,
                    filename,
                    upload["original_name"],
                    upload["media_type"],
                    upload["mime_type"],
                    start_position + offset,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
    except Exception:
        remove_court_media_files(stored_filenames)
        raise
    return stored_filenames


def remove_court_media_files(filenames: list[str]) -> None:
    media_folder = Path(current_app_config("COURT_MEDIA_FOLDER"))
    for filename in filenames:
        if filename and COURT_MEDIA_FILENAME_PATTERN.fullmatch(filename):
            (media_folder / filename).unlink(missing_ok=True)


PUSH_BODY_KEYS = {
    "updated": "push_event_updated_body",
    "archived": "push_event_archived_body",
    "restored": "push_event_restored_body",
    "roll_started": "push_event_roll_started_body",
    "editing_restored": "push_event_editing_restored_body",
    "deleted": "push_event_deleted_body",
    "members_changed": "push_members_changed_body",
}


def fetch_court_push_subscriptions(court_id: int) -> list[sqlite3.Row]:
    if not web_push_enabled():
        return []
    return get_db().execute(
        "SELECT id, endpoint, p256dh, auth, language "
        "FROM push_subscriptions WHERE court_id = ? ORDER BY id",
        (court_id,),
    ).fetchall()


def fetch_court_fcm_subscriptions(court_id: int) -> list[sqlite3.Row]:
    if not fcm_enabled():
        return []
    return get_db().execute(
        "SELECT id, token, language "
        "FROM fcm_subscriptions WHERE court_id = ? ORDER BY id",
        (court_id,),
    ).fetchall()


def fetch_court_owner_fcm_targets(court: sqlite3.Row) -> list[sqlite3.Row]:
    """The organizer's signed-in Android devices, when they want court alerts.

    Changes the organizer makes themselves are skipped: they already know.
    """
    if not fcm_enabled() or not court["owner_id"] or not court["owner_notifications"]:
        return []
    actor = current_member()
    if actor is not None and actor["id"] == court["owner_id"]:
        return []
    return get_db().execute(
        """
        SELECT MIN(t.id) AS id, t.fcm_token AS token,
               MAX(t.fcm_language) AS language
        FROM api_tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.user_id = ? AND t.fcm_token IS NOT NULL AND t.fcm_token != ''
          AND t.expires_at > ? AND u.archived = 0 AND u.banned = 0
        GROUP BY t.fcm_token
        ORDER BY MIN(t.id)
        """,
        (court["owner_id"], datetime.now().isoformat(timespec="seconds")),
    ).fetchall()


def send_court_push_notifications(guid: str, change_type: str) -> None:
    if not (web_push_enabled() or fcm_enabled()):
        return
    court = get_db().execute(
        "SELECT id, guid, event_name, hall_name, owner_id, owner_notifications "
        "FROM courts WHERE guid = ?",
        (guid,),
    ).fetchone()
    if court is None:
        return
    court_name = court["event_name"] or court["hall_name"]
    deliver_court_push_notifications(
        guid=court["guid"],
        court_name=court_name,
        change_type=change_type,
        subscriptions=fetch_court_push_subscriptions(court["id"]),
    )
    deliver_court_fcm_notifications(
        guid=court["guid"],
        court_name=court_name,
        change_type=change_type,
        subscriptions=fetch_court_fcm_subscriptions(court["id"]),
        owner_targets=fetch_court_owner_fcm_targets(court),
    )


def deliver_court_push_notifications(
    *,
    guid: str,
    court_name: str,
    change_type: str,
    subscriptions: list[sqlite3.Row],
) -> None:
    if not web_push_enabled() or not subscriptions:
        return
    body_key = PUSH_BODY_KEYS.get(change_type, "push_event_updated_body")
    stale_subscription_ids: list[int] = []
    target_url = url_for("court_detail", guid=guid, _external=True)
    icon_url = url_for(
        "static", filename="shuttlecock.png", _external=True
    )
    for subscription in subscriptions:
        language = (
            subscription["language"]
            if subscription["language"] in LANGUAGES
            else "en-us"
        )
        translations = TRANSLATIONS[language]
        payload = json.dumps(
            {
                "title": translations["push_event_updated_title"].format(
                    name=court_name
                ),
                "body": translations[body_key],
                "icon": icon_url,
                "tag": f"court-{guid}",
                "url": target_url,
            },
            ensure_ascii=False,
        )
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription["endpoint"],
                    "keys": {
                        "p256dh": subscription["p256dh"],
                        "auth": subscription["auth"],
                    },
                },
                data=payload,
                vapid_private_key=current_app.config["WEB_PUSH_PRIVATE_KEY"],
                vapid_claims={"sub": current_app.config["WEB_PUSH_SUBJECT"]},
                ttl=86_400,
                timeout=float(current_app.config["WEB_PUSH_TIMEOUT"]),
            )
        except WebPushException as error:
            status_code = getattr(error.response, "status_code", None)
            if status_code in {404, 410}:
                stale_subscription_ids.append(subscription["id"])
            current_app.logger.warning(
                "Web Push delivery failed for subscription %s (status %s)",
                subscription["id"],
                status_code or "unknown",
            )
        except Exception as error:
            current_app.logger.warning(
                "Web Push delivery failed for subscription %s (%s)",
                subscription["id"],
                type(error).__name__,
            )
    if stale_subscription_ids:
        db = get_db()
        placeholders = ",".join("?" for _ in stale_subscription_ids)
        db.execute(
            f"DELETE FROM push_subscriptions WHERE id IN ({placeholders})",
            stale_subscription_ids,
        )
        db.commit()


def deliver_court_fcm_notifications(
    *,
    guid: str,
    court_name: str,
    change_type: str,
    subscriptions: list[sqlite3.Row],
    owner_targets: list[sqlite3.Row] | None = None,
) -> None:
    client = fcm_client()
    owner_targets = owner_targets or []
    if client is None or not (subscriptions or owner_targets):
        return
    body_key = PUSH_BODY_KEYS.get(change_type, "push_event_updated_body")
    target_url = url_for("court_detail", guid=guid, _external=True)
    # A device subscribed to the court that is also the organizer's gets one
    # notification, worded for the organizer.
    owner_tokens = {target["token"] for target in owner_targets}
    recipients = [
        ("subscription", row, "push_event_updated_title")
        for row in subscriptions
        if row["token"] not in owner_tokens
    ] + [("owner", row, "push_owner_title") for row in owner_targets]
    stale_subscription_ids: list[int] = []
    stale_owner_tokens: list[str] = []
    for kind, recipient, title_key in recipients:
        language = (
            recipient["language"]
            if recipient["language"] in LANGUAGES
            else "en-us"
        )
        translations = TRANSLATIONS[language]
        try:
            client.send(
                recipient["token"],
                {
                    "type": "court_changed",
                    "guid": guid,
                    "change": change_type,
                    "audience": kind,
                    "title": translations[title_key].format(name=court_name),
                    "body": translations[body_key],
                    "url": target_url,
                },
                collapse_key=f"court-{guid}",
            )
        except FcmError as error:
            if error.stale_token:
                if kind == "owner":
                    stale_owner_tokens.append(recipient["token"])
                else:
                    stale_subscription_ids.append(recipient["id"])
            current_app.logger.warning(
                "FCM delivery failed for %s %s (%s %s)",
                kind,
                recipient["id"],
                error.status,
                error.code,
            )
        except Exception as error:
            current_app.logger.warning(
                "FCM delivery failed for %s %s (%s)",
                kind,
                recipient["id"],
                type(error).__name__,
            )
    if stale_subscription_ids or stale_owner_tokens:
        db = get_db()
        if stale_subscription_ids:
            placeholders = ",".join("?" for _ in stale_subscription_ids)
            db.execute(
                f"DELETE FROM fcm_subscriptions WHERE id IN ({placeholders})",
                stale_subscription_ids,
            )
        if stale_owner_tokens:
            placeholders = ",".join("?" for _ in stale_owner_tokens)
            db.execute(
                "UPDATE api_tokens SET fcm_token = NULL "
                f"WHERE fcm_token IN ({placeholders})",
                stale_owner_tokens,
            )
        db.commit()


def delete_court_record(guid: str, owner_id: int | None = None) -> bool:
    db = get_db()
    parameters: tuple[Any, ...] = (
        (guid, owner_id) if owner_id is not None else (guid,)
    )
    ownership_clause = " AND owner_id = ?" if owner_id is not None else ""
    court = db.execute(
        "SELECT id, guid, event_name, hall_name, owner_id, owner_notifications "
        f"FROM courts WHERE guid = ?{ownership_clause}",
        parameters,
    ).fetchone()
    if court is None:
        db.rollback()
        return False
    media = db.execute(
        "SELECT filename FROM court_media WHERE court_id = ?",
        (court["id"],),
    ).fetchall()
    subscriptions = fetch_court_push_subscriptions(court["id"])
    fcm_subscriptions = fetch_court_fcm_subscriptions(court["id"])
    owner_targets = fetch_court_owner_fcm_targets(court)
    result = db.execute(
        "DELETE FROM courts WHERE id = ?",
        (court["id"],),
    )
    if result.rowcount == 0:
        db.rollback()
        return False
    db.commit()
    remove_court_media_files([item["filename"] for item in media])
    remove_court_social_thumbnails(court["guid"])
    deliver_court_push_notifications(
        guid=court["guid"],
        court_name=court["event_name"] or court["hall_name"],
        change_type="deleted",
        subscriptions=subscriptions,
    )
    deliver_court_fcm_notifications(
        guid=court["guid"],
        court_name=court["event_name"] or court["hall_name"],
        change_type="deleted",
        subscriptions=fcm_subscriptions,
        owner_targets=owner_targets,
    )
    return True


def remove_avatar_file(filename: str) -> None:
    if not filename or not AVATAR_FILENAME_PATTERN.fullmatch(filename):
        return
    avatar_path = Path(current_app_config("AVATAR_FOLDER")) / filename
    avatar_path.unlink(missing_ok=True)


def default_court_values() -> dict[str, str]:
    return {
        "event_name": "",
        "badminton_name": "",
        "court_date": date.today().isoformat(),
        "start_time": "19:00",
        "end_time": "21:00",
        "hall_name": "",
        "location": "",
        "google_place_id": "",
        "latitude": "",
        "longitude": "",
        "remark": "",
        "court_id": "",
        "male_price": "0",
        "female_price": "0",
        "shuttlecock_info": "",
        "reserved_names_visible": "1",
        "leave_deadline_enabled": "0",
        "leave_deadline_at": "",
        "member_min": "4",
        "member_max": "8",
        "ordered_count": "0",
        "male_level_min": "1",
        "male_level_max": "18",
        "female_level_min": "1",
        "female_level_max": "18",
    }


def submitted_court_values(field_names: Any) -> dict[str, str]:
    values = {
        field: request.form.get(field, "").strip() for field in field_names
    }
    deadline_date = request.form.get("leave_deadline_date")
    deadline_time = request.form.get("leave_deadline_time")
    if deadline_date is not None or deadline_time is not None:
        values["leave_deadline_at"] = (
            f"{(deadline_date or '').strip()}T{(deadline_time or '').strip()}"
        )
    return values


def court_form_values(court: sqlite3.Row) -> dict[str, str]:
    return {
        field: "" if court[field] is None else str(court[field])
        for field in default_court_values()
    }


def court_info_export_filename(court: Any) -> str:
    court_date = str(court["court_date"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", court_date):
        court_date = "0000-00-00"

    def compact_time(value: Any) -> str:
        time_value = str(value)
        return time_value.replace(":", "") if TIME_PATTERN.fullmatch(time_value) else "0000"

    name = str(court["event_name"] or court["hall_name"] or "court")
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]+', "_", name)
    name = " ".join(name.split()).strip(" ._")
    name = name[:100].rstrip(" ._") or "court"
    return (
        f"{court_date}_{compact_time(court['start_time'])}_"
        f"{compact_time(court['end_time'])}_{name}.md"
    )


def court_thumbnail_download_filename(court: Any) -> str:
    export_filename = court_info_export_filename(court)
    return f"{export_filename.removesuffix('.md')}.jpg"


def render_court_info_markdown(court: sqlite3.Row) -> str:
    payload = {
        "format": COURT_INFO_FORMAT,
        "version": COURT_INFO_VERSION,
        "court": court_form_values(court),
        "reserved_nicknames": reserved_nickname_values(
            court["id"], court["ordered_count"]
        ),
    }
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "# Court information / 場次資訊\n\n"
        "Import this file from the new-court form to prefill another event. "
        "You may edit values inside the JSON block before importing.\n\n"
        "請在新增場次表單匯入此檔案，以預先填入另一個場次；匯入前也可編輯 "
        "JSON 區塊中的內容。\n\n"
        f"{COURT_INFO_MARKER}\n"
        "```json\n"
        f"{payload_json}\n"
        "```\n"
    )


def parse_court_info_upload(upload: Any) -> tuple[dict[str, str], list[str]]:
    if upload is None or not upload.filename:
        raise ValueError("court_info_invalid")
    data = upload.stream.read(MAX_COURT_INFO_BYTES + 1)
    if len(data) > MAX_COURT_INFO_BYTES:
        raise ValueError("court_info_too_large")
    try:
        markdown = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("court_info_invalid") from error

    marker_position = markdown.find(COURT_INFO_MARKER)
    if marker_position < 0:
        raise ValueError("court_info_invalid")
    encoded_block = markdown[
        marker_position + len(COURT_INFO_MARKER) :
    ].lstrip()
    if not encoded_block.startswith("```json"):
        raise ValueError("court_info_invalid")
    encoded_payload = encoded_block[len("```json") :].lstrip("\r\n")
    try:
        payload, payload_end = json.JSONDecoder().raw_decode(encoded_payload)
    except json.JSONDecodeError as error:
        raise ValueError("court_info_invalid") from error
    if not encoded_payload[payload_end:].lstrip().startswith("```"):
        raise ValueError("court_info_invalid")
    if (
        not isinstance(payload, dict)
        or payload.get("format") != COURT_INFO_FORMAT
        or type(payload.get("version")) is not int
        or payload["version"] != COURT_INFO_VERSION
        or not isinstance(payload.get("court"), dict)
    ):
        raise ValueError("court_info_invalid")

    defaults = default_court_values()
    values: dict[str, str] = {}
    for field, default in defaults.items():
        value = payload["court"].get(field, default)
        if value is None:
            value = ""
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError("court_info_invalid")
        text_value = str(value).strip()
        if "\x00" in text_value:
            raise ValueError("court_info_invalid")
        values[field] = text_value

    reserved_nicknames = payload.get("reserved_nicknames", [])
    if (
        not isinstance(reserved_nicknames, list)
        or len(reserved_nicknames) > 99
        or any(not isinstance(value, str) for value in reserved_nicknames)
        or any("\x00" in value for value in reserved_nicknames)
    ):
        raise ValueError("court_info_invalid")
    return values, reserved_nicknames


def fetch_saved_locations(user_id: int) -> list[sqlite3.Row]:
    return get_db().execute(
        "SELECT * FROM saved_locations WHERE user_id = ? "
        "ORDER BY hall_name COLLATE NOCASE, location COLLATE NOCASE",
        (user_id,),
    ).fetchall()


def save_member_location(user_id: int, cleaned: dict[str, Any]) -> None:
    db = get_db()
    result = db.execute(
        """
        INSERT OR IGNORE INTO saved_locations (
            user_id, hall_name, location, google_place_id,
            latitude, longitude, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            cleaned["hall_name"],
            cleaned["location"],
            cleaned["google_place_id"],
            cleaned["latitude"],
            cleaned["longitude"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    if result.rowcount:
        flash_t("saved_location_added", "success")


def create_court_record(
    cleaned: dict[str, Any],
    owner_id: int | None,
    creator_name: str,
    reserved_nicknames: list[str] | None = None,
    media_uploads: list[dict[str, Any]] | None = None,
) -> str:
    guid = str(uuid.uuid4())
    db = get_db()
    result = db.execute(
        """
        INSERT INTO courts (
            guid, event_name, badminton_name, court_date, start_time, end_time, hall_name,
            location, google_place_id, latitude, longitude, owner_id, creator_name, remark,
            court_id, male_price, female_price, shuttlecock_info,
            reserved_names_visible, leave_deadline_enabled, leave_deadline_at,
            member_min, member_max, ordered_count, male_level_min,
            male_level_max, female_level_min, female_level_max, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            guid,
            cleaned["event_name"],
            cleaned["badminton_name"],
            cleaned["court_date"],
            cleaned["start_time"],
            cleaned["end_time"],
            cleaned["hall_name"],
            cleaned["location"],
            cleaned["google_place_id"],
            cleaned["latitude"],
            cleaned["longitude"],
            owner_id,
            creator_name,
            cleaned["remark"],
            cleaned["court_id"],
            cleaned["male_price"],
            cleaned["female_price"],
            cleaned["shuttlecock_info"],
            cleaned["reserved_names_visible"],
            cleaned["leave_deadline_enabled"],
            cleaned["leave_deadline_at"],
            cleaned["member_min"],
            cleaned["member_max"],
            cleaned["ordered_count"],
            cleaned["male_level_min"],
            cleaned["male_level_max"],
            cleaned["female_level_min"],
            cleaned["female_level_max"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    stored_filenames: list[str] = []
    try:
        sync_reserved_members(db, result.lastrowid, reserved_nicknames or [])
        stored_filenames = store_court_media(
            db, result.lastrowid, media_uploads or [], 0
        )
        db.commit()
    except Exception:
        db.rollback()
        remove_court_media_files(stored_filenames)
        raise
    return guid


def update_court_record(
    guid: str,
    cleaned: dict[str, Any],
    reserved_nicknames: list[str] | None = None,
    media_uploads: list[dict[str, Any]] | None = None,
    remove_media_ids: set[int] | None = None,
) -> None:
    db = get_db()
    court = db.execute("SELECT id FROM courts WHERE guid = ?", (guid,)).fetchone()
    if court is None:
        return
    removable_media: list[sqlite3.Row] = []
    stored_filenames: list[str] = []
    try:
        db.execute(
            """
            UPDATE courts SET
                event_name = ?, badminton_name = ?,
                court_date = ?, start_time = ?, end_time = ?,
                hall_name = ?, location = ?, google_place_id = ?,
                latitude = ?, longitude = ?, remark = ?, court_id = ?,
                male_price = ?, female_price = ?, shuttlecock_info = ?,
                reserved_names_visible = ?, leave_deadline_enabled = ?,
                leave_deadline_at = ?,
                member_min = ?, member_max = ?, ordered_count = ?,
                male_level_min = ?, male_level_max = ?,
                female_level_min = ?, female_level_max = ?
            WHERE guid = ?
            """,
            (
                cleaned["event_name"],
                cleaned["badminton_name"],
                cleaned["court_date"],
                cleaned["start_time"],
                cleaned["end_time"],
                cleaned["hall_name"],
                cleaned["location"],
                cleaned["google_place_id"],
                cleaned["latitude"],
                cleaned["longitude"],
                cleaned["remark"],
                cleaned["court_id"],
                cleaned["male_price"],
                cleaned["female_price"],
                cleaned["shuttlecock_info"],
                cleaned["reserved_names_visible"],
                cleaned["leave_deadline_enabled"],
                cleaned["leave_deadline_at"],
                cleaned["member_min"],
                cleaned["member_max"],
                cleaned["ordered_count"],
                cleaned["male_level_min"],
                cleaned["male_level_max"],
                cleaned["female_level_min"],
                cleaned["female_level_max"],
                guid,
            ),
        )
        selected_ids = remove_media_ids or set()
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            removable_media = db.execute(
                "SELECT id, filename FROM court_media "
                f"WHERE court_id = ? AND id IN ({placeholders})",
                (court["id"], *selected_ids),
            ).fetchall()
            db.executemany(
                "DELETE FROM court_media WHERE id = ? AND court_id = ?",
                [(item["id"], court["id"]) for item in removable_media],
            )
        sync_reserved_members(db, court["id"], reserved_nicknames or [])
        rebalance_participants(db, court["id"])
        next_position = db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_position "
            "FROM court_media WHERE court_id = ?",
            (court["id"],),
        ).fetchone()["next_position"]
        stored_filenames = store_court_media(
            db, court["id"], media_uploads or [], next_position
        )
        db.commit()
    except Exception:
        db.rollback()
        remove_court_media_files(stored_filenames)
        raise
    remove_court_media_files([item["filename"] for item in removable_media])
    send_court_push_notifications(guid, "updated")


def fetch_registered_players(court_id: int) -> list[sqlite3.Row]:
    return get_db().execute(
        "SELECT username, waitlisted, roll_called FROM participants "
        "WHERE court_id = ? ORDER BY waitlisted, joined_at, id",
        (court_id,),
    ).fetchall()


def reserved_nickname_values(court_id: int, ordered_count: int) -> list[str]:
    values = [""] * ordered_count
    for member in get_db().execute(
        "SELECT position, nickname FROM reserved_members "
        "WHERE court_id = ? ORDER BY position",
        (court_id,),
    ).fetchall():
        if 0 <= member["position"] < ordered_count:
            values[member["position"]] = member["nickname"]
    return values


def validate_reserved_nicknames(
    submitted: list[str],
    ordered_count: int | None,
    errors: dict[str, str],
) -> list[str]:
    count = len(submitted) if ordered_count is None else ordered_count
    count = max(0, min(99, count))
    nicknames = [clean_username(value) for value in submitted[:count]]
    nicknames.extend([""] * (count - len(nicknames)))
    if any(len(nickname) > 40 for nickname in nicknames):
        errors["reserved_nicknames"] = "nickname_too_long"
    return nicknames


def sync_reserved_members(
    db: sqlite3.Connection, court_id: int, nicknames: list[str]
) -> None:
    existing_statuses = {
        member["position"]: (member["roll_called"], member["cleared"])
        for member in db.execute(
            "SELECT position, roll_called, cleared FROM reserved_members "
            "WHERE court_id = ?",
            (court_id,),
        ).fetchall()
    }
    db.execute("DELETE FROM reserved_members WHERE court_id = ?", (court_id,))
    db.executemany(
        "INSERT INTO reserved_members "
        "(court_id, position, nickname, roll_called, cleared) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (
                court_id,
                position,
                nickname,
                existing_statuses.get(position, (0, 0))[0],
                existing_statuses.get(position, (0, 0))[1],
            )
            for position, nickname in enumerate(nicknames)
        ],
    )


def rebalance_participants(db: sqlite3.Connection, court_id: int) -> None:
    """Keep the earliest online sign-ups confirmed and queue the remainder."""
    court = db.execute(
        "SELECT member_max, ordered_count FROM courts WHERE id = ?", (court_id,)
    ).fetchone()
    if court is None:
        return
    available_online_places = max(0, court["member_max"] - court["ordered_count"])
    participant_ids = [
        row["id"]
        for row in db.execute(
            "SELECT id FROM participants WHERE court_id = ? ORDER BY joined_at, id",
            (court_id,),
        ).fetchall()
    ]
    for position, participant_id in enumerate(participant_ids):
        db.execute(
            "UPDATE participants SET waitlisted = ? WHERE id = ?",
            (int(position >= available_online_places), participant_id),
        )


def validate_court(values: dict[str, str]) -> tuple[dict[str, Any], dict[str, str]]:
    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = dict(values)

    for field in ("court_date", "start_time", "end_time", "hall_name", "location", "court_id"):
        if not values.get(field):
            errors[field] = "Required"

    try:
        datetime.strptime(values["court_date"], "%Y-%m-%d")
    except (KeyError, ValueError):
        errors["court_date"] = "Use a valid date"

    for field in ("start_time", "end_time"):
        if not TIME_PATTERN.fullmatch(values.get(field, "")):
            errors[field] = "Use 24-hour time"
    if (
        "start_time" not in errors
        and "end_time" not in errors
        and values["end_time"] <= values["start_time"]
    ):
        errors["end_time"] = "End time must be later"

    integer_fields = (
        "member_min",
        "member_max",
        "ordered_count",
        "male_price",
        "female_price",
        "reserved_names_visible",
        "leave_deadline_enabled",
        "male_level_min",
        "male_level_max",
        "female_level_min",
        "female_level_max",
    )
    for field in integer_fields:
        try:
            raw_value = values.get(field, "")
            if field in {"male_price", "female_price"} and not raw_value:
                raw_value = "0"
            if field == "reserved_names_visible" and not raw_value:
                raw_value = "1"
            if field == "leave_deadline_enabled" and not raw_value:
                raw_value = "0"
            cleaned[field] = int(raw_value)
        except (KeyError, TypeError, ValueError):
            errors[field] = "Use a whole number"

    if not errors.keys() & {"member_min", "member_max", "ordered_count"}:
        if not 1 <= cleaned["member_min"] <= 99:
            errors["member_min"] = "Choose 1–99"
        if cleaned["member_max"] < cleaned["member_min"]:
            errors["member_max"] = "Must be at least the minimum"
        elif cleaned["member_max"] > 99:
            errors["member_max"] = "Choose 1–99"
        if not 0 <= cleaned["ordered_count"] <= cleaned["member_max"]:
            errors["ordered_count"] = "Must be between 0 and the maximum"

    for field in ("male_price", "female_price"):
        if field not in errors and cleaned[field] < 0:
            errors[field] = "Must be 0 or more"

    if (
        "reserved_names_visible" not in errors
        and cleaned["reserved_names_visible"] not in {0, 1}
    ):
        errors["reserved_names_visible"] = "Choose show or hide"

    if (
        "leave_deadline_enabled" not in errors
        and cleaned["leave_deadline_enabled"] not in {0, 1}
    ):
        errors["leave_deadline_enabled"] = "Choose enabled or disabled"

    cleaned["leave_deadline_at"] = ""
    if cleaned.get("leave_deadline_enabled") == 1:
        try:
            deadline = datetime.strptime(
                values.get("leave_deadline_at", ""), "%Y-%m-%dT%H:%M"
            )
        except ValueError:
            errors["leave_deadline_at"] = "Use a valid date and time"
        else:
            cleaned["leave_deadline_at"] = deadline.strftime("%Y-%m-%dT%H:%M")

    for gender in ("male", "female"):
        min_key = f"{gender}_level_min"
        max_key = f"{gender}_level_max"
        if min_key not in errors and not 1 <= cleaned[min_key] <= 18:
            errors[min_key] = "Choose 1–18"
        if max_key not in errors and not 1 <= cleaned[max_key] <= 18:
            errors[max_key] = "Choose 1–18"
        if min_key not in errors and max_key not in errors:
            if cleaned[max_key] < cleaned[min_key]:
                errors[max_key] = "Must be at least the minimum"

    for field in ("hall_name", "location", "court_id"):
        if len(values.get(field, "")) > 160:
            errors[field] = "Too long"

    for field in ("event_name", "badminton_name"):
        if len(values.get(field, "")) > 160:
            errors[field] = "Too long"
        cleaned[field] = values.get(field, "")

    if len(values.get("google_place_id", "")) > 255:
        errors["google_place_id"] = "Too long"
    cleaned["google_place_id"] = values.get("google_place_id", "")
    if len(values.get("remark", "")) > 2000:
        errors["remark"] = "Maximum 2,000 characters"
    cleaned["remark"] = values.get("remark", "")
    if len(values.get("shuttlecock_info", "")) > 500:
        errors["shuttlecock_info"] = "Maximum 500 characters"
    cleaned["shuttlecock_info"] = values.get("shuttlecock_info", "")

    for field, lower, upper in (
        ("latitude", -90, 90),
        ("longitude", -180, 180),
    ):
        raw_value = values.get(field, "")
        if not raw_value:
            cleaned[field] = None
            continue
        try:
            cleaned[field] = float(raw_value)
            if not lower <= cleaned[field] <= upper:
                errors[field] = "Invalid coordinate"
        except ValueError:
            errors[field] = "Invalid coordinate"

    return cleaned, errors


# ---------------------------------------------------------------------------
# Shared actions
#
# These functions hold the business rules used by both the HTML views and the
# JSON API (api.py). They raise CourtActionError instead of flashing or
# redirecting so each caller can present the failure in its own format.
# ---------------------------------------------------------------------------

API_ERROR_MESSAGES = {
    "not_found": {
        "en-us": "The requested resource was not found.",
        "zh-tw": "找不到要求的資源。",
    },
    "unauthorized": {
        "en-us": "Sign in to continue.",
        "zh-tw": "請先登入後再繼續。",
    },
    "invalid_token": {
        "en-us": "The access token is invalid or has expired.",
        "zh-tw": "存取權杖無效或已過期。",
    },
    "forbidden": {
        "en-us": "You do not have permission to do this.",
        "zh-tw": "你沒有執行此操作的權限。",
    },
    "bad_request": {
        "en-us": "The request could not be understood.",
        "zh-tw": "無法解析此要求。",
    },
    "method_not_allowed": {
        "en-us": "This method is not allowed for the endpoint.",
        "zh-tw": "此端點不允許使用這個方法。",
    },
    "payload_too_large": {
        "en-us": "The request body is too large.",
        "zh-tw": "要求內容過大。",
    },
    "conflict": {
        "en-us": "The request conflicts with the current state.",
        "zh-tw": "此要求與目前狀態衝突。",
    },
    "server_error": {
        "en-us": "An unexpected server error occurred.",
        "zh-tw": "伺服器發生未預期的錯誤。",
    },
    "court_not_read_only": {
        "en-us": "Start roll call and clearing before saving member statuses.",
        "zh-tw": "請先開始點名與結帳，再儲存成員狀態。",
    },
    "participant_not_found": {
        "en-us": "That participant is not part of this event.",
        "zh-tw": "此參與者不屬於這個場次。",
    },
    "unknown_member": {
        "en-us": "One or more member IDs do not belong to this event.",
        "zh-tw": "有成員編號不屬於這個場次。",
    },
    "media_not_found": {
        "en-us": "That media file is not attached to this event.",
        "zh-tw": "此媒體檔案不屬於這個場次。",
    },
    "user_not_found": {
        "en-us": "That account does not exist.",
        "zh-tw": "找不到此帳號。",
    },
    "message_not_found": {
        "en-us": "That message does not exist.",
        "zh-tw": "找不到此訊息。",
    },
    "push_unavailable": {
        "en-us": "Push notifications are not configured on this server.",
        "zh-tw": "此伺服器尚未設定推播通知。",
    },
}


def build_court_filters(
    args: Any, *, admin: bool = False
) -> tuple[list[str], list[Any], dict[str, Any]]:
    """Translate list filters into SQL clauses shared by pages and the API."""
    search = args.get("q", "").strip()[:100]
    legacy_date = "" if admin else args.get("date", "").strip()
    date_from = args.get("date_from", "").strip() or legacy_date
    date_to = args.get("date_to", "").strip() or legacy_date
    level_value = args.get("level", "").strip()
    gender = args.get("gender", "both").strip()
    status = args.get("status", "").strip()
    show_expired = args.get("show_expired", "") == "1"
    clauses: list[str] = [] if admin else ["c.archived = 0"]
    parameters: list[Any] = []
    if not show_expired:
        clauses.append(
            f"c.archived = 1 OR NOT {COURT_EXPIRED_SQL}"
            if admin
            else f"NOT {COURT_EXPIRED_SQL}"
        )

    if search:
        search_pattern = f"%{search}%"
        clauses.append(
            "c.event_name LIKE ? OR c.badminton_name LIKE ? "
            "OR c.hall_name LIKE ? OR c.location LIKE ? OR c.court_id LIKE ? "
            "OR COALESCE(NULLIF(c.creator_name, ''), u.username, ?) LIKE ?"
        )
        parameters.extend(
            [search_pattern] * 5
            + [current_app_config("ADMIN_USERNAME"), search_pattern]
        )

    parsed_date_from = parse_filter_date(date_from)
    parsed_date_to = parse_filter_date(date_to)
    if parsed_date_from:
        clauses.append("c.court_date >= ?")
        parameters.append(parsed_date_from.isoformat())
    if parsed_date_to:
        clauses.append("c.court_date <= ?")
        parameters.append(parsed_date_to.isoformat())

    try:
        level = int(level_value) if level_value else None
    except ValueError:
        level = None
    if gender not in {"male", "female", "both"}:
        gender = "both"
    if level is not None and 1 <= level <= 18:
        if gender == "male":
            clauses.append("? BETWEEN c.male_level_min AND c.male_level_max")
            parameters.append(level)
        elif gender == "female":
            clauses.append("? BETWEEN c.female_level_min AND c.female_level_max")
            parameters.append(level)
        else:
            clauses.append(
                "? BETWEEN c.male_level_min AND c.male_level_max "
                "AND ? BETWEEN c.female_level_min AND c.female_level_max"
            )
            parameters.extend([level, level])
    else:
        level_value = ""

    capacity_count = (
        "c.ordered_count + (SELECT COUNT(*) FROM participants fp "
        "WHERE fp.court_id = c.id AND fp.waitlisted = 0)"
    )
    active = f"c.archived = 0 AND NOT {COURT_EXPIRED_SQL}"
    if status == "open":
        clauses.append(
            f"{active} AND c.roll_clearing_locked = 0 "
            f"AND {capacity_count} < c.member_max"
        )
    elif status == "full":
        clauses.append(
            f"{active} AND c.roll_clearing_locked = 0 "
            f"AND {capacity_count} >= c.member_max"
        )
    elif status == "read_only":
        clauses.append(f"{active} AND c.roll_clearing_locked = 1")
    elif status == "archived" and admin:
        clauses.append("c.archived = 1")
    else:
        status = ""

    filters = {
        "q": search,
        "date_from": format_filter_date(parsed_date_from),
        "date_to": format_filter_date(parsed_date_to),
        "level": level_value,
        "gender": gender,
        "status": status,
        "show_expired": show_expired,
    }
    return [f"({clause})" for clause in clauses], parameters, filters


def court_where_sql(clauses: list[str]) -> str:
    return " WHERE " + " AND ".join(clauses) if clauses else ""


def join_court_entry(court: sqlite3.Row, raw_username: str, raw_pin: str) -> bool:
    """Sign a player up; returns True when they were placed on the waitlist."""
    if court["archived"]:
        raise CourtActionError("court_closed", 409)
    if court["is_expired"]:
        raise CourtActionError("court_expired", 409)
    if court["roll_clearing_locked"]:
        raise CourtActionError("court_read_only", 409)

    username = clean_username(raw_username)
    pin = raw_pin.strip()
    if not 2 <= len(username) <= 40:
        raise CourtActionError("invalid_username")
    if not PIN_PATTERN.fullmatch(pin):
        raise CourtActionError("invalid_pin")

    db = get_db()
    try:
        # Serialize the capacity check with the insert so simultaneous
        # sign-ups are assigned confirmed/waiting positions in order.
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            """
            SELECT c.archived, c.roll_clearing_locked, c.member_max,
                   CASE WHEN """
            + COURT_EXPIRED_SQL
            + """ THEN 1 ELSE 0 END AS is_expired,
                   c.ordered_count +
                   (SELECT COUNT(*) FROM participants p
                    WHERE p.court_id = c.id AND p.waitlisted = 0)
                       AS total_count
            FROM courts c
            WHERE c.id = ?
            """,
            (court["id"],),
        ).fetchone()
        if current is None or current["archived"]:
            db.rollback()
            raise CourtActionError("court_closed", 409)
        if current["is_expired"]:
            db.rollback()
            raise CourtActionError("court_expired", 409)
        if current["roll_clearing_locked"]:
            db.rollback()
            raise CourtActionError("court_read_only", 409)
        waitlisted = int(current["total_count"] >= current["member_max"])
        occurred_at = datetime.now().isoformat(timespec="seconds")
        db.execute(
            "INSERT INTO participants "
            "(court_id, username, username_key, pin_hash, waitlisted, joined_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                court["id"],
                username,
                username.casefold(),
                generate_password_hash(pin),
                waitlisted,
                occurred_at,
            ),
        )
        record_participation_event(db, court["id"], username, "join", occurred_at)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise CourtActionError("duplicate_username", 409) from None

    send_court_push_notifications(court["guid"], "members_changed")
    return bool(waitlisted)


def leave_court_entry(court: sqlite3.Row, raw_username: str, raw_pin: str) -> None:
    if court["is_expired"]:
        raise CourtActionError("court_expired", 409)
    if court["roll_clearing_locked"]:
        raise CourtActionError("court_read_only", 409)
    if court["leave_deadline_passed"]:
        raise CourtActionError("leave_deadline_passed", 409)

    username = clean_username(raw_username)
    pin = raw_pin.strip()
    leave_attempt_scope = court_leave_attempt_scope(court["id"])
    locked_minutes = login_lock_minutes(leave_attempt_scope, username)
    if locked_minutes:
        raise CourtActionError(
            "leave_locked",
            429,
            attempt_locked_message("leave_locked", locked_minutes),
        )
    if not 2 <= len(username) <= 40 or not PIN_PATTERN.fullmatch(pin):
        raise CourtActionError(
            "leave_failed", 403, record_leave_failure(court["id"], username)
        )

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            "SELECT roll_clearing_locked, CASE WHEN "
            + COURT_EXPIRED_SQL
            + " THEN 1 ELSE 0 END AS is_expired, CASE WHEN "
            + LEAVE_DEADLINE_PASSED_SQL
            + " THEN 1 ELSE 0 END AS leave_deadline_passed "
            "FROM courts c WHERE id = ?",
            (court["id"],),
        ).fetchone()
        if current is None:
            db.rollback()
            abort(404)
        if current["is_expired"]:
            db.rollback()
            raise CourtActionError("court_expired", 409)
        if current["roll_clearing_locked"]:
            db.rollback()
            raise CourtActionError("court_read_only", 409)
        if current["leave_deadline_passed"]:
            db.rollback()
            raise CourtActionError("leave_deadline_passed", 409)
        participant = db.execute(
            "SELECT id, pin_hash FROM participants "
            "WHERE court_id = ? AND username_key = ?",
            (court["id"], username.casefold()),
        ).fetchone()
        if participant is None or not check_password_hash(
            participant["pin_hash"], pin
        ):
            db.rollback()
            raise CourtActionError(
                "leave_failed", 403, record_leave_failure(court["id"], username)
            )

        db.execute(
            "DELETE FROM login_attempts WHERE attempt_key = ?",
            (login_attempt_key(leave_attempt_scope, username),),
        )
        db.execute("DELETE FROM participants WHERE id = ?", (participant["id"],))
        rebalance_participants(db, court["id"])
        record_participation_event(
            db,
            court["id"],
            username,
            "leave",
            datetime.now().isoformat(timespec="seconds"),
        )
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    send_court_push_notifications(court["guid"], "members_changed")


def start_roll_clearing_mode(court: sqlite3.Row) -> bool:
    """Lock the event for roll call; returns True when it was newly locked."""
    db = get_db()
    changed = False
    try:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            "SELECT id, ordered_count, roll_clearing_locked "
            "FROM courts WHERE id = ?",
            (court["id"],),
        ).fetchone()
        if current is None:
            db.rollback()
            abort(404)
        if not current["roll_clearing_locked"]:
            nicknames = reserved_nickname_values(
                current["id"], current["ordered_count"]
            )
            sync_reserved_members(db, current["id"], nicknames)
            db.execute(
                "UPDATE courts SET roll_clearing_locked = 1 WHERE id = ?",
                (current["id"],),
            )
            changed = True
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    if changed:
        send_court_push_notifications(court["guid"], "roll_started")
    return changed


def save_roll_clearing_statuses(
    court: sqlite3.Row,
    participant_statuses: dict[int, tuple[bool, bool]],
    reserved_statuses: dict[int, tuple[bool, bool]],
    *,
    reset_unlisted: bool,
) -> None:
    """Store (roll_called, cleared) flags for confirmed and reserved members.

    With ``reset_unlisted`` every member missing from the mappings is reset
    to (False, False), matching the checkbox form. Otherwise only the listed
    members change and unknown IDs are rejected.
    """
    if not court["roll_clearing_locked"]:
        raise CourtActionError("court_not_read_only", 409)
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        participant_ids = {
            row["id"]
            for row in db.execute(
                "SELECT id FROM participants "
                "WHERE court_id = ? AND waitlisted = 0",
                (court["id"],),
            ).fetchall()
        }
        reserved_ids = {
            row["id"]
            for row in db.execute(
                "SELECT id FROM reserved_members WHERE court_id = ?",
                (court["id"],),
            ).fetchall()
        }
        if not reset_unlisted and (
            participant_statuses.keys() - participant_ids
            or reserved_statuses.keys() - reserved_ids
        ):
            db.rollback()
            raise CourtActionError("unknown_member")
        for table, member_ids, statuses in (
            ("participants", participant_ids, participant_statuses),
            ("reserved_members", reserved_ids, reserved_statuses),
        ):
            targets = member_ids if reset_unlisted else statuses.keys()
            db.executemany(
                f"UPDATE {table} SET roll_called = ?, cleared = ? "
                "WHERE id = ? AND court_id = ?",
                [
                    (
                        int(bool(statuses.get(member_id, (False, False))[0])),
                        int(bool(statuses.get(member_id, (False, False))[1])),
                        member_id,
                        court["id"],
                    )
                    for member_id in targets
                ],
            )
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise


def restore_court_editing_mode(court: sqlite3.Row) -> None:
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        result = db.execute(
            "UPDATE courts SET roll_clearing_locked = 0 WHERE id = ?",
            (court["id"],),
        )
        if result.rowcount == 0:
            db.rollback()
            abort(404)
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    if court["roll_clearing_locked"]:
        send_court_push_notifications(court["guid"], "editing_restored")


def rename_court_participant(
    court: sqlite3.Row, participant_id: int, raw_username: str
) -> None:
    if court["roll_clearing_locked"]:
        raise CourtActionError("court_read_only", 409)
    username = clean_username(raw_username)
    if not 2 <= len(username) <= 40:
        raise CourtActionError("invalid_username")

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        participant = db.execute(
            "SELECT username FROM participants WHERE id = ? AND court_id = ?",
            (participant_id, court["id"]),
        ).fetchone()
        if participant is None:
            db.rollback()
            raise CourtActionError("participant_not_found", 404)
        changed = participant["username"] != username
        db.execute(
            "UPDATE participants SET username = ?, username_key = ? "
            "WHERE id = ? AND court_id = ?",
            (username, username.casefold(), participant_id, court["id"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise CourtActionError("duplicate_username", 409) from None
    except sqlite3.Error:
        db.rollback()
        raise
    if changed:
        send_court_push_notifications(court["guid"], "members_changed")


def reset_court_participant_pin(
    court: sqlite3.Row, participant_id: int, raw_pin: str
) -> None:
    if court["roll_clearing_locked"]:
        raise CourtActionError("court_read_only", 409)
    pin = raw_pin.strip()
    if not PIN_PATTERN.fullmatch(pin):
        raise CourtActionError("invalid_pin")
    db = get_db()
    result = db.execute(
        "UPDATE participants SET pin_hash = ? WHERE id = ? AND court_id = ?",
        (generate_password_hash(pin), participant_id, court["id"]),
    )
    if result.rowcount == 0:
        db.rollback()
        raise CourtActionError("participant_not_found", 404)
    db.commit()


def remove_court_participant(court: sqlite3.Row, participant_id: int) -> None:
    if court["roll_clearing_locked"]:
        raise CourtActionError("court_read_only", 409)
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        result = db.execute(
            "DELETE FROM participants WHERE id = ? AND court_id = ?",
            (participant_id, court["id"]),
        )
        if result.rowcount == 0:
            db.rollback()
            raise CourtActionError("participant_not_found", 404)
        rebalance_participants(db, court["id"])
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    send_court_push_notifications(court["guid"], "members_changed")


def authenticate_member(username: str, password: str) -> sqlite3.Row:
    """Check credentials with lockout handling and record the sign-in."""
    username = username.strip()
    user = get_db().execute(
        "SELECT id, username, password_hash, role, archived, banned, "
        "must_change_password FROM users WHERE username_key = ?",
        (username.casefold(),),
    ).fetchone()
    login_scope = (
        "admin" if user is not None and user["role"] in ADMIN_ROLES else "member"
    )
    locked_minutes = login_lock_minutes(login_scope, username)
    if locked_minutes:
        raise CourtActionError(
            "login_locked",
            429,
            attempt_locked_message("login_locked", locked_minutes),
        )
    if user is None or not check_password_hash(user["password_hash"], password):
        raise CourtActionError(
            "invalid_credentials", 401, record_login_failure(login_scope, username)
        )
    if user["banned"]:
        clear_login_failures(login_scope, username)
        raise CourtActionError("account_banned", 403)
    if user["archived"]:
        clear_login_failures(login_scope, username)
        raise CourtActionError("account_archived", 403)

    clear_login_failures(login_scope, username)
    db = get_db()
    db.execute(
        "UPDATE users SET last_login_at = ?, last_login_ip = ? WHERE id = ?",
        (
            datetime.now().isoformat(timespec="seconds"),
            client_ip_address(),
            user["id"],
        ),
    )
    db.commit()
    return user


def register_member(username: str, password: str, confirmation: str) -> int:
    username = username.strip()
    if not ACCOUNT_USERNAME_PATTERN.fullmatch(username):
        raise CourtActionError("account_username_help")
    if len(password) < 8:
        raise CourtActionError("password_too_short")
    if password != confirmation:
        raise CourtActionError("password_mismatch")
    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    try:
        cursor = db.execute(
            "INSERT INTO users "
            "(username, username_key, password_hash, created_at, "
            "last_login_at, last_login_ip) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                username,
                username.casefold(),
                generate_password_hash(password),
                now,
                now,
                client_ip_address(),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise CourtActionError("username_taken", 409) from None
    return int(cursor.lastrowid)


def revoke_api_tokens(user_id: int, keep_token_id: int | None = None) -> None:
    db = get_db()
    db.execute(
        "DELETE FROM api_tokens WHERE user_id = ? AND id IS NOT ?",
        (user_id, keep_token_id),
    )
    db.commit()


def change_member_password(
    member_id: int, current_password: str, new_password: str, confirmation: str
) -> None:
    account = get_db().execute(
        "SELECT password_hash FROM users WHERE id = ?", (member_id,)
    ).fetchone()
    if account is None or not check_password_hash(
        account["password_hash"], current_password
    ):
        raise CourtActionError("invalid_credentials", 403)
    if len(new_password) < 8:
        raise CourtActionError("password_too_short")
    if new_password != confirmation:
        raise CourtActionError("password_mismatch")
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
        (generate_password_hash(new_password), member_id),
    )
    db.commit()
    # A new password signs out other app devices; keep the caller's token.
    revoke_api_tokens(member_id, g.get("api_token_id"))


def save_member_avatar(member: sqlite3.Row, uploaded: Any) -> str:
    if uploaded is None or not uploaded.filename:
        raise CourtActionError("invalid_avatar")
    image_data = uploaded.stream.read(MAX_AVATAR_BYTES + 1)
    if len(image_data) > MAX_AVATAR_BYTES:
        raise CourtActionError("avatar_too_large", 413)
    extension = detect_image_extension(image_data)
    if extension is None:
        raise CourtActionError("invalid_avatar")

    filename = f"{secrets.token_hex(16)}.{extension}"
    avatar_path = Path(current_app_config("AVATAR_FOLDER")) / filename
    avatar_path.write_bytes(image_data)
    db = get_db()
    db.execute(
        "UPDATE users SET avatar_filename = ? WHERE id = ?",
        (filename, member["id"]),
    )
    db.commit()
    remove_avatar_file(member["avatar_filename"])
    return filename


def remove_member_avatar(member: sqlite3.Row) -> None:
    db = get_db()
    db.execute("UPDATE users SET avatar_filename = '' WHERE id = ?", (member["id"],))
    db.commit()
    remove_avatar_file(member["avatar_filename"])


def delete_member_account(member: sqlite3.Row, password: str) -> None:
    if member["role"] in ADMIN_ROLES:
        raise CourtActionError("admin_account_delete_disabled", 403)
    account = get_db().execute(
        "SELECT password_hash FROM users WHERE id = ?", (member["id"],)
    ).fetchone()
    if account is None or not check_password_hash(account["password_hash"], password):
        raise CourtActionError("invalid_credentials", 403)
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (member["id"],))
    db.commit()
    remove_avatar_file(member["avatar_filename"])


def validate_contact_message(values: dict[str, str]) -> dict[str, str]:
    errors: dict[str, str] = {}
    for field_name in ("sender_name", "subject", "message"):
        if not values[field_name]:
            errors[field_name] = "contact_form_required"
    length_rules = (
        ("sender_name", MAX_CONTACT_NAME_LENGTH, "contact_name_too_long"),
        ("reply_contact", MAX_CONTACT_REPLY_LENGTH, "contact_reply_too_long"),
        ("subject", MAX_CONTACT_SUBJECT_LENGTH, "contact_subject_too_long"),
        ("message", MAX_CONTACT_MESSAGE_LENGTH, "contact_message_too_long"),
    )
    for field_name, maximum, error_key in length_rules:
        if len(values[field_name]) > maximum:
            errors[field_name] = error_key
    for field_name, field_value in values.items():
        if contains_disallowed_control_characters(
            field_value, multiline=field_name == "message"
        ):
            errors[field_name] = "contact_form_invalid"
    return errors


def store_contact_message(
    values: dict[str, str], lang: str, client: dict[str, str] | None = None
) -> int:
    submitted_at = datetime.now().isoformat(timespec="seconds")
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO contact_messages
            (sender_name, reply_contact, subject, message, language, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            values["sender_name"],
            values["reply_contact"],
            values["subject"],
            values["message"],
            lang,
            submitted_at,
        ),
    )
    db.commit()
    message_id = int(cursor.lastrowid)
    send_contact_message_notifications(
        {
            "id": message_id,
            **values,
            **contact_message_context(client),
            "language": lang,
            "submitted_at": submitted_at,
        }
    )
    return message_id


def set_member_role(actor: sqlite3.Row, user_id: int, raw_role: str) -> None:
    if user_id == actor["id"]:
        raise CourtActionError("cannot_change_own_role", 409)
    role = raw_role.strip()
    if role not in ACCOUNT_ROLES:
        raise CourtActionError("invalid_role")
    db = get_db()
    result = db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    if result.rowcount == 0:
        db.rollback()
        raise CourtActionError("user_not_found", 404)
    db.commit()


def delete_archived_member(user_id: int) -> None:
    """Delete a non-admin account; it must be archived first."""
    db = get_db()
    user = db.execute(
        "SELECT role, archived, avatar_filename FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if user is None:
        abort(404)
    if user["role"] in ADMIN_ROLES:
        abort(403)
    if not user["archived"]:
        raise CourtActionError("account_must_be_archived", 409)
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    remove_avatar_file(user["avatar_filename"])


def fetch_admin_user_rows() -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT u.id, u.username, u.role, u.archived, u.banned, u.must_change_password,
               u.created_at, u.last_login_at, u.last_login_ip,
               COUNT(c.id) AS court_count,
               COALESCE(
                   (
                       SELECT SUM(la.failed_count)
                       FROM login_attempts la
                       WHERE la.scope = 'member'
                         AND la.username_key = u.username_key
                   ),
                   0
               ) AS failed_login_attempts
        FROM users u
        LEFT JOIN courts c ON c.owner_id = u.id
        GROUP BY u.id
        ORDER BY u.banned DESC, u.archived, u.username_key
        """
    ).fetchall()


def fetch_contact_message_page(
    message_status: str, page: int, per_page: int = 50
) -> dict[str, Any]:
    where_clause = ""
    if message_status == "unread":
        where_clause = " WHERE read_at IS NULL"
    elif message_status == "read":
        where_clause = " WHERE read_at IS NOT NULL"
    db = get_db()
    total_count = db.execute(
        f"SELECT COUNT(*) AS count FROM contact_messages{where_clause}"
    ).fetchone()["count"]
    unread_count = db.execute(
        "SELECT COUNT(*) AS count FROM contact_messages WHERE read_at IS NULL"
    ).fetchone()["count"]
    page_count = max(1, (total_count + per_page - 1) // per_page)
    page = min(max(1, page), page_count)
    messages = db.execute(
        "SELECT id, sender_name, reply_contact, subject, message, "
        "language, submitted_at, read_at FROM contact_messages"
        f"{where_clause} "
        "ORDER BY submitted_at DESC, id DESC LIMIT ? OFFSET ?",
        (per_page, (page - 1) * per_page),
    ).fetchall()
    return {
        "messages": messages,
        "total_count": total_count,
        "unread_count": unread_count,
        "page": page,
        "page_count": page_count,
    }


def set_contact_message_read(message_id: int, mark_read: bool) -> bool:
    read_at = datetime.now().isoformat(timespec="seconds") if mark_read else None
    db = get_db()
    cursor = db.execute(
        "UPDATE contact_messages SET read_at = ? WHERE id = ?",
        (read_at, message_id),
    )
    db.commit()
    return cursor.rowcount > 0


def update_court_status(guid: str, archived: int) -> None:
    db = get_db()
    result = db.execute(
        "UPDATE courts SET archived = ? WHERE guid = ?", (archived, guid)
    )
    if result.rowcount == 0:
        abort(404)
    db.commit()
    send_court_push_notifications(
        guid, "archived" if archived else "restored"
    )


def update_owned_court_status(guid: str, owner_id: int, archived: int) -> None:
    db = get_db()
    result = db.execute(
        "UPDATE courts SET archived = ? WHERE guid = ? AND owner_id = ?",
        (archived, guid, owner_id),
    )
    if result.rowcount == 0:
        abort(404)
    db.commit()
    send_court_push_notifications(
        guid, "archived" if archived else "restored"
    )


def update_user_status(user_id: int, archived: int) -> None:
    db = get_db()
    result = db.execute(
        "UPDATE users SET archived = ? WHERE id = ?", (archived, user_id)
    )
    if result.rowcount == 0:
        abort(404)
    db.commit()


def reject_privileged_account_mutation(user_id: int) -> None:
    user = get_db().execute(
        "SELECT role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if user is None:
        abort(404)
    if user["role"] in ADMIN_ROLES:
        abort(403)


def update_user_ban(user_id: int, banned: int) -> None:
    db = get_db()
    result = db.execute(
        "UPDATE users SET banned = ? WHERE id = ?", (banned, user_id)
    )
    if result.rowcount == 0:
        abort(404)
    db.commit()


def level_label(number: int, lang: str) -> str:
    if number <= 3:
        key = "level_beginner"
    elif number <= 5:
        key = "level_elementary"
    elif number <= 7:
        key = "level_preintermediate"
    elif number <= 9:
        key = "level_intermediate"
    elif number <= 12:
        key = "level_upperintermediate"
    elif number <= 15:
        key = "level_advanced"
    else:
        key = "level_professional"
    return TRANSLATIONS[lang][key]


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
