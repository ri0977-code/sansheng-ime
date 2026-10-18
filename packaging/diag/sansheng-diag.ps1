# Sansheng IME (Weasel/Rime) install diagnostic - READ ONLY.
# Collects evidence about a failed / half-installed install into one text file.
# Kept ASCII-only so Windows PowerShell 5.1 cannot misread the encoding.

$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference   = 'SilentlyContinue'

$CLSID = '{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}'
$GUID  = '{3D02CAB6-2B8E-4781-BA20-1C9267529467}'

$lines = New-Object System.Collections.ArrayList
function Add([string]$s) { [void]$lines.Add($s) }
function Path($p) { if (Test-Path -LiteralPath $p) { 'YES' } else { 'NO' } }

Add '=== Sansheng IME install diagnostic ==='
Add ('time      : ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$os = Get-CimInstance Win32_OperatingSystem
Add ('os        : ' + $os.Caption + ' | version ' + $os.Version + ' | build ' + $os.BuildNumber)
Add ('arch      : ' + $env:PROCESSOR_ARCHITECTURE)
$isAdmin = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
Add ('is_admin  : ' + $isAdmin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
Add ('ps_version: ' + $PSVersionTable.PSVersion.ToString())

# ---- [1] install directory -------------------------------------------------
Add ''
Add '--- [1] install dir (files landed?) ---'
$cands = @()
foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
    $cands += (Join-Path $d.Root 'Program Files\Rime')
}
$cands += (Join-Path $env:ProgramFiles 'Rime')
$cands = $cands | Select-Object -Unique
$found = @($cands | Where-Object { Test-Path -LiteralPath $_ })
if ($found.Count -eq 0) {
    Add ('NONE of these exist: ' + ($cands -join ' , '))
}
foreach ($inst in $found) {
    Add ("dir: $inst  (files: " + (Get-ChildItem -LiteralPath $inst -Recurse -File).Count + ')')
    foreach ($f in @('weasel-0.17.4\weaselx64.dll','weasel-0.17.4\weaselx64.ime',
                     'weasel-0.17.4\rime.dll','weasel-0.17.4\WeaselServer.exe',
                     'weasel-0.17.4\WeaselDeployer.exe','weasel-0.17.4\data\default.yaml',
                     'icon-sansheng-tray.ico','tools\enable-tip.ps1','uninstall.exe')) {
        Add ('   ' + (Path (Join-Path $inst $f)) + '  ' + $f)
    }
}

# ---- [2] system-wide TSF dll ----------------------------------------------
Add ''
Add '--- [2] weasel.dll copied into Windows dirs? ---'
foreach ($p in @("$env:SystemRoot\System32\weasel.dll", "$env:SystemRoot\SysWOW64\weasel.dll")) {
    if (Test-Path -LiteralPath $p) {
        $v = (Get-Item -LiteralPath $p)
        Add ("YES  $p  size=" + $v.Length + '  version=' + $v.VersionInfo.FileVersion + '  mtime=' + $v.LastWriteTime)
    } else {
        Add ("NO   $p")
    }
}

# ---- [3] registry: TIP registration ---------------------------------------
Add ''
Add '--- [3] registry TIP keys ---'
foreach ($root in @('HKLM:\SOFTWARE', 'HKLM:\SOFTWARE\WOW6432Node')) {
    $k = "$root\Microsoft\CTF\TIP\$CLSID\LanguageProfile\0x00000804\$GUID"
    Add ((Path $k) + '  ' + $k)
    if (Test-Path -LiteralPath $k) {
        foreach ($pr in (Get-Item -LiteralPath $k).Property) {
            Add ('       ' + $pr + ' = ' + (Get-ItemProperty -LiteralPath $k).$pr)
        }
    }
}
$clsidKey = "Registry::HKEY_CLASSES_ROOT\CLSID\$CLSID\InprocServer32"
Add ((Path $clsidKey) + '  ' + $clsidKey)
if (Test-Path -LiteralPath $clsidKey) {
    Add ('       (default) = ' + (Get-ItemProperty -LiteralPath $clsidKey).'(default)')
}

# ---- [4] is the TIP actually loaded by running apps? ----------------------
Add ''
Add '--- [4] functional check: is weasel.dll loaded inside real processes? ---'
$with = 0
$explorer = 'NO'
$samples = New-Object System.Collections.ArrayList
foreach ($p in (Get-Process -ErrorAction SilentlyContinue)) {
    try {
        foreach ($m in $p.Modules) {
            if ($m.ModuleName -eq 'weasel.dll') {
                $with++
                if ($p.ProcessName -eq 'explorer') { $explorer = 'YES' }
                if ($samples.Count -lt 6) { [void]$samples.Add($p.ProcessName + ' (pid ' + $p.Id + ') <- ' + $m.FileName) }
                break
            }
        }
    } catch {}
}
Add ('processes with weasel.dll loaded : ' + $with)
Add ('explorer.exe has weasel.dll      : ' + $explorer)
foreach ($s in $samples) { Add ('   ' + $s) }
if ($with -eq 0) { Add 'VERDICT: Windows never loaded weasel.dll -> the TIP is registered but NOT active (language bar will not show it).' }
else             { Add 'VERDICT: weasel.dll is loaded by running apps -> the TIP itself IS active on this machine.' }

Add ''
Add '--- [4b] Get-WinUserLanguageList (informational only, NOT a verdict) ---'
$lists = Get-WinUserLanguageList
if (-not $lists) { Add 'Get-WinUserLanguageList returned nothing' }
foreach ($l in $lists) {
    Add ('lang=' + $l.LanguageTag + '  inputmethods=' + @($l.TextAndTipData).Count)
    foreach ($t in $l.TextAndTipData) { Add ('   TIP: ' + $t.LanguageTipId + '   id=' + $t.Id) }
}
Add 'note: a HKLM-registered TIP works even when it is absent from this list, so NO here does not prove failure.'


# ---- [5] server process ----------------------------------------------------
Add ''
Add '--- [5] running processes ---'
foreach ($n in @('WeaselServer','WeaselDeployer','ctfmon')) {
    $p = Get-Process -Name $n
    if ($p) { Add ("RUNNING  $n  pid=" + ($p.Id -join ',') + '  path=' + (($p.Path | Select-Object -First 1))) }
    else    { Add ("NOT RUN  $n") }
}

# ---- [6] Rime user dir + deployment result --------------------------------
Add ''
Add '--- [6] rime user dirs (was deploy successful?) ---'
$dirs = @("$env:APPDATA\Rime", "$env:LOCALAPPDATA\Rime", "$env:ProgramData\Rime", 'C:\Program Files\Rime', 'D:\Program Files\Rime')
$live = @()
foreach ($d in $dirs) {
    if (-not (Test-Path -LiteralPath $d)) { Add ('absent  ' + $d); continue }
    $b = Join-Path $d 'build'
    $bl = @(Get-ChildItem -LiteralPath $b -File -ErrorAction SilentlyContinue)
    Add ((Path (Join-Path $d 'installation.yaml')) + ' installation.yaml | ' + $bl.Count + ' files in build\ | ' + $d)
    if ($bl.Count -gt 0) { $live += ,@($d, $bl) }
}
foreach ($e in $live) {
    Add ('   build\ listing of ' + $e[0] + ':')
    foreach ($f in ($e[1] | Sort-Object Name)) { Add ('     ' + $f.Name.PadRight(38) + $f.Length.ToString().PadLeft(12) + '  ' + $f.LastWriteTime) }
    $newest = ($e[1] | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
    Add ('   newest built file: ' + $newest.Name + ' @ ' + $newest.LastWriteTime)
    if (@($e[1] | Where-Object { $_.Name -like '*.prism.bin' }).Count -eq 0) {
        Add '   WARNING: build\ has NO *.prism.bin at all -> schema was never compiled, typing will produce nothing.'
    }
}


# ---- [7] newest rime/weasel log tail --------------------------------------
Add ''
Add '--- [7] newest rime log tail (temp dir) ---'
$log = Get-ChildItem -LiteralPath $env:TEMP -Filter 'rime*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($log) {
    Add ('file: ' + $log.FullName + '  mtime=' + $log.LastWriteTime)
    foreach ($l in (Get-Content -LiteralPath $log.FullName -Tail 25)) { Add ('   ' + $l) }
} else {
    Add ('no rime*.log found in ' + $env:TEMP)
}

# ---- [8] recent crash / error events --------------------------------------
Add ''
Add '--- [8] Application event log, errors in the last 3 days ---'
$ev = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Level = 2; StartTime = (Get-Date).AddDays(-3) } -MaxEvents 12
if (-not $ev) { Add 'none' }
foreach ($e in $ev) {
    $first = (($e.Message -split "`r?`n") | Where-Object { $_.Trim() } | Select-Object -First 1)
    Add ('   ' + $e.TimeCreated + '  [' + $e.ProviderName + ']  ' + $first)
}

$out = Join-Path ([Environment]::GetFolderPath('Desktop')) 'sansheng-diag.txt'
Set-Content -LiteralPath $out -Value $lines -Encoding UTF8
Write-Host ''
Write-Host ('report saved to: ' + $out)
Write-Host 'send this file back for analysis.'
