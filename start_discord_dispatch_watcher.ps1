$pythonPath = "C:\Users\sebas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$watcherPath = Join-Path $PSScriptRoot "discord_dispatch_watcher.py"

if (-not (Test-Path $pythonPath)) {
    throw "Python runtime not found at $pythonPath"
}

if (-not (Test-Path $watcherPath)) {
    throw "Watcher script not found at $watcherPath"
}

Start-Process -FilePath $pythonPath -ArgumentList @($watcherPath) -WindowStyle Hidden
