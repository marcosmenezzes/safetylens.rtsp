#!/usr/bin/env python3
"""Extrai pares de mãos com/sem luva branca usando pose e contraste."""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import cv2
from ultralytics import YOLO

from prepare_absent_ppe_video import clip_box, pose_boxes, yolo_line


NAMES = ["Com_Oculos", "Com_Capacete", "Com_Luva", "Com_Abafador", "Sem_Oculos", "Sem_Capacete", "Sem_Luva", "Sem_Abafador"]


def white_score(frame, box):
    """Estima quanto uma região se parece com a luva branca do vídeo controlado."""
    x1, y1, x2, y2 = map(int, box)
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    return float(((hsv[:, :, 1] < 75) & (hsv[:, :, 2] > 110)).mean())


def expand_hand(box, width, height):
    """Amplia a região da mão para incluir dedos e punho de forma consistente."""
    x1, y1, x2, y2 = box
    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
    box_width = max((x2 - x1) * 1.15, width * 0.18)
    box_height = max((y2 - y1) * 1.15, box_width * 1.1)
    return clip_box((center_x - box_width / 2, center_y - box_height / 2, center_x + box_width / 2, center_y + box_height / 2), width, height)


def prepare(video, output, interval=0.3, device="mps", model_path="yolo26n-pose.pt"):
    """Extrai pares com/sem luva, separa por tempo e escreve um dataset YOLO."""
    if output.exists():
        raise FileExistsError(output)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"Não foi possível abrir {video}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    model = YOLO(model_path)
    counts = Counter()
    records = []
    output.mkdir(parents=True)
    try:
        for frame_index in range(0, total, max(1, round(fps * interval))):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok or cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < 4:
                continue
            result = model.predict(frame, imgsz=640, conf=0.25, device=device, verbose=False)[0]
            if not len(result.boxes):
                continue
            person = int(result.boxes.xyxy[:, 2:].prod(1).argmax())
            hands = [box for class_id, box in pose_boxes(
                result.keypoints.xy[person].cpu().numpy(),
                result.keypoints.conf[person].cpu().numpy(),
                result.boxes.xyxy[person].cpu().numpy(),
                frame.shape[1],
                frame.shape[0],
                threshold=0.25,
            ) if class_id == 6]
            if len(hands) != 2:
                continue
            scores = [white_score(frame, box) for box in hands]
            if abs(scores[0] - scores[1]) < 0.18:
                continue
            boxes = [expand_hand(box, frame.shape[1], frame.shape[0]) for box in hands]
            if any(box is None for box in boxes):
                continue
            glove = max(range(2), key=scores.__getitem__)
            seconds = frame_index / fps
            block = int(seconds // 3)
            split = "test" if block % 7 == 0 else "valid" if block % 7 == 1 else "train"
            stem = f"glove_pair_{frame_index:06d}"
            image_dir, label_dir = output / split / "images", output / split / "labels"
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(image_dir / f"{stem}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            rows = [yolo_line(2 if index == glove else 6, box, frame.shape[1], frame.shape[0]) for index, box in enumerate(boxes)]
            (label_dir / f"{stem}.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
            counts[f"images_{split}"] += 1
            counts["Com_Luva"] += 1
            counts["Sem_Luva"] += 1
            records.append({"image": f"{stem}.jpg", "split": split, "timeSeconds": round(seconds, 2), "whiteScores": [round(score, 3) for score in scores]})
    except Exception:
        shutil.rmtree(output)
        raise
    finally:
        capture.release()

    (output / "data.yaml").write_text("\n".join([
        f"path: {output.resolve()}", "train: train/images", "val: valid/images", "test: test/images", "", "names:",
        *(f"  {index}: {name}" for index, name in enumerate(NAMES)), "",
    ]), encoding="utf-8")
    report = {"source": str(video.resolve()), "intervalSeconds": interval, "counts": dict(counts), "records": records}
    (output / "dataset-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert counts["Com_Luva"] == counts["Sem_Luva"] == sum(counts[f"images_{split}"] for split in ("train", "valid", "test"))
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--interval", type=float, default=0.3)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--model", default="yolo26n-pose.pt")
    args = parser.parse_args()
    prepare(args.video, args.output, args.interval, args.device, args.model)
