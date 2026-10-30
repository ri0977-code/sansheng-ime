param(
    [string]$Product = "default",
    [string]$KeysDir = "",
    [string]$KeyAlias = "sansheng-release",
    [string]$P12File = "",
    [string]$CertFile = "",
    [string]$ProfileFile = "",
    [string]$OutApp = "",
    [string]$ArchiveDir = "",
    [int]$CompatibleVersion = 22,
    [switch]$SkipBuild,
    [switch]$AllowNonReleaseProfile
)

# Build -> sign -> verify -> pack .app for AppGallery submission.
# Secrets come from SS_RELEASE_PWD / SS_RELEASE_KEY_PWD / SS_RELEASE_STORE_PWD
# or a hidden prompt; nothing is written to disk.
#
# ASCII-ONLY FILE: Windows PowerShell 5.1 decodes a BOM-less .ps1 as GBK.

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DevEcoRoot = "D:\DevTools\DevEco\DevEco Studio"
$JavaExe = Join-Path $DevEcoRoot "jbr\bin\java.exe"
$SignJar = Join-Path $DevEcoRoot "sdk\default\openharmony\toolchains\lib\hap-sign-tool.jar"
$PackJar = Join-Path $DevEcoRoot "sdk\default\openharmony\toolchains\lib\app_packing_tool.jar"
$BundleName = "com.sansheng.ime"

# Anything that has ever landed on the submission path is moved OUT of the build tree
# before this run overwrites it, and again whenever a later step fails. Two hazards, both
# measured (docs/ISSUES.md H-113/H-123/H-144):
#   1) a stale or unverified .app must never sit in outputs/ looking submittable;
#   2) outputs/ is inside entry/build, and "hvigorw clean" deletes that whole tree - so
#      renaming in place (the old behaviour) also destroyed the evidence. On 2026-10-23
#      00:08 a clean build wiped the only release .app (11,791,326 B, sha256 8dad9f3f...)
#      together with its quarantine name; the hash survives only because docs recorded it.
# Hence: archive outside the build tree, and keep the accepted set after a green run.
if ([string]::IsNullOrWhiteSpace($ArchiveDir)) {
    $ArchiveDir = Join-Path (Split-Path -Parent $ProjectRoot) "sansheng-release-artifacts"
}

function Stop-AsRejected([string]$artifact, [string]$reason = "rejected") {
    if (-not (Test-Path -LiteralPath $artifact)) { return }
    # One directory per run: the sweep can quarantine the .app, its sidecar and the
    # previous release HAP in the same second or the next one, and a per-call timestamp
    # would scatter them across folders (measured in the 08:4x harness).
    if ([string]::IsNullOrWhiteSpace($script:QuarantineStamp)) {
        $script:QuarantineStamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    }
    $dir = Join-Path $ArchiveDir "quarantine-$($script:QuarantineStamp)"
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $dest = Join-Path $dir ((Split-Path -Leaf $artifact) + ".$reason")
    Move-Item -LiteralPath $artifact -Destination $dest -Force
    Write-Host "QUARANTINED: $artifact -> $dest"
}

function Save-AcceptedSet([string]$appPath, [string]$hapPath, [string]$appHash, [string]$hapHash,
                          [int64]$appBytes, [int64]$hapBytes, [string]$ver,
                          [string[]]$gateLines = @(), [string]$gateItems = "n/a") {
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $dir = Join-Path $ArchiveDir "accepted-$stamp"
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Copy-Item -LiteralPath $appPath -Destination $dir -Force
    if (Test-Path -LiteralPath "$appPath.sha256") { Copy-Item -LiteralPath "$appPath.sha256" -Destination $dir -Force }
    if (Test-Path -LiteralPath $hapPath) { Copy-Item -LiteralPath $hapPath -Destination $dir -Force }
    # The gate's own output is part of the evidence: a manifest that says PASS while the
    # log is gone only proves that someone typed PASS (H-141: numbers must come from the tool).
    if ($gateLines.Count -gt 0) {
        [IO.File]::WriteAllText((Join-Path $dir "content-gate.txt"), (($gateLines | ForEach-Object { "$_" }) -join "`n") + "`n",
            (New-Object Text.UTF8Encoding($false)))
    }
    $rows = @(
        "app=$(Split-Path -Leaf $appPath)",
        "app_sha256=$appHash",
        "app_bytes=$appBytes",
        "hap=$(Split-Path -Leaf $hapPath)",
        "hap_sha256=$hapHash",
        "hap_bytes=$hapBytes",
        "version=$ver",
        "content_gate=PASS($gateItems)",
        "checker=scripts/check_app_content.py (exit 0)",
        "saved=$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))",
        "note=durable copy outside entry/build; survives hvigor clean (H-144)"
    )
    [IO.File]::WriteAllText((Join-Path $dir "MANIFEST.txt"), ($rows -join "`n") + "`n", (New-Object Text.UTF8Encoding($false)))
    Write-Host "ARCHIVED accepted submission set: $dir"
    return $dir
}

# Extract the checker's own "N/M passed" summary; anything else is "n/a".
# ASCII-only on purpose (this file is decoded as GBK by PowerShell 5.1), so the match
# is structural: the LAST line carrying a plain <digits>/<digits> token wins. The
# checker's only such token is its summary line ("...: 16/16 ..."); hash fragments are
# excluded because they are hex, and the one line that mentions "sha256" is skipped.
function Get-GateItems([string[]]$lines) {
    $items = "n/a"
    foreach ($ln in $lines) {
        $s = [string]$ln
        if ($s -match 'sha256') { continue }
        $m = [regex]::Match($s, '(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})(?!\d)')
        if ($m.Success) { $items = "$($m.Groups[1].Value)/$($m.Groups[2].Value)" }
    }
    return $items
}

if ([string]::IsNullOrWhiteSpace($KeysDir)) {
    $KeysDir = Join-Path $ProjectRoot "sign\release"
}
if ([string]::IsNullOrWhiteSpace($P12File)) { $P12File = Join-Path $KeysDir "$KeyAlias.p12" }
if ([string]::IsNullOrWhiteSpace($CertFile)) { $CertFile = Join-Path $KeysDir "$KeyAlias.cer" }
if ([string]::IsNullOrWhiteSpace($ProfileFile)) { $ProfileFile = Join-Path $KeysDir "$KeyAlias.p7b" }

foreach ($p in @($JavaExe, $SignJar, $PackJar, $P12File, $CertFile, $ProfileFile)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "missing file: $p`nRun scripts\release_csr.ps1 first; put the AGC .cer/.p7b in $KeysDir"
    }
}

# Profile sanity: must be issued for this bundle and, unless overridden, release.
$VerifyDir = Join-Path $ProjectRoot "entry\build\$Product\release-verify"
New-Item -ItemType Directory -Force -Path $VerifyDir | Out-Null
$ProfileJson = Join-Path $VerifyDir "profile-check.json"
& $JavaExe -jar $SignJar verify-profile -inFile $ProfileFile -outFile $ProfileJson
if ($LASTEXITCODE -ne 0) { throw "verify-profile failed with exit code $LASTEXITCODE" }
$profile = Get-Content -LiteralPath $ProfileJson -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $profile.verifiedPassed) { throw "profile signature verification failed: $($profile.message)" }
$profileBundle = $profile.content.'bundle-info'.'bundle-name'
$profileType = $profile.content.type
if ($profileBundle -ne $BundleName) {
    throw "profile bundle-name is '$profileBundle', expected '$BundleName'"
}
if ($profileType -ne "release" -and -not $AllowNonReleaseProfile) {
    throw "profile type is '$profileType', expected 'release' (use -AllowNonReleaseProfile only for pipeline tests)"
}
Write-Host "profile OK: type=$profileType bundle=$profileBundle"

# One password for both key and store unless separate ones are provided.
$StorePass = $env:SS_RELEASE_STORE_PWD
if ([string]::IsNullOrWhiteSpace($StorePass)) { $StorePass = $env:SS_RELEASE_PWD }
$KeyPass = $env:SS_RELEASE_KEY_PWD
if ([string]::IsNullOrWhiteSpace($KeyPass)) { $KeyPass = $StorePass }
if ([string]::IsNullOrWhiteSpace($StorePass) -or [string]::IsNullOrWhiteSpace($KeyPass)) {
    $sec = Read-Host -AsSecureString "Release key/store password (not saved to disk)"
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) }
    finally { [Runtime.InteropServices.Marshal]::FreeBSTR($b) }
    if ($plain.Length -lt 8) { throw "password must be at least 8 characters" }
    if ([string]::IsNullOrWhiteSpace($StorePass)) { $StorePass = $plain }
    if ([string]::IsNullOrWhiteSpace($KeyPass)) { $KeyPass = $plain }
}

$env:JAVA_HOME = Join-Path $DevEcoRoot "jbr"
$OutDir = Join-Path $ProjectRoot "entry\build\$Product\outputs\$Product"

# Sweep packages left by previous runs BEFORE doing anything else. The output name
# only carries the version, so it is identical run to run; without this sweep a build
# that fails half-way leaves the *previous* .app (and its .sha256) in outputs/ looking
# exactly like this run's submission candidate.
foreach ($old in @(Get-ChildItem -LiteralPath $OutDir -File -Filter '*.app' -ErrorAction SilentlyContinue)) {
    Stop-AsRejected $old.FullName "stale"
    Stop-AsRejected "$($old.FullName).sha256" "stale"
}
# The release-signed HAP has a run-invariant name too, so this run's sign step would
# silently overwrite the previous accepted one. Move it to the archive first (H-144).
foreach ($old in @(Get-ChildItem -LiteralPath $OutDir -File -Filter '*release-signed.hap' -ErrorAction SilentlyContinue)) {
    Stop-AsRejected $old.FullName "superseded"
    Stop-AsRejected "$($old.FullName).sha256" "superseded"
}

if (-not $SkipBuild) {
    Write-Host "building release HAP..."
    & (Join-Path $PSScriptRoot "build.ps1") -Product $Product -BuildMode "release"
    if ($LASTEXITCODE -ne 0) { throw "release build failed with exit code $LASTEXITCODE" }
} else {
    Write-Host "SkipBuild: using the existing unsigned release HAP"
}

$unsigned = Join-Path $OutDir "entry-$Product-unsigned.hap"
if (-not (Test-Path -LiteralPath $unsigned)) {
    $unsigned = Join-Path $OutDir "entry-default-unsigned.hap"
}
if (-not (Test-Path -LiteralPath $unsigned)) { throw "unsigned HAP not found under $OutDir" }

$signed = Join-Path $OutDir "entry-$Product-release-signed.hap"
Write-Host "signing: $unsigned"
& $JavaExe -jar $SignJar sign-app `
    -mode localSign `
    -keyAlias $KeyAlias `
    -signAlg SHA256withECDSA `
    -appCertFile $CertFile `
    -profileFile $ProfileFile `
    -inFile $unsigned `
    -keystoreFile $P12File `
    -outFile $signed `
    -keyPwd $KeyPass `
    -keystorePwd $StorePass `
    -compatibleVersion $CompatibleVersion
if ($LASTEXITCODE -ne 0) { throw "sign-app failed with exit code $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $signed)) { throw "signed HAP not produced: $signed" }

$CertOut = Join-Path $VerifyDir "cert-chain.cer"
$ProfileOut = Join-Path $VerifyDir "embedded-profile.p7b"
& $JavaExe -jar $SignJar verify-app -inFile $signed -outCertChain $CertOut -outProfile $ProfileOut
if ($LASTEXITCODE -ne 0) { throw "verify-app failed with exit code $LASTEXITCODE" }

# pack.info is produced by the build; read the version for the artifact name.
$packInfo = Join-Path $OutDir "pack.info"
if (-not (Test-Path -LiteralPath $packInfo)) { throw "pack.info not found: $packInfo" }
$pack = Get-Content -LiteralPath $packInfo -Raw -Encoding UTF8 | ConvertFrom-Json
$version = $pack.summary.app.version.name
if ([string]::IsNullOrWhiteSpace($OutApp)) {
    $OutApp = Join-Path $OutDir "sansheng-ime-$version-release.app"
}
# The sweep before the build only covered outputs/; clear an explicitly passed target too.
Stop-AsRejected $OutApp "stale"
Stop-AsRejected "$OutApp.sha256" "stale"

# Official order (hvigor SignApp): pack -> sign the .app as a whole.
# The packing tool records HAP verify info and strips per-HAP signature blocks;
# the .app signature is what AppGallery checks.
$StageDir = Join-Path $ProjectRoot "entry\build\release-stage"
if (Test-Path -LiteralPath $StageDir) { Remove-Item -LiteralPath $StageDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null
$stageHap = Join-Path $StageDir "entry-default.hap"
Copy-Item -LiteralPath $signed -Destination $stageHap -Force
$unsignedApp = Join-Path $StageDir "sansheng-ime-$version-unsigned.app"

Write-Host "packing: $unsignedApp"
& $JavaExe -jar $PackJar --mode app `
    --hap-path $stageHap `
    --pack-info-path $packInfo `
    --out-path $unsignedApp `
    --force
if ($LASTEXITCODE -ne 0) { throw "app_packing_tool failed with exit code $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $unsignedApp)) { throw ".app not produced: $unsignedApp" }

Write-Host "signing app: $OutApp"
& $JavaExe -jar $SignJar sign-app `
    -mode localSign `
    -keyAlias $KeyAlias `
    -signAlg SHA256withECDSA `
    -appCertFile $CertFile `
    -profileFile $ProfileFile `
    -inFile $unsignedApp `
    -keystoreFile $P12File `
    -outFile $OutApp `
    -keyPwd $KeyPass `
    -keystorePwd $StorePass
if ($LASTEXITCODE -ne 0) { throw "sign-app on .app failed with exit code $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $OutApp)) { throw "signed .app not produced: $OutApp" }

$AppCertOut = Join-Path $VerifyDir "app-cert-chain.cer"
$AppProfileOut = Join-Path $VerifyDir "app-embedded-profile.p7b"
$signedHash = (Get-FileHash -LiteralPath $signed -Algorithm SHA256).Hash.ToLower()
Add-Type -AssemblyName System.IO.Compression.FileSystem
# Everything that has to be true BEFORE this package may be described by a sidecar
# or picked up for upload. If any of it fails, the .app is renamed away first: the
# signing step above already put a real file at the submission path, and a file that
# sits there after a failed run is exactly the "looks submittable" hazard (H-113/H-123).
try {
    & $JavaExe -jar $SignJar verify-app -inFile $OutApp -outCertChain $AppCertOut -outProfile $AppProfileOut
    if ($LASTEXITCODE -ne 0) { throw "verify-app on .app failed with exit code $LASTEXITCODE" }

    # Structural check: pack.info and the canonical HAP are present.
    $zip = [IO.Compression.ZipFile]::OpenRead($OutApp)
    try {
        if ($null -eq $zip.GetEntry("entry-default.hap")) { throw ".app does not contain entry-default.hap" }
        if ($null -eq $zip.GetEntry("pack.info")) { throw ".app does not contain pack.info" }
    } finally {
        $zip.Dispose()
    }
} catch {
    Stop-AsRejected $OutApp
    Stop-AsRejected "$OutApp.sha256"
    throw
}

$appHash = (Get-FileHash -LiteralPath $OutApp -Algorithm SHA256).Hash.ToLower()
$appSize = (Get-Item -LiteralPath $OutApp).Length
$hapSize = (Get-Item -LiteralPath $signed).Length
$lines = @(
    "artifact=$(Split-Path -Leaf $OutApp)",
    "sha256=$appHash",
    "bytes=$appSize",
    "hap_bytes=$hapSize",
    "version=$version",
    "built=$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))"
)
[IO.File]::WriteAllText("$OutApp.sha256", ($lines -join "`n") + "`n", (New-Object Text.UTF8Encoding($false)))

# Content gate: signature validity says nothing about what is inside.
# The 16-item checker is MANDATORY: a missing checker fails the build exactly like a
# failing one, and a failed gate quarantines the signed .app (and its .sha256 sidecar)
# before throwing, so an unverified package can never sit in the output directory
# looking submittable. See docs/ISSUES.md H-113/H-123 and Stop-AsRejected() at the top.
$PyExe = "python"
$Checker = Join-Path $PSScriptRoot "check_app_content.py"
if (-not (Test-Path -LiteralPath $Checker)) {
    Stop-AsRejected $OutApp
    Stop-AsRejected "$OutApp.sha256"
    throw "check_app_content.py not found at $Checker - refusing to report RELEASE OK for an unverified package (H-113)"
}
Write-Host "checking package content (scripts\check_app_content.py)..."
$gateOutLines = @()
& $PyExe $Checker $OutApp 2>&1 | Tee-Object -Variable gateOutLines
$gateExit = $LASTEXITCODE
$gateLines = @($gateOutLines | ForEach-Object { "$_" })
if ($gateExit -ne 0) {
    Stop-AsRejected $OutApp
    Stop-AsRejected "$OutApp.sha256"
    throw "package content check FAILED (exit $gateExit) - the .app and its .sha256 were moved to $ArchiveDir\quarantine-*; do not upload it (see output above)"
}
# Item counts come from the checker's own summary line, never from a constant in here:
# the gate has changed shape before (H-115 turned two WARNs into blockers), and a
# manifest that hard-codes a count is a number nobody measured (H-141).
$gateItems = Get-GateItems $gateLines

Write-Host ""
# Green gate: keep a durable copy of the submission set before anything can clean it away.
Save-AcceptedSet -appPath $OutApp -hapPath $signed -appHash $appHash -hapHash $signedHash `
    -appBytes $appSize -hapBytes $hapSize -ver $version -gateLines $gateLines -gateItems $gateItems | Out-Null
Write-Host "RELEASE OK"
Write-Host "  HAP: $signed ($hapSize bytes) sha256=$signedHash"
Write-Host "  APP: $OutApp ($appSize bytes)"
Write-Host "  APP sha256: $appHash"
Write-Host "  verify: $VerifyDir"
Write-Host ""
Write-Host "Upload the .app to AppGallery Connect. Do NOT install release-signed HAPs via hdc;"
Write-Host "use the debug-signed HAP for Mate 80 checks."
