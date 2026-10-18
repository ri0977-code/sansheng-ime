# 安装前把用户目录里已有的 Rime 配置备份一份（带时间戳）。
# 用法: powershell -File backup-user-config.ps1 -Dir "<Rime用户目录>"
# 只备份配置文件（*.yaml / *.txt / lua），绝不动 *.userdb / sync（打字记录，又大又没必要）。
param(
  [Parameter(Mandatory = $true)][string]$Dir,
  [switch]$WhatIf
)
$ErrorActionPreference = 'SilentlyContinue'
if (-not (Test-Path -LiteralPath $Dir)) { Write-Output 'BACKUP_SKIP_NODIR'; exit 0 }

# 注意：-Include 在不带 -Recurse 时不生效，这里用通配路径 + 扩展名过滤
$files = @(Get-ChildItem -Path (Join-Path $Dir '*') -File |
           Where-Object { $_.Extension -eq '.yaml' -or $_.Extension -eq '.txt' })
$lua = Join-Path $Dir 'lua'

if ($files.Count -eq 0 -and -not (Test-Path -LiteralPath $lua)) {
  Write-Output 'BACKUP_SKIP_EMPTY'
  exit 0
}

$dst = Join-Path $Dir ('sansheng-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (-not $WhatIf) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
foreach ($f in $files) {
  if (-not $WhatIf) { Copy-Item -LiteralPath $f.FullName -Destination $dst -Force }
}
if ((Test-Path -LiteralPath $lua) -and -not $WhatIf) {
  Copy-Item -Path $lua -Destination (Join-Path $dst 'lua') -Recurse -Force
}
Write-Output ('BACKUP_OK -> ' + $dst + ' (' + $files.Count + ' 个配置文件)')
exit 0
