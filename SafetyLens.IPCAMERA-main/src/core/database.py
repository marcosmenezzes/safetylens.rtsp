"""Persistência SQLite das ocorrências detectadas pelo modelo."""

import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from src.core.epis import EPI_NAMES, MISSING_EPI_IDS


def initialize_database(database_path):
    """Cria banco, tabelas e índices sem alterar dados existentes.

    A operação é idempotente para funcionar tanto na primeira execução quanto
    em bancos que já contêm o histórico do usuário.
    """
    database_dir = os.path.dirname(database_path)
    if database_dir:
        os.makedirs(database_dir, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript("""CREATE TABLE IF NOT EXISTS epis (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                frame_data BLOB,
                epi_id INTEGER,
                FOREIGN KEY (epi_id) REFERENCES epis (id)
            );
            CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp);
            CREATE INDEX IF NOT EXISTS idx_detections_epi_timestamp ON detections(epi_id, timestamp);
        """)
        connection.executemany('INSERT OR IGNORE INTO epis (id, nome) VALUES (?, ?)', EPI_NAMES.items())
        connection.commit()
    finally:
        connection.close()


class DatabaseManager:
    """Grava detecções em série sem interromper o processamento da câmera.

    Um único worker evita disputas de escrita no SQLite. As consultas do painel
    continuam independentes e usam conexões curtas na API.
    """

    def __init__(self, database_path):
        """Prepara o banco e o executor das gravações assíncronas."""
        self.database_path = database_path
        initialize_database(database_path)
        self.executor = ThreadPoolExecutor(max_workers=1)

    def get_connection(self):
        """Abre uma conexão com espera limitada para bloqueios breves."""
        connection = sqlite3.connect(self.database_path, timeout=20, isolation_level=None)
        connection.execute('PRAGMA busy_timeout = 5000')
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def execute_with_retry(self, query, params=(), fetch_one=False):
        """Executa SQL até três vezes quando o SQLite está temporariamente ocupado."""
        last_error = None
        for attempt in range(3):
            connection = None
            try:
                connection = self.get_connection()
                cursor = connection.execute(query, params)
                result = cursor.fetchone() if fetch_one else cursor.lastrowid
                connection.commit()
                return result
            except sqlite3.OperationalError as error:
                last_error = error
                if attempt < 2:
                    time.sleep(1)
            finally:
                if connection:
                    connection.close()
        raise last_error

    def log_detection(self, timestamp, found_classes, frame_data):
        """Agenda a gravação das classes ausentes encontradas em um frame."""
        self.executor.submit(self._log_detection_task, timestamp, found_classes, frame_data)

    def _log_detection_task(self, timestamp, found_classes, frame_data):
        """Deduplica classes e grava uma ocorrência por tipo de EPI ausente."""
        try:
            for class_id in set(found_classes) & MISSING_EPI_IDS:
                epi_name = EPI_NAMES[class_id]
                epi_result = self.execute_with_retry(
                    'SELECT id FROM epis WHERE nome = ?', (epi_name,), fetch_one=True,
                )
                epi_id = epi_result[0] if epi_result else self.execute_with_retry(
                    'INSERT INTO epis (nome) VALUES (?)', (epi_name,),
                )
                self.execute_with_retry(
                    'INSERT INTO detections (timestamp, frame_data, epi_id) VALUES (?, ?, ?)',
                    (timestamp, frame_data, epi_id),
                )
        except sqlite3.Error as error:
            print(f'Erro ao registrar detecção: {error}')

    def close(self):
        """Espera gravações pendentes antes de encerrar o processo."""
        if getattr(self, 'executor', None) is not None:
            self.executor.shutdown(wait=True)
            self.executor = None

    def __del__(self):
        """Evita abandonar o executor se o encerramento explícito não ocorrer."""
        self.close()
