import tempfile
import unittest
from pathlib import Path

import yaml

from src.core.config import Config


class CameraConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / 'config.yaml'
        self.path.write_text(yaml.safe_dump({
            'camera': {'id': 0, 'url': None, 'registered': [], 'resolution': {'width': 1080, 'height': 1920}},
        }))
        self.config = Config(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_accepts_only_local_ipv4_and_persists_camera(self):
        self.assertEqual(self.config.camera_resolution, (1920, 1080))
        name, ip, candidates = self.config.camera_candidates('Entrada', '192.168.1.20', 8554)
        self.assertEqual((name, ip), ('Entrada', '192.168.1.20'))
        self.assertTrue(any(source.startswith('rtsp://192.168.1.20:8554') for source in candidates))

        self.config.register_camera(name, ip, candidates[0], 8554)
        reloaded = Config(self.path)
        self.assertEqual(reloaded.registered_cameras[0]['name'], 'Entrada')
        self.assertEqual(reloaded.registered_cameras[0]['port'], 8554)
        self.assertEqual(reloaded.camera_source, candidates[0])

        reloaded.activate_native_camera()
        self.assertEqual(Config(self.path).camera_source, 0)

        reloaded.activate_camera('192.168.1.20')
        self.assertEqual(Config(self.path).camera_source, candidates[0])
        removed, was_active = reloaded.remove_camera('192.168.1.20')
        self.assertEqual(removed['name'], 'Entrada')
        self.assertTrue(was_active)
        self.assertEqual(Config(self.path).registered_cameras, [])
        self.assertEqual(Config(self.path).camera_source, 0)

        with self.assertRaisesRegex(ValueError, 'privado'):
            self.config.camera_candidates('Externa', '8.8.8.8')
        with self.assertRaisesRegex(ValueError, 'válido'):
            self.config.camera_candidates('Inválida', 'camera.local')
        for blocked in ('127.0.0.1', '169.254.1.1', '224.0.0.1'):
            with self.assertRaisesRegex(ValueError, 'privado'):
                self.config.camera_candidates('Bloqueada', blocked)
        for port in (0, 65536, 'abc'):
            with self.assertRaisesRegex(ValueError, 'porta'):
                self.config.camera_candidates('Entrada', '192.168.1.20', port)

    def test_droidcam_uses_http_video_before_rtsp(self):
        _, _, candidates = self.config.camera_candidates('Celular', '192.168.15.6', 4747)
        self.assertEqual(candidates[0], 'http://192.168.15.6:4747/video')
        self.assertEqual(candidates[1], 'http://192.168.15.6:4747/video/force/1280x720')


if __name__ == '__main__':
    unittest.main()
