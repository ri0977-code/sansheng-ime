@echo off
rem ============================================================
rem Sansheng Input Method - installer for codeLookup_Filter
rem Backup Rime files, copy lua, wire up rime.lua and yaml.
rem Run this bat from the folder that contains codeLookup_Filter.lua
rem ============================================================
setlocal enabledelayedexpansion

rem --- 1. locate Rime dir ---
set RIME=
if exist "%APPDATA%\Rime\wubi_pinyin.custom.yaml" set RIME=%APPDATA%\Rime
if not defined RIME if exist "D:\Program Files\Rime\wubi_pinyin.custom.yaml" set RIME=D:\Program Files\Rime
if not defined RIME if exist "C:\Program Files\Rime\wubi_pinyin.custom.yaml" set RIME=C:\Program Files\Rime
if not defined RIME (
  echo [ERROR] Cannot find Rime dir. Edit this script to set RIME manually.
  pause
  exit /b 1
)
echo Rime dir: %RIME%

rem --- 2. backup with timestamp ---
set STAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set STAMP=%STAMP: =0%
set BAK=%RIME%\sansheng-backup-%STAMP%
mkdir "%BAK%" 2>nul
if exist "%RIME%\lua\codeLookup_Filter.lua" copy /Y "%RIME%\lua\codeLookup_Filter.lua" "%BAK%\" >nul
if exist "%RIME%\rime.lua" copy /Y "%RIME%\rime.lua" "%BAK%\" >nul
if exist "%RIME%\wubi_pinyin.custom.yaml" copy /Y "%RIME%\wubi_pinyin.custom.yaml" "%BAK%\" >nul
echo Backup -> %BAK%

rem --- 3. copy lua from script dir ---
set SRC=%~dp0
if not exist "%SRC%codeLookup_Filter.lua" (
  echo [ERROR] codeLookup_Filter.lua not found next to this script.
  pause
  exit /b 1
)
if not exist "%RIME%\lua" mkdir "%RIME%\lua"
copy /Y "%SRC%codeLookup_Filter.lua" "%RIME%\lua\codeLookup_Filter.lua" >nul
echo Copied codeLookup_Filter.lua -> lua/

rem --- 4. add require to rime.lua (idempotent) ---
set RL=%RIME%\rime.lua
findstr /C:"codeLookup_Filter" "%RL%" >nul 2>&1
if errorlevel 1 (
  echo codeLookup_Filter = require("codeLookup_Filter")>>"%RL%"
  echo Added require line to rime.lua
) else (
  echo rime.lua already references codeLookup_Filter, skipped
)

rem --- 5. insert lua_filter into wubi_pinyin.custom.yaml (idempotent, via powershell) ---
powershell -NoProfile -Command "$f='%RIME%\wubi_pinyin.custom.yaml'; $t=Get-Content $f -Raw; if($t -notmatch 'lua_filter@codeLookup_Filter'){ if($t -match 'pinyinAdding_Filter'){ $t=$t -replace '(?m)(- lua_filter@pinyinAdding_Filter)',('$1'+[Environment]::NewLine+'  - lua_filter@codeLookup_Filter'); Set-Content -Path $f -Value $t -NoNewline; Write-Host 'Inserted lua_filter@codeLookup_Filter after pinyinAdding_Filter' } else { Write-Host 'WARNING: pinyinAdding_Filter not found; please manually add: - lua_filter@codeLookup_Filter under engine/filters' } } else { Write-Host 'yaml already has codeLookup_Filter, skipped' }"

echo.
echo Done. Right-click Weasel tray icon and choose Redeploy.
pause
