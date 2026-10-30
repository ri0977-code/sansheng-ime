param(
    [string]$OutDir = "",
    [string]$KeyAlias = "sansheng-release",
    [string]$Subject = "C=CN,O=Sansheng,OU=IME,CN=Sansheng IME Release"
)

# Generate the LOCAL release key pair and a CSR for the AppGallery Connect
# release certificate. The private key never leaves this machine; only the
# .csr file is uploaded to AGC. Passwords are never written to disk.
#
# ASCII-ONLY FILE: Windows PowerShell 5.1 decodes a BOM-less .ps1 as GBK.

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DevEcoRoot = "D:\DevTools\DevEco\DevEco Studio"
$JavaExe = Join-Path $DevEcoRoot "jbr\bin\java.exe"
$SignJar = Join-Path $DevEcoRoot "sdk\default\openharmony\toolchains\lib\hap-sign-tool.jar"

if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $ProjectRoot "sign\release"
}
$P12 = Join-Path $OutDir "$KeyAlias.p12"
$Csr = Join-Path $OutDir "$KeyAlias.csr"
$Info = Join-Path $OutDir "release-csr.info.txt"

foreach ($p in @($JavaExe, $SignJar)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "missing tool: $p" }
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# One password for both the key and the PKCS#12 store. Read from the
# environment for automation, otherwise prompt without echo.
$KeyPass = $env:SS_RELEASE_PWD
if ([string]::IsNullOrWhiteSpace($KeyPass)) {
    $sec1 = Read-Host -AsSecureString "Release keystore password (not saved to disk)"
    $sec2 = Read-Host -AsSecureString "Repeat password"
    $b1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec1)
    $b2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec2)
    try {
        $p1 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b1)
        $p2 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b2)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b1)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b2)
    }
    if ($p1 -ne $p2) { throw "passwords do not match" }
    if ($p1.Length -lt 8) { throw "password must be at least 8 characters" }
    $KeyPass = $p1
}

$env:JAVA_HOME = Join-Path $DevEcoRoot "jbr"

if (Test-Path -LiteralPath $P12) {
    Write-Host "reusing existing key pair: $P12"
    Write-Host "the password must be the one used when this .p12 was created"
} else {
    Write-Host "generating release key pair: $P12"
    & $JavaExe -jar $SignJar generate-keypair `
        -keyAlias $KeyAlias `
        -keyPwd $KeyPass `
        -keyAlg ECC `
        -keySize NIST-P-256 `
        -keystoreFile $P12 `
        -keystorePwd $KeyPass
    if ($LASTEXITCODE -ne 0) { throw "generate-keypair failed with exit code $LASTEXITCODE" }
}

Write-Host "generating CSR: $Csr"
& $JavaExe -jar $SignJar generate-csr `
    -keyAlias $KeyAlias `
    -keyPwd $KeyPass `
    -subject $Subject `
    -signAlg SHA256withECDSA `
    -keystoreFile $P12 `
    -keystorePwd $KeyPass `
    -outFile $Csr
if ($LASTEXITCODE -ne 0) { throw "generate-csr failed with exit code $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $Csr)) { throw "CSR not produced: $Csr" }

$csrHash = (Get-FileHash -LiteralPath $Csr -Algorithm SHA256).Hash.ToLower()
$p12Hash = (Get-FileHash -LiteralPath $P12 -Algorithm SHA256).Hash.ToLower()
$lines = @(
    "alias=$KeyAlias",
    "subject=$Subject",
    "created=$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))",
    "csr_sha256=$csrHash",
    "p12_sha256=$p12Hash"
)
# LF only: keeps hashes stable when the info file is copied between systems.
[IO.File]::WriteAllText($Info, ($lines -join "`n") + "`n", (New-Object Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "CSR OK: $Csr"
Write-Host "CSR SHA-256: $csrHash"
Write-Host "Key store: $P12 (KEEP PRIVATE, back it up together with sign\)"
Write-Host "Info: $Info"
Write-Host ""
Write-Host "Next (owner, AGC):"
Write-Host "  1. Certificates: create a RELEASE certificate, upload the .csr above."
Write-Host "  2. Download the .cer, put it in: $OutDir"
Write-Host "  3. Create a RELEASE profile for com.sansheng.ime with that certificate."
Write-Host "  4. Download the .p7b, put it in: $OutDir"
Write-Host "  5. Run scripts\release_build.ps1"
