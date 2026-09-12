@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0dianping-auto\run.cmd" --inspect
exit /b %errorlevel%
