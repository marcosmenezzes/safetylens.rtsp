"""Criação e inicialização do servidor web do SafetyLens."""

import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from src.core.config import Config
from src.core.database import initialize_database
from src.web.api import create_api
from src.web.camera_runtime import CameraRuntime


def create_app(config=None):
    """Monta a aplicação Flask, sua API e os arquivos compilados do React.

    A fábrica existe para permitir que os testes criem instâncias isoladas sem
    iniciar um servidor real ou depender do banco de produção.
    """
    config = config or Config()
    project_root = Path(__file__).resolve().parents[2]
    frontend = project_root / 'frontend' / 'dist'
    initialize_database(config.database_path)
    camera_runtime = CameraRuntime(config) if hasattr(config, 'camera_source') else None
    app = Flask(__name__, static_folder=None)
    app.config['MAX_CONTENT_LENGTH'] = 4096
    app.register_blueprint(create_api(config.database_path, config, camera_runtime))

    @app.after_request
    def secure_headers(response):
        """Aplica cabeçalhos seguros a todas as respostas da aplicação."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.get('/assets/<path:filename>')
    def frontend_assets(filename):
        """Entrega JavaScript e CSS gerados pelo Vite."""
        return send_from_directory(frontend / 'assets', filename)

    @app.get('/img/<path:filename>')
    def images(filename):
        """Entrega as fotos institucionais usadas pela página Sobre."""
        source = frontend / 'img' if (frontend / 'img').exists() else project_root / 'static' / 'img'
        return send_from_directory(source, filename)

    @app.get('/')
    @app.get('/detections')
    @app.get('/analytics')
    @app.get('/monitoring')
    @app.get('/about')
    def frontend_app():
        """Entrega a SPA React para todas as rotas navegáveis do painel."""
        if not (frontend / 'index.html').exists():
            return jsonify({'error': 'Frontend ainda não compilado. Execute npm run build em frontend/.'}), 503
        return send_from_directory(frontend, 'index.html')

    return app


def main():
    """Inicia o servidor local; é o destino dos comandos ``make start`` e ``make api``."""
    create_app().run(host='127.0.0.1', port=int(os.getenv('SAFETYLENS_WEB_PORT', '5050')))


if __name__ == '__main__':
    main()
