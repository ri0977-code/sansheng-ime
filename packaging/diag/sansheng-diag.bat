@echo off
rem Sansheng IME read-only install diagnostic - writes only one text file to the Desktop.
rem Forces the 64-bit PowerShell so System32 / Classes\CLSID are the real 64-bit views.
"%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0sansheng-diag.ps1"
echo.
pause
