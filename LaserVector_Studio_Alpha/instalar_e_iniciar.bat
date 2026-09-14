@echo off
setlocal
title LaserVector Studio Alpha
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    ) else (
        echo Python nao foi encontrado.
        echo Instale o Python 3.11 ou 3.12, 64 bits.
        echo Marque a opcao Add Python to PATH.
        pause
        exit /b 1
    )
)

echo Versao do Python:
%PYTHON_CMD% --version
echo.

echo Atualizando instalador...
%PYTHON_CMD% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :erro

echo.
echo Instalando as dependencias...
%PYTHON_CMD% -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :erro

echo.
echo Verificando...
%PYTHON_CMD% -c "import PySide6, cv2, numpy; print('Dependencias OK')"
if errorlevel 1 goto :erro

echo.
echo Abrindo LaserVector Studio...
%PYTHON_CMD% main.py
if errorlevel 1 pause
exit /b 0

:erro
echo.
echo Nao foi possivel concluir a instalacao.
echo Recomendacao: utilize Python 3.11 ou 3.12 de 64 bits.
pause
exit /b 1
