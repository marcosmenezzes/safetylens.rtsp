@echo off
title SafetyLens - Sistema de Monitoramento de EPIs

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

:: Verifica se o modelo existe
if not exist model\best.pt (
    echo Arquivo model\best.pt nao encontrado!
    echo Por favor, certifique-se de que o arquivo do modelo esta presente na pasta 'model'.
    pause
    exit /b 1
)

:: Verifica se o arquivo de configuração existe
if not exist config.yaml (
    echo Arquivo config.yaml nao encontrado!
    pause
    exit /b 1
)

:: Configura o PYTHONPATH para incluir o diretório raiz do projeto
set "PYTHONPATH=%CD%;%PYTHONPATH%"

:: Inicia o aplicativo
echo Iniciando o SafetyLens...
python src/main.py

:: Se o aplicativo fechar com erro, mostra a mensagem
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao executar o aplicativo.
    echo Por favor, verifique se todas as dependencias estao instaladas corretamente.
    pause
)

:: Desativa o ambiente virtual
deactivate

pause
