@echo off
rem Pre-verification Atlas : lecture seule, rien n'est installe.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0precheck_atlas.ps1"
echo.
pause
