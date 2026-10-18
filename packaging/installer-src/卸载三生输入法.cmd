@echo off
REM 双击即可运行 · 三生输入法卸载（默认预演，看清单后再选“执行卸载”）
REM 注意：本文件必须存成 ANSI/GBK + CRLF，否则 cmd 解析中文行会串位（详见工作记录 §二十一）
cd /d "%~dp0"
set /p GO=直接回车 = 只看预演清单；输入 Y 再回车 = 真的卸载（会弹一次管理员授权）：
if /I "%GO%"=="Y" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0卸载三生输入法.ps1" -Apply
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0卸载三生输入法.ps1"
)
echo.
pause
