@echo off
rem ============================================================
rem Supply Chain Risk Control System - frontend watchdog starter
rem Forwards to the PowerShell watchdog script (start-frontend.ps1)
rem Double-click this file to start the frontend with auto-restart.
rem ============================================================
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-frontend.ps1"
pause
