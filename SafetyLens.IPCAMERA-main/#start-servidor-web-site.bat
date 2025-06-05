@echo off
title SafetyLens - Servidor Web

:: Verifica se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado! Por favor, instale o Python 3.8 ou superior.
    pause
    exit /b 1
)

:: Verifica se o arquivo requirements.txt existe
if not exist requirements.txt (
    echo requirements.txt nao encontrado!
    pause
    exit /b 1
)

:: Criar ambiente virtual se não existir
if not exist venv\ (
    echo Criando ambiente virtual...
    python -m venv venv
)

:: Ativar ambiente virtual
call venv\Scripts\activate.bat

:: Instalar ou atualizar dependências
echo Verificando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Verifica se as pastas necessárias existem
if not exist templates\ (
    echo Pasta templates nao encontrada!
    pause
    exit /b 1
)

if not exist static\ (
    echo Pasta static nao encontrada!
    pause
    exit /b 1
)

:: Verifica se o banco de dados existe
if not exist database\epi_detections.db (
    echo Arquivo do banco de dados nao encontrado!
    pause
    exit /b 1
)

:: Inicia o servidor web
echo Iniciando o servidor web do SafetyLens...
python #servidor-web-site.py

:: Se o servidor fechar com erro, mostra a mensagem
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao executar o servidor web.
    echo Por favor, verifique se todas as dependencias estao instaladas corretamente.
    pause
)

:: Desativa o ambiente virtual
deactivate

pause