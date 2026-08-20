"""Extrai frames e pré-anota ausência de EPIs via pose."""

import argparse
import json
import math
from pathlib import Path

import cv2
from ultralytics import YOLO


NAMES = {4: "Sem_Oculos", 5: "Sem_Capacete", 6: "Sem_Luva", 7: "Sem_Abafador"}


def clip_box(box, width, height):
    """Limita uma caixa ao frame e descarta regiões pequenas demais."""
    x1, y1, x2, y2 = box
    x1, x2 = sorted((max(0.0, x1), min(float(width), x2)))
    y1, y2 = sorted((max(0.0, y1), min(float(height), y2)))
    return (x1, y1, x2, y2) if x2 - x1 >= 8 and y2 - y1 >= 8 else None


def distance(a, b):
    """Calcula a distância euclidiana entre dois pontos da pose."""
    return math.hypot(float(a[0] - b[0]), float(a[1] - b[1]))


def pose_boxes(points, confidence, person_box, width, height, threshold=0.45):
    """Deriva regiões de cabeça, olhos, ouvidos e mãos dos pontos corporais."""
    visible = lambda index: float(confidence[index]) >= threshold
    person_width = float(person_box[2] - person_box[0])
    shoulder_span = distance(points[5], points[6]) if visible(5) and visible(6) else person_width * 0.45
    head_points = [points[i] for i in range(5) if visible(i)]
    boxes = []

    if len(head_points) >= 2:
        center_x = sum(float(point[0]) for point in head_points) / len(head_points)
        eye_y = sum(float(points[i][1]) for i in (1, 2) if visible(i)) / sum(visible(i) for i in (1, 2)) if visible(1) or visible(2) else sum(float(point[1]) for point in head_points) / len(head_points)
        candidates = [shoulder_span * 0.42]
        if visible(1) and visible(2):
            candidates.append(distance(points[1], points[2]) * 2.5)
        if visible(3) and visible(4):
            candidates.append(distance(points[3], points[4]) * 1.25)
        head_width = min(max(candidates), person_width * 0.68)
        head_height = head_width * 0.92
        head = clip_box((center_x - head_width / 2, eye_y - head_height * 0.55, center_x + head_width / 2, eye_y + head_height * 0.45), width, height)
        if head:
            boxes.append((5, head))
            eye_width = head_width * 0.72
            eyes = clip_box((center_x - eye_width / 2, eye_y - head_height * 0.13, center_x + eye_width / 2, eye_y + head_height * 0.14), width, height)
            if eyes:
                boxes.append((4, eyes))
            ear_width = head_width * 0.3
            ear_height = head_height * 0.42
            for index in (3, 4):
                if visible(index):
                    ear_x, ear_y = map(float, points[index])
                    ear = clip_box((ear_x - ear_width / 2, ear_y - ear_height / 2, ear_x + ear_width / 2, ear_y + ear_height / 2), width, height)
                    if ear:
                        boxes.append((7, ear))

    for elbow, wrist in ((7, 9), (8, 10)):
        if not visible(elbow) or not visible(wrist):
            continue
        forearm = distance(points[elbow], points[wrist])
        if forearm < 8:
            continue
        dx = float(points[wrist][0] - points[elbow][0]) / forearm
        dy = float(points[wrist][1] - points[elbow][1]) / forearm
        size = min(max(forearm * 0.75, shoulder_span * 0.2), person_width * 0.35)
        center_x = float(points[wrist][0]) + dx * size * 0.35
        center_y = float(points[wrist][1]) + dy * size * 0.35
        hand = clip_box((center_x - size * 0.55, center_y - size * 0.65, center_x + size * 0.55, center_y + size * 0.65), width, height)
        if hand:
            boxes.append((6, hand))
    return boxes


def yolo_line(class_id, box, width, height):
    """Converte uma caixa em pixels para a linha normalizada esperada pelo YOLO."""
    x1, y1, x2, y2 = box
    return f"{class_id} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} {(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}"


def main():
    """Valida argumentos, extrai frames úteis e gera o relatório de pré-anotação."""
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--interval", type=float, default=0.9)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--model", default="yolo26n-pose.pt")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error("vídeo não encontrado")
    if args.output.exists():
        parser.error("a pasta de saída já existe")
    if args.interval < 0.25:
        parser.error("intervalo mínimo: 0.25 segundo")

    images = args.output / "images"
    labels = args.output / "labels"
    images.mkdir(parents=True)
    labels.mkdir()
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        parser.error("não foi possível abrir o vídeo")
    fps = capture.get(cv2.CAP_PROP_FPS)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    model = YOLO(args.model)
    counts = {name: 0 for name in NAMES.values()}
    records = []
    previous_signature = None
    frame_step = max(1, round(fps * args.interval))

    try:
        for frame_index in range(0, total, frame_step):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if cv2.Laplacian(gray, cv2.CV_64F).var() < 18:
                continue
            signature = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
            if previous_signature is not None and cv2.absdiff(signature, previous_signature).mean() < 2.0:
                continue
            previous_signature = signature
            result = model.predict(frame, imgsz=640, conf=0.3, device=args.device, verbose=False)[0]
            if not len(result.boxes):
                continue
            largest = int(result.boxes.xyxy[:, 2:].prod(1).argmax())
            boxes = pose_boxes(
                result.keypoints.xy[largest].cpu().numpy(),
                result.keypoints.conf[largest].cpu().numpy(),
                result.boxes.xyxy[largest].cpu().numpy(),
                frame.shape[1],
                frame.shape[0],
            )
            if not boxes:
                continue
            stem = f"IMG_1564_{len(records):06d}"
            cv2.imwrite(str(images / f"{stem}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            (labels / f"{stem}.txt").write_text("\n".join(yolo_line(c, b, frame.shape[1], frame.shape[0]) for c, b in boxes) + "\n", encoding="utf-8")
            for class_id, _ in boxes:
                counts[NAMES[class_id]] += 1
            records.append({"image": f"{stem}.jpg", "sourceFrame": frame_index, "timeSeconds": round(frame_index / fps, 3), "boxes": len(boxes)})
    finally:
        capture.release()

    (args.output / "classes.txt").write_text("\n".join(["Com_Oculos", "Com_Capacete", "Com_Luva", "Com_Abafador", "Sem_Oculos", "Sem_Capacete", "Sem_Luva", "Sem_Abafador"]) + "\n", encoding="utf-8")
    report = {
        "source": str(args.video.resolve()),
        "purpose": "Pré-anotação; revisar antes do treinamento",
        "split": "train only; use another recording for validation/test",
        "fps": fps,
        "sourceFrames": total,
        "intervalSeconds": args.interval,
        "images": len(records),
        "boxes": counts,
        "records": records,
    }
    (args.output / "dataset-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert all(0 <= float(value) <= 1 for label in labels.glob("*.txt") for line in label.read_text().splitlines() for value in line.split()[1:])
    print(json.dumps({"images": len(records), "boxes": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
