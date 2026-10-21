@echo off
setlocal
title AI Engineering Harness Installer

cd /d "%~dp0"
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo abrir la carpeta del Harness.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0install\setup.ps1" (
    echo.
    echo ERROR: Falta install\setup.ps1. Extrae o descarga nuevamente el paquete completo.
    echo.
    pause
    exit /b 1
)

echo Instalando AI Engineering Harness...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\setup.ps1" %*
set "HARNESS_EXIT_CODE=%ERRORLEVEL%"

echo.
if "%HARNESS_EXIT_CODE%"=="0" (
    echo INSTALACION COMPLETADA: STATUS READY
) else (
    echo NO SE COMPLETO LA INSTALACION. Codigo: %HARNESS_EXIT_CODE%
)
echo.
pause
exit /b %HARNESS_EXIT_CODE%
