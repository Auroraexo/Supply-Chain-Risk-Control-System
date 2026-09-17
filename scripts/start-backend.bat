@echo off
rem ============================================================
rem Supply Chain Risk Control System - backend watchdog starter
rem Forwards to the PowerShell watchdog script (start-backend.ps1)
rem Double-click this file to start the backend with auto-restart.
rem ============================================================
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-backend.ps1"
pause
