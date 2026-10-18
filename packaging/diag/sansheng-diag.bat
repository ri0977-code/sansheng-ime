@echo off
rem Sansheng IME install diagnostic - read only, writes sansheng-diag.txt to the Desktop.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sansheng-diag.ps1"
echo.
pause
