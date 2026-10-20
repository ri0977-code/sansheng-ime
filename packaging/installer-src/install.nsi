!include "MUI2.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"

Name "三生输入法"
OutFile "三生输入法-v1.9.10-setup.exe"
InstallDir "$PROGRAMFILES64\Rime"
RequestExecutionLevel admin

!define MUI_ICON "config\icon-sansheng-tray.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ---- 卸载程序界面（v1.9 新增，须排在 MUI_LANGUAGE 之前）----
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"

; 程序和功能 / Add-Remove Programs 里的登记键
!define UN_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\SanshengIME"
!define TIP_CLSID "{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}"
!define TIP_GUID  "{3D02CAB6-2B8E-4781-BA20-1C9267529467}"

; 官方小狼毫（Weasel）的登记位置。三生与官方版共用同一个 TIP CLSID 和
; System32/SysWOW64 里的 weasel.dll，两者不能共存，所以安装时要识别并接管。
!define WEASEL_UN_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Weasel"
!define RIME_WEASEL_KEY "Software\Rime\Weasel"

; 用户 Rime 目录用 $R9（$0-$9 会被 ExecWait 返回值复用）

; 安装目录默认值：
;   1) 命令行 /D= 指定时完全尊重用户；
;   2) 已装官方小狼毫 -> 沿用官方 InstallDir，直接原地覆盖，避免在 C 盘再装一份；
;   3) 已装三生 -> 沿用上次安装目录；
;   4) 全新机器 -> $PROGRAMFILES64\Rime。
; 这段必须在页面创建前跑，目录页才会显示正确的默认路径。
Function .onInit
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/D=" $R1
  ${IfNot} ${Errors}
    Return
  ${EndIf}

  ; 官方小狼毫的安装根目录（官方安装器是 32 位，优先读 32 位视图）
  StrCpy $R1 ""
  SetRegView 32
  ReadRegStr $R1 HKLM "${RIME_WEASEL_KEY}" "InstallDir"
  ${If} ${RunningX64}
    ${If} $R1 == ""
      SetRegView 64
      ReadRegStr $R1 HKLM "${RIME_WEASEL_KEY}" "InstallDir"
      SetRegView 32
    ${EndIf}
  ${EndIf}
  ${If} $R1 != ""
  ${AndIf} ${FileExists} "$R1\*.*"
    StrCpy $INSTDIR $R1
    Return
  ${EndIf}

  ; 三生自己的上次安装目录（写在 64 位视图的卸载键里）
  StrCpy $R1 ""
  SetRegView 64
  ReadRegStr $R1 HKLM "${UN_KEY}" "InstallLocation"
  ${If} ${RunningX64}
    ${If} $R1 == ""
      SetRegView 32
      ReadRegStr $R1 HKLM "${UN_KEY}" "InstallLocation"
    ${EndIf}
  ${EndIf}
  SetRegView 32
  ${If} $R1 != ""
  ${AndIf} ${FileExists} "$R1\*.*"
    StrCpy $INSTDIR $R1
  ${EndIf}
FunctionEnd

Section "MainSection"
  ; ===== 0a. 识别官方小狼毫 / 旧版三生 =====
  ; 官方小狼毫（Weasel）与三生共用同一套 TIP CLSID、同一个 System32/
  ; SysWOW64 weasel.dll、同一个默认安装目录和同一个 Rime 用户目录。
  ; 两者不是两套可以并存的输入法，装过官方的机器再装三生，必须由三生
  ; 接管：保留词库和用户目录，先卸掉官方的注册与自启，再装三生的引擎。
  ; 用户不需要先去「程序和功能」里手动卸载小狼毫。
  StrCpy $R7 "0"   ; 1 = 检测到官方小狼毫
  StrCpy $R6 "0"   ; 1 = 已装过三生（普通升级，不再询问）
  StrCpy $R8 ""    ; 官方引擎目录（WeaselRoot）

  ; 三生自己的卸载登记：两个注册表视图都查，兼容旧版本或手工安装
  SetRegView 64
  ReadRegStr $R5 HKLM "${UN_KEY}" "DisplayVersion"
  ${If} $R5 != ""
    StrCpy $R6 "1"
  ${EndIf}
  ${If} ${RunningX64}
    SetRegView 32
    ReadRegStr $R5 HKLM "${UN_KEY}" "DisplayVersion"
    ${If} $R5 != ""
      StrCpy $R6 "1"
    ${EndIf}
  ${EndIf}

  ; 官方卸载登记 + 官方引擎目录
  SetRegView 64
  ReadRegStr $R5 HKLM "${WEASEL_UN_KEY}" "DisplayVersion"
  ${If} $R5 != ""
    StrCpy $R7 "1"
  ${EndIf}
  ReadRegStr $R8 HKLM "${RIME_WEASEL_KEY}" "WeaselRoot"
  ${If} ${RunningX64}
    SetRegView 32
    ReadRegStr $R5 HKLM "${WEASEL_UN_KEY}" "DisplayVersion"
    ${If} $R5 != ""
      StrCpy $R7 "1"
    ${EndIf}
    ReadRegStr $R4 HKLM "${RIME_WEASEL_KEY}" "WeaselRoot"
    ${If} $R8 == ""
      StrCpy $R8 $R4
    ${EndIf}
  ${EndIf}

  ; 只剩 Rime 键、卸载键已经丢了的半残安装也要接管
  ${If} $R8 != ""
    StrCpy $R7 "1"
  ${EndIf}

  ; WeaselRoot 没写时按官方默认布局推算
  ${If} $R7 == "1"
  ${AndIf} $R8 == ""
    SetRegView 64
    ReadRegStr $R8 HKLM "${RIME_WEASEL_KEY}" "InstallDir"
    ${If} ${RunningX64}
      SetRegView 32
      ReadRegStr $R4 HKLM "${RIME_WEASEL_KEY}" "InstallDir"
      ${If} $R8 == ""
        StrCpy $R8 $R4
      ${EndIf}
    ${EndIf}
    ${If} $R8 != ""
      StrCpy $R8 "$R8\weasel-0.17.4"
    ${Else}
      StrCpy $R8 "$INSTDIR\weasel-0.17.4"
    ${EndIf}
  ${EndIf}

  ; 用户 Rime 目录必须在任何卸载/清理之前读出来。
  ; 官方 WeaselSetup /u 只清 HKLM，不会动 HKCU 和用户目录，但先读更稳。
  SetRegView 64
  ReadRegStr $R9 HKCU "${RIME_WEASEL_KEY}" "RimeUserDir"
  ${If} $R9 == ""
    StrCpy $R9 "$APPDATA\Rime"
  ${EndIf}

  DetailPrint "检测结果：官方小狼毫=$R7，已装三生=$R6，官方引擎=$R8"
  DetailPrint "Rime 用户目录: $R9"

  ; 第一次从官方小狼毫切到三生时只问一次；三生自己的升级不再打扰。
  ; 静默安装（/S）直接接管，方便批量部署。
  ${If} $R7 == "1"
  ${AndIf} $R6 != "1"
    IfSilent sansheng_takeover
    MessageBox MB_OKCANCEL|MB_ICONQUESTION "检测到本机已安装官方小狼毫（Rime Weasel）。$\n$\n三生输入法会直接接管安装，不需要先手动卸载小狼毫：$\n - 保留你的词库、打字记录和 Rime 用户目录$\n - 旧配置先备份到 sansheng-backup-时间戳$\n - 自动移除官方输入法登记并安装成三生$\n$\n继续安装吗？" IDOK sansheng_takeover
    Abort
  ${EndIf}

sansheng_takeover:
  ; ===== 0b. 先把小狼毫结束掉（覆盖安装，不用手动退出）=====
  ; 坑：老脚本在第 5 步才 taskkill，而第 1 步的 File /r 早就跑完了。
  ; WeaselServer.exe / WeaselDeployer.exe 正在运行时文件是被占用的，
  ; File /r 覆盖不了它们（NSIS 只会静默跳过），于是「装了新版、引擎还是旧版」。
  ; 所以任何 File / CopyFiles 之前必须先杀进程。第 5 步再杀一次是保险：
  ; 中间只要切出去打过字，WeaselServer 就会被输入法重新拉起来。
  DetailPrint "结束小狼毫进程（覆盖安装，无需手动退出）..."
  ExecWait 'taskkill /f /im WeaselServer.exe' $0
  ExecWait 'taskkill /f /im WeaselDeployer.exe' $0
  ExecWait 'taskkill /f /im WeaselSetup.exe' $0
  Sleep 800

  ; ===== 0c. 接管官方小狼毫 =====
  ${If} $R7 == "1"
    ; 官方 WeaselSetup 只认 /u 一个参数，写成 "/u /s" 会被当成未知参数而不卸载。
    ; /u 本身就是静默卸载（源码里 silent = true），不会弹窗。
    ${If} $R8 != ""
    ${AndIf} ${FileExists} "$R8\WeaselSetup.exe"
      DetailPrint "调用官方卸载：$R8\WeaselSetup.exe /u"
      ExecWait '"$R8\WeaselSetup.exe" /u' $0
      DetailPrint "官方卸载返回码: $0"
      Sleep 500
    ${Else}
      DetailPrint "未找到官方 WeaselSetup.exe，跳过 /u，直接清理登记并覆盖 DLL。"
    ${EndIf}

    ; 官方卸载键不区分视图，两个都删；同时删官方 Rime 键和 HKLM 自启。
    ; 官方安装器是 32 位，常见位置在 WOW6432Node，但也可能被写进 64 位视图。
    SetRegView 64
    DeleteRegKey HKLM "${WEASEL_UN_KEY}"
    DeleteRegKey HKLM "${RIME_WEASEL_KEY}"
    DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "WeaselServer"
    ${If} ${RunningX64}
      SetRegView 32
      DeleteRegKey HKLM "${WEASEL_UN_KEY}"
      DeleteRegKey HKLM "${RIME_WEASEL_KEY}"
      DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "WeaselServer"
    ${EndIf}
    SetRegView 64

    ; 官方开始菜单（简/繁/英三套名字，当前用户和所有用户都清）
    SetShellVarContext all
    RMDir /r "$SMPROGRAMS\小狼毫输入法"
    RMDir /r "$SMPROGRAMS\小狼毫輸入法"
    RMDir /r "$SMPROGRAMS\Weasel"
    SetShellVarContext current
    RMDir /r "$SMPROGRAMS\小狼毫输入法"
    RMDir /r "$SMPROGRAMS\小狼毫輸入法"
    RMDir /r "$SMPROGRAMS\Weasel"

    ; 官方装在别的目录时不整目录删（那是用户自选路径），只去掉它的卸载入口，
    ; 避免「程序和功能」里留下一个指向空壳的条目。
    ${If} $R8 != ""
    ${AndIf} $R8 != "$INSTDIR\weasel-0.17.4"
      Delete "$R8\uninstall.exe"
    ${EndIf}
  ${EndIf}

  ; ===== 1. 安装 weasel 引擎 =====
  ; 接管官方版时先把旧引擎目录清空。File /r 只覆盖同名文件，不会删除新版
  ; 已经去掉的旧文件（官方的 uninstall.exe、旧 DLL 等），不清空就会新旧混杂。
  ${If} $R7 == "1"
  ${AndIf} "$INSTDIR\weasel-0.17.4" != $R9
    DetailPrint "清空旧引擎目录：$INSTDIR\weasel-0.17.4"
    RMDir /r "$INSTDIR\weasel-0.17.4"
  ${EndIf}

  SetOutPath "$INSTDIR\weasel-0.17.4"
  File /r "weasel-0.17.4\*"

  ; 验证 WeaselServer.exe
  IfFileExists "$INSTDIR\weasel-0.17.4\WeaselServer.exe" 0 +4
    DetailPrint "WeaselServer.exe OK"
    Goto engine_ok
    MessageBox MB_ICONSTOP "错误：WeaselServer.exe 未释放成功！"
    Abort

engine_ok:
  ; ===== 2. 部署用户配置到 Rime 用户目录 =====
  ; 用户目录已在 0a 步读出（HKCU\Software\Rime\Weasel -> RimeUserDir，
  ; 没有才用 %APPDATA%\Rime），这里只保证目录存在，绝不改写原路径。
  IfFileExists "$R9\*.*" 0 +2
    Goto userdir_ready
    CreateDirectory "$R9"

userdir_ready:
  DetailPrint "Rime 用户目录: $R9"

  ; 铺配置之前，先把该目录里已有的配置备份一份（带时间戳），出问题能回滚
  SetOutPath "$TEMP"
  File "backup-user-config.ps1"
  ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$TEMP\backup-user-config.ps1" -Dir "$R9"' $0
  DetailPrint "旧配置备份返回: $0"
  Delete "$TEMP\backup-user-config.ps1"

  SetOutPath "$R9"
  ; 把 config 目录里的配置文件释放到用户配置目录。
  ; Custom_phrase.txt 是用户自造词（用户数据），升级时必须保留原文件：
  ; 旧安装器用 File /r 直接覆盖，把用户自己加的短语换成了空白模板（备份里虽然有，
  ; 但用户不知道要去找）。这里排除它，只有文件不存在（全新安装）时才写模板。
  File /r /x "Custom_phrase.txt" "config\*"
  IfFileExists "$R9\Custom_phrase.txt" custom_phrase_ready
    File "config\Custom_phrase.txt"
custom_phrase_ready:

  ; 简繁转换数据：用户目录再放一份（shared + user 两个搜索根都覆盖，最稳）
  SetOutPath "$R9\opencc"
  File /r "weasel-0.17.4\data\opencc\*"
  SetOutPath "$R9"

  DetailPrint "配置文件已释放到 $R9"

  ; ===== 3. 把图标文件复制到安装根目录（注册表 IconFile 指向这里） =====
  SetOutPath "$INSTDIR"
  ExecWait 'cmd /c copy /y "$R9\icon-sansheng-tray.ico" "$INSTDIR\icon-sansheng-tray.ico"'
  ; v1.9.9：不再复制 icon-sansheng-cn/-en.ico（10-16 之后停更的老图，配置里已无引用）；
  ;          卸载段仍保留对这两个文件的 Delete，用来清掉老版本安装留下的残留文件。

  ; 验证图标
  IfFileExists "$INSTDIR\icon-sansheng-tray.ico" 0 +4
    DetailPrint "icon OK"
    Goto icon_ok
    MessageBox MB_ICONSTOP "错误：图标文件复制失败！"
    Abort

icon_ok:
  ; ===== 4. 释放注册表文件到临时目录 =====
  SetOutPath "$TEMP"
  File "weasel-clsid.reg"
  File "weasel-tip.reg"
  ${If} ${RunningX64}
    File "weasel-clsid32.reg"
    File "weasel-tip32.reg"
  ${EndIf}

  IfFileExists "$TEMP\weasel-clsid.reg" 0 +4
    DetailPrint "reg file OK"
    Goto reg_ok
    MessageBox MB_ICONSTOP "错误：注册表文件未释放到临时目录！"
    Abort

reg_ok:
  SetOverwrite on

  ; ===== 5. 复制 DLL 到系统目录 =====
  ; 坑（v1.9 笔记本装不上的根因之一）：本安装器是 32 位程序，
  ; 32 位进程里写 %WINDIR%\System32 会被 WOW64 文件重定向悄悄改到 SysWOW64，
  ; 于是 64 位 weasel.dll 永远进不了 System32，64 位程序一个都加载不上三生。
  ; 所以这一步必须先关掉重定向再复制、再校验（校验不关重定向同样会被骗）。
  ExecWait 'taskkill /f /im WeaselServer.exe' $0
  ExecWait 'taskkill /f /im WeaselDeployer.exe' $0
  Sleep 800

  ${If} ${RunningX64}
    DetailPrint "复制 64位 DLL 到 System32..."
    ${DisableX64FSRedirection}
    CopyFiles /SILENT "$INSTDIR\weasel-0.17.4\weaselx64.dll" "$WINDIR\System32\weasel.dll"
    ${If} ${FileExists} "$WINDIR\System32\weasel.dll"
      DetailPrint "System32\weasel.dll 已就位（64位那份）✓"
    ${Else}
      ${EnableX64FSRedirection}
      MessageBox MB_ICONSTOP "错误：weasel.dll 没能放进 System32（多半是权限不够）。$\n请右键安装包「以管理员身份运行」重试。$\n安装已中止，未做任何后续注册。"
      Abort
    ${EndIf}
    ${EnableX64FSRedirection}

    DetailPrint "复制 32位 DLL 到 SysWOW64..."
    CopyFiles /SILENT "$INSTDIR\weasel-0.17.4\weasel.dll" "$WINDIR\SysWOW64\weasel.dll"
    ${If} ${FileExists} "$WINDIR\SysWOW64\weasel.dll"
      DetailPrint "SysWOW64\weasel.dll 已就位 ✓"
    ${Else}
      DetailPrint "警告：SysWOW64\weasel.dll 没写成——可能正被 32 位程序占用，注销后重跑安装即可。"
    ${EndIf}
  ${Else}
    DetailPrint "复制 DLL 到 System32..."
    CopyFiles /SILENT "$INSTDIR\weasel-0.17.4\weasel.dll" "$WINDIR\System32\weasel.dll"
    ${If} ${FileExists} "$WINDIR\System32\weasel.dll"
      DetailPrint "System32\weasel.dll 已就位 ✓"
    ${Else}
      MessageBox MB_ICONSTOP "错误：weasel.dll 没能放进 System32（多半是权限不够）。$\n安装已中止，未做任何后续注册。"
      Abort
    ${EndIf}
  ${EndIf}

  ; ===== 6. 导入注册表 =====
  ; 坑（根因之二）：32 位 reg.exe 会把 .reg 里的 HKLM\SOFTWARE\Classes\CLSID
  ; 写进 WOW6432Node\Classes\CLSID，64 位视图读不到 InprocServer32 → 64 位程序加载不了。
  ; 四个 .reg 一律改用 64 位 reg.exe（经 Sysnative 别名取到）导入：
  ; 文件里写的是哪条路径就实实在在落在那条路径，不会被重定向改写。
  ${If} ${RunningX64}
    StrCpy $5 "$WINDIR\Sysnative\reg.exe"
  ${Else}
    StrCpy $5 "reg.exe"
  ${EndIf}

  DetailPrint "导入 CLSID 注册表..."
  ExecWait '"$5" import "$TEMP\weasel-clsid.reg"' $0
  DetailPrint "返回码: $0"

  DetailPrint "导入 TIP 注册表..."
  ExecWait '"$5" import "$TEMP\weasel-tip.reg"' $0
  DetailPrint "返回码: $0"

  ${If} ${RunningX64}
    DetailPrint "导入 32位 CLSID 注册表..."
    ExecWait '"$5" import "$TEMP\weasel-clsid32.reg"' $0
    DetailPrint "返回码: $0"

    DetailPrint "导入 32位 TIP 注册表..."
    ExecWait '"$5" import "$TEMP\weasel-tip32.reg"' $0
    DetailPrint "返回码: $0"
  ${EndIf}

  ; ===== 6b. 硬校验：64 位视图里必须真能读到注册结果 =====
  ; 这一关存在的原因：上面任何一步即使失败，旧脚本也照样会弹「安装完成」，
  ; 装完的机器看着像成功、实际打不出字。读不到就直接中止，不再报喜。
  SetRegView 64
  ReadRegStr $6 HKLM "SOFTWARE\Classes\CLSID\${TIP_CLSID}\InprocServer32" ""
  ReadRegStr $7 HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000804\${TIP_GUID}" "Enable"
  DetailPrint "64位 InprocServer32 = $6"
  DetailPrint "64位 TIP Enable(0x00000804) = $7"
  ${If} $6 == ""
    MessageBox MB_ICONSTOP "错误：64 位视图里读不到 InprocServer32（CLSID 注册没落地）。$\n安装已中止，请勿使用。"
    Abort
  ${EndIf}
  ${If} $7 != "1"
    MessageBox MB_ICONSTOP "错误：64 位视图里三生的 TIP 配置不是启用状态（Enable=$7）。$\n安装已中止，请勿使用。"
    Abort
  ${EndIf}

  ; ===== 7. 动态修正 IconFile 路径 =====
  ${If} ${RunningX64}
    SetRegView 64
  ${Else}
    SetRegView 32
  ${EndIf}

  WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00000804\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
  WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00000404\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
  WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00000c04\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
  WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00001004\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
  WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00001404\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"

  ${If} ${RunningX64}
    SetRegView 32
    WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00000804\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
    WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00000404\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
    WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00000c04\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
    WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00001004\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
    WriteRegStr HKLM "SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x00001404\{3D02CAB6-2B8E-4781-BA20-1C9267529467}" "IconFile" "$INSTDIR\icon-sansheng-tray.ico"
  ${EndIf}

  ; ===== 8. 部署词典（编译配置） =====
  DetailPrint "部署配置和词典..."
  SetOutPath "$INSTDIR\weasel-0.17.4"
  ; 必须写全路径：以前只给个裸文件名，靠「当前输出目录」去解析，
  ; 一旦 NSIS 的工作目录判定跟想的不一样，这句就白跑（返回码照样是 0，看不出来）。
  ; 这次气泡图标是靠 custom.yaml 里的 schema/*_icon 经部署编译进 build/ 才生效的，
  ; 部署静默失败 = 笔记本上气泡还是老图标，所以把路径钉死。
  ExecWait '"$INSTDIR\weasel-0.17.4\WeaselDeployer.exe" /deploy' $0
  DetailPrint "部署返回码: $0"

  ; ===== 9. 开机自启 + 启动 WeaselServer =====
  ; 不写这条，重启后输入法服务不自启，候选窗会出不来
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "WeaselServer" '"$INSTDIR\weasel-0.17.4\WeaselServer.exe"'

  ; 接管官方版后强制关闭官方自动更新（WinSparkle）：
  ; 它开着的话会在后台把三生引擎换回官方新版，等于白装。
  WriteRegStr HKCU "${RIME_WEASEL_KEY}\Updates" "CheckForUpdates" "0"
  DetailPrint "启动 WeaselServer..."
  SetOutPath "$INSTDIR\weasel-0.17.4"
  ExecShell "" "WeaselServer.exe" ""

  ; ===== 10. 释放卸载工具与键盘脚本 =====
  DetailPrint "释放卸载工具..."
  SetOutPath "$INSTDIR\tools"
  File "enable-tip.ps1"
  File "remove-tip.ps1"
  File "卸载三生输入法.ps1"
  File "卸载三生输入法.cmd"
  File "检查更新.ps1"
  File "检查更新.cmd"
  File "反查诊断.ps1"
  File "反查诊断.cmd"

  ; ===== 11. 把三生加入当前用户的键盘列表（免手动去设置里添加）=====
  DetailPrint "注册到输入法列表..."
  ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\tools\enable-tip.ps1" -Tip "0804:${TIP_CLSID}${TIP_GUID}"' $0
  DetailPrint "键盘列表返回: $0"
  ; Win10/Win11 上旧版脚本直接改 InputMethodTips 会因「只读属性」失败，这里重试一次；
  ; 仍失败就明确告警（不再默默报安装成功），静默安装用退出码 2 表示需要人工处理。
  ${If} $0 != 0
    Sleep 800
    ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\tools\enable-tip.ps1" -Tip "0804:${TIP_CLSID}${TIP_GUID}"' $0
    DetailPrint "键盘列表重试返回: $0"
  ${EndIf}
  ${If} $0 != 0
    SetErrorLevel 2
    IfSilent tip_warn_done
    MessageBox MB_ICONEXCLAMATION "三生输入法已安装，但没能自动加入当前用户的键盘列表（返回码 $0）。$\n$\n请打开 设置 > 时间和语言 > 语言和区域 > 中文 > 键盘，手动添加「三生输入法」；或重新运行安装包。"
  ${EndIf}
tip_warn_done:

  ; ===== 12. 开始菜单 + 控制面板卸载入口 =====
  CreateDirectory "$SMPrograms\三生输入法"
  ; 图标必须用 icon-sansheng-tray.ico（金圈三，md5 6939d30208ec）。
  ; 原先这里挂的是 icon-sansheng-cn.ico —— 一张 10-16 之后就没再更新的老图，
  ; 配置与引擎里都没有任何引用（只有安装器在复制/删除它），所以开始菜单那个
  ; 「三生输入法」一直显示旧图标，跟托盘/气泡对不上。仅改图标项，目标与参数不动。
  CreateShortcut "$SMPrograms\三生输入法\三生输入法.lnk" "$INSTDIR\weasel-0.17.4\WeaselServer.exe" "" "$INSTDIR\icon-sansheng-tray.ico"
  CreateShortcut "$SMPrograms\三生输入法\卸载三生输入法.lnk" "$INSTDIR\uninstall-sansheng.exe"
  CreateShortcut "$SMPrograms\三生输入法\检查更新.lnk" "$INSTDIR\tools\检查更新.cmd" "" "$INSTDIR\icon-sansheng-tray.ico"
  CreateShortcut "$SMPrograms\三生输入法\反查诊断.lnk" "$INSTDIR\tools\反查诊断.cmd" "" "$INSTDIR\icon-sansheng-tray.ico"

  WriteUninstaller "$INSTDIR\uninstall-sansheng.exe"
  SetRegView 64
  WriteRegStr HKLM "${UN_KEY}" "DisplayIcon" "$INSTDIR\icon-sansheng-tray.ico"
  WriteRegStr HKLM "${UN_KEY}" "DisplayName" "三生输入法"
  WriteRegStr HKLM "${UN_KEY}" "DisplayVersion" "1.9.10"
  WriteRegStr HKLM "${UN_KEY}" "Publisher" "WorkBuddy"
  WriteRegStr HKLM "${UN_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UN_KEY}" "UninstallString" '"$INSTDIR\uninstall-sansheng.exe"'
  WriteRegStr HKLM "${UN_KEY}" "QuietUninstallString" '"$INSTDIR\uninstall-sansheng.exe" /S'
  WriteRegDWORD HKLM "${UN_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UN_KEY}" "NoRepair" 1

  ; ===== 13. 完成 =====
  ; /S 静默安装不能弹框，否则批处理会一直卡在这里。
  IfSilent install_finish
  MessageBox MB_ICONINFORMATION "安装完成！$\n$\n现在按 Win+空格（或左 Alt+Shift）就能切换到「三生输入法」。$\n如需卸载：控制面板 > 程序和功能 > 三生输入法。"
install_finish:
SectionEnd

; ============================================================
;  卸载段（v1.9 新增）
;  铁律：只删三生自己放进去的东西。
;  Rime 用户目录（词库 / 个人配置 / 用户词典）一概不动，
;  安装目录也只在「删干净后已经空了」的情况下才移除。
; ============================================================
Section "Uninstall"
  DetailPrint "正在卸载三生输入法..."

  ; 0) 记住哪个目录是用户的 Rime 配置目录，稍后绝不碰它
  ReadRegStr $R9 HKCU "Software\Rime\Weasel" "RimeUserDir"
  ${If} $R9 == ""
    StrCpy $R9 "$APPDATA\Rime"
  ${EndIf}
  DetailPrint "Rime 用户目录（保留）: $R9"

  ; 0a) 判断共享输入法组件现在归谁。
  ; 官方小狼毫和三生共用 TIP CLSID、系统 DLL 和同一个引擎目录。如果用户
  ; 在装完三生之后又跑了官方安装包，现在的 weasel.dll / TIP 注册 / 引擎
  ; 都属于官方版。此时三生的卸载器只能删三生自己的东西，绝不能把官方的
  ; 输入法连根拔掉。
  StrCpy $R7 "0"
  SetRegView 64
  ReadRegStr $R5 HKLM "${WEASEL_UN_KEY}" "DisplayVersion"
  ReadRegStr $R8 HKLM "${RIME_WEASEL_KEY}" "WeaselRoot"
  ${If} ${RunningX64}
    SetRegView 32
    ReadRegStr $R4 HKLM "${WEASEL_UN_KEY}" "DisplayVersion"
    ${If} $R5 == ""
      StrCpy $R5 $R4
    ${EndIf}
    ReadRegStr $R4 HKLM "${RIME_WEASEL_KEY}" "WeaselRoot"
    ${If} $R8 == ""
      StrCpy $R8 $R4
    ${EndIf}
  ${EndIf}
  SetRegView 64

  ; WeaselRoot 缺失时按官方 InstallDir + weasel-0.17.4 推算
  ${If} $R5 != ""
  ${AndIf} $R8 == ""
    ReadRegStr $R8 HKLM "${RIME_WEASEL_KEY}" "InstallDir"
    ${If} ${RunningX64}
      SetRegView 32
      ReadRegStr $R4 HKLM "${RIME_WEASEL_KEY}" "InstallDir"
      ${If} $R8 == ""
        StrCpy $R8 $R4
      ${EndIf}
      SetRegView 64
    ${EndIf}
    ${If} $R8 != ""
      StrCpy $R8 "$R8\weasel-0.17.4"
    ${EndIf}
  ${EndIf}

  ${If} $R5 != ""
  ${AndIf} $R8 != ""
  ${AndIf} ${FileExists} "$R8\WeaselSetup.exe"
    StrCpy $R7 "1"
  ${EndIf}
  DetailPrint "共享组件归属检查：官方小狼毫仍在使用=$R7 ($R8)"

  ${If} $R7 == "1"
    Goto uninstall_sansheng_only
  ${EndIf}

  ; 1) 从键盘列表移除
  ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\tools\remove-tip.ps1" -Tip "0804:${TIP_CLSID}${TIP_GUID}"' $0

  ; 2) 停进程
  ExecWait 'taskkill /f /im WeaselServer.exe' $0
  ExecWait 'taskkill /f /im WeaselDeployer.exe' $0
  Sleep 1200

  ; 3) 从输入法表中注销（64 位视图 + 32 位视图）
  SetRegView 64
  DeleteRegKey HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}"
  DeleteRegKey HKLM "SOFTWARE\Classes\CLSID\${TIP_CLSID}"
  ${If} ${RunningX64}
    SetRegView 32
    DeleteRegKey HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}"
    DeleteRegKey HKLM "SOFTWARE\Classes\CLSID\${TIP_CLSID}"
    SetRegView 64
  ${EndIf}
  DeleteRegKey HKLM "${UN_KEY}"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "WeaselServer"

  ; 4) 系统 DLL：先当场删，删不掉才交给系统排队
  ;    v1.9.5 改动的原因：以前一上来就 /REBOOTOK，只要某个 32 位程序还开着
  ;    weasel.dll 就直接排到重启后，卸载完还留着一堆文件，看着他像「没卸干净」，
  ;    于是每次卸载都得重启一次。现在先试普通 Delete：此刻 TIP 已经注销、
  ;    WeaselServer 已停，多数机器当场就能删干净，根本不用重启。
  ;    卸载程序同样是 32 位进程，不关重定向两条删除都会删到 SysWOW64，
  ;    把 64 位那份留在 System32 里，所以和安装一样先关掉重定向。
  ${DisableX64FSRedirection}
  Delete "$WINDIR\System32\weasel.dll"
  ${If} ${FileExists} "$WINDIR\System32\weasel.dll"
    DetailPrint "System32\weasel.dll 正被程序占用，改由下次开机时删除。"
    Delete /REBOOTOK "$WINDIR\System32\weasel.dll"
    ; /REBOOTOK 一旦真的排上队，NSIS 会把「需要重启」标志置起来，卸载完就必然弹重启提示。
    ; 文件照样在下次开机由系统顺手删掉，但这个标志要清掉——它不该拿重启去烦用户。
    SetRebootFlag false
  ${EndIf}
  ${EnableX64FSRedirection}
  ${If} ${RunningX64}
    Delete "$WINDIR\SysWOW64\weasel.dll"
    ${If} ${FileExists} "$WINDIR\SysWOW64\weasel.dll"
      DetailPrint "SysWOW64\weasel.dll 正被 32 位程序占用，改由下次开机时删除。"
      Delete /REBOOTOK "$WINDIR\SysWOW64\weasel.dll"
      SetRebootFlag false
    ${EndIf}
  ${EndIf}

  ; 5) 引擎子目录与三生自己的图标（都是精确文件名，不用通配）
  RMDir /r "$INSTDIR\weasel-0.17.4"
  RMDir /r "$INSTDIR\tools"
  Delete "$INSTDIR\icon-sansheng-tray.ico"
  Delete "$INSTDIR\icon-sansheng-cn.ico"
  Delete "$INSTDIR\icon-sansheng-en.ico"

  ; 6) 开始菜单
  Delete "$SMPrograms\三生输入法\三生输入法.lnk"
  Delete "$SMPrograms\三生输入法\卸载三生输入法.lnk"
  Delete "$SMPrograms\三生输入法\检查更新.lnk"
  Delete "$SMPrograms\三生输入法\反查诊断.lnk"
  RMDir "$SMPrograms\三生输入法"

  ; 7) 安装目录：仅当它不是用户词库目录、且已经空了才移除
  ${If} $INSTDIR != $R9
    RMDir "$INSTDIR"
  ${Else}
    DetailPrint "安装目录与 Rime 用户目录相同，目录本身保留。"
  ${EndIf}

  IfSilent uninstall_full_msg_done
  MessageBox MB_ICONINFORMATION "三生输入法已卸载。$\n$\n你的 Rime 用户目录（词库与个人配置）未做任何删除。$\n不用重启电脑：输入法列表已经刷新，Win+空格 里立刻只剩系统自带输入法。$\n（只有个别 DLL 被正在运行的程序占用时，系统才会在下次开机顺手清掉，不影响你现在用机。）"
uninstall_full_msg_done:
  Delete "$INSTDIR\uninstall-sansheng.exe"
  Goto uninstall_done

; ------------------------------------------------------------
;  只卸三生、保留官方小狼毫
;  触发条件：官方卸载登记 + 官方 WeaselRoot 里的 WeaselSetup.exe 都还在，
;  说明三生装好之后官方版又被装回来了，共享组件现在属于官方。
; ------------------------------------------------------------
uninstall_sansheng_only:
  DetailPrint "官方小狼毫仍在使用共享输入法组件，只移除三生专属内容。"

  ; 三生登记（两个视图都删）
  SetRegView 64
  DeleteRegKey HKLM "${UN_KEY}"
  ${If} ${RunningX64}
    SetRegView 32
    DeleteRegKey HKLM "${UN_KEY}"
    SetRegView 64
  ${EndIf}

  ; 三生写的 HKCU 自启（官方用 HKLM 自启，保留官方那条）
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "WeaselServer"

  ; 三生自己的工具、图标、开始菜单
  RMDir /r "$INSTDIR\tools"
  ${If} "$INSTDIR" != "$R9"
    ; 共享 TIP 的 IconFile 现在指向三生图标。图标文件马上要删，先把
    ; 这几个 IconFile 收回官方默认（官方安装包根本不写 IconFile），
    ; 否则输入法列表里会留下一个指向「已不存在文件」的图标。
    ; 只在值确实等于三生图标时才删，绝不覆盖用户自己改过的图标。
    SetRegView 64
    ReadRegStr $R5 HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000804\${TIP_GUID}" "IconFile"
    ${If} $R5 == "$INSTDIR\icon-sansheng-tray.ico"
    ${OrIf} $R5 == "$INSTDIR\icon-sansheng-cn.ico"
      DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000804\${TIP_GUID}" "IconFile"
      DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000404\${TIP_GUID}" "IconFile"
      DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000c04\${TIP_GUID}" "IconFile"
      DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00001004\${TIP_GUID}" "IconFile"
      DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00001404\${TIP_GUID}" "IconFile"
    ${EndIf}
    ${If} ${RunningX64}
      SetRegView 32
      ReadRegStr $R5 HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000804\${TIP_GUID}" "IconFile"
      ${If} $R5 == "$INSTDIR\icon-sansheng-tray.ico"
      ${OrIf} $R5 == "$INSTDIR\icon-sansheng-cn.ico"
        DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000804\${TIP_GUID}" "IconFile"
        DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000404\${TIP_GUID}" "IconFile"
        DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00000c04\${TIP_GUID}" "IconFile"
        DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00001004\${TIP_GUID}" "IconFile"
        DeleteRegValue HKLM "SOFTWARE\Microsoft\CTF\TIP\${TIP_CLSID}\LanguageProfile\0x00001404\${TIP_GUID}" "IconFile"
      ${EndIf}
      SetRegView 64
    ${EndIf}
    Delete "$INSTDIR\icon-sansheng-tray.ico"
    Delete "$INSTDIR\icon-sansheng-cn.ico"
    Delete "$INSTDIR\icon-sansheng-en.ico"
  ${Else}
    DetailPrint "安装目录同时是用户配置目录，保留其中的图标文件。"
  ${EndIf}
  Delete "$SMPrograms\三生输入法\三生输入法.lnk"
  Delete "$SMPrograms\三生输入法\卸载三生输入法.lnk"
  Delete "$SMPrograms\三生输入法\检查更新.lnk"
  Delete "$SMPrograms\三生输入法\反查诊断.lnk"
  RMDir "$SMPrograms\三生输入法"

  ; 官方引擎在别的目录时，三生自己的引擎目录可以安全移除；
  ; 同一目录时那是官方正在用的引擎，绝不能删。
  ${If} "$INSTDIR\weasel-0.17.4" != $R8
  ${AndIf} "$INSTDIR\weasel-0.17.4" != $R9
    RMDir /r "$INSTDIR\weasel-0.17.4"
  ${EndIf}

  ${If} "$INSTDIR" != "$R9"
    RMDir "$INSTDIR"
  ${EndIf}

  IfSilent uninstall_partial_msg_done
  MessageBox MB_ICONINFORMATION "三生输入法已从本机移除。$\n$\n检测到官方小狼毫仍在使用共享输入法组件，所以输入法本体、词库和 Rime 配置都保留，没有一起删除。$\n你可以在「程序和功能」里继续管理官方小狼毫。"
uninstall_partial_msg_done:
  Delete "$INSTDIR\uninstall-sansheng.exe"

uninstall_done:
SectionEnd
