@echo off
setlocal
call "%~dp0run.cmd" --inspect %*
exit /b %errorlevel%
