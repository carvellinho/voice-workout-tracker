[app]
title = Voice Workout Tracker
package.name = voiceworkout
package.domain = org.personal.workout
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,md,wav,mp3,txt,conf,model,mdl,ark,mat
source.exclude_dirs = .git,.github,tests,__pycache__
version = 1.0.0
requirements = python3,kivy==2.2.1,kivymd,vosk,sounddevice,pyttsx3,sqlite3,pyjnius
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.permissions = RECORD_AUDIO,INTERNET,VIBRATE,WAKE_LOCK
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.add_src = android_src
android.add_resources = android_resources
android.entrypoint = org.kivy.android.PythonActivity
android.private_storage = True
android.allow_backup = True
android.gradle_dependencies =

[buildozer:android]
# Kept as a separate section for compatibility with older Buildozer releases.
