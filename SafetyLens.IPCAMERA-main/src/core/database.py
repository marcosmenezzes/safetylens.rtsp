import sqlite3
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class DatabaseManager:
    def __init__(self, database_path):
        self.database_path = database_path
        self.ensure_database()
        self.executor = ThreadPoolExecutor(max_workers=1)
        # Mapeamento correto das classes
        self.epi_mapping = {
            4: 'Sem_Oculos',    # Classes que indicam ausência
            5: 'Sem_Capacete',
            6: 'Sem_Luva',
            7: 'Sem_Abafador',
            0: 'Com_Oculos',    # Classes que indicam presença
            1: 'Com_Capacete',
            2: 'Com_Luva',
            3: 'Com_Abafador'
        }

    def ensure_database(self):
        if not os.path.exists(os.path.dirname(self.database_path)):
            os.makedirs(os.path.dirname(self.database_path))
            
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # Tabela EPIs
        cursor.execute("""CREATE TABLE IF NOT EXISTS epis (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL
        )""")

        # Tabela Detecções
        cursor.execute("""CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            frame_data BLOB,
            epi_id INTEGER,
            FOREIGN KEY (epi_id) REFERENCES epis (id)
        )""")

        # Tabela Configurações
        cursor.execute("""CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_resolution_w INTEGER,
            camera_resolution_h INTEGER,
            brightness_value INTEGER,
            contrast_value INTEGER,
            sharpness_value INTEGER,
            grayscale_value INTEGER,
            min_confidence_value REAL,
            alert_frequency_value INTEGER,
            alert_duration_value INTEGER,
            delay_time_value INTEGER,
            selected_epi_classes TEXT
        )""")
        
        conn.commit()
        conn.close()

        # Inserir EPIs padrão se não existirem
        epis = [
            (0, "Capacete"),
            (1, "Óculos"),
            (2, "Protetor Auricular"),
            (3, "Máscara"),
            (4, "Sem Capacete"),
            (5, "Sem Óculos"),
            (6, "Sem Protetor Auricular"),
            (7, "Sem Máscara")
        ]

        for epi in epis:
            try:
                self.execute_with_retry(
                    "INSERT OR IGNORE INTO epis (id, nome) VALUES (?, ?)",
                    epi
                )
            except sqlite3.IntegrityError:
                pass  # Ignora se já existir

    def get_connection(self):
        """
        Cria uma conexão com o banco de dados com timeout e configurações de segurança.
        """
        conn = sqlite3.connect(self.database_path, timeout=20, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 5000")  # 5 segundos de timeout
        return conn

    def execute_with_retry(self, query, params=None):
        """
        Executa uma query com retry em caso de falha.
        """
        max_retries = 3
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    return cursor
            except sqlite3.OperationalError as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)  # Espera 1 segundo antes de tentar novamente

        raise last_error

    def log_detection(self, timestamp, missing_epis, found_classes, frame_data):
        """Registra uma detecção no banco de dados em uma thread separada"""
        self.executor.submit(self._log_detection_task, timestamp, missing_epis, found_classes, frame_data)

    def _log_detection_task(self, timestamp, missing_epis, found_classes, frame_data):
        try:
            for class_id in found_classes:
                if class_id in [4, 5, 6, 7]:  # IDs das classes de EPIs ausentes
                    epi_name = self.epi_mapping[class_id]
                    
                    # Verifica se o EPI já existe na tabela
                    cursor = self.execute_with_retry("SELECT id FROM epis WHERE nome = ?", (epi_name,))
                    epi_result = cursor.fetchone()
                    
                    if epi_result:
                        epi_id = epi_result[0]
                    else:
                        cursor = self.execute_with_retry("INSERT INTO epis (nome) VALUES (?)", (epi_name,))
                        epi_id = cursor.lastrowid

                    # Registra a detecção
                    self.execute_with_retry(
                        "INSERT INTO detections (timestamp, frame_data, epi_id) VALUES (?, ?, ?)",
                        (timestamp, frame_data, epi_id)
                    )

            print(f"Detecção registrada com sucesso: {timestamp}, EPIs ausentes: {missing_epis}")

        except sqlite3.Error as e:
            print(f"Erro ao registrar detecção: {e}")

    def save_settings(self, **settings):
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM settings")
                cursor.execute(
                    """INSERT INTO settings (
                        camera_resolution_w, camera_resolution_h,
                        brightness_value, contrast_value,
                        sharpness_value, grayscale_value,
                        min_confidence_value, alert_frequency_value,
                        alert_duration_value, delay_time_value,
                        selected_epi_classes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        settings.get('camera_resolution_w'),
                        settings.get('camera_resolution_h'),
                        settings.get('brightness_value'),
                        settings.get('contrast_value'),
                        settings.get('sharpness_value'),
                        settings.get('grayscale_value'),
                        settings.get('min_confidence_value'),
                        settings.get('alert_frequency_value'),
                        settings.get('alert_duration_value'),
                        settings.get('delay_time_value'),
                        settings.get('selected_epi_classes')
                    )
                )
        except sqlite3.Error as e:
            print(f"Erro ao salvar configurações: {e}")

    def load_settings(self):
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM settings")
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Erro ao carregar configurações: {e}")
            return None

    def __del__(self):
        """Garante que o executor seja fechado corretamente"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
