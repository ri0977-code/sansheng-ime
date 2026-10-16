@echo off
rem ============================================================
rem Sansheng Input Method - reset auto-tuning (user dictionary)
rem Backs up then removes wubi_pinyin.userdb so Rime relearns
rem your word choices from scratch. Does NOT touch dictionaries,
rem lua, or any config. Safe to run any time.
rem ============================================================
setlocal enabledelayedexpansion

set FOUND=0
set STAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set STAMP=%STAMP: =0%

for %%D in ("%APPDATA%\Rime" "D:\Program Files\Rime" "C:\Program Files\Rime") do (
  if exist "%%~D\wubi_pinyin.userdb" (
    set /a FOUND+=1
    copy /Y "%%~D\wubi_pinyin.userdb" "%%~D\wubi_pinyin.userdb.bak-%STAMP%" >nul
    del "%%~D\wubi_pinyin.userdb"
    echo Reset: %%~D\wubi_pinyin.userdb ^(backup: wubi_pinyin.userdb.bak-%STAMP%^)
  )
)

if "%FOUND%"=="0" (
  echo No wubi_pinyin.userdb found - nothing to reset.
) else (
  echo.
  echo Done. Right-click Weasel tray icon and choose Redeploy.
  echo Your input habits will be relearned from scratch.
)
pause
