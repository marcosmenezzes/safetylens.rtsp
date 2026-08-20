"""Runtime contínuo de captura, inferência e streaming MJPEG."""

import threading
import time
from datetime import datetime


class CameraRuntime:
    """Mantém captura e inferência fora das requisições do Flask."""

    def __init__(self, config):
        """Cria o estado compartilhado; a câmera só abre quando o stream é pedido."""
        self.config = config
        self._condition = threading.Condition()
        self._stop = threading.Event()
        self._thread = None
        self._frame = None
        self._sequence = 0
        self._detector = None
        self._status = {
            'state': 'idle',
            'message': 'Aguardando visualização',
            'fps': 0,
            'resolution': None,
            'missingEpis': [],
            'updatedAt': None,
        }

    def status(self):
        """Retorna uma fotografia segura do estado atual para a API."""
        with self._condition:
            return dict(self._status)

    def ensure_started(self):
        """Inicia uma única thread de captura quando ainda não existe uma ativa."""
        with self._condition:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._status.update(state='connecting', message='Conectando à câmera')
            self._thread = threading.Thread(target=self._run, name='camera-runtime', daemon=True)
            self._thread.start()

    def restart(self):
        """Reabre a fonte se ela estava em uso, preservando o estado ocioso."""
        was_running = bool(self._thread and self._thread.is_alive())
        self.stop()
        if was_running:
            self.ensure_started()
        else:
            with self._condition:
                self._status.update(state='idle', message='Aguardando visualização')

    def stop(self):
        """Sinaliza parada e aguarda brevemente a liberação do dispositivo."""
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=4)
        self._thread = None

    def update_confidence(self, value):
        """Atualiza o detector ativo sem reiniciar o vídeo."""
        with self._condition:
            if self._detector:
                self._detector.update_min_confidence(value)

    def frames(self):
        """Produz partes MJPEG à medida que novos frames ficam disponíveis."""
        self.ensure_started()
        last_sequence = -1
        while not self._stop.is_set():
            with self._condition:
                self._condition.wait_for(
                    lambda: self._sequence != last_sequence or self._stop.is_set(),
                    timeout=2,
                )
                if self._stop.is_set():
                    return
                frame = self._frame
                last_sequence = self._sequence
            if frame:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'

    def _run(self):
        """Conecta, processa frames, salva alertas e publica o stream."""
        import cv2

        from src.core.database import DatabaseManager
        from src.core.detection import EPIDetector, ImageProcessor

        capture = None
        database = None
        try:
            camera = self.config.config['camera']
            active_name = camera.get('active_name', 'Câmera nativa')
            registered = next((item for item in self.config.registered_cameras if item.get('name') == active_name), None)
            sources = [self.config.camera_source]
            if registered:
                _, _, sources = self.config.camera_candidates(
                    registered['name'], registered['ip'], registered.get('port', 554),
                )

            first_frame = None
            selected_source = None
            for source in dict.fromkeys(sources):
                if isinstance(source, int):
                    candidate = cv2.VideoCapture(source)
                else:
                    try:
                        candidate = cv2.VideoCapture(source, cv2.CAP_FFMPEG, [
                            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2500,
                            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2500,
                        ])
                    except (TypeError, cv2.error):
                        candidate = cv2.VideoCapture(source)
                if candidate.isOpened():
                    ok, frame = candidate.read()
                    if ok and frame is not None:
                        capture, first_frame, selected_source = candidate, frame, source
                        break
                candidate.release()

            if capture is None:
                raise RuntimeError('Não foi possível abrir a câmera configurada')

            if registered and selected_source != registered.get('source'):
                self.config.register_camera(
                    registered['name'], registered['ip'], selected_source, registered.get('port', 554),
                )

            width, height = self.config.camera_resolution
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self._detector = EPIDetector(self.config.model_path, self.config.min_confidence)
            database = DatabaseManager(self.config.database_path)
            last_alert = 0
            frames = 0
            fps_started = time.monotonic()

            while not self._stop.is_set():
                if first_frame is not None:
                    ok, frame, first_frame = True, first_frame, None
                else:
                    ok, frame = capture.read()
                if not ok or frame is None:
                    raise RuntimeError('A câmera parou de enviar imagens')

                settings = self.config.config['camera']['default_settings']
                processed = ImageProcessor.adjust_image(
                    frame,
                    settings['brightness'],
                    settings['contrast'],
                    settings['sharpness'],
                    settings['grayscale'],
                )
                annotated, missing, found = self._detector.detect(processed)
                now = time.time()
                if missing and now - last_alert >= self.config.delay_time:
                    last_alert = now
                    encoded_ok, evidence = cv2.imencode('.jpg', annotated)
                    if encoded_ok:
                        database.log_detection(
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            found,
                            evidence.tobytes(),
                        )

                encoded_ok, encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if not encoded_ok:
                    continue
                frames += 1
                elapsed = time.monotonic() - fps_started
                fps = round(frames / elapsed, 1) if elapsed >= 1 else self._status['fps']
                if elapsed >= 1:
                    frames = 0
                    fps_started = time.monotonic()
                h, w = annotated.shape[:2]
                with self._condition:
                    self._frame = encoded.tobytes()
                    self._sequence += 1
                    self._status = {
                        'state': 'online',
                        'message': 'Monitoramento ativo',
                        'fps': fps,
                        'resolution': f'{w}x{h}',
                        'missingEpis': list(dict.fromkeys(missing)),
                        'updatedAt': datetime.now().isoformat(timespec='seconds'),
                    }
                    self._condition.notify_all()
        except Exception as error:
            with self._condition:
                self._status.update(
                    state='offline',
                    message=str(error),
                    fps=0,
                    updatedAt=datetime.now().isoformat(timespec='seconds'),
                )
                self._condition.notify_all()
        finally:
            if capture is not None:
                capture.release()
            if database is not None:
                database.close()
            self._detector = None
