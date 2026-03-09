@echo off
chcp 65001 >nul
title Guitar-to-Doom: Tutorial
cd /d "%~dp0"
echo.
echo   1. Gitara ^(6 strun^)
echo   2. Bass ^(4 struny^)
echo.
set /p MODE="Vyberi rezhim ^(1/2^): "
if "%MODE%"=="2" (
    python guitar_tutorial.py --bass
) else (
    python guitar_tutorial.py
)
pause
