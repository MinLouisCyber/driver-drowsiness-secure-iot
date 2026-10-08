$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& .\stop-camera.ps1
& .\start-mqtt-broker.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "MQTT broker ready. Start Wokwi, then keep it running. Press Ctrl+C here to stop."
& .\.venv\Scripts\python.exe -m driver_monitor camera --index 0 --no-preview --mqtt-host 127.0.0.1
