param(
    [string]$Title = "Sansheng IME",
    [string]$Message = "Task completed",
    [int]$DurationMs = 5000
)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = $Title
$notify.BalloonTipText = $Message
$notify.Visible = $true
$notify.ShowBalloonTip($DurationMs)
Start-Sleep -Milliseconds ($DurationMs + 1000)
$notify.Dispose()
