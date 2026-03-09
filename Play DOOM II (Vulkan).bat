@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "ARGS=-config ""%~dp0gzdoom.ini"" -savedir ""%~dp0save"" -iwad ""%~dp0iwads\doom2.wad"""
set "ARGS=%ARGS% -file "%~dp0lights.pk3" "%~dp0brightmaps.pk3" "%~dp0game_support.pk3" "%~dp0game_widescreen_gfx.pk3""
call :append_files "%~dp0mods" "IDKFAv2.wad"
call :append_files "%~dp0skins"

start "" "%~dp0gzdoom.exe" !ARGS!
exit /b

:append_files
set "DIR=%~1"
set "SKIP=%~2"
for /f "delims=" %%F in ('dir /b /s /a-d "%DIR%\*.wad" "%DIR%\*.pk3" "%DIR%\*.ipk3" "%DIR%\*.zip" "%DIR%\*.deh" "%DIR%\*.bex" 2^>nul') do (
    if /I not "%%~nxF"=="%SKIP%" set "ARGS=!ARGS! -file ""%%~fF"""
)
exit /b
