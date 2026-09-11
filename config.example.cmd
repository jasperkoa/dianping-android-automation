@echo off
REM Copy this file to config.local.cmd and edit only what your machine needs.
REM config.local.cmd is ignored by Git so local device information is not committed.

REM Optional: full path to adb.exe. Leave empty if adb is already in PATH.
REM set "ADB_PATH=C:\Android\platform-tools\adb.exe"

REM Optional: required only when more than one ADB device is connected.
REM set "ANDROID_SERIAL=YOUR_DEVICE_SERIAL"

REM Target package. Dianping default:
set "TARGET_PACKAGE=com.dianping.v1"

REM Back navigation mode: adb, gesture-left, gesture-right, nav-left, nav-right
REM Most AOSP devices can start with adb. Some MIUI devices may need a UHID mode.
set "ANDROID_BACK_MODE=adb"

REM Optional override for three-button navigation Y coordinate (0.0-1.0).
REM set "ANDROID_BACK_Y_RATIO=0.973"

REM Optional: only needed if scrcpy-server cannot be discovered automatically.
REM set "SCRCPY_SERVER_PATH=C:\path\to\scrcpy-server"
REM set "SCRCPY_SERVER_VERSION=4.1"
