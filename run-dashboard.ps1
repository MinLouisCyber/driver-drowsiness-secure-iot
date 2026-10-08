$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& .\.venv\Scripts\python.exe -m driver_monitor serve

