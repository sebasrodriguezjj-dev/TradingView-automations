$workspaceRoot = $PSScriptRoot
. (Join-Path $workspaceRoot "watcher_process_control.ps1")

$watchers = @(
    @{
        Name = "market"
        Owner = "SMART MONEY - GOOD MONEY Market Watchdog"
        WorkspaceRoot = $workspaceRoot
        ScriptPath = Join-Path $workspaceRoot "market_watchdog.py"
        LauncherPath = Join-Path $workspaceRoot "start_market_watchdog.ps1"
        PidPath = Join-Path $workspaceRoot "market_runtime\market_watchdog.pid.json"
        StatePath = Join-Path $workspaceRoot "market_runtime\market_watchdog_state.json"
    },
    @{
        Name = "chart"
        Owner = "SMART MONEY - GOOD MONEY Chart Watchdog"
        WorkspaceRoot = $workspaceRoot
        ScriptPath = Join-Path $workspaceRoot "chart_watchdog.py"
        LauncherPath = Join-Path $workspaceRoot "start_chart_watchdog.ps1"
        PidPath = Join-Path $workspaceRoot "chart_runtime\chart_watchdog.pid.json"
        StatePath = Join-Path $workspaceRoot "chart_runtime\chart_watchdog_state.json"
    },
    @{
        Name = "discord"
        Owner = "SMART MONEY - GOOD MONEY Discord Dispatch Watcher"
        WorkspaceRoot = $workspaceRoot
        ScriptPath = Join-Path $workspaceRoot "discord_dispatch_watcher.py"
        LauncherPath = Join-Path $workspaceRoot "start_discord_dispatch_watcher.ps1"
        PidPath = Join-Path $workspaceRoot "discord_dispatch_watcher.pid.json"
        StatePath = Join-Path $workspaceRoot "discord_dispatch_state.json"
    }
)

function Get-StateSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $fileInfo = Get-FileInfoForRestart -Path $Path
    $payload = Read-JsonFile -Path $Path

    return [pscustomobject]@{
        exists = $fileInfo.exists
        last_write_time = $fileInfo.last_write_time
        runtime_status = if ($payload -and $payload.status) { $payload.status } else { $null }
        heartbeat_at = if ($payload -and $payload.heartbeat_at) { $payload.heartbeat_at } else { $null }
        dependency_status = if ($payload -and $payload.dependency_status) { $payload.dependency_status } else { $null }
        last_error = if ($payload -and $payload.last_error) { $payload.last_error } else { $null }
    }
}

$stopResults = @()
$allStoppedProcessIds = @()

foreach ($watcher in $watchers) {
    $stopResult = Stop-ManagedWatcher -Watcher $watcher -StopExactOrphans
    $allStoppedProcessIds += @($stopResult.stopped_process_ids)
    $stopResults += [pscustomobject]@{
        name = $watcher.Name
        stopped_process_ids = @($stopResult.stopped_process_ids)
        skipped = @($stopResult.skipped)
    }
}

$lockResult = Clear-StaleTvGatewayLock `
    -LockPath (Join-Path $workspaceRoot "tv_gateway.lock") `
    -StoppedProcessIds @($allStoppedProcessIds)

$restartResults = @()

foreach ($watcher in $watchers) {
    $startResult = Start-ManagedWatcherProcess -Watcher $watcher
    Start-Sleep -Seconds 2

    $managed = Get-ManagedWatcherProcess -Watcher $watcher
    $stateSummary = Get-StateSummary -Path $watcher.StatePath

    $restartResults += [pscustomobject]@{
        name = $watcher.Name
        script = $watcher.ScriptPath
        launcher = $watcher.LauncherPath
        pid_path = $watcher.PidPath
        start_result = $startResult.reason
        started_new_process = $startResult.started
        pid = $startResult.pid
        process_status = if ($managed.running -and $managed.verified) { "running" } else { "not_verified" }
        process_verification = $managed.reason
        state_path = $watcher.StatePath
        state_exists = $stateSummary.exists
        state_last_write_time = $stateSummary.last_write_time
        runtime_status = $stateSummary.runtime_status
        heartbeat_at = $stateSummary.heartbeat_at
        dependency_status = $stateSummary.dependency_status
        last_error = $stateSummary.last_error
    }
}

$summary = [pscustomobject]@{
    owner = "SMART MONEY - GOOD MONEY Watcher Restart"
    restarted_at = (Get-Date).ToString("o")
    workspace = $workspaceRoot
    stopped_watchers = $stopResults
    tv_gateway_lock = $lockResult
    watchers = $restartResults
}

$summary | ConvertTo-Json -Depth 8
