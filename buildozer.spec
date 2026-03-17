[app]
# Application title and package info
title = TimeBound
package.name = timebound
package.domain = org.timebound

# Source files
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# Version
version = 1.3

# Requirements - critical for the build
requirements = python3,kivy==2.2.1,plyer,pyjnius,android,google-generativeai,requests,urllib3,certifi

# Permissions required for notifications, app blocking, and core features
android.permissions = INTERNET,VIBRATE,POST_NOTIFICATIONS,SCHEDULE_EXACT_ALARM,QUERY_ALL_PACKAGES,MANAGE_EXTERNAL_STORAGE,READ_LOGS,PACKAGE_USAGE_STATS

# Architecture targets
android.archs = armeabi-v7a,arm64-v8a

# Python and Kivy versions
p4a.source_dir = 
p4a.local_recipes = 

# Orientation
orientation = portrait

# Fullscreen
fullscreen = 1

# Android-specific settings
android.api = 34
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# App icon - place your icon at: icon.jpg (512x512 pixels recommended)
icon.filename = %(source.dir)s/icon.jpg

# Presplash image (optional, shows on app startup)
presplash.filename = %(source.dir)s/presplash.jpg

# Enable/Disable features
android.allow_backup = True
android.logcat_filters = *:S python:D

# Required features for app blocking (no device admin, uses accessibility service)
android.required_features = 

[buildozer]
# Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# Display warnings or not
warn_on_root = 1


