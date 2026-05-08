$PythonPath = "C:\Users\sebas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

function ConvertTo-IsoString {
    param(
        [Parameter(Mandatory = $true)]
        [datetime]$DateTime
    )

    return $DateTime.ToString("o")
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Payload
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-PythonCommandLineProcesses {
    try {
        return @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
            $_.Name -match '^python(?:\.exe)?$' -and $_.CommandLine
        })
    }
    catch {
        return @()
    }
}

function Get-WatcherProcessesByCommandLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    $normalizedScriptPath = [System.IO.Path]::GetFullPath($ScriptPath)
    @(Get-PythonCommandLineProcesses | Where-Object {
        $_.CommandLine.Contains($normalizedScriptPath)
    })
}

function Get-ManagedWatcherProcess {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Watcher
    )

    $pidState = Read-JsonFile -Path $Watcher.PidPath
    if (-not $pidState -or -not $pidState.pid) {
        return [pscustomobject]@{
            running = $false
            verified = $false
            pid = $null
            process = $null
            reason = "missing_pid_file"
        }
    }

    $processId = [int]$pidState.pid
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $process) {
        return [pscustomobject]@{
            running = $false
            verified = $false
            pid = $processId
            process = $null
            reason = "pid_not_running"
        }
    }

    if ($process.ProcessName -notmatch '^python') {
        return [pscustomobject]@{
            running = $false
            verified = $false
            pid = $processId
            process = $process
            reason = "pid_not_python"
        }
    }

    $normalizedScriptPath = [System.IO.Path]::GetFullPath($Watcher.ScriptPath)
    $commandMatch = @(Get-PythonCommandLineProcesses | Where-Object {
        $_.ProcessId -eq $processId -and $_.CommandLine.Contains($normalizedScriptPath)
    })
    if (@($commandMatch).Count -gt 0) {
        return [pscustomobject]@{
            running = $true
            verified = $true
            pid = $processId
            process = $process
            reason = "command_line_match"
        }
    }

    $startedAt = $null
    if ($pidState.started_at) {
        try {
            $startedAt = [datetime]::Parse([string]$pidState.started_at)
        }
        catch {
            $startedAt = $null
        }
    }

    if ($startedAt -and $process.StartTime) {
        $deltaSeconds = [math]::Abs(($process.StartTime - $startedAt).TotalSeconds)
        if ($deltaSeconds -le 30) {
            return [pscustomobject]@{
                running = $true
                verified = $true
                pid = $processId
                process = $process
                reason = "pid_start_time_match"
            }
        }
    }

    return [pscustomobject]@{
        running = $false
        verified = $false
        pid = $processId
        process = $process
        reason = "pid_unverified"
    }
}

function Stop-ProcessSafely {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId
    )

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) {
        return $false
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    return -not [bool](Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Stop-ManagedWatcher {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Watcher,
        [switch]$StopExactOrphans
    )

    $stopped = @()
    $skipped = @()
    $managed = Get-ManagedWatcherProcess -Watcher $Watcher

    if ($managed.running -and $managed.verified -and $managed.pid) {
        if (Stop-ProcessSafely -ProcessId ([int]$managed.pid)) {
            $stopped += [int]$managed.pid
        }
        else {
            $skipped += [pscustomobject]@{
                pid = [int]$managed.pid
                reason = "stop_failed"
            }
        }
    }

    if (-not $managed.running -and (Test-Path -LiteralPath $Watcher.PidPath)) {
        Remove-Item -LiteralPath $Watcher.PidPath -Force -ErrorAction SilentlyContinue
    }

    if ($StopExactOrphans) {
        foreach ($process in Get-WatcherProcessesByCommandLine -ScriptPath $Watcher.ScriptPath) {
            $processId = [int]$process.ProcessId
            if ($stopped -contains $processId) {
                continue
            }
            if (Stop-ProcessSafely -ProcessId $processId) {
                $stopped += $processId
            }
            else {
                $skipped += [pscustomobject]@{
                    pid = $processId
                    reason = "exact_orphan_stop_failed"
                }
            }
        }
    }

    if (Test-Path -LiteralPath $Watcher.PidPath) {
        $afterStop = Get-ManagedWatcherProcess -Watcher $Watcher
        if (-not $afterStop.running) {
            Remove-Item -LiteralPath $Watcher.PidPath -Force -ErrorAction SilentlyContinue
        }
    }

    return [pscustomobject]@{
        stopped_process_ids = @($stopped)
        skipped = @($skipped)
    }
}

function Start-ManagedWatcherProcess {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Watcher
    )

    if (-not (Test-Path -LiteralPath $PythonPath)) {
        throw "Python runtime not found at $PythonPath"
    }

    if (-not (Test-Path -LiteralPath $Watcher.ScriptPath)) {
        throw "$($Watcher.Name) watcher script not found at $($Watcher.ScriptPath)"
    }

    $existing = Get-ManagedWatcherProcess -Watcher $Watcher
    if ($existing.running -and $existing.verified) {
        return [pscustomobject]@{
            started = $false
            pid = [int]$existing.pid
            reason = "already_running"
        }
    }

    $process = Start-Process -FilePath $PythonPath -ArgumentList @($Watcher.ScriptPath) -WorkingDirectory $Watcher.WorkspaceRoot -WindowStyle Hidden -PassThru
    Start-Sleep -Milliseconds 300

    $startedAt = Get-Date
    try {
        $startedAt = $process.StartTime
    }
    catch {
        $startedAt = Get-Date
    }

    Write-JsonFile -Path $Watcher.PidPath -Payload ([pscustomobject]@{
        pid_file_version = 1
        name = $Watcher.Name
        owner = $Watcher.Owner
        pid = [int]$process.Id
        process_name = $process.ProcessName
        script_path = [System.IO.Path]::GetFullPath($Watcher.ScriptPath)
        launcher_path = $Watcher.LauncherPath
        workspace = $Watcher.WorkspaceRoot
        started_at = ConvertTo-IsoString -DateTime $startedAt
        written_at = ConvertTo-IsoString -DateTime (Get-Date)
    })

    return [pscustomobject]@{
        started = $true
        pid = [int]$process.Id
        reason = "started"
    }
}

function Get-FileInfoForRestart {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{
            exists = $false
            last_write_time = $null
        }
    }

    $item = Get-Item -LiteralPath $Path
    return [pscustomobject]@{
        exists = $true
        last_write_time = $item.LastWriteTime.ToString("o")
    }
}

function Clear-StaleTvGatewayLock {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LockPath,
        [int[]]$StoppedProcessIds = @()
    )

    if (-not (Test-Path -LiteralPath $LockPath)) {
        return [pscustomobject]@{
            existed = $false
            removed = $false
            reason = "missing"
            owner_pid = $null
        }
    }

    $lockPayload = Read-JsonFile -Path $LockPath
    $ownerPid = $null
    if ($lockPayload -and $lockPayload.pid) {
        $ownerPid = [int]$lockPayload.pid
    }

    $ownerRunning = $false
    if ($ownerPid) {
        $ownerRunning = [bool](Get-Process -Id $ownerPid -ErrorAction SilentlyContinue)
    }

    $stoppedOwner = $ownerPid -and ($StoppedProcessIds -contains $ownerPid)
    if (-not $ownerPid -or $stoppedOwner -or -not $ownerRunning) {
        Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
        return [pscustomobject]@{
            existed = $true
            removed = $true
            reason = if ($stoppedOwner) { "owner_stopped" } elseif (-not $ownerPid) { "missing_owner_pid" } else { "owner_not_running" }
            owner_pid = $ownerPid
        }
    }

    return [pscustomobject]@{
        existed = $true
        removed = $false
        reason = "owner_still_running"
        owner_pid = $ownerPid
    }
}
