@echo off
chcp 65001 >nul
title 五笔词通 - 安装程序
setlocal enabledelayedexpansion

echo.
echo ============================================
echo           五笔词通 · 五笔拼音中英混输自造词
echo                     v1.0.0
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

if not defined RIME (
  goto :notfound
)

echo [OK] 找到 Rime 目录: %RIME%

REM ---- 2. 验证安装源 ----
set "SRC=%~dp0rime"
if not exist "%SRC%\wubi_pinyin.schema.yaml" (
  echo [X] 找不到安装源文件
  echo     期望: %SRC%\wubi_pinyin.schema.yaml
  echo.
  echo     可能原因：zip 没有完整解压，或缺少 rime 子目录
  echo.
  pause
  exit /b 1
)
echo [OK] 安装源: %SRC%

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
) else (
  echo       [!] 无法创建备份目录（权限不足？）
)

REM ---- 4. 复制 lua ----
echo [2/4] 复制 lua 滤镜...
if not exist "%RIME%\lua" mkdir "%RIME%\lua"
copy /y "%SRC%\lua\*.lua" "%RIME%\lua\" >nul
echo       完成

REM ---- 5. 复制词库与方案 ----
echo [3/4] 复制词库与方案（约 20 MB，请稍候）...
set "N=0"
for %%f in (
  wubi_pinyin.schema.yaml
  wubi_pinyin.custom.yaml
  wubi86_jidian_pinyin.schema.yaml
  wubi86_jidian_trad_pinyin.schema.yaml
  default.custom.yaml
  cn_pinyin_wp.dict.yaml
  cn_pinyin_py.dict.yaml
  zh2en_pinyin_wp.dict.yaml
  zh2en_pinyin_py.dict.yaml
  zh2en_wubi_wp.dict.yaml
  zh2en_wubi_py.dict.yaml
  en2zh_v2_wp.dict.yaml
  en2zh_v2_py.dict.yaml
  wubi86.dict.yaml
  wubi86_jidian.dict.yaml
  wubi86_jidian_py.dict.yaml
  pinyin_simp.dict.yaml
) do (
  if exist "%SRC%\%%f" (
    copy /y "%SRC%\%%f" "%RIME%\" >nul && set /a N+=1
  )
)
echo       已复制 !N! 个文件

REM ---- 6. 自造词提示 ----
echo [4/4] 自造词（可选）
if exist "%SRC%\我的自造词_可选" (
  echo       你的万能五笔自造词在「我的自造词_可选」目录
  echo       默认不安装。如需继承，看 使用说明\README.md 第 2 节。
) else (
  echo       （包内无自造词文件）
)

echo.
echo ============================================
echo   安装完成！
echo ============================================
echo.
echo 接下来请做：
echo.
echo   1. 退出小狼毫（托盘图标右键 → 退出）
echo   2. 重新打开小狼毫
echo   3. 托盘右键 → 【重新部署】     ← 关键，必须做
echo   4. 按 F4 选「五笔·拼音」
echo.
echo 验证：打 vb 应出「好」+ good
echo.
pause
exit /b 0

:notfound
echo [X] 没找到小狼毫（Rime）安装目录
echo.
echo 请检查：
echo.
echo   1. 是否已安装小狼毫？
echo      下载地址: https://github.com/rime/weasel/releases
echo
echo   2. 如果装在特殊路径，请手动安装：
echo      - 把 rime 文件夹里的所有文件复制到 Rime 安装目录
echo      - 打开小狼毫 → 托盘右键 → 重新部署
echo
echo   3. 或手动告诉我路径，我帮你重新生成脚本
echo.
pause
exit /b 1
