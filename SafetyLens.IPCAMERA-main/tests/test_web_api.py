import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

from src.core.config import Config
from src.core.database import initialize_database
from src.web import create_app


class WebApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / 'test.db'
        initialize_database(str(self.database))
        connection = sqlite3.connect(self.database)
        try:
            connection.executescript('''
                INSERT INTO detections VALUES
                    (1, '2026-08-01 10:00:00', X'FFD8FFD9', 5),
                    (2, '2026-08-02 11:00:00', NULL, 6),
                    (3, '2026-08-03 12:00:00', NULL, 5);
            ''')
            connection.commit()
        finally:
            connection.close()
        app = create_app(SimpleNamespace(database_path=str(self.database)))
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detection_contract_and_pagination(self):
        response = self.client.get('/api/detections?start=2026-08-01T00:00&end=2026-08-04T00:00&page=1&limit=2')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual((body['total'], body['totalPages'], len(body['items'])), (3, 2, 2))
        self.assertNotIn('frame_data', body['items'][0])
        self.assertEqual(body['items'][0]['id'], 3)

    def test_invalid_filters_are_rejected(self):
        self.assertEqual(self.client.get('/api/detections?page=0').status_code, 400)
        self.assertEqual(self.client.get('/api/analytics?start=invalid').status_code, 400)
        self.assertEqual(self.client.get('/api/analytics?start=2026-08-03&end=2026-08-01').status_code, 400)

    def test_dashboard_and_analytics_aggregate_same_period(self):
        period = 'start=2026-08-01T00:00&end=2026-08-04T00:00'
        dashboard = self.client.get(f'/api/dashboard?{period}').get_json()
        analytics = self.client.get(f'/api/analytics?{period}').get_json()
        self.assertEqual(dashboard['summary']['totalDetections'], 3)
        self.assertEqual(analytics['summary']['periodTotal'], 3)
        self.assertEqual(analytics['summary']['periodShare'], 100)
        self.assertEqual(analytics['byEpi'][0]['name'], 'Sem_Capacete')

    def test_image_is_binary_and_private(self):
        response = self.client.get('/image/1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/jpeg')
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertEqual(self.client.get('/image/999').status_code, 404)


class CameraWebApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.config_path = root / 'config.yaml'
        self.config_path.write_text(yaml.safe_dump({
            'alerts': {'delay_time': 30, 'duration': 300, 'frequency': 1000},
            'camera': {
                'active_name': 'Câmera nativa', 'default_settings': {
                    'brightness': 100, 'contrast': 100, 'grayscale': False, 'sharpness': 2,
                },
                'id': 0, 'registered': [], 'resolution': {'height': 720, 'width': 1280}, 'url': None,
            },
            'detection': {'min_confidence': .5, 'classes': {'epi_ausentes': [], 'epi_presentes': []}},
            'paths': {'database': 'test.db', 'model': 'best.pt'},
        }))
        app = create_app(Config(self.config_path))
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_camera_registration_rejects_ssrf_and_hides_source(self):
        blocked = self.client.post('/api/cameras', json={'name': 'Localhost', 'ip': '127.0.0.1'})
        self.assertEqual(blocked.status_code, 400)

        created = self.client.post('/api/cameras', json={'name': 'Entrada', 'ip': '192.168.1.20', 'port': 8554})
        self.assertEqual(created.status_code, 201)
        body = self.client.get('/api/cameras').get_json()
        self.assertEqual(body['items'][0]['ip'], '192.168.1.20')
        self.assertEqual(body['items'][0]['port'], 8554)
        self.assertNotIn('source', body['items'][0])
        self.assertEqual(self.client.post('/api/cameras', json={'name': 'Outra', 'ip': '192.168.1.20'}).status_code, 409)
        self.assertEqual(self.client.post('/api/cameras', json={'name': 'Porta', 'ip': '192.168.1.21', 'port': 70000}).status_code, 400)
        deleted = self.client.delete('/api/cameras/192.168.1.20').get_json()
        self.assertEqual(deleted['deleted']['name'], 'Entrada')
        self.assertEqual(self.client.get('/api/cameras').get_json()['items'], [])

    def test_camera_settings_validate_ranges_and_persist(self):
        self.assertEqual(self.client.patch('/api/camera/settings', json={'brightness': 999}).status_code, 400)
        response = self.client.patch('/api/camera/settings', json={'brightness': 115, 'minConfidence': .62})
        self.assertEqual(response.status_code, 200)
        reloaded = Config(self.config_path)
        self.assertEqual(reloaded.config['camera']['default_settings']['brightness'], 115)
        self.assertEqual(reloaded.min_confidence, .62)


if __name__ == '__main__':
    unittest.main()
