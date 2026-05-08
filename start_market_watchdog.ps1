$workspaceRoot = $PSScriptRoot
. (Join-Path $workspaceRoot "watcher_process_control.ps1")

$watcher = @{
    Name = "market"
    Owner = "SMART MONEY - GOOD MONEY Market Watchdog"
    WorkspaceRoot = $workspaceRoot
    ScriptPath = Join-Path $workspaceRoot "market_watchdog.py"
    LauncherPath = $MyInvocation.MyCommand.Path
    PidPath = Join-Path $workspaceRoot "market_runtime\market_watchdog.pid.json"
}

Start-ManagedWatcherProcess -Watcher $watcher | Out-Null
