import cv2
from ultralytics import YOLO
import numpy as np

class EPIDetector:
    def __init__(self, model_path, min_confidence=0.5):
        self.model = YOLO(model_path)
        self.min_confidence = min_confidence
        # Mapeamento de classes com seus nomes corretos
        self.epi_mapping = {
            0: 'Com_Oculos',
            1: 'Com_Capacete',
            2: 'Com_Luva',
            3: 'Com_Abafador',
            4: 'Sem_Oculos',
            5: 'Sem_Capacete',
            6: 'Sem_Luva',
            7: 'Sem_Abafador'
        }
        # Define quais IDs representam EPIs ausentes
        self.ausentes_ids = {4, 5, 6, 7}  # Conjunto para busca mais eficiente

    def detect(self, frame):
        results = self.model(frame, verbose=False)
        found_classes = []
        missing_epis = []

        # Processa os resultados da detecção
        for result in results:
            boxes = result.boxes
            for box in boxes:
                conf = float(box.conf)  # Confiança da detecção
                cls = int(box.cls[0])   # ID da classe detectada
                
                if conf > self.min_confidence:
                    found_classes.append(cls)
                    x1, y1, x2, y2 = map(int, box.xyxy[0])  # Coordenadas da caixa
                    label = f'{self.epi_mapping[cls]} {conf:.2f}'
                    
                    # Cor vermelha para EPIs ausentes, verde para presentes
                    color = (0, 0, 255) if cls in self.ausentes_ids else (0, 255, 0)
                    
                    # Desenha a caixa delimitadora e o rótulo
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    # Fundo preto semi-transparente para o texto
                    cv2.rectangle(frame, (x1, y1 - 30), (x1 + len(label) * 12, y1), color, -1)
                    cv2.putText(frame, label, (x1, y1 - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                    # Se é uma classe de EPI ausente, adiciona à lista
                    if cls in self.ausentes_ids:
                        missing_epis.append(self.epi_mapping[cls])

        print(f"Classes detectadas: {[self.epi_mapping[cls] for cls in found_classes]}")
        return frame, missing_epis, found_classes

    def update_min_confidence(self, value):
        self.min_confidence = value

class ImageProcessor:
    @staticmethod
    def adjust_image(frame, brightness, contrast, sharpness, grayscale):
        adjusted_frame = frame.copy()
        
        # Ajusta o brilho
        adjusted_frame = cv2.convertScaleAbs(adjusted_frame, beta=brightness - 100)
        
        # Ajusta o contraste
        adjusted_frame = cv2.convertScaleAbs(adjusted_frame, alpha=contrast / 100)
        
        # Aplica nitidez
        if sharpness > 0:
            kernel = (1 / 16) * np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]])
            adjusted_frame = cv2.filter2D(adjusted_frame, -1, kernel * sharpness)
        
        # Converte para escala de cinza se necessário
        if grayscale:
            adjusted_frame = cv2.cvtColor(adjusted_frame, cv2.COLOR_BGR2GRAY)
            adjusted_frame = cv2.cvtColor(adjusted_frame, cv2.COLOR_GRAY2BGR)
        
        return adjusted_frame