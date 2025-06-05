import tkinter as tk
from tkinter import ttk
import cv2
from datetime import datetime
import threading
import time
import winsound
from concurrent.futures import ThreadPoolExecutor
import sv_ttk

from src.ui.camera_frame import CameraFrame
from src.ui.settings_frame import SettingsFrame
from src.core.detection import EPIDetector, ImageProcessor
from src.core.config import Config
from src.core.database import DatabaseManager


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SafetyLens - Sistema de Detecção de EPIs")
        self.root.geometry("1600x900")  # Tamanho inicial maior
        self.root.minsize(1280, 720)    # Tamanho mínimo adequado

        sv_ttk.set_theme("dark")
        self.setup_styles()

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.setup_config()
        self.setup_detector()
        self.setup_database()
        self.setup_components()  # Criar componentes (incluindo status_label) antes da câmera
        self.setup_camera()

        self.is_running = True
        self.alert_thread = None
        self.last_alert_time = 0
        self.executor = ThreadPoolExecutor(max_workers=4)

    def setup_styles(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 28, "bold"), padding=10)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 14), padding=5)
        style.configure("Status.TLabel", font=("Segoe UI", 11), padding=5)
        style.configure("Main.TFrame", padding=5)
        style.configure("Custom.TLabelframe", padding=8)
        style.configure("Custom.TLabelframe.Label", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TNotebook.Tab", font=("Segoe UI", 10))

    def setup_components(self):
        main_container = ttk.Frame(self.root)
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        self.setup_header(main_container)

        content_container = ttk.Frame(main_container, style="Main.TFrame")
        content_container.grid(row=1, column=0, sticky="nsew")
        content_container.grid_columnconfigure(0, weight=4)
        content_container.grid_columnconfigure(1, weight=1)
        content_container.grid_rowconfigure(0, weight=1)

        self.camera_frame = CameraFrame(content_container)
        self.camera_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.settings_frame = SettingsFrame(content_container, self.config, self.on_settings_change)
        self.settings_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.setup_status_bar(main_container)

    def setup_header(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        title_container = ttk.Frame(header_frame)
        title_container.grid(row=0, column=0, sticky="ew")

        title = ttk.Label(title_container, text="SafetyLens", style="Title.TLabel")
        title.pack(side="left", padx=10)

        subtitle = ttk.Label(header_frame,
                             text="Sistema Profissional de Monitoramento de EPIs",
                             style="Subtitle.TLabel")
        subtitle.grid(row=1, column=0, sticky="ew")

    def setup_status_bar(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        status_frame.grid_columnconfigure(1, weight=1)

        self.status_label = ttk.Label(status_frame, text="Sistema Iniciado", style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")

        version_label = ttk.Label(status_frame, text="v1.0.0", style="Status.TLabel")
        version_label.grid(row=0, column=2, sticky="e")

    def setup_config(self):
        self.config = Config()

    def setup_camera(self):
        self.cap = cv2.VideoCapture(self.config.camera_url)

        if not self.cap.isOpened():
            self.update_status("❌ Erro: Não foi possível conectar à câmera.")
            print(f"❌ Erro ao conectar na câmera RTSP: {self.config.camera_url}")
            return

        w, h = self.config.camera_resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

        self.update_status("✅ Câmera conectada com sucesso.")
        print(f"✅ Câmera conectada: {self.config.camera_url}")

    def setup_detector(self):
        self.detector = EPIDetector(self.config.model_path, self.config.min_confidence)
        self.processor = ImageProcessor()

    def setup_database(self):
        self.db = DatabaseManager(self.config.database_path)

    def update_status(self, message):
        self.status_label.config(text=message)

    def play_alert(self):
        # Alerta sonoro
        winsound.Beep(self.config.alert_frequency, self.config.alert_duration)

    def show_alert(self, missing_epis, frame, found_classes):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _, frame_encoded = cv2.imencode('.jpg', frame)
        frame_data = frame_encoded.tobytes()

        self.db.log_detection(timestamp, missing_epis, found_classes, frame_data)

        threading.Thread(target=self.play_alert, daemon=True).start()

        epi_list = ", ".join(missing_epis)
        self.update_status(f"⚠️ EPIs ausentes: {epi_list}")
        self.root.after(2000, lambda: self.update_status("Sistema Monitorando..."))

    def on_settings_change(self, **settings):
        if 'min_confidence' in settings:
            self.detector.update_min_confidence(settings['min_confidence'])
        self.config.update_camera_settings(**settings)

    def process_frame(self):
        if not self.cap.isOpened():
            self.update_status("❌ Sem conexão com a câmera.")
            self.root.after(1000, self.process_frame)
            return

        ret, frame = self.cap.read()
        if ret:
            settings = self.settings_frame.get_settings()
            processed_frame = self.processor.adjust_image(
                frame,
                settings['brightness'],
                settings['contrast'],
                settings['sharpness'],
                settings['grayscale']
            )

            frame_with_detections, missing_epis, found_classes = self.detector.detect(processed_frame)

            self.camera_frame.update_frame(frame_with_detections)

            if missing_epis and time.time() - self.last_alert_time > self.config.delay_time:
                self.last_alert_time = time.time()
                if self.alert_thread is None or not self.alert_thread.is_alive():
                    self.alert_thread = threading.Thread(
                        target=self.show_alert,
                        args=(missing_epis, frame_with_detections, found_classes)
                    )
                    self.alert_thread.start()

        else:
            self.update_status("⚠️ Frame não capturado. Verifique a câmera.")

        if self.is_running:
            self.root.after(10, self.process_frame)

    def run(self):
        self.process_frame()
        self.root.mainloop()

    def cleanup(self):
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        self.executor.shutdown(wait=True)


if __name__ == "__main__":
    app = MainWindow()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.cleanup()
