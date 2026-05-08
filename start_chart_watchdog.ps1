$workspaceRoot = $PSScriptRoot
. (Join-Path $workspaceRoot "watcher_process_control.ps1")

$watcher = @{
    Name = "chart"
    Owner = "SMART MONEY - GOOD MONEY Chart Watchdog"
    WorkspaceRoot = $workspaceRoot
    ScriptPath = Join-Path $workspaceRoot "chart_watchdog.py"
    LauncherPath = $MyInvocation.MyCommand.Path
    PidPath = Join-Path $workspaceRoot "chart_runtime\chart_watchdog.pid.json"
}

Start-ManagedWatcherProcess -Watcher $watcher | Out-Null
