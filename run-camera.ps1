$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& .\stop-camera.ps1
& .\start-mqtt-broker.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe -m driver_monitor camera --index 0 --mqtt-host 127.0.0.1
