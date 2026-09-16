@echo off
title HK Speaks Dev Server
set PYTHON_EXE=backend\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)
"%PYTHON_EXE%" scripts\supervisor.py --dev %*
