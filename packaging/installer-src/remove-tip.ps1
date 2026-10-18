# 卸载时：从「当前用户可用键盘列表」里摘掉指定输入法（TIP）。
# 用法： powershell -NoProfile -ExecutionPolicy Bypass -File remove-tip.ps1 -Tip "0804:{CLSID}{GUID}"
# 设计要点：只在真的挂着它时才重写列表，其余情况一律不动。
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

$changed = $false
foreach ($lang in $list) {
  if ($lang.InputMethodTips -contains $Tip) {
    $copy = New-Object System.Collections.Generic.List[string]
    foreach ($t in $lang.InputMethodTips) {
      if ($t -ne $Tip) { $copy.Add($t) }
    }
    $lang.InputMethodTips = $copy.ToArray()
    $changed = $true
  }
}
if (-not $changed) { Write-Output 'TIPNONE'; exit 0 }

try {
  Set-WinUserLanguageList $list -Force
  Write-Output 'TIPREMOVED'
  exit 0
} catch {
  Write-Output 'TIPFAIL_SET'
  exit 4
}
