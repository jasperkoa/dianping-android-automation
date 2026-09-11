@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if exist "%~dp0config.local.cmd" call "%~dp0config.local.cmd"

if exist "%~dp0.venv\Scripts\python.exe" goto run_venv
where py.exe >nul 2>&1
if not errorlevel 1 goto run_py
where python.exe >nul 2>&1
if not errorlevel 1 goto run_python

echo ERROR: Python 3 was not found.
set "RESULT=2"
goto done

:run_venv
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0src\auto_apply.py" %*
set "RESULT=%errorlevel%"
goto done

:run_py
py -3 -X utf8 "%~dp0src\auto_apply.py" %*
set "RESULT=%errorlevel%"
goto done

:run_python
python.exe -X utf8 "%~dp0src\auto_apply.py" %*
set "RESULT=%errorlevel%"

:done
echo.
echo Exit code: %RESULT%
if not defined NO_PAUSE pause
exit /b %RESULT%
