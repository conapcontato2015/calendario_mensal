@echo off
setlocal
chcp 65001 >nul
title Calendario de Tarefas
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

rem ---------------------------------------------------------------- Python
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo [!] Python nao encontrado.
    echo     Instale o Python 3.10 ou mais novo em https://www.python.org/downloads/
    echo     e marque a opcao "Add python.exe to PATH" na instalacao.
    echo.
    pause
    exit /b 1
)

rem ---------------------------------------------------------------- ambiente virtual
if not exist ".venv\Scripts\python.exe" (
    echo Preparando o ambiente pela primeira vez. Isso leva cerca de 1 minuto...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [!] Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

rem reinstala dependencias so quando requirements.txt mudar
set "MARCA=.venv\requirements.instalado"
fc /b requirements.txt "%MARCA%" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
    if errorlevel 1 (
        echo [!] Falha ao instalar dependencias. Confira a conexao com a internet e tente de novo.
        pause
        exit /b 1
    )
    copy /y requirements.txt "%MARCA%" >nul
)

rem ---------------------------------------------------------------- iniciar
".venv\Scripts\python.exe" run.py
if errorlevel 1 (
    echo.
    pause
)
endlocal
