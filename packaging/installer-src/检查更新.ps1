#Requires -Version 5.0
<#
  三生输入法 · 检查更新（Qoder 版）
  ---------------------------------------------------------------
  读注册表里装的版本 → 问 GitHub 最新发行版 → 有新版就给你三个选择：
    1 = 自动下载安装包（校验 SHA-256 后帮你启动安装程序，弹一次管理员授权）
    2 = 只打开下载页，剩下自己来
    回车 = 先不弄

  不读你的词库、不碰你的配置，除了下载一个 exe 到 %TEMP% 之外不写任何东西。
  不需要管理员权限（安装程序自己会申请）。

  用法：
    双击 检查更新.cmd                                  → 正常用
    powershell -File 检查更新.ps1 -NoOpen              → 只报告，不打开网页
    powershell -File 检查更新.ps1 -LocalVersion 1.9.0  → 自测「有新版」分支
    powershell -File 检查更新.ps1 -DownloadOnly        → 自测下载+校验，不启动安装
    powershell -File 检查更新.ps1 -Repo x/y            → 自测「拿不到」分支
#>
param(
  [string]$Repo         = 'ri0977-code/sansheng-ime',
  [string]$LocalVersion = '',      # 不传就从注册表读；传了用于自测
  [int]$TimeoutSec      = 10,
  [switch]$NoOpen,
  [switch]$DownloadOnly          # 只下载并校验，绝不启动安装程序（自测用）
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
  # 主路径：setup.exe 写的卸载键（32 位安装器会被重定向，所以 WOW6432Node 也看）。
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
  # 兜底：键名可能不一样（老版本、或手装），按显示名「三生」在卸载列表里找一遍。
  foreach ($root in ($paths[0] -replace '\\SanshengIME$',''), ($paths[1] -replace '\\SanshengIME$','')) {
    if (-not (Test-Path $root)) { continue }
    foreach ($k in (Get-ChildItem $root -ErrorAction SilentlyContinue)) {
      $dv = Get-ItemProperty -Path $k.PSPath -ErrorAction SilentlyContinue
      if ($dv.DisplayName -like '*三生*' -and $dv.DisplayVersion) { return [string]$dv.DisplayVersion }
    }
  }
  return ''
}

function Invoke-Release($api) {
  # 先走系统代理，失败再强制直连；两条路的错误分别打印。
  $headers = @{ 'User-Agent' = 'sansheng-ime-check-update'; 'Accept' = 'application/vnd.github+json' }
  try {
    return Invoke-RestMethod -Uri $api -Headers $headers -TimeoutSec $TimeoutSec
  } catch { $first = $_ }
  try {
    $wc = New-Object Net.WebClient
    $wc.Proxy = $null
    $wc.Headers.Add('User-Agent', 'sansheng-ime-check-update')
    $wc.Headers.Add('Accept', 'application/vnd.github+json')
    return ($wc.DownloadString($api) | ConvertFrom-Json)
  } catch {
    Write-Host ''
    Write-Host '  请求失败（代理和直连都试过）：' -ForegroundColor Yellow
    Write-Host ('    代理: ' + $first.Exception.Message)
    Write-Host ('    直连: ' + $_.Exception.Message)
    return $null
  }
}

function Get-Setup([string]$url, [string]$dest) {
  # 下载：先按系统代理走 Invoke-WebRequest，失败再 WebClient 直连。
  try {
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -TimeoutSec 120
    return $true
  } catch { $first = $_ }
  try {
    $wc = New-Object Net.WebClient
    $wc.Proxy = $null
    $wc.DownloadFile($url, $dest)
    return $true
  } catch {
    Write-Host '  下载失败（代理和直连都试过）：' -ForegroundColor Yellow
    Write-Host ('    代理: ' + $first.Exception.Message)
    Write-Host ('    直连: ' + $_.Exception.Message)
    return $false
  }
}

Write-Host ''
Write-Host '  三生输入法 · 检查更新' -ForegroundColor Cyan
Write-Host '  ------------------------------------------------------------'

$local = if ($LocalVersion) { $LocalVersion } else { Get-InstalledVersion }
if ($local) { Write-Host ("  本机版本：{0}" -f $local) }
else { Write-Host '  本机版本：注册表里没找到（可能没装，或不是用 setup.exe 装的）' -ForegroundColor Yellow }

$api = 'https://api.github.com/repos/{0}/releases/latest' -f $Repo
Write-Host ("  查询地址：{0}" -f $api)
Write-Host '  正在查询…'

$rel = Invoke-Release $api
if (-not $rel -or -not $rel.tag_name) {
  Write-Host ''
  Write-Host '  没拿到版本信息。可能是网络不通、GitHub 临时不可用，或者仓库地址写错了。' -ForegroundColor Yellow
  Write-Host ('  也可以自己打开看看：https://github.com/{0}/releases' -f $Repo)
  exit 1
}

$latest = Norm-Version $rel.tag_name
$cur    = Norm-Version $local
$pub = ('{0}' -f $rel.published_at)
$pub = ($pub -replace 'T', ' ') -replace 'Z$', ''
Write-Host ("  最新版本：{0}（发布 {1}）" -f $rel.tag_name, $pub) -ForegroundColor Green

$setup = $null
foreach ($a in @($rel.assets)) {
  if ($a -and $a.name -and $a.name -match '\.exe$') { $setup = $a; break }
}
if ($setup) {
  $mb = if ($setup.size) { '{0:N1} MB' -f ($setup.size / 1MB) } else { '未知大小' }
  Write-Host ("    安装包：{0}（{1}）" -f $setup.name, $mb)
  if ($setup.digest) { Write-Host ("           SHA-256 {0}" -f ($setup.digest -replace '^sha256:', '')) }
} else {
  Write-Host '    （这个发行版没有 .exe 安装包）' -ForegroundColor DarkGray
}
Write-Host '  ------------------------------------------------------------'

if (-not $local -or -not $cur -or -not $latest) {
  if (-not $local) {
    Write-Host '  本机版本没读到，所以没法比较。上面就是线上最新版，需要的话自己对照。' -ForegroundColor Yellow
  } else {
    Write-Host '  版本号格式没认出来，无法比较。上面是最新版信息，需要的话自己对照。' -ForegroundColor Yellow
  }
  exit 0
}

if ($latest -le $cur) {
  Write-Host ("  已经是最新版（本机 {0}，线上 {1}），不用更新。" -f $local, $rel.tag_name) -ForegroundColor Green
  exit 0
}

Write-Host ("  有新版本：{0} → {1}" -f $local, $rel.tag_name) -ForegroundColor Yellow
Write-Host '  安装器会覆盖程序文件与三生的配置模板；你的 user.txt / 用户词库 / 打字记录'
Write-Host '  在覆盖前会先备份，不会被删掉。'
Write-Host ''
Write-Host '    [1] 自动下载安装包并启动安装（推荐，装完即用）'
Write-Host '    [2] 只打开下载网页，我自己下载'
Write-Host '    [回车] 先不弄'
$choice = (Read-Host '  选一个').Trim()

if ($choice -eq '1') {
  if (-not $setup -or -not $setup.browser_download_url) {
    Write-Host '  这个发行版没有可下载的安装包，改用 [2] 或直接看网页。' -ForegroundColor Yellow
    exit 1
  }
  $dest = Join-Path $env:TEMP $setup.name
  if (Test-Path $dest) { Remove-Item $dest -Force }
  Write-Host ''
  Write-Host ("  下载到：{0}" -f $dest)
  Write-Host '  下载中…（几十 MB，看网速，可能要一两分钟）'
  if (-not (Get-Setup $setup.browser_download_url $dest)) { exit 1 }

  $got = (Get-Item $dest).Length
  Write-Host ("  下载完成：{0:N1} MB" -f ($got / 1MB)) -ForegroundColor Green
  if ($setup.size -and [int]$setup.size -ne $got) {
    Write-Host ("  大小和线上对不上（线上 {0}，本机 {1}），不敢用，已删。" -f $setup.size, $got) -ForegroundColor Red
    Remove-Item $dest -Force; exit 1
  }
  $hash = (Get-FileHash -Algorithm SHA256 -Path $dest).Hash.ToLower()
  Write-Host ("  本机算得 SHA-256：{0}" -f $hash)
  if ($setup.digest) {
    $want = ($setup.digest -replace '^sha256:', '').ToLower()
    if ($hash -ne $want) {
      Write-Host ("  校验不过（线上 {0}），文件可能被动过，已删除，不会运行。" -f $want) -ForegroundColor Red
      Remove-Item $dest -Force; exit 1
    }
    Write-Host '  校验通过：与 GitHub 公布的 SHA-256 一致。' -ForegroundColor Green
  } else {
    Write-Host '  线上没公布 digest，只对了文件大小。' -ForegroundColor Yellow
  }
  if ($DownloadOnly) {
    Write-Host '  （-DownloadOnly：到此为止，不启动安装程序。文件留在 %TEMP%）' -ForegroundColor DarkGray
    exit 0
  }
  Write-Host ''
  Write-Host '  即将启动安装程序（会弹一次管理员授权）。装完按提示重新部署即可。' -ForegroundColor Cyan
  Start-Process -FilePath $dest
  exit 0
}
elseif ($choice -eq '2' -or $choice -match '^[yY]') {
  if ($NoOpen) { Write-Host '  （-NoOpen：本次不打开网页）' -ForegroundColor DarkGray }
  else { Start-Process $rel.html_url; Write-Host '  已打开浏览器。' }
}
else {
  Write-Host '  好的，没动。链接在上面，随时可以手动访问。'
}
exit 0
