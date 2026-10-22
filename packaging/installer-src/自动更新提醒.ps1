# 自动更新提醒.ps1 —— 定时检查有没有新版，有就弹桌面通知（Windows 通知中心 / 气泡）
#
# 这是给计划任务用的「静默版」检查：安静运行，不开控制台窗口，不问任何问题。
# 有新版 → 弹一条通知；没新版 / 网络不通 → 一声不吭。
# 绝不自动下载、绝不自动安装：只负责告诉主人一句「有新版了」。
#
# 手动运行（看详细过程）：
#   powershell -NoProfile -ExecutionPolicy Bypass -File 自动更新提醒.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File 自动更新提醒.ps1 -Force
#       ↑ -Force：即使已是最新版也弹一条，用来确认通知通道还活着。
#
# 注意：本文件必须存成 UTF-8 带 BOM，否则 PowerShell 5.1 读中文字面量会报语法错。

#Requires -Version 5.0
param(
  [int]$TimeoutSec = 15,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

function Norm-Version([string]$s) {
  if (-not $s) { return $null }
  $t = ($s -replace '^[vV]', '') -replace '-.*$', ''
  $p = $t.Split('.')
  while ($p.Count -lt 3) { $p = $p + '0' }
  $n = @($p[0..2] | ForEach-Object { ($_ -replace '[^0-9]', '') })
  if ($n -contains '' -or -not $n[0]) { return $null }
  try { return [version]($n -join '.') } catch { return $null }
}

function Get-InstalledVersion {
  $paths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SanshengIME',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SanshengIME'
  )
  foreach ($p in $paths) {
    if (Test-Path $p) {
      $v = (Get-ItemProperty -Path $p -ErrorAction SilentlyContinue).DisplayVersion
      if ($v) { return [string]$v }
    }
  }
  return $null
}

function Show-Notice([string]$title, [string]$text, [int]$seconds) {
  try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $icon = New-Object System.Windows.Forms.NotifyIcon
    $icon.Icon = [System.Drawing.SystemIcons]::Exclamation
    $icon.Visible = $true
    $icon.BalloonTipIcon    = [System.Windows.Forms.ToolTipIcon]::Info
    $icon.BalloonTipTitle   = $title
    $icon.BalloonTipText    = $text
    $icon.ShowBalloonTip($seconds * 1000)
    Start-Sleep -Seconds $seconds
    $icon.Visible = $false
    $icon.Dispose()
  } catch {
    # 通知发不出去也不能影响检查本身（写一行日志就够）
    try {
      $log = Join-Path $env:LOCALAPPDATA 'SanshengIME\update-notice.log'
      if (-not (Test-Path (Split-Path $log))) {
        New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null
      }
      Add-Content -Path $log -Value ("{0} 通知发送失败: {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $_.Exception.Message) -Encoding UTF8
    } catch { }
  }
}

# ---- 安静模式：不弹控制台窗口 ----
$quiet = -not ([Environment]::UserInteractive)
if (-not $quiet) { [Console]::OutputEncoding = [Text.Encoding]::UTF8 }

try {
  $local = Get-InstalledVersion
  if (-not $local) {
    # 不是用 setup.exe 装的（或已卸载），不打扰
    exit 0
  }

  $api = 'https://api.github.com/repos/ri0977-code/sansheng-ime/releases/latest'
  $headers = @{ 'User-Agent' = 'sansheng-ime-auto-update'; 'Accept' = 'application/vnd.github+json' }
  $rel = $null
  try {
    $rel = Invoke-RestMethod -Uri $api -Headers $headers -TimeoutSec $TimeoutSec
  } catch {
    try {
      $wc = New-Object Net.WebClient
      $wc.Proxy = $null
      $wc.Headers.Add('User-Agent', 'sansheng-ime-auto-update')
      $wc.Headers.Add('Accept', 'application/vnd.github+json')
      $rel = ($wc.DownloadString($api) | ConvertFrom-Json)
    } catch { $rel = $null }
  }
  if (-not $rel -or -not $rel.tag_name) {
    # 网络不通就安静退开，下次再问
    exit 0
  }

  $latest = Norm-Version $rel.tag_name
  $cur    = Norm-Version $local
  if (-not $latest -or -not $cur) { exit 0 }

  if ($Force) {
    Show-Notice '三生输入法 · 更新提醒通道正常' ("本机 {0}，线上 {1}。这条是 -Force 测试。" -f $local, $rel.tag_name) 10
    exit 0
  }

  if ($latest -gt $cur) {
    $mb = ''
    foreach ($a in @($rel.assets)) {
      if ($a -and $a.name -and $a.name -match '\.exe$' -and $a.size) {
        $mb = "（{0:N1} MB）" -f ($a.size / 1MB); break
      }
    }
    Show-Notice '三生输入法 有新版本' ("{0} → {1}{2}。开始菜单 ▸ 三生输入法 ▸ 检查更新，或直接下载覆盖安装。" -f $local, $rel.tag_name, $mb) 20
  }
  exit 0
} catch {
  exit 0   # 定时任务里绝不让异常冒出去
}