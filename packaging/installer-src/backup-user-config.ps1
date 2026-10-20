# 安装前把用户目录里已有的 Rime 配置备份一份（带时间戳）。
# 用法: powershell -File backup-user-config.ps1 -Dir "<Rime用户目录>"
# 备份范围：顶层 *.yaml / *.txt / *.lua / *.json、lua 目录、opencc 目录。
# 绝不动 *.userdb（打字记录）、sync（同步目录）和 build（部署生成物，会重建）。
param(
  [Parameter(Mandatory = $true)][string]$Dir,
  [switch]$WhatIf
)
$ErrorActionPreference = 'SilentlyContinue'
if (-not (Test-Path -LiteralPath $Dir)) { Write-Output 'BACKUP_SKIP_NODIR'; exit 0 }

# 注意：-Include 在不带 -Recurse 时不生效，这里用通配路径 + 扩展名过滤
$files = @(Get-ChildItem -Path (Join-Path $Dir '*') -File |
           Where-Object { $_.Extension -in '.yaml', '.txt', '.lua', '.json' })
$folders = @('lua', 'opencc') |
           ForEach-Object { Join-Path $Dir $_ } |
           Where-Object { Test-Path -LiteralPath $_ }

if ($files.Count -eq 0 -and $folders.Count -eq 0) {
  Write-Output 'BACKUP_SKIP_EMPTY'
  exit 0
}

$dst = Join-Path $Dir ('sansheng-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (-not $WhatIf) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
foreach ($f in $files) {
  if (-not $WhatIf) { Copy-Item -LiteralPath $f.FullName -Destination $dst -Force }
}
foreach ($d in $folders) {
  if (-not $WhatIf) {
    Copy-Item -LiteralPath $d -Destination (Join-Path $dst (Split-Path $d -Leaf)) -Recurse -Force
  }
}
Write-Output ('BACKUP_OK -> ' + $dst + ' (' + $files.Count + ' 个配置文件，' + $folders.Count + ' 个目录)')
exit 0
