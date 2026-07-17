@echo off
rem Optional Windows helper: runs the service detached-friendly with logs
rem appended to service.log (gitignored). Cross-platform path: python run.py
cd /d "%~dp0"
".venv\Scripts\python.exe" run.py >> service.log 2>&1
