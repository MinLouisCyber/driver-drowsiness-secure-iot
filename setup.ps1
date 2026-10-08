$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Can cai uv truoc: https://docs.astral.sh/uv/"
}

uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e .
Write-Host "Da cai dat xong. Chay: .\.venv\Scripts\python.exe -m driver_monitor simulate"

