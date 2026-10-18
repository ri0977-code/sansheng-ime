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
Add ('os_64bit  : ' + [Environment]::Is64BitOperatingSystem)
# Bitness matters: a 32-bit PowerShell sees SysWOW64 when you ask for System32 and
# sees WOW6432Node when you ask for HKLM\SOFTWARE\Classes\CLSID. Read below with that in mind.
if ([Environment]::Is64BitProcess) {
    Add ('ps_bitness: 64-bit  (System32 / Classes\CLSID below are the real 64-bit views)' )
} else {
    Add ('ps_bitness: 32-bit  !! System32 paths and Classes\CLSID are REDIRECTED - re-run with the 64-bit powershell.exe')
}

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
                     'icon-sansheng-tray.ico','tools\enable-tip.ps1',
                     'uninstall-sansheng.exe')) {
        Add ('   ' + (Path (Join-Path $inst $f)) + '  ' + $f)
    }
    # source dll sizes - compare with [2] to see which copy landed where
    foreach ($f in @('weasel-0.17.4\weaselx64.dll','weasel-0.17.4\weasel.dll')) {
        $sf = Join-Path $inst $f
        if (Test-Path -LiteralPath $sf) {
            Add ('   SRC  ' + $f + '  size=' + (Get-Item -LiteralPath $sf).Length)
        } else {
            Add ('   NO   ' + $f)
        }
    }
}

# ---- [2] system-wide TSF dll ----------------------------------------------
Add ''
Add '--- [2] weasel.dll copied into Windows dirs? ---'
Add '      (System32 must be the 64-bit one = same size as weaselx64.dll above;'
Add '       SysWOW64 must be the 32-bit one = same size as weasel.dll above)'
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
# Both CLSID views separately. 64-bit apps (explorer, browsers, Office) use the first one;
# a 32-bit installer can only ever write the second, which is why an IME can be "installed"
# yet invisible to everything on screen.
foreach ($ck in @("HKLM:\SOFTWARE\Classes\CLSID\$CLSID\InprocServer32",
                  "HKLM:\SOFTWARE\WOW6432Node\Classes\CLSID\$CLSID\InprocServer32")) {
    Add ((Path $ck) + '  ' + $ck)
    if (Test-Path -LiteralPath $ck) {
        Add ('       (default) = ' + (Get-ItemProperty -LiteralPath $ck).'(default)')
    }
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
if ($with -eq 0) {
    Add 'VERDICT: Windows never loaded weasel.dll -> the TIP is registered but NOT active (language bar will not show it).'
    if (-not [Environment]::Is64BitProcess) {
        Add '  NOTE: this PowerShell is 32-bit, so the load-module count above may be misleading - re-run the .bat from a 64-bit shell.'
    } elseif ((Path "HKLM:\SOFTWARE\Classes\CLSID\$CLSID\InprocServer32") -eq 'NO' -or -not (Test-Path -LiteralPath "$env:SystemRoot\System32\weasel.dll")) {
        Add '  CAUSE MATCHED: the 64-bit half of the registration is missing (no System32\weasel.dll and/or no 64-bit Classes\CLSID).'
        Add '  That is the 32-bit-installer WOW64 redirect defect, not a config/dictionary problem. Type the 64-bit repair, then reboot.'
    } else {
        Add '  64-bit registration looks present but nothing loaded weasel.dll - reboot once, then re-run this .bat.'
    }
} else { Add 'VERDICT: weasel.dll is loaded by running apps -> the TIP itself IS active on this machine.' }

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

# ---- [6b] lua wiring: does the user dir have the rime.lua entry point? -----
# librime-lua only sees a filter/translator named in a schema if <userdir>\rime.lua
# assigned that name. Compile (prism/table) does NOT touch lua, so a machine without
# rime.lua deploys "successfully" and then types nothing at all.
Add ''
Add '--- [6b] lua wiring check (rime.lua) ---'
foreach ($d in $dirs) {
    if (-not (Test-Path -LiteralPath $d)) { continue }
    # which schemas are actually enabled (compiled build\default.yaml wins)
    $active = @()
    $bdef = Join-Path $d 'build\default.yaml'
    if (Test-Path -LiteralPath $bdef) {
        $raw = Get-Content -LiteralPath $bdef -Raw -ErrorAction SilentlyContinue
        if ($raw) { $active = @([regex]::Matches($raw, 'schema:\s*"?([A-Za-z0-9_]+)"?') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique) }
    }
    $schemas = @(Get-ChildItem -LiteralPath $d -Filter '*.schema.yaml' -File -ErrorAction SilentlyContinue)
    if ($active.Count -gt 0) {
        $scan = @($active | ForEach-Object { $_ } | Where-Object { Test-Path -LiteralPath (Join-Path $d ($_ + '.schema.yaml')) })
    } else {
        $scan = @($schemas | ForEach-Object { $_.BaseName -replace '\.schema$', '' })
    }
    if ($scan.Count -eq 0) { continue }
    $used = New-Object System.Collections.Generic.HashSet[string]
    foreach ($s in $scan) {
        foreach ($suffix in @('.schema.yaml', '.custom.yaml')) {
            $sp = Join-Path $d ($s + $suffix)
            if (-not (Test-Path -LiteralPath $sp)) { continue }
            $raw = Get-Content -LiteralPath $sp -Raw -ErrorAction SilentlyContinue
            if (-not $raw) { continue }
            foreach ($m in ([regex]::Matches($raw, 'lua_(?:filter|translator|processor|segmentor)@([A-Za-z_][A-Za-z0-9_]*)'))) {
                [void]$used.Add($m.Groups[1].Value)
            }
        }
    }
    $entry = Join-Path $d 'rime.lua'
    $lualib = Join-Path $d 'lua'
    $nfiles = @(Get-ChildItem -LiteralPath $lualib -File -ErrorAction SilentlyContinue).Count
    Add ($d + ' | enabled schema(s)=' + ($scan -join ',') + ' | lua\ ' + (Path $lualib) + ' (' + $nfiles + ' files) | lua names used=' + $used.Count)
    if (-not (Test-Path -LiteralPath $entry)) {
        Add ('MISSING  ' + $entry)
        Add ('   needs: ' + (($used | Sort-Object) -join ', '))
        Add 'VERDICT: no rime.lua in this user dir -> schema cannot be built at runtime, typing produces NO Chinese. Fix: put rime.lua here and redeploy.'
    } else {
        $txt = Get-Content -LiteralPath $entry -Raw -ErrorAction SilentlyContinue
        $ndefined = @([regex]::Matches($txt, '(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*require')).Count
        Add ((Path $entry) + '  rime.lua  defines=' + $ndefined + ' names')
        $unresolved = @($used | Where-Object { $txt -notmatch ('(?m)^\s*' + [regex]::Escape($_) + '\s*=\s*require') })
        if ($unresolved.Count -gt 0) {
            Add ('   UNRESOLVED (enabled schema uses it but rime.lua does not define it): ' + ($unresolved -join ', '))
        } else {
            Add '   all referenced lua names resolve -> wiring OK'
        }
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
