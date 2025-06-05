import yaml

class Config:
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def save_config(self):
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f)

    @property
    def model_path(self):
        return self.config['paths']['model']

    @property
    def database_path(self):
        return self.config['paths']['database']

    @property
    def camera_id(self):
        return self.config['camera'].get('id', 0)  # Valor padrão 0

    @property
    def camera_url(self):
        return self.config['camera'].get('url', None)  # Pode não existir

    @property
    def camera_source(self):
        """Retorna a URL da câmera se existir, senão o ID."""
        return self.camera_url if self.camera_url else self.camera_id

    @property
    def camera_resolution(self):
        return (
            self.config['camera']['resolution']['width'],
            self.config['camera']['resolution']['height']
        )

    @property
    def default_brightness(self):
        return self.config['camera']['default_settings']['brightness']

    @property
    def default_contrast(self):
        return self.config['camera']['default_settings']['contrast']

    @property
    def default_sharpness(self):
        return self.config['camera']['default_settings']['sharpness']

    @property
    def default_grayscale(self):
        return self.config['camera']['default_settings']['grayscale']

    @property
    def min_confidence(self):
        return self.config['detection']['min_confidence']

    @property
    def classes_epi_ausentes(self):
        return self.config['detection']['classes']['epi_ausentes']

    @property
    def classes_epi_presentes(self):
        return self.config['detection']['classes']['epi_presentes']

    @property
    def alert_frequency(self):
        return self.config['alerts']['frequency']

    @property
    def alert_duration(self):
        return self.config['alerts']['duration']

    @property
    def delay_time(self):
        return self.config['alerts']['delay_time']

    def update_camera_settings(self, **kwargs):
        for key, value in kwargs.items():
            # Configurações de alerta vão para a seção 'alerts'
            if key in ['alert_frequency', 'alert_duration', 'delay_time']:
                self.config['alerts'][key.replace('alert_', '')] = value
            elif key == 'url':
                self.config['camera']['url'] = value
            elif key == 'id':
                self.config['camera']['id'] = value
            else:
                # Outras configurações vão para camera.default_settings
                self.config['camera']['default_settings'][key] = value
        self.save_config()
