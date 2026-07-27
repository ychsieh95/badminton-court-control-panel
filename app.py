from __future__ import annotations

import base64
import binascii
import hmac
import hashlib
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
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
    send_from_directory,
    session,
    url_for,
)
from pywebpush import WebPushException, webpush
from werkzeug.security import check_password_hash, generate_password_hash


load_dotenv(Path(__file__).with_name(".env"))


LANGUAGES = {"en-us", "zh-tw"}
PIN_PATTERN = re.compile(r"^\d{6}$")
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
ACCOUNT_USERNAME_PATTERN = re.compile(r"^[^\s<>]{3,40}$")
AVATAR_FILENAME_PATTERN = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png|webp)$")
COURT_MEDIA_FILENAME_PATTERN = re.compile(
    r"^[a-f0-9]{32}\.(?:jpg|png|webp|mp4|webm)$"
)
WEB_PUSH_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")
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
ACCOUNT_ROLES = {"member", "sub_admin", "admin", "super_admin"}
ADMIN_ROLES = {"sub_admin", "admin", "super_admin"}
COURT_EXPIRED_SQL = (
    "(c.court_date || ' ' || c.end_time || ':00') "
    "< strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')"
)

TRANSLATIONS = {
    "en-us": {
        "brand": "Badminton Court Control Panel",
        "home": "Courts",
        "introduction": "Introduction",
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
        "username": "Username",
        "pin": "6-digit PIN",
        "join": "Join court",
        "leave": "Leave court",
        "participants": "Players",
        "no_participants": "No online sign-ups yet.",
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
        "reserved_nicknames_help": "Optionally record one nickname for each pre-booked place.",
        "reserved_nickname": "Reserved nickname",
        "reserved_nickname_placeholder": "Nickname (optional)",
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
        "username": "使用者名稱",
        "pin": "6 位數 PIN 碼",
        "join": "加入場次",
        "leave": "離開場次",
        "participants": "球友名單",
        "no_participants": "目前尚無線上報名。",
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
        "reserved_nicknames_help": "可為每個已預訂名額記錄一個暱稱。",
        "reserved_nickname": "預訂球友暱稱",
        "reserved_nickname_placeholder": "暱稱（選填）",
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


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    username_key TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    avatar_filename TEXT NOT NULL DEFAULT '',
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
    roll_clearing_locked INTEGER NOT NULL DEFAULT 0 CHECK(roll_clearing_locked IN (0, 1)),
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
"""


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
        AVATAR_FOLDER=str(Path(app.instance_path) / "avatars"),
        COURT_MEDIA_FOLDER=str(Path(app.instance_path) / "court_media"),
        GEOIP_COUNTRY_DB=os.environ.get("GEOIP_COUNTRY_DB", ""),
        DEFAULT_COUNTRY_CODE=os.environ.get("DEFAULT_COUNTRY_CODE", "").upper(),
        TRUST_PROXY_HEADERS=os.environ.get("TRUST_PROXY_HEADERS", "0") == "1",
        LOGIN_MAX_ATTEMPTS=int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5")),
        LOGIN_LOCKOUT_SECONDS=int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "900")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["AVATAR_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["COURT_MEDIA_FOLDER"]).mkdir(parents=True, exist_ok=True)
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

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        lang = current_language()
        member = current_member()
        turnstile_is_enabled = turnstile_enabled()
        return {
            "lang": lang,
            "t": lambda key: TRANSLATIONS[lang].get(key, key),
            "csrf_token": csrf_token,
            "level_label": lambda number: level_label(number, lang),
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
            return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M:%S")
        except (TypeError, ValueError):
            return value

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

    @app.get("/licenses")
    def licenses():
        return render_template("licenses.html")

    @app.get("/introduction")
    def introduction():
        return render_template("introduction.html")

    @app.get("/courts")
    def public_courts():
        search = request.args.get("q", "").strip()[:100]
        legacy_date = request.args.get("date", "").strip()
        date_from = request.args.get("date_from", "").strip() or legacy_date
        date_to = request.args.get("date_to", "").strip() or legacy_date
        level_value = request.args.get("level", "").strip()
        gender = request.args.get("gender", "both").strip()
        status = request.args.get("status", "").strip()
        show_expired = request.args.get("show_expired", "") == "1"
        clauses = ["c.archived = 0"]
        parameters: list[Any] = []
        if not show_expired:
            clauses.append(f"NOT {COURT_EXPIRED_SQL}")

        if search:
            search_pattern = f"%{search}%"
            clauses.append(
                "(c.event_name LIKE ? OR c.badminton_name LIKE ? "
                "OR c.hall_name LIKE ? OR c.location LIKE ? OR c.court_id LIKE ? "
                "OR COALESCE(NULLIF(c.creator_name, ''), u.username, ?) LIKE ?)"
            )
            parameters.extend(
                [
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    app.config["ADMIN_USERNAME"],
                    search_pattern,
                ]
            )

        parsed_date_from = parse_filter_date(date_from)
        if date_from and parsed_date_from is None:
            date_from = ""
        parsed_date_to = parse_filter_date(date_to)
        if date_to and parsed_date_to is None:
            date_to = ""
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
                clauses.append(
                    "? BETWEEN c.female_level_min AND c.female_level_max"
                )
                parameters.append(level)
            else:
                clauses.append(
                    "(? BETWEEN c.male_level_min AND c.male_level_max "
                    "AND ? BETWEEN c.female_level_min AND c.female_level_max)"
                )
                parameters.extend([level, level])
        else:
            level = None
            level_value = ""

        capacity_count = (
            "c.ordered_count + (SELECT COUNT(*) FROM participants fp "
            "WHERE fp.court_id = c.id AND fp.waitlisted = 0)"
        )
        if status == "open":
            clauses.append(
                f"NOT {COURT_EXPIRED_SQL} AND c.roll_clearing_locked = 0 "
                f"AND {capacity_count} < c.member_max"
            )
        elif status == "full":
            clauses.append(
                f"NOT {COURT_EXPIRED_SQL} AND c.roll_clearing_locked = 0 "
                f"AND {capacity_count} >= c.member_max"
            )
        elif status == "read_only":
            clauses.append(f"NOT {COURT_EXPIRED_SQL} AND c.roll_clearing_locked = 1")
        else:
            status = ""

        courts = get_db().execute(
            court_query()
            + " WHERE "
            + " AND ".join(clauses)
            + " ORDER BY is_expired, c.court_date, c.start_time",
            parameters,
        ).fetchall()
        return render_template(
            "courts.html",
            courts=courts,
            filters={
                "q": search,
                "date_from": format_filter_date(parsed_date_from),
                "date_to": format_filter_date(parsed_date_to),
                "level": level_value,
                "gender": gender,
                "status": status,
                "show_expired": show_expired,
            },
        )

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
            password = request.form.get("password", "")
            confirmation = request.form.get("confirm_password", "")
            if not ACCOUNT_USERNAME_PATTERN.fullmatch(username):
                flash_t("account_username_help", "error")
            elif len(password) < 8:
                flash_t("password_too_short", "error")
            elif password != confirmation:
                flash_t("password_mismatch", "error")
            else:
                db = get_db()
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
                            datetime.now().isoformat(timespec="seconds"),
                            datetime.now().isoformat(timespec="seconds"),
                            client_ip_address(),
                        ),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    flash_t("username_taken", "error")
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
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
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT id, username, password_hash, role, archived, banned, "
                "must_change_password FROM users WHERE username_key = ?",
                (username.casefold(),),
            ).fetchone()
            login_scope = (
                "admin"
                if user is not None and user["role"] in ADMIN_ROLES
                else "member"
            )
            locked_minutes = login_lock_minutes(login_scope, username)
            if locked_minutes:
                flash_login_locked(locked_minutes)
                return render_template("account/auth.html", signup=False)
            if user is None or not check_password_hash(user["password_hash"], password):
                flash_login_failure(login_scope, username)
            elif user["banned"]:
                clear_login_failures(login_scope, username)
                flash_t("account_banned", "error")
            elif user["archived"]:
                clear_login_failures(login_scope, username)
                flash_t("account_archived", "error")
            else:
                clear_login_failures(login_scope, username)
                db = get_db()
                db.execute(
                    "UPDATE users SET last_login_at = ?, last_login_ip = ? "
                    "WHERE id = ?",
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        client_ip_address(),
                        user["id"],
                    ),
                )
                db.commit()
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
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirmation = request.form.get("confirm_password", "")
            account = get_db().execute(
                "SELECT password_hash FROM users WHERE id = ?", (member["id"],)
            ).fetchone()
            if account is None or not check_password_hash(
                account["password_hash"], current_password
            ):
                flash_t("invalid_credentials", "error")
            elif len(new_password) < 8:
                flash_t("password_too_short", "error")
            elif new_password != confirmation:
                flash_t("password_mismatch", "error")
            else:
                db = get_db()
                db.execute(
                    "UPDATE users SET password_hash = ?, must_change_password = 0 "
                    "WHERE id = ?",
                    (generate_password_hash(new_password), member["id"]),
                )
                db.commit()
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
            uploaded = request.files.get("avatar")
            if uploaded is None or not uploaded.filename:
                flash_t("invalid_avatar", "error")
                return redirect(url_for("account_profile"))

            image_data = uploaded.stream.read(MAX_AVATAR_BYTES + 1)
            if len(image_data) > MAX_AVATAR_BYTES:
                flash_t("avatar_too_large", "error")
                return redirect(url_for("account_profile"))
            extension = detect_image_extension(image_data)
            if extension is None:
                flash_t("invalid_avatar", "error")
                return redirect(url_for("account_profile"))

            filename = f"{secrets.token_hex(16)}.{extension}"
            avatar_path = Path(app.config["AVATAR_FOLDER"]) / filename
            avatar_path.write_bytes(image_data)
            db = get_db()
            old_filename = member["avatar_filename"]
            db.execute(
                "UPDATE users SET avatar_filename = ? WHERE id = ?",
                (filename, member["id"]),
            )
            db.commit()
            remove_avatar_file(old_filename)
            flash_t("avatar_updated", "success")
            return redirect(url_for("account_profile"))
        saved_locations = get_db().execute(
            "SELECT * FROM saved_locations WHERE user_id = ? "
            "ORDER BY hall_name COLLATE NOCASE, location COLLATE NOCASE",
            (member["id"],),
        ).fetchall()
        return render_template(
            "account/profile.html", saved_locations=saved_locations
        )

    @app.post("/account/profile/avatar/remove")
    @member_required
    def account_remove_avatar():
        verify_csrf()
        member = current_member()
        db = get_db()
        db.execute(
            "UPDATE users SET avatar_filename = '' WHERE id = ?", (member["id"],)
        )
        db.commit()
        remove_avatar_file(member["avatar_filename"])
        flash_t("avatar_removed", "success")
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
        member = current_member()
        if member["role"] in ADMIN_ROLES:
            flash_t("admin_account_delete_disabled", "error")
            return redirect(url_for("account_profile"))
        password = request.form.get("current_password", "")
        account = get_db().execute(
            "SELECT password_hash FROM users WHERE id = ?", (member["id"],)
        ).fetchone()
        if account is None or not check_password_hash(
            account["password_hash"], password
        ):
            flash_t("invalid_credentials", "error")
            return redirect(url_for("account_profile"))

        db = get_db()
        db.execute("DELETE FROM users WHERE id = ?", (member["id"],))
        db.commit()
        remove_avatar_file(member["avatar_filename"])
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
        return render_template(
            "court.html",
            court=court,
            participants=[p for p in participants if not p["waitlisted"]],
            waiting_participants=[p for p in participants if p["waitlisted"]],
            reserved_members=[member for member in all_reserved_members if member["nickname"]],
            all_reserved_members=all_reserved_members,
            court_media=fetch_court_media(court["id"]),
            participation_history=participation_history,
        )

    @app.post("/<guid>/roll-clearing/start")
    def start_roll_clearing(guid: str):
        verify_csrf()
        court = fetch_managed_court(guid)
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
            send_court_push_notifications(guid, "roll_started")
        flash_t("roll_and_clearing_started", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.post("/<guid>/roll-clearing/status")
    def update_roll_clearing_status(guid: str):
        verify_csrf()
        court = fetch_managed_court(guid)
        if not court["roll_clearing_locked"]:
            abort(409)

        participant_roll = set(request.form.getlist("participant_roll"))
        participant_cleared = set(request.form.getlist("participant_cleared"))
        reserved_roll = set(request.form.getlist("reserved_roll"))
        reserved_cleared = set(request.form.getlist("reserved_cleared"))
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            participants = db.execute(
                "SELECT id FROM participants "
                "WHERE court_id = ? AND waitlisted = 0",
                (court["id"],),
            ).fetchall()
            db.executemany(
                "UPDATE participants SET roll_called = ?, cleared = ? "
                "WHERE id = ? AND court_id = ?",
                [
                    (
                        int(str(member["id"]) in participant_roll),
                        int(str(member["id"]) in participant_cleared),
                        member["id"],
                        court["id"],
                    )
                    for member in participants
                ],
            )
            reserved_members = db.execute(
                "SELECT id FROM reserved_members WHERE court_id = ?",
                (court["id"],),
            ).fetchall()
            db.executemany(
                "UPDATE reserved_members SET roll_called = ?, cleared = ? "
                "WHERE id = ? AND court_id = ?",
                [
                    (
                        int(str(member["id"]) in reserved_roll),
                        int(str(member["id"]) in reserved_cleared),
                        member["id"],
                        court["id"],
                    )
                    for member in reserved_members
                ],
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise
        flash_t("member_statuses_saved", "success")
        return redirect(url_for("court_detail", guid=guid))

    @app.post("/<guid>/roll-clearing/edit")
    def restore_court_editing(guid: str):
        verify_csrf()
        court = fetch_managed_court(guid)
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
            send_court_push_notifications(guid, "editing_restored")
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
        if court["archived"]:
            flash_t("court_closed", "error")
            return redirect(url_for("court_detail", guid=guid))
        if court["is_expired"]:
            flash_t("court_expired", "error")
            return redirect(url_for("court_detail", guid=guid))
        if court["roll_clearing_locked"]:
            flash_t("court_read_only", "error")
            return redirect(url_for("court_detail", guid=guid))

        username = clean_username(request.form.get("username", ""))
        pin = request.form.get("pin", "").strip()
        if not 2 <= len(username) <= 40:
            flash_t("invalid_username", "error")
            return redirect(url_for("court_detail", guid=guid))
        if not PIN_PATTERN.fullmatch(pin):
            flash_t("invalid_pin", "error")
            return redirect(url_for("court_detail", guid=guid))

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
                flash_t("court_closed", "error")
                return redirect(url_for("court_detail", guid=guid))
            if current["is_expired"]:
                db.rollback()
                flash_t("court_expired", "error")
                return redirect(url_for("court_detail", guid=guid))
            if current["roll_clearing_locked"]:
                db.rollback()
                flash_t("court_read_only", "error")
                return redirect(url_for("court_detail", guid=guid))
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
            record_participation_event(
                db, court["id"], username, "join", occurred_at
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash_t("duplicate_username", "error")
            return redirect(url_for("court_detail", guid=guid))

        send_court_push_notifications(guid, "members_changed")
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
        if court["is_expired"]:
            flash_t("court_expired", "error")
            return redirect(url_for("court_detail", guid=guid))
        if court["roll_clearing_locked"]:
            flash_t("court_read_only", "error")
            return redirect(url_for("court_detail", guid=guid))

        username = clean_username(request.form.get("username", ""))
        pin = request.form.get("pin", "").strip()
        if not PIN_PATTERN.fullmatch(pin):
            flash_t("invalid_credentials", "error")
            return redirect(url_for("court_detail", guid=guid))

        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT roll_clearing_locked, CASE WHEN "
                + COURT_EXPIRED_SQL
                + " THEN 1 ELSE 0 END AS is_expired "
                "FROM courts c WHERE id = ?",
                (court["id"],),
            ).fetchone()
            if current is None:
                db.rollback()
                abort(404)
            if current["is_expired"]:
                db.rollback()
                flash_t("court_expired", "error")
                return redirect(url_for("court_detail", guid=guid))
            if current["roll_clearing_locked"]:
                db.rollback()
                flash_t("court_read_only", "error")
                return redirect(url_for("court_detail", guid=guid))
            participant = db.execute(
                "SELECT id, pin_hash FROM participants "
                "WHERE court_id = ? AND username_key = ?",
                (court["id"], username.casefold()),
            ).fetchone()
            if participant is None or not check_password_hash(
                participant["pin_hash"], pin
            ):
                db.rollback()
                flash_t("invalid_credentials", "error")
                return redirect(url_for("court_detail", guid=guid))

            db.execute(
                "DELETE FROM participants WHERE id = ?", (participant["id"],)
            )
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
        send_court_push_notifications(guid, "members_changed")
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
        search = request.args.get("q", "").strip()[:100]
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        level_value = request.args.get("level", "").strip()
        gender = request.args.get("gender", "both").strip()
        status = request.args.get("status", "").strip()
        show_expired = request.args.get("show_expired", "") == "1"
        clauses: list[str] = []
        parameters: list[Any] = []
        if not show_expired:
            clauses.append(f"(c.archived = 1 OR NOT {COURT_EXPIRED_SQL})")

        if search:
            search_pattern = f"%{search}%"
            clauses.append(
                "(c.event_name LIKE ? OR c.badminton_name LIKE ? "
                "OR c.hall_name LIKE ? OR c.location LIKE ? OR c.court_id LIKE ? "
                "OR COALESCE(NULLIF(c.creator_name, ''), u.username, ?) LIKE ?)"
            )
            parameters.extend(
                [
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    app.config["ADMIN_USERNAME"],
                    search_pattern,
                ]
            )

        parsed_date_from = parse_filter_date(date_from)
        if date_from and parsed_date_from is None:
            date_from = ""
        parsed_date_to = parse_filter_date(date_to)
        if date_to and parsed_date_to is None:
            date_to = ""
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
                clauses.append(
                    "? BETWEEN c.female_level_min AND c.female_level_max"
                )
                parameters.append(level)
            else:
                clauses.append(
                    "(? BETWEEN c.male_level_min AND c.male_level_max "
                    "AND ? BETWEEN c.female_level_min AND c.female_level_max)"
                )
                parameters.extend([level, level])
        else:
            level = None
            level_value = ""

        capacity_count = (
            "c.ordered_count + (SELECT COUNT(*) FROM participants afp "
            "WHERE afp.court_id = c.id AND afp.waitlisted = 0)"
        )
        if status == "open":
            clauses.append(
                f"c.archived = 0 AND NOT {COURT_EXPIRED_SQL} "
                f"AND c.roll_clearing_locked = 0 "
                f"AND {capacity_count} < c.member_max"
            )
        elif status == "full":
            clauses.append(
                f"c.archived = 0 AND NOT {COURT_EXPIRED_SQL} "
                f"AND c.roll_clearing_locked = 0 "
                f"AND {capacity_count} >= c.member_max"
            )
        elif status == "read_only":
            clauses.append(
                f"c.archived = 0 AND NOT {COURT_EXPIRED_SQL} "
                "AND c.roll_clearing_locked = 1"
            )
        elif status == "archived":
            clauses.append("c.archived = 1")
        else:
            status = ""

        where_clause = (
            " WHERE " + " AND ".join(f"({clause})" for clause in clauses)
            if clauses
            else ""
        )
        courts = get_db().execute(
            court_query()
            + where_clause
            + " ORDER BY c.archived, c.court_date DESC, c.start_time DESC",
            parameters,
        ).fetchall()
        return render_template(
            "admin/dashboard.html",
            courts=courts,
            admin_filters={
                "q": search,
                "date_from": format_filter_date(parsed_date_from),
                "date_to": format_filter_date(parsed_date_to),
                "level": level_value,
                "gender": gender,
                "status": status,
                "show_expired": show_expired,
            },
            home_court_limit=get_int_setting(
                "homepage_court_limit", 12, 1, 100
            ),
        )

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
        users = get_db().execute(
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
        return render_template("admin/users.html", users=users)

    @app.post("/admin/users/<int:user_id>/role")
    @super_admin_required
    def admin_update_user_role(user_id: int):
        verify_csrf()
        actor = current_member()
        if user_id == actor["id"]:
            flash_t("cannot_change_own_role", "error")
            return redirect(url_for("admin_users"))
        role = request.form.get("role", "").strip()
        if role not in ACCOUNT_ROLES:
            flash_t("invalid_role", "error")
            return redirect(url_for("admin_users"))
        db = get_db()
        result = db.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id),
        )
        if result.rowcount == 0:
            abort(404)
        db.commit()
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
            flash_t("account_must_be_archived", "error")
            return redirect(url_for("admin_users"))

        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        remove_avatar_file(user["avatar_filename"])
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
            values = {
                field: request.form.get(field, "").strip() for field in field_names
            }
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
            save_location = request.form.get("save_location") == "1"
            values = {key: request.form.get(key, "").strip() for key in values}
            cleaned, errors = validate_court(values)
            reserved_nicknames = validate_reserved_nicknames(
                request.form.getlist("reserved_nickname"),
                cleaned.get("ordered_count") if "ordered_count" not in errors else None,
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
            values = {
                field: request.form.get(field, "").strip() for field in field_names
            }
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


def current_language() -> str:
    saved_language = request.cookies.get("court_lang", "").lower()
    if saved_language in LANGUAGES:
        return saved_language
    return "zh-tw" if detected_country_code() == "TW" else "en-us"


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


def flash_login_failure(scope: str, username: str) -> None:
    db = get_db()
    now = datetime.now()
    attempt_key = login_attempt_key(scope, username)
    attempt_window = max(60, int(current_app_config("LOGIN_LOCKOUT_SECONDS")))
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
            username.casefold(),
            now.isoformat(timespec="seconds"),
        ),
    )
    attempt = db.execute(
        "SELECT failed_count FROM login_attempts WHERE attempt_key = ?",
        (attempt_key,),
    ).fetchone()
    max_attempts = max(1, int(current_app_config("LOGIN_MAX_ATTEMPTS")))
    failed_count = attempt["failed_count"]
    remaining = max(0, max_attempts - failed_count)
    if remaining:
        db.commit()
        message = TRANSLATIONS[current_language()]["login_attempts_remaining"].format(
            count=remaining
        )
        flash(message, "error")
        return

    lockout_seconds = attempt_window
    locked_until = now + timedelta(seconds=lockout_seconds)
    db.execute(
        "UPDATE login_attempts SET locked_until = ? WHERE attempt_key = ?",
        (locked_until.isoformat(timespec="seconds"), attempt_key),
    )
    db.commit()
    flash_login_locked(max(1, (lockout_seconds + 59) // 60))


def flash_login_locked(minutes: int) -> None:
    message = TRANSLATIONS[current_language()]["login_locked"].format(minutes=minutes)
    flash(message, "error")


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


def flash_t(key: str, category: str) -> None:
    flash(TRANSLATIONS[current_language()].get(key, key), category)


def turnstile_enabled() -> bool:
    return bool(
        not current_app.debug
        and current_app.config.get("TURNSTILE_SITE_KEY")
        and current_app.config.get("TURNSTILE_SECRET_KEY")
    )


def verify_turnstile_response(expected_action: str) -> bool:
    if not turnstile_enabled():
        return True
    token = request.form.get("cf-turnstile-response", "").strip()
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
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = get_db().execute(
        "SELECT id, username, created_at, avatar_filename, last_login_at, "
        "archived, banned, must_change_password, role "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
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


def fetch_court_push_subscriptions(court_id: int) -> list[sqlite3.Row]:
    if not web_push_enabled():
        return []
    return get_db().execute(
        "SELECT id, endpoint, p256dh, auth, language "
        "FROM push_subscriptions WHERE court_id = ? ORDER BY id",
        (court_id,),
    ).fetchall()


def send_court_push_notifications(guid: str, change_type: str) -> None:
    if not web_push_enabled():
        return
    court = get_db().execute(
        "SELECT id, guid, event_name, hall_name FROM courts WHERE guid = ?",
        (guid,),
    ).fetchone()
    if court is None:
        return
    subscriptions = fetch_court_push_subscriptions(court["id"])
    deliver_court_push_notifications(
        guid=court["guid"],
        court_name=court["event_name"] or court["hall_name"],
        change_type=change_type,
        subscriptions=subscriptions,
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
    body_keys = {
        "updated": "push_event_updated_body",
        "archived": "push_event_archived_body",
        "restored": "push_event_restored_body",
        "roll_started": "push_event_roll_started_body",
        "editing_restored": "push_event_editing_restored_body",
        "deleted": "push_event_deleted_body",
        "members_changed": "push_members_changed_body",
    }
    body_key = body_keys.get(change_type, "push_event_updated_body")
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


def delete_court_record(guid: str, owner_id: int | None = None) -> bool:
    db = get_db()
    parameters: tuple[Any, ...] = (
        (guid, owner_id) if owner_id is not None else (guid,)
    )
    ownership_clause = " AND owner_id = ?" if owner_id is not None else ""
    court = db.execute(
        "SELECT id, guid, event_name, hall_name FROM courts "
        f"WHERE guid = ?{ownership_clause}",
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
    result = db.execute(
        "DELETE FROM courts WHERE id = ?",
        (court["id"],),
    )
    if result.rowcount == 0:
        db.rollback()
        return False
    db.commit()
    remove_court_media_files([item["filename"] for item in media])
    deliver_court_push_notifications(
        guid=court["guid"],
        court_name=court["event_name"] or court["hall_name"],
        change_type="deleted",
        subscriptions=subscriptions,
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
        "member_min": "4",
        "member_max": "8",
        "ordered_count": "0",
        "male_level_min": "1",
        "male_level_max": "18",
        "female_level_min": "1",
        "female_level_max": "18",
    }


def court_form_values(court: sqlite3.Row) -> dict[str, str]:
    return {
        field: "" if court[field] is None else str(court[field])
        for field in default_court_values()
    }


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
            reserved_names_visible, member_min, member_max, ordered_count, male_level_min,
            male_level_max, female_level_min, female_level_max, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                reserved_names_visible = ?,
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
