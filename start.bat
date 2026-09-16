@echo off
title HK Speaks Continuous Platform Supervisor
cd /d "%~dp0"

echo =========================================================
echo   Starting HK Speaks Continuous Platform Supervisor...
echo =========================================================

set PYTHON_EXE=backend\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" scripts\supervisor.py %*
