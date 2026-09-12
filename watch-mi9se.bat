@echo off
setlocal EnableExtensions

set "ADB=D:\Android\platform-tools-latest-windows\platform-tools\adb.exe"
set "SERIAL=90acad9"

title Xiaomi Mi 9 SE Watchdog

if not exist "%ADB%" (
    echo ERROR: adb.exe not found:
    echo %ADB%
    pause
    exit /b 1
)

where scrcpy.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: scrcpy.exe not found in PATH.
    pause
    exit /b 1
)

"%ADB%" start-server >nul 2>&1

:WAIT_DEVICE

"%ADB%" -s "%SERIAL%" get-state >nul 2>&1

if errorlevel 1 (
    echo [%date% %time%] Device unavailable. Retrying in 5 seconds...
    timeout /t 5 /nobreak >nul
    goto WAIT_DEVICE
)

echo [%date% %time%] Device connected.
echo [%date% %time%] Starting scrcpy...

scrcpy.exe ^
    -s "%SERIAL%" ^
    --mouse=uhid ^
    --turn-screen-off ^
    --stay-awake ^
    --max-size=1280 ^
    --max-fps=30 ^
    --video-bit-rate=4M ^
    --no-audio ^
    --window-title="Xiaomi Mi 9 SE Cloud Phone"

echo [%date% %time%] scrcpy stopped.
echo [%date% %time%] Restarting in 5 seconds...

timeout /t 5 /nobreak >nul
goto WAIT_DEVICE