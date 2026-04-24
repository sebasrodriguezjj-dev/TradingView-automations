$pythonPath = "C:\Users\sebas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$watchdogPath = Join-Path $PSScriptRoot "chart_watchdog.py"

if (-not (Test-Path $pythonPath)) {
    throw "Python runtime not found at $pythonPath"
}

if (-not (Test-Path $watchdogPath)) {
    throw "Chart watchdog script not found at $watchdogPath"
}

Start-Process -FilePath $pythonPath -ArgumentList @($watchdogPath) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
