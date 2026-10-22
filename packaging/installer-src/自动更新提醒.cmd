@echo off
REM 自动更新提醒的包装器 —— 计划任务指向本文件，而不是直接指向 .ps1。
REM 为什么要这一层：schtasks 的 /TR 参数在命令行解析里会把带空格的路径
REM （典型如 C:\Program Files\...）拆成两段，直接写 -File "C:\Program Files\x.ps1"
REM 会被判成非法参数。绕法有两种，这里选更稳的一种：
REM   1) 任务 /TR 指向本 .cmd（路径不带空格就不怕被拆；带空格时由 Task Scheduler 以文件路径方式取用）；
REM   2) 内部用 pushd + 短名 8.3 路径执行 .ps1，彻底避开空格。
REM 本文件必须存成 ANSI/GBK + CRLF，否则 cmd 解析中文脚本名会出错。

setlocal
pushd "%~dp0"
for %%F in ("自动更新提醒.ps1") do set "PS1=%%~fF"
if not exist "%PS1%" (
  echo update-notice script missing: %~dp0自动更新提醒.ps1 >&2
  popd
  exit /quiet 2
)
powershell -NoProfile -WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File "%PS1%"
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%