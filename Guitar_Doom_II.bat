@echo off
chcp 65001 >nul
title Guitar-to-Doom: DOOM II
cd /d "%~dp0"

echo ================================================
echo   Guitar-to-Doom Controller Pro
echo   DOOM II: Hell on Earth
echo ================================================
echo.
echo Запуск GZDoom + Guitar Controller...
echo.

:: Check if Python and script exist
if not exist "guitar_to_doom.py" (
    echo [ERROR] guitar_to_doom.py не найден!
    pause
    exit /b 1
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден! Запустите Install_Dependencies.bat
    pause
    exit /b 1
)

:: Launch GZDoom in background
start "" gzdoom.exe -config "%~dp0gzdoom.ini" -savedir "%~dp0save" -iwad "%~dp0iwads\doom2.wad" -file "%~dp0lights.pk3" "%~dp0brightmaps.pk3" "%~dp0game_support.pk3" "%~dp0game_widescreen_gfx.pk3" "%~dp0mods\audio\IDKFAv2.wad" "%~dp0mods\graphics\NeuralUpscale2x_v1.0.pk3"

:: Wait for GZDoom to start
timeout /t 2 /nobreak >nul

echo [OK] GZDoom запущен
echo [OK] Запуск Guitar Controller...
echo.
echo Управление:
echo E=W  A=S  D=A  G=D  B=Left  e=Right  SlabUdar=Space  SilnUdar=CTRL  ESC=Stop
echo.
echo ================================================

:: Run guitar controller
python guitar_to_doom.py

echo.
echo ================================================
echo   Guitar Controller остановлен
echo ================================================
pause
