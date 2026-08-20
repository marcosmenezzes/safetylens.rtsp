#!/usr/bin/env python3
"""Monta o fine-tuning somente com anotações próprias e frames da câmera."""

import argparse
import json
import shutil
from collections import Counter
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile


NAMES = ["Com_Oculos", "Com_Capacete", "Com_Luva", "Com_Abafador", "Sem_Oculos", "Sem_Capacete", "Sem_Luva", "Sem_Abafador"]
# Duplicatas corrigidas no segundo arquivo; as versões antigas têm rótulos conflitantes/incompletos.
SKIP = {"istockphoto-1140837585-612x612", "pexels-pexels-user-2148623819-30223853"}


def validate(text, source):
    """Valida classes e coordenadas antes de aceitar uma anotação pessoal."""
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if len(parts) != 5 or int(parts[0]) not in range(len(NAMES)) or not all(0 <= float(value) <= 1 for value in parts[1:]):
            raise ValueError(f"Rótulo inválido: {source}:{number}")
        rows.append(line)
    if not rows:
        raise ValueError(f"Rótulo vazio: {source}")
    return rows


def add_file(image, rows, output, split, prefix, counts):
    """Copia imagem/rótulo com nome único e contabiliza classes por split."""
    stem = f"{prefix}_{image.stem}"
    image_dest = output / split / "images" / f"{stem}{image.suffix.lower()}"
    label_dest = output / split / "labels" / f"{stem}.txt"
    if image_dest.exists() or label_dest.exists():
        raise FileExistsError(stem)
    image_dest.parent.mkdir(parents=True, exist_ok=True)
    label_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image, image_dest)
    label_dest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    counts[f"images_{split}"] += 1
    for row in rows:
        counts[NAMES[int(row.split()[0])]] += 1


def prepare(images, labels_zip, camera, output):
    """Combina MakeSense e frames próprios em um dataset pessoal reproduzível."""
    if output.exists():
        raise FileExistsError(f"Destino já existe: {output}")
    output.mkdir(parents=True)
    counts = Counter()
    try:
        image_by_stem = {path.stem: path for path in images.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".avif"}}
        with ZipFile(labels_zip) as archive:
            members = sorted(name for name in archive.namelist() if name.endswith(".txt"))
            for member in members:
                stem = Path(member).stem
                if stem in SKIP:
                    counts["duplicates_skipped"] += 1
                    continue
                image = image_by_stem.get(stem)
                if image is None:
                    raise FileNotFoundError(f"Imagem ausente para {member}")
                bucket = int.from_bytes(sha256(stem.encode()).digest()[:8], "big") % 100
                split = "train" if bucket < 75 else "valid" if bucket < 90 else "test"
                add_file(image, validate(archive.read(member).decode("utf-8"), member), output, split, "makesense", counts)

        for label in sorted((camera / "labels").glob("*.txt")):
            image = camera / "images" / f"{label.stem}.jpg"
            if not image.is_file():
                raise FileNotFoundError(f"Imagem ausente para {label}")
            add_file(image, validate(label.read_text(encoding="utf-8"), label), output, "train", "camera", counts)

        yaml = [
            f"path: {output.resolve()}",
            "train: train/images",
            "val: valid/images",
            "test: test/images",
            "",
            "names:",
            *(f"  {index}: {name}" for index, name in enumerate(NAMES)),
        ]
        (output / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
        report = {
            "purpose": "Fine-tuning exclusivamente com anotações próprias",
            "sources": [str(images.resolve()), str(labels_zip.resolve()), str(camera.resolve())],
            "split": "MakeSense 75/15/10 por hash; vídeo somente no treino",
            "counts": dict(counts),
        }
        (output / "dataset-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    except Exception:
        shutil.rmtree(output)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("images", type=Path)
    parser.add_argument("labels_zip", type=Path)
    parser.add_argument("camera", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.images, args.labels_zip, args.camera, args.output)
