@echo off
setlocal
title LaserVector Studio Alpha
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -c "import PySide6, cv2, numpy" >nul 2>&1
if errorlevel 1 (
    echo Dependencias ausentes.
    echo Execute primeiro instalar_e_iniciar.bat
    pause
    exit /b 1
)

%PYTHON_CMD% main.py
if errorlevel 1 pause
