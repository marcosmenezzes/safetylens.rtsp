#!/usr/bin/env python3
"""Extrai capacete ausente e abafador presente/ausente de um vídeo controlado."""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import cv2
from ultralytics import YOLO

from prepare_absent_ppe_video import clip_box, pose_boxes, yolo_line
from prepare_glove_pair_video import expand_hand, white_score


NAMES = ["Com_Oculos", "Com_Capacete", "Com_Luva", "Com_Abafador", "Sem_Oculos", "Sem_Capacete", "Sem_Luva", "Sem_Abafador"]
WITH_HEADSET = ((0, 31), (121, 136))
WITHOUT_HEADSET = ((35, 46), (82, 110))


def state_at(seconds):
    """Retorna o estado conhecido do headset no instante do vídeo controlado."""
    if any(start <= seconds <= end for start, end in WITH_HEADSET):
        return "with"
    if any(start <= seconds <= end for start, end in WITHOUT_HEADSET):
        return "without"


def fallback_head(points, confidence, person_box, width, height):
    """Estima a cabeça quando olhos e orelhas não bastam para a regra principal."""
    if float(confidence[5]) >= 0.2 and float(confidence[6]) >= 0.2:
        center_x = float(points[5][0] + points[6][0]) / 2
        shoulder_y = float(points[5][1] + points[6][1]) / 2
        head_width = abs(float(points[5][0] - points[6][0])) * 0.68
        return clip_box((center_x - head_width / 2, shoulder_y - head_width, center_x + head_width / 2, shoulder_y - head_width * 0.08), width, height)
    person_width = float(person_box[2] - person_box[0])
    center_x = float(person_box[0] + person_box[2]) / 2
    head_width = person_width * 0.36
    return clip_box((center_x - head_width / 2, float(person_box[1]), center_x + head_width / 2, float(person_box[1]) + head_width), width, height)


def side_boxes(head, width, height, scale):
    """Cria regiões laterais consistentes para abafador presente ou ausente."""
    x1, y1, x2, y2 = head
    head_width, head_height = x2 - x1, y2 - y1
    box_width, box_height = head_width * 0.28 * scale, head_height * 0.42 * scale
    center_y = y1 + head_height * 0.62
    return [
        clip_box((x1 - box_width * 0.2, center_y - box_height / 2, x1 + box_width * 0.8, center_y + box_height / 2), width, height),
        clip_box((x2 - box_width * 0.8, center_y - box_height / 2, x2 + box_width * 0.2, center_y + box_height / 2), width, height),
    ]


def prepare(video, output, interval=0.4, device="mps", model_path="yolo26n-pose.pt"):
    """Converte o vídeo controlado de headset em splits e rótulos YOLO."""
    if output.exists():
        raise FileExistsError(output)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"Não foi possível abrir {video}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    model = YOLO(model_path)
    counts, records = Counter(), []
    output.mkdir(parents=True)
    try:
        for frame_index in range(0, total, max(1, round(fps * interval))):
            seconds = frame_index / fps
            state = state_at(seconds)
            if not state:
                continue
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok or cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < 4:
                continue
            result = model.predict(frame, imgsz=640, conf=0.25, device=device, verbose=False)[0]
            if not len(result.boxes):
                continue
            boxes = result.boxes.xyxy
            person = int(((boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])).argmax())
            points = result.keypoints.xy[person].cpu().numpy()
            confidence = result.keypoints.conf[person].cpu().numpy()
            person_box = result.boxes.xyxy[person].cpu().numpy()
            regions = pose_boxes(points, confidence, person_box, frame.shape[1], frame.shape[0], threshold=0.25)
            head = next((box for class_id, box in regions if class_id == 5), None) or fallback_head(points, confidence, person_box, frame.shape[1], frame.shape[0])
            if not head:
                continue
            rows = [(5, head)]
            eyes = next((box for class_id, box in regions if class_id == 4), None)
            if eyes:
                rows.append((4, eyes))
            ears = [box for class_id, box in regions if class_id == 7]
            if len(ears) < 2:
                ears = side_boxes(head, frame.shape[1], frame.shape[0], 1.35 if state == "with" else 1.0)
            rows.extend((3 if state == "with" else 7, box) for box in ears if box)

            hands = [box for class_id, box in regions if class_id == 6]
            if len(hands) == 2:
                scores = [white_score(frame, box) for box in hands]
                if abs(scores[0] - scores[1]) >= 0.18:
                    glove = max(range(2), key=scores.__getitem__)
                    rows.extend((2 if index == glove else 6, expand_hand(box, frame.shape[1], frame.shape[0])) for index, box in enumerate(hands))

            block = int(seconds // 3)
            split = "test" if block % 8 == 0 else "valid" if block % 8 == 1 else "train"
            stem = f"headset_{frame_index:06d}"
            image_dir, label_dir = output / split / "images", output / split / "labels"
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(image_dir / f"{stem}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            (label_dir / f"{stem}.txt").write_text("\n".join(yolo_line(class_id, box, frame.shape[1], frame.shape[0]) for class_id, box in rows if box) + "\n", encoding="utf-8")
            counts[f"images_{split}"] += 1
            counts["with_headset" if state == "with" else "without_headset"] += 1
            for class_id, box in rows:
                if box:
                    counts[NAMES[class_id]] += 1
            records.append({"image": f"{stem}.jpg", "split": split, "timeSeconds": round(seconds, 2), "headset": state})
    except Exception:
        shutil.rmtree(output)
        raise
    finally:
        capture.release()

    (output / "data.yaml").write_text("\n".join([
        f"path: {output.resolve()}", "train: train/images", "val: valid/images", "test: test/images", "", "names:",
        *(f"  {index}: {name}" for index, name in enumerate(NAMES)), "",
    ]), encoding="utf-8")
    report = {"source": str(video.resolve()), "intervalSeconds": interval, "safeIntervals": {"with": WITH_HEADSET, "without": WITHOUT_HEADSET}, "counts": dict(counts), "records": records}
    (output / "dataset-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert counts["Sem_Capacete"] == sum(counts[f"images_{split}"] for split in ("train", "valid", "test"))
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--interval", type=float, default=0.4)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--model", default="yolo26n-pose.pt")
    args = parser.parse_args()
    prepare(args.video, args.output, args.interval, args.device, args.model)
