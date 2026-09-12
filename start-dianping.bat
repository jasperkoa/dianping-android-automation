@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "LIMIT=0"
set "MAX_SCROLLS=0"
call "%~dp0dianping-auto\run.cmd" --input uhid --limit %LIMIT% --max-scrolls %MAX_SCROLLS% %*
exit /b %errorlevel%
