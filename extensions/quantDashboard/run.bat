@echo off
setlocal
cd /d "%~dp0"

echo === quantDashboard ===
echo [1/3] Pulling performance.db from rwUbuntu...
python pull_db.py
if errorlevel 1 (
    echo ERROR: DB pull failed
    pause
    exit /b 1
)

echo [2/3] Building dashboard...
python build_dashboard.py %*
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo [3/3] Opening dashboard...
start dashboard.html

echo === Done ===
