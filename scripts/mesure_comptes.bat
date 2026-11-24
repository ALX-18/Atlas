@echo off
rem IF7, etape 0 sur AtlasTest : ce que ce compte voit de l'Atlas et de l'Ollama d'un autre compte. Rien n'est installe.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mesure_comptes.ps1"
echo.
pause
