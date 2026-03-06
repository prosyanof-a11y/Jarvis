[app]
# ─── ОСНОВНЫЕ НАСТРОЙКИ ───────────────────────────────
title           = ARIA Assistant
package.name    = aria_assistant
package.domain  = com.yourname

source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,json,db

version         = 1.0.0

# ─── ЗАВИСИМОСТИ ──────────────────────────────────────
requirements = python3,\
    kivy==2.3.0,\
    kivymd==1.2.0,\
    pillow,\
    requests,\
    gspread,\
    google-auth,\
    google-auth-oauthlib,\
    plyer,\
    pyjnius,\
    android

# ─── ANDROID НАСТРОЙКИ ────────────────────────────────
android.permissions = INTERNET,\
    RECORD_AUDIO,\
    READ_EXTERNAL_STORAGE,\
    WRITE_EXTERNAL_STORAGE,\
    ACCESS_NETWORK_STATE,\
    VIBRATE

android.api         = 33
android.minapi      = 26
android.sdk         = 33
android.ndk         = 25b
android.ndk_api     = 26
android.archs       = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True

# ─── ИКОНКИ ──────────────────────────────────────────
# presplash.filename = assets/presplash.png
# icon.filename      = assets/icon.png

# ─── ОРИЕНТАЦИЯ ──────────────────────────────────────
orientation = portrait

# ─── BUILD ───────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1
