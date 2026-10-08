$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& .\start-mqtt-broker.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Keep the Wokwi simulator running during this MQTT test."
& .\.venv\Scripts\python.exe -m driver_monitor mqtt-test --mqtt-host 127.0.0.1
