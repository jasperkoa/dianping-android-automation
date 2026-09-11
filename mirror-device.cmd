@echo off
setlocal EnableExtensions DisableDelayedExpansion
if exist "%~dp0config.local.cmd" call "%~dp0config.local.cmd"

set "SERIAL_ARG="
if defined ANDROID_SERIAL set "SERIAL_ARG=-s %ANDROID_SERIAL%"

where scrcpy.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: scrcpy.exe was not found in PATH.
    pause
    exit /b 1
)

scrcpy.exe %SERIAL_ARG% --mouse=uhid --turn-screen-off --stay-awake --max-size=1280 --max-fps=30 --video-bit-rate=4M --no-audio
exit /b %errorlevel%
