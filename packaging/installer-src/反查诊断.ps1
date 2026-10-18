# 三生输入法 · 反查自检（2026-10-18）
# 只读：不改任何配置、不删任何文件、不写注册表。
# 产出：桌面上「三生反查诊断.txt」，把这份文件发给维护者就能定位反查问题。
$ErrorActionPreference = 'SilentlyContinue'
$sb = New-Object System.Text.StringBuilder
function W($s) { [void]$sb.AppendLine($s) }

W "三生输入法 · 反查自检  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
W "机器 $env:COMPUTERNAME / 用户 $env:USERNAME / 64位 $([Environment]::Is64BitOperatingSystem)"
W ""

# ---- 1) 配置目录在哪、里面有没有码表 ----
$ud = (Get-ItemProperty 'HKCU:\Software\Rime\Weasel').RimeUserDir
if (-not $ud) { $ud = Join-Path $env:APPDATA 'Rime' }
W "HKCU RimeUserDir = $ud   存在=$(Test-Path $ud)"
$dirs = @($ud, "$env:ProgramFiles\Rime", "${env:ProgramFiles(x86)}\Rime", 'D:\Program Files\Rime') | Where-Object { $_ } | Select-Object -Unique
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) { W "目录 $d ：不存在"; continue }
    $nd = @(Get-ChildItem $d -Filter '*.dict.yaml').Count
    $hasLua = Test-Path (Join-Path $d 'lua\codeLookup_Filter.lua')
    $hasUser = Test-Path (Join-Path $d 'user.txt')
    W "目录 $d ：*.dict.yaml=$nd 个  codeLookup_Filter.lua=$hasLua  user.txt=$hasUser"
}
W ""

# ---- 2) 反查要读的几张表：在不在、多大、md5 ----
W "反查依赖的文件（相对 $ud）："
foreach ($f in @('rime.lua','lua\codeLookup_Filter.lua','lua\runLog.lua','wubi86.dict.yaml',
                 'wnwb_wubi_custom_wp.dict.yaml','wnwb_wubi_user_wp.dict.yaml','cn_pinyin_wp.dict.yaml','user.txt')) {
    $p = Join-Path $ud $f
    if (Test-Path $p) {
        $i = Get-Item $p
        $h = (Get-FileHash -Algorithm MD5 -LiteralPath $p).Hash
        W ("  [有] {0,-34} {1,9:N0} B  {2}" -f $f, $i.Length, $h)
    } else {
        W ("  [缺] {0,-34} ——反查会少一路数据" -f $f)
    }
}
W ""

# ---- 3) 部署产物里 codeLookup 到底挂没挂上 ----
W "build\ 里的方案是否引用 codeLookup："
$bd = Join-Path $ud 'build'
if (Test-Path $bd) {
    foreach ($b in @(Get-ChildItem $bd -Filter '*.schema.yaml')) {
        $t = Get-Content -LiteralPath $b.FullName -Raw -Encoding UTF8
        $hit = if ($t -match 'codeLookup') { '有 codeLookup' } else { '不含 codeLookup' }
        W ("  {0,-34} {1}" -f $b.Name, $hit)
    }
    $bw = Join-Path $bd 'weasel.yaml'
    if (Test-Path $bw) {
        $tw = Get-Content -LiteralPath $bw -Raw -Encoding UTF8
        if ($tw -match '(?m)^\s*show_notifications:\s*(\S+)') { W "  build/weasel.yaml show_notifications = $($matches[1])" }
    }
} else { W "  build 目录不存在（说明从没部署成功过）" }
W ""

# ---- 3b) 活动方案的编译产物齐不齐（缺 prism/table = 那次部署半途而废） ----
W "build\ 各方案的编译产物是否齐全："
$bs = @(Get-ChildItem $bd -Filter '*.schema.yaml' -ErrorAction SilentlyContinue)
if ($bs.Count -eq 0) { W "  （build 里没有 *.schema.yaml）" }
foreach ($s in $bs) {
    $n = $s.Name -replace '\.schema\.yaml$', ''
    $pm = Test-Path (Join-Path $bd "$n.prism.bin")
    $tb = Test-Path (Join-Path $bd "$n.table.bin")
    $rv = Test-Path (Join-Path $bd "$n.reverse.bin")
    $flag = ''
    if (-not $pm -or -not $tb) { $flag = '   <-- 没编译成功' }
    W ("  {0,-28} prism={1,-5} table={2,-5} reverse={3,-5}{4}" -f $n, $pm, $tb, $rv, $flag)
}
$bdef = Join-Path $bd 'default.yaml'
if (Test-Path $bdef) {
    $td = Get-Content -LiteralPath $bdef -Raw -Encoding UTF8
    $sl = @([regex]::Matches($td, 'schema:\s*([A-Za-z0-9_]+)') | ForEach-Object { $_.Groups[1].Value })
    W "  build/default.yaml 启用的方案 = $($sl -join ', ')"
}
W ""

# ---- 3c) rime 自己的日志（部署失败原因都写在这里） ----
W "rime 引擎日志："
# glog 的落点有三种可能：%TEMP% 根下、%TEMP%\rime.weasel\ 目录里，
# 甚至 %TEMP%\rime.weasel.<主机>.<用户>.log.INFO.<时间>.<pid> 这种「目录名里带 log」的怪布局（笔记本实测就是目录）。
# 老写法只用 -File 扫 Temp 根，那种布局一条都捞不到，所以先捞名字含 rime 的容器，再钻进去找文件。
$cand = @()
foreach ($t in @($env:TEMP, "$env:LOCALAPPDATA\Temp")) {
    if (-not (Test-Path -LiteralPath $t)) { continue }
    foreach ($it in @(Get-ChildItem -LiteralPath $t -Filter 'rime*' -ErrorAction SilentlyContinue)) {
        if ($it.PSIsContainer) {
            $cand += @(Get-ChildItem -LiteralPath $it.FullName -Recurse -File -ErrorAction SilentlyContinue |
                       Where-Object { $_.Name -like '*.log*' })
        } elseif ($it.Name -like '*.log*') {
            $cand += $it
        }
    }
}
$cand = @($cand | Sort-Object LastWriteTime -Descending | Group-Object FullName | ForEach-Object { $_.Group[0] } | Select-Object -First 6)
if ($cand.Count -eq 0) {
    W "  Temp 里没找到任何 rime 日志（引擎可能从没起来过）"
} else {
    foreach ($lg in $cand) {
        W "  --- $($lg.FullName)  $($lg.LastWriteTime)  $($lg.Length) B ---"
        foreach ($l in @(Get-Content -LiteralPath $lg.FullName -Tail 20 -Encoding UTF8 -ErrorAction SilentlyContinue)) { W "    $l" }
    }
    # 关键行去重后再打印：同一个报错在 INFO/WARNING/ERROR 三份里重复出现，不去重会把报告撑满。
    W "  关键行（部署跑没跑 / codeLookup 认了哪个目录 / 报错）："
    $re = 'updating (rime installation|workspace|schemas)|source file changed|finished updating schemas|saving config file|codeLookup:|attempt to open non-existent|Error loading table|^E20'
    $all = @()
    foreach ($lg in $cand) {
        foreach ($h in @(Select-String -LiteralPath $lg.FullName -Pattern $re -ErrorAction SilentlyContinue)) {
            $all += ,@($h.Line -replace '^[IWEF]\d{8} [\d:.]+ \d+ ', '')
        }
    }
    foreach ($m in @($all | ForEach-Object { $_[0] } | Select-Object -Unique | Select-Object -Last 20)) { W "    $m" }
}
W ""

# ---- 4) 运行日志尾部：滤镜在引擎里真正读到的目录与条数 ----
$rl = Join-Path $ud 'lua\runLog.txt'
W "lua\runLog.txt 最后 30 行（引擎里 codeLookup 真正载入的路径就在这里）："
if (Test-Path $rl) {
    foreach ($l in @(Get-Content -LiteralPath $rl -Tail 30)) { W "  $l" }
} else { W "  没有这个文件（日志没开，或从没部署过）" }
W ""

# ---- 5) 独立跑一次加载器：数据目录解析到哪儿、表里有多少条 ----
W "独立自检（用 Rime 自带 lua54 跑一遍 codeLookup 的加载器，只读）："
$luaExe = $null
foreach ($root in @($ud, "$env:ProgramFiles\Rime", 'D:\Program Files\Rime')) {
    if (-not (Test-Path $root)) { continue }
    $c = @(Get-ChildItem $root -Recurse -Filter 'lua54.exe' -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match 'x64' })
    if ($c.Count -gt 0) { $luaExe = $c[0].FullName; break }
}
if (-not $luaExe) { W "  没找到 lua54.exe，跳过"; }
else {
    W "  解释器：$luaExe"
    $mod = Join-Path $ud 'lua\codeLookup_Filter.lua'
    if (-not (Test-Path $mod)) { W "  没有 codeLookup_Filter.lua，跳过" }
    else {
        $raw = Get-Content -LiteralPath $mod -Raw -Encoding UTF8
        $diag = @'

collectgarbage('collect')
local function _c(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end
print('SELFTEST data_dir=' .. tostring(M.data_dir))
print('SELFTEST wubiMap=' .. _c(wubiMap) .. ' pinyinMap=' .. _c(pinyinMap) .. ' multiOwners=' .. _c(wubiMultiOwners))
for _, s in ipairs({'电','长','你好','中','国'}) do
  local ok, r = pcall(function() return M.lookup(s) end)
  print('SELFTEST ' .. s .. ' ok=' .. tostring(ok) .. ' -> ' .. tostring(r))
end
'@
        $idx = $raw.LastIndexOf('return codeLookup')
        if ($idx -lt 0) { W '  文件里没有 return codeLookup 这一行，跳过（防呆）' }
        else {
            $tmp = Join-Path $env:TEMP 'sansheng_selftest.lua'
            Set-Content -LiteralPath $tmp -Value ($raw.Substring(0,$idx) + $diag + "`nreturn codeLookup`n") -Encoding UTF8
            $harness = Join-Path $env:TEMP 'sansheng_selftest_harness.lua'
            $luaDir = (Join-Path $ud 'lua') -replace '\\','/'
            $tmpFwd = $tmp -replace '\\','/'
            Set-Content -LiteralPath $harness -Value "package.path = '$luaDir/?.lua;' .. package.path`nlocal ok, err = pcall(dofile, '$tmpFwd')`nprint('HARNESS ok=' .. tostring(ok) .. ' msg=' .. tostring(err))`n" -Encoding UTF8
            Push-Location (Join-Path $ud 'lua')
            $o = & $luaExe $harness 2>&1
            Pop-Location
            foreach ($l in @($o)) { W "  $l" }
            Remove-Item $tmp, $harness -ErrorAction SilentlyContinue
        }
    }
}
W ""
W "说明：以上全部为只读采集。SELFTEST 是脱离 Rime 引擎单独跑的，"
W "它和引擎里真正生效的目录可能不同；引擎里的真实路径看第 4 段 runLog 的「载入」行。"

$txt = $sb.ToString()
$outFile = Join-Path ([Environment]::GetFolderPath('Desktop')) '三生反查诊断.txt'
Set-Content -LiteralPath $outFile -Value $txt -Encoding UTF8
Write-Output $txt
Write-Output ""
Write-Output "已保存到：$outFile"
try { Start-Process notepad.exe -ArgumentList "`"$outFile`"" } catch {}

