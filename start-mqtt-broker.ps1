$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$listener = Get-NetTCPConnection -LocalPort 1883 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "MQTT broker is already running on port 1883."
    exit 0
}

$logDirectory = Join-Path $projectRoot "data"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$stdout = Join-Path $logDirectory "mqtt-broker.log"
$stderr = Join-Path $logDirectory "mqtt-broker-error.log"
$process = Start-Process .\.venv\Scripts\python.exe `
    -ArgumentList "-m", "driver_monitor", "broker" `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

Start-Sleep -Seconds 2
$listener = Get-NetTCPConnection -LocalPort 1883 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Write-Host "MQTT broker failed to start. See: $stderr"
    if (Test-Path $stderr) { Get-Content $stderr }
    exit 1
}

Write-Host "MQTT broker started: PID=$($process.Id), port=1883"
Write-Host "Log: $stdout"
