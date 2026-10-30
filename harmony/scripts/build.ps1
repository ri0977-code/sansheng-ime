param(
  [string]$Product = "default",
  [string]$BuildMode = "debug"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DevEcoRoot = "D:\DevTools\DevEco\DevEco Studio"
$NodeExe = Join-Path $DevEcoRoot "tools\node\node.exe"
$HvigorJs = Join-Path $DevEcoRoot "tools\hvigor\bin\hvigorw.js"
$SdkRoot = Join-Path $DevEcoRoot "sdk"
$JbrRoot = Join-Path $DevEcoRoot "jbr"

if (-not (Test-Path $NodeExe)) { throw "node not found: $NodeExe" }
if (-not (Test-Path $HvigorJs)) { throw "hvigor not found: $HvigorJs" }
if (-not (Test-Path $SdkRoot)) { throw "SDK not found: $SdkRoot" }
if (-not (Test-Path $JbrRoot)) { throw "JBR not found: $JbrRoot" }

$env:DEVECO_SDK_HOME = $SdkRoot
$env:JAVA_HOME = $JbrRoot
$env:PATH = "$($env:JAVA_HOME)\bin;$($env:PATH)"

Write-Host "Project: $ProjectRoot"
Write-Host "SDK:     $env:DEVECO_SDK_HOME"
Write-Host "JAVA:    $env:JAVA_HOME"
Write-Host "Build:   assembleHap product=$Product mode=$BuildMode"

# Collaboration hook (owner decision 2026-10-21 14:49): a build == the start of a
# work round, so first show the other agent's inbox (docs/WIP.md via scripts/wip.py).
# Non-blocking, and it never touches the other agent's read-state.
# WARNING: keep THIS FILE ASCII-ONLY. Windows PowerShell 5.1 decodes a BOM-less .ps1
# as GBK; CJK comments then turn into mojibake that can silently swallow the following
# line, which made $WipScript null and killed the whole build at Test-Path.
$WipScript = Join-Path $ProjectRoot "scripts\wip.py"
$ErrorActionPreference = "Continue"
if (Test-Path $WipScript) {
  if ($env:SS_WHO -eq "Qoder" -or $env:SS_WHO -eq "CodeArts") {
    Push-Location $ProjectRoot
    python $WipScript inbox --who $env:SS_WHO --brief 2>&1 | ForEach-Object { Write-Host $_ }
    Pop-Location
  } else {
    Write-Host "[wip] set SS_WHO=Qoder|CodeArts to auto-check the other agent's inbox (scripts/wip.py inbox)"
  }
}
$ErrorActionPreference = "Stop"

Push-Location $ProjectRoot
try {
  & $NodeExe $HvigorJs assembleHap --mode module -p "product=$Product" -p "buildMode=$BuildMode" --no-daemon
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}

if ($exitCode -ne 0) {
  throw "hvigor failed with exit code $exitCode"
}

$hapDir = Join-Path $ProjectRoot "entry\build\$Product\outputs\$Product"
$unsigned = Join-Path $hapDir "entry-$Product-unsigned.hap"
if (-not (Test-Path $unsigned)) {
  $unsigned = Join-Path $hapDir "entry-default-unsigned.hap"
}

if (Test-Path $unsigned) {
  $item = Get-Item $unsigned
  Write-Host "BUILD OK: $($item.FullName) ($($item.Length) bytes)"
  # Desktop notification on build success
  $notifyScript = Join-Path $PSScriptRoot "notify.ps1"
  if (Test-Path $notifyScript) {
    & $notifyScript -Title "Sansheng IME Build" -Message "BUILD OK: $($item.Length) bytes" -DurationMs 3000
  }
} else {
  Write-Host "BUILD OK, but expected HAP was not found under: $hapDir"
  Get-ChildItem -Path $hapDir -Filter *.hap -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  $($_.FullName) ($($_.Length) bytes)"
  }
}

