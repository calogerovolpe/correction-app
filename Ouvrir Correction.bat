@echo off
rem ==================================================
rem  Correction - ouvre l'application web en local
rem  Double-cliquez : le serveur demarre en arriere-plan
rem  puis le navigateur s'ouvre sur http://localhost:8000
rem  Pour arreter : fermer la fenetre "Correction - serveur".
rem ==================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Erreur : environnement virtuel introuvable dans le dossier du projet.
    pause
    exit /b 1
)
rem Le serveur tourne-t-il deja sur le port 8000 ?
powershell -NoProfile -Command "try { $null = New-Object Net.Sockets.TcpClient('127.0.0.1',8000); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 goto :ouvrir
start "Correction - serveur" /min ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
:attendre
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try { $null = New-Object Net.Sockets.TcpClient('127.0.0.1',8000); exit 0 } catch { exit 1 }" >nul 2>&1
if not %errorlevel%==0 goto :attendre
:ouvrir
start "" "http://localhost:8000"
exit /b 0
