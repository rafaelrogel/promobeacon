#!/usr/bin/env bash
set -e

APK_PATH="/home/rafael/.openclaw/workspace/flutter/examples/hello_world/android/app/build/outputs/apk/debug/app-debug.apk"

if [ ! -f "$APK_PATH" ]; then
    echo "APK not found at $APK_PATH"
    exit 1
fi

echo "Installing APK ..."
adb install -r "$APK_PATH"

echo "Launching app ..."
adb shell am start -n io.flutter.examples.hello_world/io.flutter.embedding.android.FlutterActivity

echo "Capturing logs ..."
adb logcat -d > /home/rafael/.openclaw/workspace/logcat_output.txt

# Output logs to stdout as functional test result
cat /home/rafael/.openclaw/workspace/logcat_output.txt