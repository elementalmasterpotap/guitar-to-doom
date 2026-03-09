@echo off
chcp 65001 >nul
title Bass-to-Doom: Controller Only Mode
cd /d "%~dp0"

echo ================================================
echo   Bass-to-Doom Controller Pro
echo   Только модуль ^(без запуска игры^)
echo ================================================
echo.
echo Запуск только Bass Controller...
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

echo Управление ^(бас^):
echo   E струна ^(E1^) - Вперед ^(W^)
echo   A струна ^(A1^) - Назад ^(S^)
echo   D струна ^(D2^) - Влево ^(A^)
echo   G струна ^(G2^) - Вправо ^(D^)
echo   Резкий удар    - Выстрел ^(CTRL^)
echo   ESC            - Panic Button ^(остановка^)
echo.
echo ================================================

python guitar_to_doom.py --bass

echo.
echo ================================================
echo   Bass Controller остановлен
echo ================================================
pause
