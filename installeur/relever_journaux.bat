@echo off
rem Releve des journaux d'Atlas et de son installeur, anonymises, dans le dossier de ce fichier (cle USB).
rem Rien n'est modifie sur cet ordinateur. La memoire, les reglages et les secrets ne sont jamais copies.
set "PY=%LOCALAPPDATA%\Programs\Atlas\python\python.exe"
set "SCRIPT=%LOCALAPPDATA%\Programs\Atlas\installeur\relever_journaux.py"
if not exist "%PY%" goto absent
if not exist "%SCRIPT%" goto absent
"%PY%" "%SCRIPT%" --vers "%~dp0releves"
echo.
pause
exit /b 0
:absent
echo Atlas n'est pas installe sur cet ordinateur : rien a relever avec ce fichier.
echo Apres une desinstallation, relancer ce releve une fois Atlas reinstalle.
echo.
pause
exit /b 1
