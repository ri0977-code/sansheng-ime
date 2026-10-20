# 卸载时：从「当前用户可用键盘列表」里摘掉指定输入法（TIP）。
# 用法： powershell -NoProfile -ExecutionPolicy Bypass -File remove-tip.ps1 -Tip "0804:{CLSID}{GUID}"
# 设计要点：
#   1) 首选系统 API InstallLayoutOrTip(ILOT_UNINSTALL = 1)，Win10/Win11 上
#      比读-改-写可靠（那里 InputMethodTips 是只读属性）。该 API 是幂等的：
#      本来就不在列表里时调用也返回成功。
#   2) 旧系统回退到读-改-写。
#   3) 参数格式先校验，格式不对直接报错，绝不拿垃圾字符串去重写语言列表。
param(
  [Parameter(Mandatory = $true)] [string]$Tip
)
$ErrorActionPreference = 'SilentlyContinue'

# 形如 0804:{CLSID}{GUID}
if ($Tip -notmatch '^\d{4}:\{[0-9A-Fa-f-]{36}\}\{[0-9A-Fa-f-]{36}\}$') {
  Write-Output 'TIPFAIL_FORMAT'
  exit 5
}

function Test-TipPresent {
  try {
    $list = Get-WinUserLanguageList
    foreach ($lang in $list) {
      if ($lang.InputMethodTips -contains $Tip) { return $true }
    }
  } catch { }
  return $false
}

if (-not (Test-TipPresent)) { Write-Output 'TIPNONE'; exit 0 }

# 首选：input.dll!InstallLayoutOrTip(ILOT_UNINSTALL = 1)
try {
  if (-not ([System.Management.Automation.PSTypeName]'SanshengInputLayoutApi').Type) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class SanshengInputLayoutApi {
  [DllImport("input.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  public static extern bool InstallLayoutOrTip(string psz, uint dwFlags);
}
"@
  }
  if ([SanshengInputLayoutApi]::InstallLayoutOrTip($Tip, 1)) {
    Write-Output 'TIPREMOVED_API'
    exit 0
  }
} catch { }

# 回退：旧系统，读-改-写当前用户语言列表
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
    $done = $false
    try {
      $lang.InputMethodTips.Remove($Tip) | Out-Null
      $done = $true
    } catch {
      try {
        $copy = New-Object System.Collections.Generic.List[string]
        foreach ($t in $lang.InputMethodTips) {
          if ($t -ne $Tip) { $copy.Add($t) }
        }
        $lang.InputMethodTips = $copy.ToArray()
        $done = $true
      } catch { }
    }
    if ($done) { $changed = $true }
  }
}
if (-not $changed) { Write-Output 'TIPFAIL_SET'; exit 4 }

try {
  Set-WinUserLanguageList $list -Force
} catch {
  Write-Output 'TIPFAIL_SET'
  exit 4
}

if (Test-TipPresent) { Write-Output 'TIPFAIL_VERIFY'; exit 4 }
Write-Output 'TIPREMOVED'
exit 0
