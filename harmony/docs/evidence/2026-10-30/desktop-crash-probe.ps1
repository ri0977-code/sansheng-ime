$ErrorActionPreference = 'SilentlyContinue'
$since = (Get-Date).AddDays(-2)
$ev = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = $since } |
      Where-Object { $_.ProviderName -match 'Application Error|Windows Error Reporting|Application Hang|\.NET Runtime|SideBySide' }
if (-not $ev) { 'NO CRASH EVENTS IN APPLICATION LOG (last 2 days)'; exit 0 }
foreach ($e in $ev) {
  '---- ' + $e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss') + '  [' + $e.ProviderName + '] id=' + $e.Id
  $lines = ($e.Message -split "`r?`n")
  ($lines | Select-Object -First 12) -join "`n"
  ''
}
