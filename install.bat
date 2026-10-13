@echo off
chcp 936 >nul
title 五笔词通 - 安装程序
setlocal enabledelayedexpansion

REM ---- 第一件事：建日志文件（就算窗口看不见，日志也一定在）----
set "LOG=%~dp0install-log.txt"
echo [%date% %time%] 脚本已启动 > "%LOG%"


REM ---- 保险1：窗口先停住，绝不闪退 ----
echo 正在启动五笔词通安装程序...
echo 如果这行字你都看不到，说明系统拦了 .bat 脚本运行。
echo.
pause

REM ---- 保险2：先自检安装包完整性 ----
if exist "%~dp0校验安装包.py" (
  where python >nul 2>&1 && (
    echo [自检] 正在校验安装包完整性...
    python "%~dp0校验安装包.py" "%~dp0"
    echo.
  )
)

echo.
echo ============================================
echo           五笔词通 · 五笔拼音中英混输自造词
echo                     v1.0.0
echo ============================================
echo.
echo   bat 用不了？打开这个文件看手动安装步骤：
echo     %~dp0使用说明\手动安装指南.md
echo.
echo   如果这个窗口一闪而过，请看同目录的
echo   install-log.txt，里面有出错原因。
echo.
echo ============================================
echo.

REM ---- 1. 定位 Rime 安装目录 ----
set "RIME="

REM 策略A：注册表（官方安装版有，绿色版没有）
for /f "tokens=2,*" %%a in ('reg query "HKLM\SOFTWARE\Rime\Weasel" /v InstallPath 2^>nul ^| find "InstallPath"') do set "RIME=%%b"
for /f "tokens=2,*" %%a in ('reg query "HKCU\SOFTWARE\Rime\Weasel" /v InstallPath 2^>nul ^| find "InstallPath"') do set "RIME=%%b"

REM 策略B：扫盘符，用 installation.yaml + build 双标志确认
if not defined RIME (
  for %%d in (C D E F G) do (
    for %%s in ("%%d:\Program Files\Rime" "%%d:\Program Files (x86)\Rime" "%%d:\Rime" "%%d:\Apps\Rime" "%%d:\小狼毫") do (
      if exist "%%~s\installation.yaml" if exist "%%~s\build" (
        set "RIME=%%~s"
        goto :found
      )
    )
  )
)

:found
REM 策略C：兜底 — 扫当前用户目录下可能的位置
if not defined RIME (
  for %%s in ("%USERPROFILE%\AppData\Roaming\Rime" "%LOCALAPPDATA%\Rime") do (
    if exist "%%~s\installation.yaml" if exist "%%~s\build" (
      set "RIME=%%~s"
    )
  )
)

if not defined RIME goto :notfound

echo [OK] 找到 Rime 目录: %RIME%
echo [OK] 找到 Rime 目录: %RIME% >> "%LOG%"

REM ---- 2. 验证安装源 ----
set "SRC=%~dp0rime"
if not exist "%SRC%\wubi_pinyin.schema.yaml" (
  echo [X] 找不到安装源文件
  echo     期望: %SRC%\wubi_pinyin.schema.yaml
  echo     原因：zip 没有完整解压，或缺少 rime 子目录 >> "%LOG%"
  echo     解决办法：按 使用说明\手动安装指南.md 手动复制
  echo.
  goto :fail
)
echo [OK] 安装源: %SRC%
echo [OK] 安装源: %SRC% >> "%LOG%"

REM ---- 3. 备份 ----
echo.
echo [1/4] 备份原配置...
set "BAK=%RIME%\_wbcitong_backup"
mkdir "%BAK%" 2>nul
if exist "%BAK%" (
  for %%f in (wubi_pinyin.schema.yaml wubi_pinyin.custom.yaml default.custom.yaml wubi86.dict.yaml wubi86_jidian.dict.yaml) do (
    if exist "%RIME%\%%f" copy /y "%RIME%\%%f" "%BAK%\" >nul 2>&1
  )
  if exist "%RIME%\lua\inputShow_Filter.lua" copy /y "%RIME%\lua\inputShow_Filter.lua" "%BAK%\" >nul 2>&1
  echo       已备份到: %BAK%
  echo       已备份 >> "%LOG%"
) else (
  echo       [!] 无法创建备份目录，建议以管理员身份运行
  echo       [!] 备份失败 >> "%LOG%"
)

REM ---- 4. 复制 lua ----
echo [2/5] 复制 lua 滤镜...
if not exist "%RIME%\lua" mkdir "%RIME%\lua"
copy /y "%SRC%\lua\*.lua" "%RIME%\lua\" >nul 2>&1
echo       完成

REM ---- 4b. 复制自定义短语表（custom_phrase 用 stabledb，改内容不会触发自动重编）----
echo [3/5] 复制自定义短语表...
if exist "%SRC%\Custom_phrase.txt" (
  copy /y "%SRC%\Custom_phrase.txt" "%RIME%\" >nul 2>&1
  echo       已安装（可用自定义短语，如直接打 ri0977 上屏）
) else (
  echo       [!] 包内无 Custom_phrase.txt
)

REM ---- 5. 复制词库与方案 ----
echo [4/5] 复制词库与方案（约 20 MB，请稍候）...
copy /y "%SRC%\*.yaml" "%RIME%\" >nul 2>&1
echo       已复制全部 .yaml 方案与词库
echo       已复制全部 yaml >> "%LOG%"

REM ---- 6. 自造词 ----
echo [5/5] 自造词
echo       万能五笔自造词已随词表一并安装（wubi86 依赖它们，缺了无法编译）
echo       自造词原文件另存于 rime\我的自造词_可选\ 目录

echo.
echo ============================================


REM ---- 7. 自动触发 Rime 重新部署 ----
echo [5/5] 触发小狼毫重新部署（编译词库，约 1-2 分钟，请勿关机）...
set "DEPLOY="
for /f "delims=" %%d in ('dir /b /s "%RIME%\WeaselDeployer.exe" 2^>nul') do if not defined DEPLOY set "DEPLOY=%%d"
if defined DEPLOY (
  start "" "%DEPLOY%"
  echo       已唤起部署器，正在编译...
) else (
  taskkill /f /im WeaselServer.exe >nul 2>&1
  set "SV="
  for /f "delims=" %%d in ('dir /b /s "%RIME%\WeaselServer.exe" 2^>nul') do if not defined SV set "SV=%%d"
  if defined SV (
    start "" "%SV%"
    echo       已重启小狼毫（部署会在启动时自动执行）
  ) else (
    echo       [!] 找不到部署器，请手动操作（见下方步骤）
  )
)
echo       已触发部署 >> "%LOG%"
echo.
echo ============================================
echo   文件安装完成！
echo ============================================
echo.
echo 部署完成后请做：
echo.
echo   1. 等待编译完成（首次约 1-2 分钟，build 目录文件数不再增加即完成）
echo   2. 按 F4 选「五笔·拼音」
echo.
echo   若部署失败：请把 %LOG% 的内容发出来排查。
echo.
echo 验证：打 vb 应出「好」+ good
echo.
echo 日志: %LOG%
echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1

:notfound
echo [X] 没找到小狼毫（Rime）安装目录
echo [X] 没找到 Rime 目录 >> "%LOG%"
echo.
echo ============================================
echo   改用【手动安装】吧，3 分钟搞定
echo ============================================
echo.
echo 打开这个文件，按里面步骤做：
echo.
echo     %~dp0使用说明\手动安装指南.md
echo.
echo 简单说就三步：
echo.
echo   1. 找 Rime 目录：托盘右键小狼毫 -^> 用户文件夹
echo      ^（该目录里一定有 installation.yaml 和 build^）
echo.
echo   2. 把本包 rime 文件夹里所有 .yaml 文件、
echo      连同 lua 子目录，复制到 Rime 目录（覆盖）
echo.
echo   3. 退出小狼毫 -^> 重开 -^> 托盘右键【重新部署】
echo.
echo 另：双击 bat 闪退请右键选「以管理员身份运行」。
echo     bat 显示乱码就直接看手动指南，不影响手动安装。
echo.
echo 下载小狼毫: https://github.com/rime/weasel/releases
echo.
echo 日志: %LOG%
echo.
pause
exit /b 1
