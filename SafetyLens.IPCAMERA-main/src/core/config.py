"""Leitura, validação e persistência da configuração local do SafetyLens."""

import ipaddress
import os
from pathlib import Path

import yaml


class Config:
    """Centraliza caminhos, câmera ativa e ajustes usados pelo detector.

    O YAML permanece simples para que uma instalação local possa ser
    configurada sem banco administrativo. A API nunca devolve a URL completa
    da câmera, pois ela pode conter credenciais.
    """

    def __init__(self, config_path=None):
        """Usa o caminho informado nos testes ou o ``config.yaml`` do projeto."""
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parents[2] / 'config.yaml'
        self.load_config()

    def load_config(self):
        """Carrega o YAML para a memória antes de qualquer acesso às propriedades."""
        with self.config_path.open(encoding='utf-8') as file:
            self.config = yaml.safe_load(file)

    def save_config(self):
        """Salva por troca atômica para não deixar um YAML parcial após falhas."""
        temporary_path = self.config_path.with_suffix(f'{self.config_path.suffix}.tmp')
        temporary_path.write_text(
            yaml.safe_dump(self.config, allow_unicode=True, sort_keys=False),
            encoding='utf-8',
        )
        temporary_path.replace(self.config_path)

    @property
    def model_path(self):
        """Retorna o peso YOLO ativo como caminho absoluto."""
        return str(self.config_path.parent / self.config['paths']['model'])

    @property
    def database_path(self):
        """Retorna o SQLite local como caminho absoluto."""
        return str(self.config_path.parent / self.config['paths']['database'])

    @property
    def camera_id(self):
        """Retorna o índice OpenCV da câmera nativa; zero é a câmera padrão."""
        return self.config['camera'].get('id', 0)

    @property
    def camera_url(self):
        """Prioriza uma URL temporária do ambiente sobre o valor salvo no YAML."""
        return os.getenv('SAFETYLENS_CAMERA_URL') or self.config['camera'].get('url')

    @property
    def camera_source(self):
        """Retorna a URL da câmera de rede ou o índice da câmera nativa."""
        return self.camera_url or self.camera_id

    @property
    def registered_cameras(self):
        """Entrega uma cópia rasa das câmeras cadastradas para evitar mutação acidental."""
        return list(self.config['camera'].get('registered', []))

    def camera_candidates(self, name, ip, port=554):
        """Valida a câmera e monta caminhos comuns de RTSP/HTTP para conexão.

        Apenas IPv4 privados são aceitos. A restrição reduz o risco de SSRF
        caso o painel seja futuramente acessado por outra máquina da rede.
        """
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 64:
            raise ValueError('Informe um nome de até 64 caracteres.')
        name = name.strip()
        if not isinstance(ip, str):
            raise ValueError('Informe um endereço IP válido.')
        try:
            address = ipaddress.ip_address(ip.strip())
        except ValueError as error:
            raise ValueError('Informe um endereço IP válido.') from error
        private_ranges = (
            ipaddress.ip_network('10.0.0.0/8'),
            ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),
        )
        if address.version != 4 or not any(address in network for network in private_ranges):
            raise ValueError('Use somente um IPv4 privado da rede local.')
        if isinstance(port, bool):
            raise ValueError('Informe uma porta entre 1 e 65535.')
        try:
            port = int(port)
        except (TypeError, ValueError) as error:
            raise ValueError('Informe uma porta entre 1 e 65535.') from error
        if not 1 <= port <= 65535:
            raise ValueError('Informe uma porta entre 1 e 65535.')

        saved = next((item.get('source') for item in self.registered_cameras if item.get('ip') == str(address)), None)
        rtsp = [
            f'rtsp://{address}:{port}/stream1',
            f'rtsp://{address}:{port}/Streaming/Channels/101',
            f'rtsp://{address}:{port}/cam/realmonitor?channel=1&subtype=0',
            f'rtsp://{address}:{port}/live',
        ]
        http = [
            f'http://{address}:{port}/video',
            f'http://{address}:{port}/video/force/1280x720',
            f'http://{address}:8080/video',
            f'http://{address}/video',
        ]
        common = http + rtsp if port == 4747 else rtsp + http
        ordered = common + ([saved] if saved else []) if port == 4747 else ([saved] if saved else []) + common
        return name, str(address), list(dict.fromkeys(ordered))

    def register_camera(self, name, ip, source, port=554):
        """Persiste uma câmera validada e a torna a fonte ativa."""
        cameras = self.config['camera'].setdefault('registered', [])
        camera = {'name': name, 'ip': ip, 'port': int(port), 'source': source}
        cameras[:] = [item for item in cameras if item.get('ip') != ip]
        cameras.append(camera)
        self.config['camera'].update(url=source, active_name=name)
        self.save_config()
        return camera

    def activate_camera(self, ip):
        """Seleciona uma câmera já cadastrada sem criar uma duplicata."""
        camera = next((item for item in self.registered_cameras if item.get('ip') == ip), None)
        if camera is None:
            raise ValueError('Câmera não encontrada.')
        self.config['camera'].update(url=camera['source'], active_name=camera['name'])
        self.save_config()
        return camera

    def remove_camera(self, ip):
        """Exclui uma câmera e volta à nativa quando ela era a fonte ativa."""
        cameras = self.config['camera'].setdefault('registered', [])
        camera = next((item for item in cameras if item.get('ip') == ip), None)
        if camera is None:
            raise ValueError('Câmera não encontrada.')
        was_active = self.config['camera'].get('url') == camera.get('source')
        cameras.remove(camera)
        if was_active:
            self.config['camera'].update(url=None, active_name='Câmera nativa')
        self.save_config()
        return camera, was_active

    def activate_native_camera(self):
        """Seleciona a webcam local e mantém as câmeras de rede salvas."""
        self.config['camera'].update(url=None, active_name='Câmera nativa')
        self.save_config()

    @property
    def camera_resolution(self):
        """Normaliza orientação da webcam nativa para evitar imagem ampliada/cortada."""
        width = self.config['camera']['resolution']['width']
        height = self.config['camera']['resolution']['height']
        return (height, width) if not self.camera_url and height > width else (width, height)

    @property
    def min_confidence(self):
        """Retorna a confiança mínima aceita pelo detector."""
        return self.config['detection']['min_confidence']

    @property
    def delay_time(self):
        """Retorna o intervalo mínimo entre evidências salvas."""
        return self.config['alerts']['delay_time']

    def update_camera_settings(self, **settings):
        """Distribui ajustes da API nas seções corretas do YAML e salva uma vez."""
        for key, value in settings.items():
            if key == 'delay_time':
                self.config['alerts'][key.replace('alert_', '')] = value
            elif key == 'min_confidence':
                self.config['detection']['min_confidence'] = value
            elif key in {'url', 'id'}:
                self.config['camera'][key] = value
            else:
                self.config['camera']['default_settings'][key] = value
        self.save_config()
