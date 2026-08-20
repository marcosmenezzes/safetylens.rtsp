"""Inferência YOLO, desenho das caixas e ajustes visuais do frame."""

import cv2
from ultralytics import YOLO
from src.core.epis import EPI_NAMES, MISSING_EPI_IDS


CONFLICTING_CLASSES = {frozenset((present, missing)) for present, missing in ((0, 4), (1, 5), (2, 6), (3, 7))}


def _overlap_over_smaller(first, second):
    """Mede quanto duas caixas disputam a mesma região do menor objeto."""
    x1, y1 = max(first[0], second[0]), max(first[1], second[1])
    x2, y2 = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    smaller = min((first[2] - first[0]) * (first[3] - first[1]), (second[2] - second[0]) * (second[3] - second[1]))
    return intersection / smaller if smaller > 0 else 0


def _deduplicate(detections, threshold=0.65):
    """Mantém a caixa mais confiante entre previsões sobrepostas/conflitantes."""
    kept = []
    for detection in sorted(detections, key=lambda item: item[1], reverse=True):
        class_id, _, box = detection
        if any(
            _overlap_over_smaller(box, other_box) >= threshold
            and (class_id == other_class or frozenset((class_id, other_class)) in CONFLICTING_CLASSES)
            for other_class, _, other_box in kept
        ):
            continue
        kept.append(detection)
    return kept

class EPIDetector:
    """Carrega o modelo uma vez e converte previsões em alertas legíveis."""

    def __init__(self, model_path, min_confidence=0.5):
        """Inicializa o peso ativo e a confiança ajustável pelo painel."""
        self.model = YOLO(model_path)
        self.min_confidence = min_confidence
        # Mapeamento de classes com seus nomes corretos
        self.epi_mapping = EPI_NAMES
        # Define quais IDs representam EPIs ausentes
        self.ausentes_ids = MISSING_EPI_IDS

    def detect(self, frame):
        """Executa inferência, desenha caixas e retorna classes encontradas."""
        # Um EPI da mesma pessoa não deve gerar caixas concorrentes em escalas diferentes.
        results = self.model.predict(frame, conf=self.min_confidence, iou=0.3, verbose=False)
        found_classes = []
        missing_epis = []

        detections = []
        for result in results:
            for box in result.boxes:
                conf = float(box.conf)  # Confiança da detecção
                cls = int(box.cls[0])   # ID da classe detectada
                if conf > self.min_confidence:
                    detections.append((cls, conf, tuple(map(int, box.xyxy[0]))))

        for cls, conf, (x1, y1, x2, y2) in _deduplicate(detections):
            found_classes.append(cls)
            label = f'{self.epi_mapping[cls]} {conf:.2f}'
            color = (0, 0, 255) if cls in self.ausentes_ids else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.rectangle(frame, (x1, y1 - 30), (x1 + len(label) * 12, y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            if cls in self.ausentes_ids:
                missing_epis.append(self.epi_mapping[cls])

        return frame, missing_epis, found_classes

    def update_min_confidence(self, value):
        """Aplica imediatamente uma nova confiança sem recarregar o modelo."""
        self.min_confidence = value

class ImageProcessor:
    """Reúne os ajustes de imagem aplicados antes da inferência."""

    @staticmethod
    def adjust_image(frame, brightness, contrast, sharpness, grayscale):
        """Aplica brilho, contraste, nitidez e cinza sem alterar o frame original."""
        adjusted_frame = cv2.convertScaleAbs(
            frame,
            alpha=contrast / 100,
            beta=brightness - 100,
        )

        if sharpness > 0:
            blurred = cv2.GaussianBlur(adjusted_frame, (0, 0), 1.2)
            strength = sharpness / 10
            adjusted_frame = cv2.addWeighted(adjusted_frame, 1 + strength, blurred, -strength, 0)
        
        # Converte para escala de cinza se necessário
        if grayscale:
            adjusted_frame = cv2.cvtColor(adjusted_frame, cv2.COLOR_BGR2GRAY)
            adjusted_frame = cv2.cvtColor(adjusted_frame, cv2.COLOR_GRAY2BGR)
        
        return adjusted_frame
