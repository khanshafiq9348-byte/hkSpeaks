@echo off
rem =========================================================================
rem  HK Speaks Platform - Background Auto-Start Script
rem =========================================================================
cd /d "%~dp0\.."

set PYTHON_EXE=backend\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" scripts\supervisor.py --daemon
