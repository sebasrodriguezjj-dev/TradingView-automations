param(
    [Parameter(Mandatory = $true)]
    [string]$Automation,

    [string]$Message,

    [string]$MessageFile,

    [string]$Config,

    [string]$LogFile,

    [string]$Username = "SMART MONEY - GOOD MONEY"
)

function Add-NotifierLog {
    param(
        [string]$AutomationName,
        [string]$LogMessage
    )

    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    "$timestamp | $AutomationName | $LogMessage" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

function Read-WebhookUrl {
    param([string]$ConfigPath)

    if ($env:DISCORD_WEBHOOK_URL -and $env:DISCORD_WEBHOOK_URL.Trim()) {
        return $env:DISCORD_WEBHOOK_URL.Trim()
    }

    if (-not (Test-Path $ConfigPath)) {
        return $null
    }

    foreach ($rawLine in Get-Content $ConfigPath -Encoding utf8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }
        if ($line -match '^\s*DISCORD_WEBHOOK_URL\s*=\s*(.+)\s*$') {
            return $matches[1].Trim()
        }
    }

    return $null
}

function Get-MessageBody {
    param(
        [string]$InlineMessage,
        [string]$FilePath
    )

    if ($InlineMessage -and $InlineMessage.Trim()) {
        return $InlineMessage.Trim()
    }

    if ($FilePath -and (Test-Path $FilePath)) {
        return (Get-Content -Raw $FilePath -Encoding utf8).Trim()
    }

    return $null
}

function Add-WaitQuery {
    param([string]$WebhookUrl)

    if ($WebhookUrl -match '\?') {
        if ($WebhookUrl -match '(^|[?&])wait=') {
            return $WebhookUrl
        }
        return "${WebhookUrl}&wait=true"
    }

    return "${WebhookUrl}?wait=true"
}

if (-not $Config) {
    $Config = Join-Path $PSScriptRoot ".discord_webhook.env"
}

if (-not $LogFile) {
    $LogFile = Join-Path $PSScriptRoot "discord_notifier.log"
}

$pythonPath = "C:\Users\sebas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pythonNotifier = Join-Path $PSScriptRoot "discord_notifier.py"

$canUsePythonBridge = (Test-Path $pythonPath) -and (Test-Path $pythonNotifier)
if ($canUsePythonBridge) {
    $args = @(
        $pythonNotifier,
        "--automation", $Automation,
        "--config", $Config,
        "--log-file", $LogFile,
        "--username", $Username
    )

    if ($Message -and $Message.Trim()) {
        $args += @("--message", $Message.Trim())
    }
    elseif ($MessageFile) {
        $args += @("--message-file", $MessageFile)
    }

    & $pythonPath @args
    exit 0
}

$messageBody = Get-MessageBody -InlineMessage $Message -FilePath $MessageFile
if (-not $messageBody) {
    Add-NotifierLog -AutomationName $Automation -LogMessage "skip: empty message"
    exit 0
}

$webhookUrl = Read-WebhookUrl -ConfigPath $Config
if (-not $webhookUrl) {
    Add-NotifierLog -AutomationName $Automation -LogMessage "skip: missing webhook configuration"
    exit 0
}

try {
    $targetUrl = Add-WaitQuery -WebhookUrl $webhookUrl
    $payload = @{
        content  = $messageBody
        username = $Username
    } | ConvertTo-Json -Compress

    Invoke-RestMethod `
        -Method Post `
        -Uri $targetUrl `
        -ContentType "application/json" `
        -Body $payload `
        -Headers @{
            "User-Agent" = "Codex-Discord-Notifier/1.0"
            "Accept"     = "application/json"
        } `
        -TimeoutSec 8 | Out-Null

    Add-NotifierLog -AutomationName $Automation -LogMessage "sent"
}
catch {
    Add-NotifierLog -AutomationName $Automation -LogMessage ("failed: " + $_.Exception.GetType().Name + ": " + $_.Exception.Message)
}

exit 0
