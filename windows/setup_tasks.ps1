# SNS-spiritual Windows Task Scheduler Setup Script
# LunaVeil_7th account auto-posting tasks
#
# Tasks registered:
#   - Daily        07:00 JST
#   - Daily        12:00 JST
#   - Daily        21:00 JST
#   - Wed/Sat only 15:00 JST
#
# WakeToRun: wakes PC from S3 sleep to execute.
# Run via setup_tasks.bat (admin elevation is handled automatically).

$ErrorActionPreference = 'Stop'

# ---- Admin check and auto-elevation --------------------------
# Use New-Object to avoid multi-line cast issues on PS 5.1
$currentIdentity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host 'Admin rights required. Please approve the UAC dialog...'
    $psArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"'
    Start-Process PowerShell -Verb RunAs -ArgumentList $psArgs
    exit
}

# ---- Path setup ----------------------------------------------
$ScriptDir = $PSScriptRoot                  # windows\ folder
$RepoDir   = Split-Path -Parent $ScriptDir  # repository root
$RunBat    = Join-Path $ScriptDir 'run_post.bat'

Write-Host ''
Write-Host '=== SNS-spiritual Task Scheduler Setup ===' -ForegroundColor Cyan
Write-Host "Repository : $RepoDir"
Write-Host "Run script : $RunBat"
Write-Host ''

if (-not (Test-Path $RunBat)) {
    Write-Host "[ERROR] run_post.bat not found: $RunBat" -ForegroundColor Red
    exit 1
}

# ---- Common task settings ------------------------------------

# Action: run run_post.bat via cmd.exe
$action = New-ScheduledTaskAction `
    -Execute          'cmd.exe' `
    -Argument         ("/c `"" + $RunBat + "`"") `
    -WorkingDirectory $RepoDir

# Settings:
#   WakeToRun         ... wake from S3 sleep and run
#   StartWhenAvailable... run at next boot if missed
#   MultipleInstances ... do not run concurrently
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# Principal: run as current user (requires login)
$currentName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal `
    -UserId    $currentName `
    -LogonType Interactive `
    -RunLevel  Highest

# ---- Task definitions ----------------------------------------
$taskDefs = @(
    @{ Name = 'LunaVeil_Post_07';        Trigger = (New-ScheduledTaskTrigger -Daily -At '07:00');                                       Desc = 'Daily 07:00 JST' },
    @{ Name = 'LunaVeil_Post_12';        Trigger = (New-ScheduledTaskTrigger -Daily -At '12:00');                                       Desc = 'Daily 12:00 JST' },
    @{ Name = 'LunaVeil_Post_21';        Trigger = (New-ScheduledTaskTrigger -Daily -At '21:00');                                       Desc = 'Daily 21:00 JST' },
    @{ Name = 'LunaVeil_Post_WedSat_15'; Trigger = (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday,Saturday -At '15:00'); Desc = 'Wed/Sat 15:00 JST' }
)

# ---- Register tasks ------------------------------------------
Write-Host 'Registering tasks...' -ForegroundColor White

foreach ($td in $taskDefs) {
    $existing = Get-ScheduledTask -TaskName $td.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $td.Name -Confirm:$false
        Write-Host ("  [removed] " + $td.Name + " (re-registering)") -ForegroundColor Yellow
    }

    Register-ScheduledTask `
        -TaskName    $td.Name `
        -Description ("LunaVeil_7th: " + $td.Desc) `
        -Action      $action `
        -Trigger     $td.Trigger `
        -Settings    $settings `
        -Principal   $principal | Out-Null

    Write-Host ("  [OK]   " + $td.Name) -ForegroundColor Green
}

# ---- Results -------------------------------------------------
Write-Host ''
Write-Host '=== Setup Complete ===' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Registered tasks:' -ForegroundColor White

Get-ScheduledTask | Where-Object { $_.TaskName -like 'LunaVeil_*' } | ForEach-Object {
    $info    = Get-ScheduledTaskInfo -TaskName $_.TaskName -ErrorAction SilentlyContinue
    $nextRun = if ($info -and $info.NextRunTime) { $info.NextRunTime.ToString('yyyy-MM-dd HH:mm') } else { 'unknown' }
    Write-Host ("  {0,-35} Next run: {1}" -f $_.TaskName, $nextRun)
}

# ---- Notes ---------------------------------------------------
Write-Host ''
Write-Host '================================================================' -ForegroundColor Yellow
Write-Host '[IMPORTANT] To enable wake-from-sleep, confirm the following:' -ForegroundColor Yellow
Write-Host '================================================================' -ForegroundColor Yellow
Write-Host ''
Write-Host '(1) Enable wake timers in Windows Power Plan:'
Write-Host '    Control Panel -> Power Options -> Change plan settings'
Write-Host '    -> Change advanced power settings -> Sleep'
Write-Host '    -> Allow wake timers -> set to [Enable]'
Write-Host ''
Write-Host '(2) Ensure Wake on RTC (RTC Alarm) is enabled in BIOS/UEFI'
Write-Host '    (S3 sleep support confirmed, so this should be fine)'
Write-Host ''
Write-Host '(3) Check Task Scheduler: [Win+R] -> taskschd.msc'
Write-Host '    LunaVeil_Post_* tasks should appear in Task Scheduler Library'
Write-Host ''
Write-Host '(4) Manual test: right-click a task -> Run'
Write-Host '    Check logs\post.log for output'
Write-Host ''
