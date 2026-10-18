#Requires -Version 5.0
<#
  三生输入法 · 卸载程序（Qoder 版）
  ---------------------------------------------------------------
  默认「只预演不删除」（dry-run），确认清单没问题再加 -Apply 真删。
  需要管理员权限：不加 -Apply 时不需要；加 -Apply 时会自动请求提权。

  用法：
    右键 ▸ 用 PowerShell 运行                      → 只看会删什么
    powershell -File 卸载三生输入法.ps1 -Apply     → 真的卸载
    powershell -File 卸载三生输入法.ps1 -Apply -IncludeUserData
                                                 → 连用户词库/配置一起删（默认保留）

  它按「注册表 + 常见目录」两头找，所以不管是用 setup.exe 还是 install.bat
  装的，都能找到并清干净。
#>
param(
  [switch]$Apply,
  [switch]$IncludeUserData,
  [switch]$SkipSystemDll          # 特殊情况：只清注册表和输入法列表，不碰 System32 的 dll
)

$ErrorActionPreference = 'Continue'
$TipClsid  = '{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}'
$TipGuid   = '{3D02CAB6-2B8E-4781-BA20-1C9267529467}'
$TipStr    = "0804:$TipClsid$TipGuid"
$UnKey     = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SanshengIME'
$CtfPaths  = @("HKLM:\SOFTWARE\Microsoft\CTF\TIP\$TipClsid",
               "HKLM:\SOFTWARE\WOW6432Node\Microsoft\CTF\TIP\$TipClsid")
$ClsidPaths = @("HKLM:\SOFTWARE\Classes\CLSID\$TipClsid",
                "HKLM:\SOFTWARE\Classes\WOW6432Node\CLSID\$TipClsid")

$script:Actions = @()
function Add-Act($kind, $what) { $script:Actions += [pscustomobject]@{ 动作 = $kind; 对象 = $what } }
function Do-It($kind, $what, [scriptblock]$block) {
  Add-Act $kind $what
  if (-not $Apply) { return }
  try { & $block | Out-Null; Write-Host ("  [删] {0}  {1}" -f $kind, $what) -Fore Green }
  catch { Write-Host ("  [失败] {0}  {1} :: {2}" -f $kind, $what, $_.Exception.Message) -Fore Yellow }
}

# ---------- 0. 权限 ----------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
            ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($Apply -and -not $isAdmin) {
  Write-Host '需要管理员权限，正在重新以管理员身份启动...' -Fore Yellow
  $args2 = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Apply'
  if ($IncludeUserData) { $args2 += ' -IncludeUserData' }
  if ($SkipSystemDll)   { $args2 += ' -SkipSystemDll' }
  Start-Process -FilePath 'powershell.exe' -ArgumentList $args2 -Verb RunAs
  exit
}

Write-Host ('==== 三生输入法 卸载{0} ====' -f $(if ($Apply) { '（执行模式）' } else { '（预演模式，不会删除任何东西）' }))

# ---------- 1. 定位安装位置 ----------
$InstallDir = $null
if (Test-Path $UnKey) {
  $InstallDir = (Get-ItemProperty $UnKey -ErrorAction SilentlyContinue).InstallLocation
}
$cand = @($InstallDir, "$env:ProgramFiles\Rime", "${env:ProgramFiles(x86)}\Rime",
          'D:\Program Files\Rime', 'C:\Program Files\Rime') | Where-Object { $_ }
foreach ($c in $cand) {
  if (Test-Path $c) {
    $eng = Get-ChildItem $c -Directory -Filter 'weasel-*' -ErrorAction SilentlyContinue |
           Where-Object { Test-Path (Join-Path $_.FullName 'WeaselServer.exe') }
    if ($eng) { $InstallDir = $c; break }
  }
}
if (-not $InstallDir) { Write-Host '  没找到安装目录（可能已经被删过）' -Fore Yellow }

$EngineDir = $null
if ($InstallDir) {
  $EngineDir = (Get-ChildItem $InstallDir -Directory -Filter 'weasel-*' -ErrorAction SilentlyContinue |
               Select-Object -First 1).FullName
}

# Rime 用户目录（配置 + 词库）
$UserDir = (Get-ItemProperty 'HKCU:\Software\Rime\Weasel' -ErrorAction SilentlyContinue).RimeUserDir
if (-not $UserDir) { $UserDir = Join-Path $env:APPDATA 'Rime' }

Write-Host ('  安装目录   : {0}' -f $(if ($InstallDir) { $InstallDir } else { '(未发现)' }))
Write-Host ('  引擎目录   : {0}' -f $(if ($EngineDir) { $EngineDir } else { '(未发现)' }))
Write-Host ('  配置/词库  : {0}' -f $UserDir)
Write-Host ''

# ---------- 2. 输入法键盘列表 ----------
Write-Host '[1] 当前用户的可用键盘列表'
try {
  $list = Get-WinUserLanguageList
  $hit = @($list | Where-Object { $_.InputMethodTips -contains $TipStr })
  if ($hit.Count -gt 0) {
    Do-It '摘除键盘项' $TipStr {
      foreach ($lang in $list) {
        if ($lang.InputMethodTips -contains $TipStr) {
          $keep = New-Object System.Collections.Generic.List[string]
          foreach ($t in $lang.InputMethodTips) { if ($t -ne $TipStr) { $keep.Add($t) } }
          $lang.InputMethodTips = $keep.ToArray()
        }
      }
      Set-WinUserLanguageList $list -Force
      'OK'
    }
  } else { Add-Act '键盘项' '本来就不在列表里（无需处理）' }
} catch { Write-Host ('  读语言列表失败：{0}' -f $_.Exception.Message) -Fore Yellow }

# ---------- 3. 停进程 ----------
Write-Host '[2] 运行中的进程'
Do-It '结束进程' 'WeaselServer.exe' {
  Get-Process WeaselServer -ErrorAction SilentlyContinue | Stop-Process -Force; 'OK'
}
Do-It '结束进程' 'WeaselDeployer.exe' {
  Get-Process WeaselDeployer -ErrorAction SilentlyContinue | Stop-Process -Force; 'OK'
}

# ---------- 4. 注册表 ----------
Write-Host '[3] 系统注册表（输入法本体 + 控制面板条目 + 开机自启）'
foreach ($p in $CtfPaths)  { if (Test-Path $p) { Do-It '删注册表' $p { Remove-Item $p -Recurse -Force } } }
foreach ($p in $ClsidPaths){ if (Test-Path $p) { Do-It '删注册表' $p { Remove-Item $p -Recurse -Force } } }
if (Test-Path $UnKey)      { Do-It '删注册表' $UnKey { Remove-Item $UnKey -Recurse -Force } }
$run = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
if ($run -and ($run.PSObject.Properties.Name -contains 'WeaselServer')) {
  Do-It '删开机自启' 'HKCU\...\Run\WeaselServer' { Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'WeaselServer' }
}
if ($InstallDir -and $UserDir -and ($UserDir.TrimEnd('\') -eq $InstallDir.TrimEnd('\'))) {
  Do-It '删用户目录指向' 'HKCU\Software\Rime\Weasel\RimeUserDir' {
    Remove-ItemProperty 'HKCU:\Software\Rime\Weasel' -Name 'RimeUserDir'
  }
} elseif ($UserDir -and -not (Test-Path $UserDir)) {
  Do-It '删用户目录指向' 'HKCU\Software\Rime\Weasel\RimeUserDir（目标目录已不存在）' {
    Remove-ItemProperty 'HKCU:\Software\Rime\Weasel' -Name 'RimeUserDir'
  }
}

# ---------- 5. 系统 DLL ----------
Write-Host '[4] 系统目录里的 weasel.dll'
if ($SkipSystemDll) {
  Add-Act '系统 DLL' '按参数跳过（-SkipSystemDll）'
} else {
  foreach ($d in @("$env:WINDIR\System32\weasel.dll", "$env:WINDIR\SysWOW64\weasel.dll")) {
    if (Test-Path $d) {
      Do-It '删系统文件' $d {
        try { Remove-Item $d -Force -ErrorAction Stop; 'OK' }
        catch {
          Add-Act '需重启后删' $d
          Write-Host ('     被占用，重启后再跑一次卸载即可清掉：{0}' -f $d) -Fore Yellow
          'LOCKED'
        }
      }
    }
  }
}

# ---------- 6. 安装目录里的东西 ----------
Write-Host '[5] 安装目录 / 开始菜单'
# 安全闸：很多机器上「安装目录」和「词库目录」是同一个（本机就是这样）。
# 这种情况下只准删我们自己铺的东西，绝不允许整目录递归删除。
$SameDir = [bool]($InstallDir -and $UserDir -and
                  ($UserDir.TrimEnd('\') -eq $InstallDir.TrimEnd('\')))
if ($EngineDir) { Do-It '删引擎目录' $EngineDir { Remove-Item $EngineDir -Recurse -Force } }
if ($InstallDir) {
  foreach ($ico in @('icon-sansheng-tray.ico','icon-sansheng-cn.ico','icon-sansheng-en.ico')) {
    $p = Join-Path $InstallDir $ico
    if (Test-Path $p) { Do-It '删图标' $p { Remove-Item $p -Force } }
  }
}
$sm = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\三生输入法'
if (Test-Path $sm) { Do-It '删开始菜单' $sm { Remove-Item $sm -Recurse -Force } }
$smAll = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\三生输入法'
if (Test-Path $smAll) { Do-It '删开始菜单(全用户)' $smAll { Remove-Item $smAll -Recurse -Force } }
if ($InstallDir -and (Test-Path $InstallDir)) {
  if ($SameDir -and -not $IncludeUserData) {
    Add-Act '保留' ('{0} ＝ 词库目录，只删上面列出的引擎/图标，目录本身保留' -f $InstallDir)
  } else {
    Add-Act '稍后处理' ('{0}：等用户数据清完后，若目录已空则删除' -f $InstallDir)
  }
}

# ---------- 7. 用户数据 ----------
Write-Host '[6] 用户词库与配置'
if ($IncludeUserData -and $UserDir -and (Test-Path $UserDir)) {
  # 只清「三生/小狼毫自己产生」的东西，其它同名目录里的无关文件不碰
  $dirs  = @('build', 'lua', 'opencc', 'sync', 'wiki-keep')
  $globs = @('*.userdb')
  $files = @('*.yaml', '*.dict.yaml', '*.schema.yaml', '*.custom.yaml', '*.txt',
             '*.ico', '*.reverse.bin', '*.bin', 'LICENSE', 'AUTHORS')
  Add-Act '删用户数据' $UserDir
  if ($Apply) {
    foreach ($d in $dirs) {
      $p = Join-Path $UserDir $d
      if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
    }
    foreach ($g in $globs) {
      Get-ChildItem $UserDir -Directory -Filter $g -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    foreach ($f in $files) {
      Get-ChildItem $UserDir -File -Filter $f -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
    }
    Write-Host ('  [删] 用户数据（按类型清理）{0}' -f $UserDir) -Fore Green
    $left = @(Get-ChildItem $UserDir -Force -ErrorAction SilentlyContinue)
    Write-Host ('     目录还剩 {0} 项，未动' -f $left.Count) -Fore DarkGray
  }
} elseif ($UserDir) {
  Add-Act '保留用户数据' ('{0}（要连它一起删请加 -IncludeUserData）' -f $UserDir)
}

# ---------- 7.5 最后收口：目录真的空了才删 ----------
if ($InstallDir -and (Test-Path $InstallDir) -and -not ($SameDir -and -not $IncludeUserData)) {
  Do-It '删安装目录(仅当已空)' $InstallDir {
    $left = @(Get-ChildItem $InstallDir -Force -ErrorAction SilentlyContinue)
    if ($left.Count -gt 0) {
      Add-Act '保留非空目录' ('{0}（还剩 {1} 项，没动）' -f $InstallDir, $left.Count)
      'NOT-EMPTY'
    } else {
      Remove-Item $InstallDir -Force
      'OK'
    }
  }
}

# ---------- 8. 汇总 ----------
Write-Host ''
Write-Host '==================== 清单 ===================='
$script:Actions | Format-Table -AutoSize -Wrap | Out-String -Width 200 | Write-Host
if (-not $Apply) {
  Write-Host '这是预演。确认无误后执行： powershell -File 卸载三生输入法.ps1 -Apply' -Fore Cyan
} else {
  Write-Host '卸载执行完毕。建议重启一次，把仍被占用的系统文件清干净。' -Fore Green
}
