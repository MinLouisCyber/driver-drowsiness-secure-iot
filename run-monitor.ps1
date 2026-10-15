$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& .\stop-camera.ps1
& .\start-mqtt-broker.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Starting hidden camera and live dashboard..."
Write-Host "Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop."
& .\.venv\Scripts\python.exe -m driver_monitor monitor --index 0 --mqtt-host 127.0.0.1
