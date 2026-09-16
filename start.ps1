# HK Speaks Continuous Platform Supervisor (PowerShell Launcher)
Set-Location -Path $PSScriptRoot

$PythonExe = Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$SupervisorScript = Join-Path $PSScriptRoot "scripts\supervisor.py"
& $PythonExe $SupervisorScript $args
