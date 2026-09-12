@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "DP_PYTHON="
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "DP_PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"
if defined DP_PYTHON goto run
if exist "D:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" set "DP_PYTHON=D:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
if defined DP_PYTHON goto run
where python.exe >nul 2>&1
if errorlevel 1 goto missing
set "DP_PYTHON=python.exe"
:run
"%DP_PYTHON%" -X utf8 "%~dp0auto_apply.py" %*
set "DP_RESULT=%errorlevel%"
goto done
:missing
echo ERROR: Python 3 is not installed or cannot be found.
set "DP_RESULT=2"
:done
echo.
echo Exit code: %DP_RESULT%
if not defined DIANPING_NO_PAUSE pause
exit /b %DP_RESULT%
