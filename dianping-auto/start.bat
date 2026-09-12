@echo off
setlocal
call "%~dp0run.cmd" %*
exit /b %errorlevel%
