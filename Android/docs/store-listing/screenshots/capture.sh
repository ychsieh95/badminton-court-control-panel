#!/usr/bin/env bash
set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
ANDROID_DIR="$ROOT/Android"
APP_ID="cc.holey.badmintoncourtcontrolpanel"
ALL_SCENARIOS="courts,court-detail,members-levels,join,messages,organize,court-form"
SCENARIOS="$ALL_SCENARIOS"
LOCALE="all"
# Default PNG root: version-<versionCode> (<versionName>)/app, read from app/build.gradle.kts.
VERSION_CODE="$(sed -nE 's/^[[:space:]]*versionCode[[:space:]]*=[[:space:]]*([0-9]+).*/\1/p' "$ANDROID_DIR/app/build.gradle.kts" | head -n 1)"
VERSION_NAME="$(sed -nE 's/^[[:space:]]*versionName[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$ANDROID_DIR/app/build.gradle.kts" | head -n 1)"
[[ -n "$VERSION_CODE" && -n "$VERSION_NAME" ]] || { printf 'ERROR: cannot read versionCode/versionName from app/build.gradle.kts\n' >&2; exit 1; }
OUTPUT="$HERE/version-$VERSION_CODE ($VERSION_NAME)/app"
AVD=""
SERIAL=""
NO_START=false
NO_BUILD=false
KEEP_EMULATOR=false
TIMEOUT=180
PORT=5055
STARTED_PID=""
SERVER_PID=""
EMULATOR_LOG=""
OLD_ACCELEROMETER=""
OLD_ROTATION=""
OLD_NIGHT=""
WORK=""

usage() {
    cat <<'EOF'
Usage: Android/docs/store-listing/screenshots/capture.sh [options]
  --avd NAME             Start or select this existing AVD.
  --serial SERIAL        Use this already-running emulator (never a phone).
  --output DIRECTORY     PNG root (default: .../screenshots/version-<versionCode>
                         (<versionName>)/app, from app/build.gradle.kts).
                         Each locale is written to its own subdirectory.
  --locale all|zh-TW|en-US
                         Capture both languages or one locale (default: all).
  --scenarios LIST       Comma-separated subset: courts,court-detail,
                         members-levels,join,messages,organize,court-form.
  --port PORT            Host port for the fixture server (default: 5055).
  --no-start             Do not start an emulator; requires --serial.
  --no-build             Install the existing debug APK instead of rebuilding.
  --keep-emulator        Keep an emulator started by this script running.
  --timeout SECONDS      Boot/readiness timeout (default: 180).
  --help                 Show this help.

The script builds and installs the debug app, runs the website against a
throwaway database of fictional courts (fixture_server.py), points the app at
it through the emulator host alias 10.0.2.2, signs in a fictional organizer,
and captures and validates every PNG. It clears the app's data on the emulator.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
stop_server() {
    if [[ -n "$SERVER_PID" ]]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        SERVER_PID=""
    fi
}
cleanup() {
    local status=$?
    stop_server
    if [[ -n "$SERIAL" && -n "${ADB:-}" ]]; then
        "$ADB" -s "$SERIAL" shell am broadcast -a com.android.systemui.demo -e command exit >/dev/null 2>&1 || true
        if [[ -n "$OLD_ACCELEROMETER" ]]; then
            "$ADB" -s "$SERIAL" shell settings put system accelerometer_rotation "$OLD_ACCELEROMETER" >/dev/null 2>&1 || true
            "$ADB" -s "$SERIAL" shell settings put system user_rotation "$OLD_ROTATION" >/dev/null 2>&1 || true
        fi
        if [[ -n "$OLD_NIGHT" ]]; then
            "$ADB" -s "$SERIAL" shell cmd uimode night "$OLD_NIGHT" >/dev/null 2>&1 || true
        fi
    fi
    if [[ -n "$STARTED_PID" && "$KEEP_EMULATOR" == false && -n "$SERIAL" ]]; then
        "$ADB" -s "$SERIAL" emu kill >/dev/null 2>&1 || true
        wait "$STARTED_PID" 2>/dev/null || true
    fi
    [[ -n "$WORK" ]] && rm -rf "$WORK"
    exit "$status"
}
trap cleanup EXIT INT TERM

while (($#)); do
    case "$1" in
        --avd) [[ $# -ge 2 ]] || die "--avd needs a value"; AVD=$2; shift 2 ;;
        --serial) [[ $# -ge 2 ]] || die "--serial needs a value"; SERIAL=$2; shift 2 ;;
        --output) [[ $# -ge 2 ]] || die "--output needs a value"; OUTPUT=$2; shift 2 ;;
        --locale) [[ $# -ge 2 ]] || die "--locale needs a value"; LOCALE=$2; shift 2 ;;
        --scenarios) [[ $# -ge 2 ]] || die "--scenarios needs a value"; SCENARIOS=$2; shift 2 ;;
        --port) [[ $# -ge 2 ]] || die "--port needs a value"; PORT=$2; shift 2 ;;
        --timeout) [[ $# -ge 2 ]] || die "--timeout needs a value"; TIMEOUT=$2; shift 2 ;;
        --no-start) NO_START=true; shift ;;
        --no-build) NO_BUILD=true; shift ;;
        --keep-emulator) KEEP_EMULATOR=true; shift ;;
        --help|-h) usage; exit 0 ;;
        *) die "unknown argument: $1 (use --help)" ;;
    esac
done

[[ "$LOCALE" == all || "$LOCALE" == zh-TW || "$LOCALE" == en-US ]] || die "unsupported locale: $LOCALE"
[[ "$TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die "--timeout must be a positive integer"
[[ "$PORT" =~ ^[1-9][0-9]*$ ]] || die "--port must be a positive integer"
[[ -n "$SCENARIOS" ]] || die "--scenarios cannot be empty"
IFS=',' read -r -a scenario_list <<< "$SCENARIOS"
for scenario in "${scenario_list[@]}"; do
    [[ ",$ALL_SCENARIOS," == *",$scenario,"* ]] || die "unsupported scenario: $scenario"
done
[[ "$NO_START" == false || -n "$SERIAL" ]] || die "--no-start requires --serial"
[[ -z "$SERIAL" || -z "$AVD" ]] || die "use either --serial or --avd, not both"

PYTHON="$ROOT/Web/.venv/bin/python"
[[ -x "$PYTHON" ]] || die "website virtualenv not found at Web/.venv; create it as described in Web/README.md"
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then die "port $PORT is already in use; pass --port"; fi

SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Android/Sdk}}"
ADB="$SDK/platform-tools/adb"
EMULATOR="$SDK/emulator/emulator"
[[ -x "$ADB" ]] || ADB="$(command -v adb || true)"
[[ -n "$ADB" && -x "$ADB" ]] || die "adb not found; set ANDROID_SDK_ROOT or ANDROID_HOME"
if [[ -z "$SERIAL" ]]; then
    [[ -n "$AVD" ]] || die "select an emulator explicitly with --avd or --serial"
    [[ -x "$EMULATOR" ]] || EMULATOR="$(command -v emulator || true)"
    [[ -n "$EMULATOR" && -x "$EMULATOR" ]] || die "emulator not found in the selected SDK or PATH"
    "$EMULATOR" -list-avds | grep -Fxq "$AVD" || die "AVD '$AVD' does not exist; list AVDs with: $EMULATOR -list-avds"
    mapfile -t adb_device_lines < <("$ADB" devices | tail -n +2)
    matching_serials=()
    for line in "${adb_device_lines[@]}"; do
        read -r candidate device_state _ <<< "$line"
        [[ "$candidate" == emulator-* && "$device_state" == device ]] || continue
        running_avd="$($ADB -s "$candidate" emu avd name 2>/dev/null | sed -n '1{s/\r$//;p;}')"
        if [[ "$running_avd" == "$AVD" ]]; then matching_serials+=("$candidate"); fi
    done
    if ((${#matching_serials[@]} > 1)); then
        die "multiple running emulators use AVD '$AVD'; select one with --serial"
    elif ((${#matching_serials[@]} == 1)); then
        SERIAL="${matching_serials[0]}"
        printf 'Using running AVD %s as %s.\n' "$AVD" "$SERIAL"
    else
        for port in $(seq 5554 2 5682); do
            candidate="emulator-$port"
            if ! printf '%s\n' "${adb_device_lines[@]}" | awk '{print $1}' | grep -Fxq "$candidate"; then SERIAL=$candidate; break; fi
        done
        [[ -n "$SERIAL" ]] || die "no free emulator console port is available"
        printf 'Starting AVD %s as %s...\n' "$AVD" "$SERIAL"
        EMULATOR_LOG="${TMPDIR:-/tmp}/bccp-emulator-${SERIAL}.log"
        "$EMULATOR" -avd "$AVD" -port "${SERIAL#emulator-}" -no-snapshot-save -no-boot-anim >"$EMULATOR_LOG" 2>&1 &
        STARTED_PID=$!
    fi
fi

deadline=$((SECONDS + TIMEOUT))
while ((SECONDS < deadline)); do
    if [[ -n "$STARTED_PID" ]] && ! kill -0 "$STARTED_PID" 2>/dev/null; then
        printf 'Emulator process exited before boot. Log: %s\n' "$EMULATOR_LOG" >&2
        tail -40 "$EMULATOR_LOG" >&2 || true
        die "AVD '$AVD' failed to start"
    fi
    state="$($ADB -s "$SERIAL" get-state 2>/dev/null || true)"
    boot="$($ADB -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    [[ "$state" == device && "$boot" == 1 ]] && break
    sleep 2
done
[[ "${state:-}" == device && "${boot:-}" == 1 ]] || die "emulator $SERIAL did not finish booting in ${TIMEOUT}s"
[[ "$($ADB -s "$SERIAL" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || die "$SERIAL is not an emulator; physical devices are never accepted"
sdk_level="$($ADB -s "$SERIAL" shell getprop ro.build.version.sdk | tr -d '\r')"
((sdk_level >= 33)) || die "$SERIAL runs API $sdk_level; per-app languages need API 33 or later"

APK="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
if [[ "$NO_BUILD" == false ]]; then
    printf 'Building debug APK...\n'
    if [[ -z "${JAVA_HOME:-}" && -x /opt/android-studio/jbr/bin/java ]]; then export JAVA_HOME=/opt/android-studio/jbr; fi
    (cd "$ANDROID_DIR" && ./gradlew -q :app:assembleDebug)
fi
[[ -s "$APK" ]] || die "debug APK was not found at $APK"
"$ADB" -s "$SERIAL" install -r "$APK" >/dev/null || die "APK installation failed on $SERIAL"

mkdir -p "$OUTPUT"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/bccp-screenshots.XXXXXX")"
OLD_ACCELEROMETER="$($ADB -s "$SERIAL" shell settings get system accelerometer_rotation | tr -d '\r')"
OLD_ROTATION="$($ADB -s "$SERIAL" shell settings get system user_rotation | tr -d '\r')"
OLD_NIGHT="$($ADB -s "$SERIAL" shell cmd uimode night | tr -d '\r' | sed -n 's/^Night mode: //p')"
"$ADB" -s "$SERIAL" shell settings put system accelerometer_rotation 0 >/dev/null
"$ADB" -s "$SERIAL" shell settings put system user_rotation 0 >/dev/null
"$ADB" -s "$SERIAL" shell cmd uimode night no >/dev/null

# Status bar: fixed full battery and signal, current host time, no notification icons.
demo() { "$ADB" -s "$SERIAL" shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
"$ADB" -s "$SERIAL" shell settings put global sysui_demo_allowed 1 >/dev/null
demo enter
demo clock -e hhmm "$(date +%H%M)"
demo battery -e level 100 -e plugged false
demo network -e wifi show -e level 4 -e fully true -e mobile hide
demo notifications -e visible false

if [[ "$LOCALE" == all ]]; then locales=(en-US zh-TW); else locales=("$LOCALE"); fi
captured=0
for locale in "${locales[@]}"; do
    state_file="$WORK/state-$locale.json"
    server_log="$WORK/server-$locale.log"
    "$PYTHON" "$HERE/fixture_server.py" --locale "$locale" --port "$PORT" \
        --data-dir "$WORK/data-$locale" --state-file "$state_file" >"$server_log" 2>&1 &
    SERVER_PID=$!
    deadline=$((SECONDS + 60))
    until grep -q fixture-server-ready "$server_log" 2>/dev/null; do
        kill -0 "$SERVER_PID" 2>/dev/null || { cat "$server_log" >&2; die "fixture server for $locale exited"; }
        ((SECONDS < deadline)) || die "fixture server for $locale did not become ready"
        sleep 1
    done
    printf 'Fixture server for %s is serving fictional courts on port %s.\n' "$locale" "$PORT"
    python3 "$HERE/capture.py" --serial "$SERIAL" --adb "$ADB" --locale "$locale" \
        --state-file "$state_file" --server-url "http://10.0.2.2:$PORT" \
        --output "$OUTPUT/$locale" --scenarios "$SCENARIOS"
    captured=$((captured + ${#scenario_list[@]}))
    stop_server
done

# Leave the app without the fixture sign-in or a dead server address.
"$ADB" -s "$SERIAL" shell pm clear "$APP_ID" >/dev/null || true
"$ADB" -s "$SERIAL" shell cmd locale set-app-locales "$APP_ID" --locales "" >/dev/null 2>&1 || true
printf 'Captured %d screenshot(s) from %s with fictional %s fixtures.\n' "$captured" "$SERIAL" "$LOCALE"
