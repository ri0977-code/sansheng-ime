@echo off
REM 双击即可运行 · 三生输入法检查更新（有新版时可选「自动下载安装包」）
REM 注意：本文件必须存成 ANSI/GBK + CRLF，否则 cmd 解析中文行会串位（详见工作记录 §二十一）
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0检查更新.ps1"
echo.
pause
