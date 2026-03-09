@echo off
chcp 65001 >nul
title Guitar-to-Doom: Controller Only Mode
cd /d "%~dp0"

echo ================================================
echo   Guitar-to-Doom Controller Pro
echo   Только модуль (без запуска игры)
echo ================================================
echo.
echo Запуск только Guitar Controller...
echo GZDoom должен быть уже запущен вручную!
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

echo Управление:
echo   E струна - Вперед (W)
echo   A струна - Назад (S)
echo   D струна - Влево (A)
echo   G струна - Вправо (D)
echo   Резкий удар - Выстрел (CTRL)
echo   ESC - Panic Button (остановка)
echo.
echo ================================================

python guitar_to_doom.py

echo.
echo ================================================
echo   Guitar Controller остановлен
echo ================================================
pause
