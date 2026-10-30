param(
  [string]$Hap = "",
  [string]$Target = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Hdc = "D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"

if ([string]::IsNullOrWhiteSpace($Hap)) {
  $Hap = Join-Path $ProjectRoot "entry\build\default\outputs\default\entry-default-signed.hap"
}
if (-not (Test-Path $Hap)) {
  throw "HAP not found: $Hap. Build and sign first, or pass -Hap <path>."
}
if (-not (Test-Path $Hdc)) {
  throw "hdc not found: $Hdc"
}

$targets = @(& $Hdc list targets | Where-Object { $_ -and ($_ -notmatch '\[Empty\]') })
if ($Target) {
  # Explicit -Target wins: never guess, a wrong machine is unrecoverable at night.
  if ($targets -notcontains $Target) {
    throw "Device '$Target' is not online. Online: $($targets -join ', ')"
  }
  $target = $Target
} else {
  if ($targets.Count -gt 1) {
    throw "Multiple devices online ($($targets -join ', ')) - refusing to guess. Pass -Target <serial> (Mate 80 = 7GL0226408083897)."
  }
  $target = $targets | Select-Object -First 1
}
if (-not $target) {
  throw "No device found. Connect the Mate 80 and allow USB debugging, then retry."
}

$item = Get-Item $Hap
Write-Host "Device: $target"
Write-Host "HAP:    $($item.FullName) ($($item.Length) bytes)"

# H-182（Qoder 2026-10-26）：hdc 装机失败时**退出码仍是 0**，只在 stdout 打 `[Fail][Exxxxxx]`。
# 旧写法只看 $LASTEXITCODE ⇒ 通道没建立时也照样打 "INSTALL OK"（今天上午的假成功就这么来的）。
# 现在：输出里出现 [Fail] 就算失败，重试 3 次；仍失败则抛错。装完再用 bm dump 的 updateTime 验真。
$ok = $false
$lastOut = ""
for ($i = 1; $i -le 3; $i++) {
  $lastOut = (& $Hdc -t $target install -r $Hap 2>&1 | Out-String)
  Write-Host $lastOut.Trim()
  if ($LASTEXITCODE -eq 0 -and $lastOut -notmatch '\[Fail\]' -and $lastOut -match 'success') {
    $ok = $true
    break
  }
  Write-Host "install attempt $i failed, retrying in 6s ..."
  Start-Sleep -Seconds 6
}
if (-not $ok) {
  throw "hdc install failed after 3 attempts (see output above). If it says 'communication channel is being established', unlock the phone / re-authorize USB debugging."
}

# 验真：包更新时间必须晚于 HAP 文件最后写入时间（设备时钟与 PC 时钟可能有偏差，容差 10 分钟）
# 2026-10-26 11:3x（Qoder）：第一次跑时 bm dump 偶发没吐 updateTime（通道刚恢复），
# 于是这里重试 3 次；仍读不到就打 "INSTALL OK (未验真)"——**不许**只打 "INSTALL OK"，
# 否则「装了没装上」又回到 H-182 那个假成功的老路上。
$upd = $null
for ($j = 1; $j -le 3 -and $null -eq $upd; $j++) {
  $dump = (& $Hdc -t $target shell "bm dump -n com.sansheng.ime" 2>&1 | Out-String)
  if ($dump -match 'updateTime"\s*:\s*(\d+)') { $upd = [int64]$Matches[1] }
  elseif ($j -lt 3) { Start-Sleep -Seconds 3 }
}
$verified = $false
if ($null -ne $upd) {
  $hapMs = ([DateTimeOffset]$item.LastWriteTime.ToUniversalTime()).ToUnixTimeMilliseconds()
  $deltaMin = ($hapMs - $upd) / 60000.0
  Write-Host ("installed updateTime={0}  hapMtime={1}  delta={2:N1} min" -f $upd, $hapMs, $deltaMin)
  if ($upd -lt ($hapMs - 10*60000)) {
    throw "INSTALL VERIFY FAILED: installed bundle is older than this HAP (delta $([math]::Round($deltaMin,1)) min)"
  }
  $verified = $true
} else {
  Write-Host "WARN: 3 次 bm dump 都没给出 updateTime（通道不稳），本次装机**未验真**"
}
if ($verified) { Write-Host "INSTALL OK (已验真: updateTime 不早于 HAP)" }
else { Write-Host "INSTALL OK (未验真, 请复核)" }
