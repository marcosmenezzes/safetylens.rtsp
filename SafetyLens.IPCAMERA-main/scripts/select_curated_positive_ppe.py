#!/usr/bin/env python3
"""Seleciona um conjunto pequeno e limpo de EPIs presentes já convertidos para YOLO."""

import argparse
import json
import math
import shutil
from collections import Counter
from hashlib import sha256
from pathlib import Path

import cv2
from ultralytics import YOLO

from prepare_absent_ppe_video import clip_box, pose_boxes, yolo_line


NAMES = ["Com_Oculos", "Com_Capacete", "Com_Luva", "Com_Abafador", "Sem_Oculos", "Sem_Capacete", "Sem_Luva", "Sem_Abafador"]


def dhash(gray):
    """Produz um hash perceptual curto para remover imagens visualmente repetidas."""
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = small[:, 1:] > small[:, :-1]
    return sum(int(value) << index for index, value in enumerate(bits.flat))


def overlap_over_smaller(first, second):
    """Mede sobreposição relativa ao menor objeto para associar caixas."""
    x1, y1 = max(first[0], second[0]), max(first[1], second[1])
    x2, y2 = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    smaller = min((first[2] - first[0]) * (first[3] - first[1]), (second[2] - second[0]) * (second[3] - second[1]))
    return intersection / smaller if smaller else 0


def normalize(image, rows, model):
    """Refaz caixas positivas com pose e rejeita anotações sem correspondência."""
    frame = cv2.imread(str(image))
    height, width = frame.shape[:2]
    originals = {target: [] for target in range(4)}
    for row in rows:
        target = int(row[0])
        x, y, box_width, box_height = map(float, row[1:])
        originals[target].append(((x - box_width / 2) * width, (y - box_height / 2) * height, (x + box_width / 2) * width, (y + box_height / 2) * height))

    result = model.predict(frame, imgsz=640, conf=0.3, device="mps", verbose=False)[0]
    derived = {target: [] for target in range(4)}
    for index in range(len(result.boxes)):
        points = result.keypoints.xy[index].cpu().numpy()
        confidence = result.keypoints.conf[index].cpu().numpy()
        if min(float(confidence[5]), float(confidence[6])) < 0.35:
            continue
        regions = pose_boxes(points, confidence, result.boxes.xyxy[index].cpu().numpy(), width, height, threshold=0.35)
        head = next((box for class_id, box in regions if class_id == 5), None)
        for class_id, box in regions:
            if class_id in (4, 5, 6):
                if class_id == 6 and max(float(confidence[11]), float(confidence[12])) < 0.25:
                    continue
                derived[{4: 0, 5: 1, 6: 2}[class_id]].append(box)
        if head:
            head_width = head[2] - head[0]
            for ear in (3, 4):
                if float(confidence[ear]) < 0.35:
                    continue
                size = head_width * 0.34
                ear_box = clip_box((points[ear][0] - size / 2, points[ear][1] - size * 0.7, points[ear][0] + size / 2, points[ear][1] + size * 0.7), width, height)
                if ear_box:
                    derived[3].append(ear_box)

    normalized = []
    for target, source_boxes in originals.items():
        if not source_boxes:
            continue
        matched = [box for box in derived[target] if any(overlap_over_smaller(box, source) >= 0.25 for source in source_boxes)]
        if not matched:
            return None
        for box in matched:
            if not any(overlap_over_smaller(box, previous) > 0.75 for previous_target, previous in normalized if previous_target == target):
                normalized.append((target, box))
    return [yolo_line(target, box, width, height) for target, box in normalized]


def candidates(source):
    """Classifica candidatos nítidos, visíveis e exclusivamente positivos."""
    found = {target: [] for target in range(4)}
    for label_dir in source.glob("*/labels"):
        image_dir = label_dir.parent / "images"
        image_by_stem = {image.stem: image for image in image_dir.iterdir() if image.is_file()}
        for label in label_dir.glob("*.txt"):
            rows = [line.split() for line in label.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not rows or any(len(row) != 5 for row in rows):
                continue
            classes = {int(row[0]) for row in rows}
            if not classes <= set(range(4)) or len(rows) > 20:
                continue
            image = image_by_stem.get(label.stem)
            frame = cv2.imread(str(image)) if image else None
            if frame is None or min(frame.shape[:2]) < 320:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            if sharpness < 25:
                continue
            height, width = frame.shape[:2]
            visual_hash = dhash(gray)
            for target in classes:
                target_rows = [row for row in rows if int(row[0]) == target]
                if target == 2 and max(float(row[3]) * float(row[4]) for row in target_rows) > 0.05:
                    continue
                visible = max(min(float(row[3]) * width, float(row[4]) * height) * 640 / max(width, height) for row in target_rows)
                if visible < 5:
                    continue
                score = math.log1p(sharpness) + math.log1p(min(width, height)) + math.log1p(visible)
                found[target].append((score, image, label, rows, visual_hash))
    return {target: sorted(items, reverse=True, key=lambda item: item[0]) for target, items in found.items()}


def prepare(source, output, pose_model):
    """Seleciona 400 imagens diversas e gera o complemento positivo curado."""
    if output.exists():
        raise FileExistsError(f"Destino já existe: {output}")
    images = output / "train/images"
    labels = output / "train/labels"
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    used_files = set()
    used_hashes = set()
    selected_hashes = {target: [] for target in range(4)}
    source_counts = {target: Counter() for target in range(4)}
    selected = []
    wanted = {0: 120, 1: 125, 2: 110, 3: 45}

    try:
        model = YOLO(pose_model)
        candidate_by_target = candidates(source)
        for target in (3, 0, 1, 2):  # O abafador tem menos candidatos; reserva primeiro.
            for score, image, label, rows, visual_hash in candidate_by_target[target]:
                content_hash = sha256(image.read_bytes()).digest()
                prefix = label.stem.split("_", 1)[0]
                if target == 2 and prefix in {"gloves", "glovesv2"}:
                    continue
                if label in used_files or content_hash in used_hashes or source_counts[target][prefix] >= 80:
                    continue
                if any((visual_hash ^ previous).bit_count() < 3 for previous in selected_hashes[target]):
                    continue
                normalized = normalize(image, rows, model)
                if not normalized or target not in {int(row.split()[0]) for row in normalized}:
                    continue
                destination_stem = f"curated_{target}_{len(selected_hashes[target]):03d}"
                shutil.copy2(image, images / f"{destination_stem}{image.suffix.lower()}")
                (labels / f"{destination_stem}.txt").write_text("\n".join(normalized) + "\n", encoding="utf-8")
                used_files.add(label)
                used_hashes.add(content_hash)
                selected_hashes[target].append(visual_hash)
                source_counts[target][prefix] += 1
                selected.append({"image": image.name, "primaryClass": NAMES[target], "source": prefix, "score": round(score, 3)})
                if len(selected_hashes[target]) == wanted[target]:
                    break
            if len(selected_hashes[target]) != wanted[target]:
                raise RuntimeError(f"Só foi possível selecionar {len(selected_hashes[target])} imagens de {NAMES[target]}")

        box_counts = Counter()
        for label in labels.glob("*.txt"):
            for line in label.read_text().splitlines():
                box_counts[NAMES[int(line.split()[0])]] += 1
        yaml = [
            f"path: {output.resolve()}",
            "train: train/images",
            "",
            "names:",
            *(f"  {index}: {name}" for index, name in enumerate(NAMES)),
        ]
        (output / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
        report = {
            "purpose": "Complemento positivo curado; usar somente no treino",
            "selection": "400 imagens com pessoa detectável e caixas normalizadas por pose para olhos, cabeça, mãos e ouvidos",
            "images": len(selected),
            "primaryClasses": {NAMES[target]: len(values) for target, values in selected_hashes.items()},
            "boxes": dict(box_counts),
            "sources": {NAMES[target]: dict(counts) for target, counts in source_counts.items()},
            "items": selected,
        }
        (output / "dataset-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        assert len(list(images.iterdir())) == len(list(labels.iterdir())) == sum(wanted.values())
        print(json.dumps({key: report[key] for key in ("images", "primaryClasses", "boxes", "sources")}, indent=2, ensure_ascii=False))
    except Exception:
        shutil.rmtree(output)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pose-model", type=Path, default=Path("yolo26n-pose.pt"))
    args = parser.parse_args()
    prepare(args.source, args.output, args.pose_model)
