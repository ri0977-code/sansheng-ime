!include "MUI2.nsh"
!include "x64.nsh"

Name "三生输入法"
OutFile "三生输入法-v1.9.2-setup.exe"
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

; 用户 Rime 目录用 $R9（$0-$9 会被 ExecWait 返回值复用）

Section "MainSection"
  ; ===== 1. 安装 weasel 引擎 =====
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
  ; 先读已存在的用户目录（小狼毫键：HKCU\Software\Rime\Weasel -> RimeUserDir）
  ; 已有且有效就沿用它，绝不改写别人原来的目录
  ReadRegStr $R9 HKCU "Software\Rime\Weasel" "RimeUserDir"
  ${If} $R9 == ""
    StrCpy $R9 "$APPDATA\Rime"
  ${EndIf}
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
  ; 把 config 目录里所有配置文件释放到用户配置目录
  File /r "config\*"

  ; 简繁转换数据：用户目录再放一份（shared + user 两个搜索根都覆盖，最稳）
  SetOutPath "$R9\opencc"
  File /r "weasel-0.17.4\data\opencc\*"
  SetOutPath "$R9"

  DetailPrint "配置文件已释放到 $R9"

  ; ===== 3. 把图标文件复制到安装根目录（注册表 IconFile 指向这里） =====
  SetOutPath "$INSTDIR"
  ExecWait 'cmd /c copy /y "$R9\icon-sansheng-tray.ico" "$INSTDIR\icon-sansheng-tray.ico"'
  ExecWait 'cmd /c copy /y "$R9\icon-sansheng-cn.ico" "$INSTDIR\icon-sansheng-cn.ico"'
  ExecWait 'cmd /c copy /y "$R9\icon-sansheng-en.ico" "$INSTDIR\icon-sansheng-en.ico"'

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
  ExecWait 'WeaselDeployer.exe /deploy' $0
  DetailPrint "部署返回码: $0"

  ; ===== 9. 开机自启 + 启动 WeaselServer =====
  ; 不写这条，重启后输入法服务不自启，候选窗会出不来
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "WeaselServer" '"$INSTDIR\weasel-0.17.4\WeaselServer.exe"'
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

  ; ===== 11. 把三生加入当前用户的键盘列表（免手动去设置里添加）=====
  DetailPrint "注册到输入法列表..."
  ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\tools\enable-tip.ps1" -Tip "0804${TIP_CLSID}${TIP_GUID}"' $0
  DetailPrint "键盘列表返回: $0"

  ; ===== 12. 开始菜单 + 控制面板卸载入口 =====
  CreateDirectory "$SMPrograms\三生输入法"
  CreateShortcut "$SMPrograms\三生输入法\三生输入法.lnk" "$INSTDIR\weasel-0.17.4\WeaselServer.exe" "" "$INSTDIR\icon-sansheng-cn.ico"
  CreateShortcut "$SMPrograms\三生输入法\卸载三生输入法.lnk" "$INSTDIR\uninstall-sansheng.exe"

  WriteUninstaller "$INSTDIR\uninstall-sansheng.exe"
  SetRegView 64
  WriteRegStr HKLM "${UN_KEY}" "DisplayIcon" "$INSTDIR\icon-sansheng-tray.ico"
  WriteRegStr HKLM "${UN_KEY}" "DisplayName" "三生输入法"
  WriteRegStr HKLM "${UN_KEY}" "DisplayVersion" "1.9.2"
  WriteRegStr HKLM "${UN_KEY}" "Publisher" "WorkBuddy"
  WriteRegStr HKLM "${UN_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UN_KEY}" "UninstallString" '"$INSTDIR\uninstall-sansheng.exe"'
  WriteRegStr HKLM "${UN_KEY}" "QuietUninstallString" '"$INSTDIR\uninstall-sansheng.exe" /S'
  WriteRegDWORD HKLM "${UN_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UN_KEY}" "NoRepair" 1

  ; ===== 13. 完成 =====
  MessageBox MB_ICONINFORMATION "安装完成！$\n$\n现在按 Win+空格（或左 Alt+Shift）就能切换到「三生输入法」。$\n如需卸载：控制面板 > 程序和功能 > 三生输入法。"
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

  ; 1) 从键盘列表移除
  ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\tools\remove-tip.ps1" -Tip "0804${TIP_CLSID}${TIP_GUID}"' $0

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

  ; 4) 系统 DLL（被占用时由系统安排在重启后删除）
  ;    卸载程序同样是 32 位进程，不关重定向的话两条删除都会删到 SysWOW64，
  ;    把 64 位那份留在 System32 里。这里和安装一样先关掉重定向。
  ${DisableX64FSRedirection}
  Delete /REBOOTOK "$WINDIR\System32\weasel.dll"
  ${EnableX64FSRedirection}
  ${If} ${RunningX64}
    Delete /REBOOTOK "$WINDIR\SysWOW64\weasel.dll"
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
  RMDir "$SMPrograms\三生输入法"

  ; 7) 安装目录：仅当它不是用户词库目录、且已经空了才移除
  ${If} $INSTDIR != $R9
    RMDir "$INSTDIR"
  ${Else}
    DetailPrint "安装目录与 Rime 用户目录相同，目录本身保留。"
  ${EndIf}

  MessageBox MB_ICONINFORMATION "三生输入法已卸载。$\n$\n你的 Rime 用户目录（词库与个人配置）未做任何删除。$\n建议重启一次，让系统输入法表彻底刷新。"
  Delete "$INSTDIR\uninstall-sansheng.exe"
SectionEnd
