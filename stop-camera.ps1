$cameraProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and
    $_.CommandLine -match "-m\s+driver_monitor\s+camera"
}

if (-not $cameraProcesses) {
    Write-Host "No previous project camera process is running."
    exit 0
}

foreach ($cameraProcess in $cameraProcesses) {
    Stop-Process -Id $cameraProcess.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500
Write-Host "Stopped previous project camera process(es)."
