# 把指定输入法（TIP）加入「当前用户可用键盘列表」。
# 用法： powershell -NoProfile -ExecutionPolicy Bypass -File enable-tip.ps1 -Tip "0804:{CLSID}{GUID}"
# 设计要点：读-改-写，幂等，绝不重建语言列表（避免把别的输入法/语言弄丢）。
param(
  [Parameter(Mandatory = $true)] [string]$Tip
)
$ErrorActionPreference = 'SilentlyContinue'
try {
  $list = Get-WinUserLanguageList
} catch {
  Write-Output 'TIPFAIL_LIST'
  exit 2
}
if (-not $list) { Write-Output 'TIPFAIL_EMPTY'; exit 3 }

$hit = $null
foreach ($lang in $list) {
  if ($lang.InputMethodTips -contains $Tip) { $hit = 'already'; break }
}
if ($hit -eq 'already') { Write-Output 'TIPALREADY'; exit 0 }

# 找一个中文（zh-*）语言对象挂上去；没有中文就挂第一个
$target = $null
foreach ($lang in $list) {
  if ($lang.LanguageTag -match '^(zh|chi)' ) { $target = $lang; break }
}
if (-not $target) { $target = $list[0] }

try {
  $copy = New-Object System.Collections.Generic.List[string]
  foreach ($t in $target.InputMethodTips) { $copy.Add($t) }
  $copy.Add($Tip)
  $target.InputMethodTips = $copy.ToArray()
  Set-WinUserLanguageList $list -Force
  Write-Output 'TIPADDED'
  exit 0
} catch {
  Write-Output 'TIPFAIL_SET'
  exit 4
}
