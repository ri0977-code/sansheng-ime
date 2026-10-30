param(
    [string]$Hap = "",
    [string]$Out = "",
    [string]$KeysFile = "",
    [string]$KeyAlias = ""
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DevEcoRoot = "D:\DevTools\DevEco\DevEco Studio"
$JavaExe = Join-Path $DevEcoRoot "jbr\bin\java.exe"
$SignJar = Join-Path $DevEcoRoot "sdk\default\openharmony\toolchains\lib\hap-sign-tool.jar"
$SignDir = Join-Path $ProjectRoot "sign"

if ([string]::IsNullOrWhiteSpace($Hap)) {
    $Hap = Join-Path $ProjectRoot "entry\build\default\outputs\default\entry-default-unsigned.hap"
}
if ([string]::IsNullOrWhiteSpace($Out)) {
    $Out = Join-Path $ProjectRoot "entry\build\default\outputs\default\entry-default-signed.hap"
}
if ([string]::IsNullOrWhiteSpace($KeysFile)) {
    $KeysFile = Join-Path $SignDir "keys.local.json"
}

foreach ($p in @($Hap, $SignJar, $KeysFile,
        (Join-Path $SignDir "sansheng.p12"),
        (Join-Path $SignDir "sansheng.cer"),
        (Join-Path $SignDir "sanshengDebug.p7b"))) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "missing file: $p"
    }
}

$keys = Get-Content -LiteralPath $KeysFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($KeyAlias)) { $KeyAlias = $keys.keyAlias }
if ([string]::IsNullOrWhiteSpace($KeyAlias)) { throw "keyAlias missing in $KeysFile" }
if ([string]::IsNullOrWhiteSpace($keys.keyPwd) -or [string]::IsNullOrWhiteSpace($keys.keystorePwd)) {
    throw "keyPwd/keystorePwd missing in $KeysFile"
}

$env:JAVA_HOME = Join-Path $DevEcoRoot "jbr"

Write-Host "signing: $Hap"
& $JavaExe -jar $SignJar sign-app `
    -keyAlias $KeyAlias `
    -signAlg "SHA256withECDSA" `
    -mode "localSign" `
    -appCertFile (Join-Path $SignDir "sansheng.cer") `
    -profileFile (Join-Path $SignDir "sanshengDebug.p7b") `
    -inFile $Hap `
    -keystoreFile (Join-Path $SignDir "sansheng.p12") `
    -outFile $Out `
    -keyPwd $keys.keyPwd `
    -keystorePwd $keys.keystorePwd

if ($LASTEXITCODE -ne 0) {
    throw "hap-sign-tool failed with exit code $LASTEXITCODE"
}
if (-not (Test-Path -LiteralPath $Out)) {
    throw "signing reported success but output not found: $Out"
}
$size = (Get-Item -LiteralPath $Out).Length
Write-Host "SIGN OK: $Out ($size bytes)"
