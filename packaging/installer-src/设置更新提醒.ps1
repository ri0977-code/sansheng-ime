# 建立或删除「自动更新提醒」计划任务（安装器与卸载器共用）
#
# 为什么不用 schtasks 命令行：它会在空格处把 /TR 的参数拆开，
# 装在 C:\Program Files\... 的用户会得到一个 Execute=D:\Program、Arguments=Files\...
# 的坏任务（实测踩过，LastTaskResult 非 0 且目标文件 Test-Path=False）。
# Task Scheduler 的 COM 接口直接收完整路径，不经过那层命令行引号解析。
#
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File 设置更新提醒.ps1 -Action Install -ScriptPath "C:\...\自动更新提醒.cmd"
#   powershell -NoProfile -ExecutionPolicy Bypass -File 设置更新提醒.ps1 -Action Remove
#
# 退出码：0 = 成功；2 = 失败（调用方据此决定要不要提示用户，不影响输入法本身）
# 注意：本文件必须存成 UTF-8 带 BOM，否则 PowerShell 5.1 读中文字面量会报语法错。

#Requires -Version 5.0
param(
  [ValidateSet('Install', 'Remove')]
  [string]$Action = 'Install',
  [string]$ScriptPath = '',
  [string]$TaskName = 'SanshengIME-UpdateCheck',
  [string]$At = '11:30',
  [string]$Days = 'Sunday'
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

function Write-Info([string]$m) { Write-Output ("[update-notice] " + $m) }

if ($Action -eq 'Remove') {
  try {
    $old = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($old) {
      Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
      Write-Info ("已删除计划任务 " + $TaskName)
    } else {
      Write-Info ("计划任务不存在，跳过：" + $TaskName)
    }
    exit 0
  } catch {
    Write-Info ("删除计划任务失败（不影响卸载）：" + $_.Exception.Message)
    exit 2
  }
}

# ---- Install ----
if (-not $ScriptPath) { Write-Info '缺少 -ScriptPath'; exit 2 }
if (-not (Test-Path -LiteralPath $ScriptPath)) {
  Write-Info ("脚本不存在：" + $ScriptPath); exit 2
}

try {
  $dayEnum = [System.DayOfWeek]$Days
  $atTime  = [DateTime]::ParseExact($At, 'HH:mm', $null)

  # 交互式用户身份（不用 SYSTEM）：气泡通知要显示在主人桌面上，
  # 用 SYSTEM 身份跑在会话 0 里，通知出不来。
  $principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
                                          -LogonType Interactive -RunLevel Limited

  $act = New-ScheduledTaskAction -Execute $ScriptPath
  $trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $dayEnum -At $atTime
  $st  = New-ScheduledTask -Action $act -Trigger $trg -Principal $principal `
                            -Description '三生输入法自动更新提醒：每周查一次，有新版本弹一条桌面通知（不自动下载、不自动安装）'
  Register-ScheduledTask -TaskName $TaskName -InputObject $st -Force | Out-Null

  # 回读核对：路径必须完整、文件必须真的在
  $t = Get-ScheduledTask -TaskName $TaskName
  $exe = $t.Actions[0].Execute
  $info = Get-ScheduledTaskInfo -TaskName $TaskName
  $ok = ($t.State -eq 'Ready') -and (Test-Path -LiteralPath $exe) -and ($null -ne $info.NextRunTime)
  Write-Info ("任务=" + $TaskName + "  状态=" + $t.State + "  下次=" + $info.NextRunTime)
  Write-Info ("指向=" + $exe + "  文件存在=" + (Test-Path -LiteralPath $exe))
  if ($ok) { exit 0 } else { exit 2 }
} catch {
  Write-Info ("建立计划任务失败（不影响输入法使用）：" + $_.Exception.Message)
  exit 2
}