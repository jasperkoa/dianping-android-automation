@echo off
setlocal EnableExtensions

set "ADB=D:\Android\platform-tools-latest-windows\platform-tools\adb.exe"
set "SERIAL=90acad9"

title Xiaomi Mi 9 SE Cloud Phone

echo ========================================
echo Xiaomi Mi 9 SE Cloud Phone
echo ========================================
echo.

REM Check adb.exe
if not exist "%ADB%" (
    echo ERROR: adb.exe not found:
    echo %ADB%
    echo.
    pause
    exit /b 1
)

REM Check scrcpy.exe
where scrcpy.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: scrcpy.exe is not available in PATH.
    echo.
    echo Test this command manually:
    echo where scrcpy
    echo.
    pause
    exit /b 1
)

REM Start ADB server
echo [1/3] Starting ADB...
"%ADB%" start-server >nul 2>&1

REM Check specified phone
echo [2/3] Checking device %SERIAL%...
"%ADB%" -s "%SERIAL%" get-state >nul 2>&1

if errorlevel 1 (
    echo.
    echo ERROR: Device %SERIAL% is not available.
    echo.
    echo Current ADB devices:
    "%ADB%" devices
    echo.
    echo Expected:
    echo %SERIAL%    device
    echo.
    pause
    exit /b 2
)

echo Device connected.
echo.

REM Start scrcpy
echo [3/3] Starting scrcpy...
echo.

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

set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo scrcpy exited with error code %RESULT%.
) else (
    echo scrcpy closed normally.
)

pause
exit /b %RESULT%