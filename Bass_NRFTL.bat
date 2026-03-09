@echo off
chcp 65001 >nul
title Bass-to-Doom: No Rest for the Living
cd /d "%~dp0"

echo ================================================
echo   Bass-to-Doom Controller Pro
echo   No Rest for the Living ^(NRFTL^)
echo ================================================
echo.
echo Запуск GZDoom + Bass Controller...
echo.

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

start "" gzdoom.exe -config "%~dp0gzdoom.ini" -savedir "%~dp0save" -iwad "%~dp0iwads\doom2.wad" -file "%~dp0lights.pk3" "%~dp0brightmaps.pk3" "%~dp0game_support.pk3" "%~dp0game_widescreen_gfx.pk3" "%~dp0official\nerve.wad" "%~dp0mods\audio\IDKFAv2.wad" "%~dp0mods\graphics\NeuralUpscale2x_v1.0.pk3"
timeout /t 2 /nobreak >nul

echo [OK] GZDoom + NRFTL запущены
echo [OK] Запуск Bass Controller...
echo.
echo Управление ^(бас^): E=W, A=S, D=A, G=D, Удар=CTRL, ESC=Panic
echo ================================================

python guitar_to_doom.py --bass

echo.
echo ================================================
echo   Bass Controller остановлен
echo ================================================
pause
