@echo off
chcp 65001 >nul
title Guitar-to-Doom Launcher
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден! Запустите Install_Dependencies.bat
    pause
    exit /b 1
)

python launcher.py
