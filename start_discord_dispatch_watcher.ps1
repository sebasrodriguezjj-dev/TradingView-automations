$workspaceRoot = $PSScriptRoot
. (Join-Path $workspaceRoot "watcher_process_control.ps1")

$watcher = @{
    Name = "discord"
    Owner = "SMART MONEY - GOOD MONEY Discord Dispatch Watcher"
    WorkspaceRoot = $workspaceRoot
    ScriptPath = Join-Path $workspaceRoot "discord_dispatch_watcher.py"
    LauncherPath = $MyInvocation.MyCommand.Path
    PidPath = Join-Path $workspaceRoot "discord_dispatch_watcher.pid.json"
}

Start-ManagedWatcherProcess -Watcher $watcher | Out-Null
