#!/usr/bin/env python3
"""Extrai do PPE-0.3 somente as oito classes usadas pelo SafetyLens."""

import argparse
import json
import shutil
import tempfile
from collections import Counter
from hashlib import sha256
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


CLASS_MAP = {
    1: (0, "Com_Oculos"),
    3: (1, "Com_Capacete"),
    2: (2, "Com_Luva"),
    0: (3, "Com_Abafador"),
    9: (4, "Sem_Oculos"),
    11: (5, "Sem_Capacete"),
    10: (6, "Sem_Luva"),
    8: (7, "Sem_Abafador"),
}
GLOVES_CLASS_MAP = {
    0: (2, "Com_Luva"),
    1: (6, "Sem_Luva"),
}
GLOVES_V2_CLASS_MAP = {
    0: (2, "Com_Luva"),
    2: (6, "Sem_Luva"),
}
SAFETY_GLASSES_CLASS_MAP = {
    0: (0, "Com_Oculos"),
    1: (4, "Sem_Oculos"),
}
PERSONAL_PPE_CLASS_MAP = {
    0: (3, "Com_Abafador"),
    2: (2, "Com_Luva"),
    3: (1, "Com_Capacete"),
    5: (7, "Sem_Abafador"),
    6: (6, "Sem_Luva"),
    7: (5, "Sem_Capacete"),
}
SPLITS = ("train", "valid", "test")


def add_archive(source, temp, class_map, prefix, boxes, images, groups, seen_hashes, stats, skip_duplicates=False):
    """Extrai um ZIP seguro, converte classes e distribui grupos sem vazamento."""
    with ZipFile(source) as archive:
        members = archive.infolist()
        if any(PurePosixPath(item.filename).is_absolute() or ".." in PurePosixPath(item.filename).parts for item in members):
            raise ValueError("ZIP contém caminho inseguro")
        image_by_key = {}
        labels = []
        for item in members:
            path = PurePosixPath(item.filename)
            if len(path.parts) != 3 or path.parts[0] not in SPLITS:
                continue
            if path.parts[1] == "images" and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                image_by_key[(path.parts[0], path.stem)] = item
            elif path.parts[1] == "labels" and path.suffix == ".txt":
                labels.append(item)

        for label_info in labels:
            label_path = PurePosixPath(label_info.filename)
            source_split, stem = label_path.parts[0], label_path.stem
            image_info = image_by_key.get((source_split, stem))
            if image_info is None:
                raise FileNotFoundError(f"Imagem ausente para {label_info.filename}")
            image_bytes = archive.read(image_info)
            image_hash = sha256(image_bytes).digest()
            if skip_duplicates and image_hash in seen_hashes:
                stats[f"{prefix}_duplicates_skipped"] += 1
                continue
            seen_hashes.add(image_hash)
            converted = []
            for number, line in enumerate(archive.read(label_info).decode("utf-8").splitlines(), 1):
                parts = line.split()
                if not parts:
                    continue
                old_id = int(parts[0])
                if old_id not in class_map:
                    continue
                values = [float(value) for value in parts[1:]]
                if len(values) == 4:
                    coords = values
                elif len(values) >= 6 and len(values) % 2 == 0:
                    xs, ys = values[0::2], values[1::2]
                    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
                    coords = [(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1]
                    stats[f"{prefix}_polygons_converted"] += 1
                else:
                    raise ValueError(f"Caixa inválida em {label_info.filename}:{number}")
                if not all(0 <= value <= 1 for value in coords):
                    raise ValueError(f"Coordenada inválida em {label_info.filename}:{number}")
                new_id, name = class_map[old_id]
                converted.append(f"{new_id} {' '.join(f'{value:.8f}' for value in coords)}")
                boxes[name] += 1

            if not converted:
                continue
            base_name = f"{prefix}:{stem.split('.rf.', 1)[0]}"
            bucket = int.from_bytes(sha256(base_name.encode()).digest()[:8], "big") % 100
            split = "train" if bucket < 80 else "valid" if bucket < 95 else "test"
            image_path = PurePosixPath(image_info.filename)
            image_dest = temp / split / "images" / f"{prefix}_{image_path.name}"
            label_dest = temp / split / "labels" / f"{prefix}_{label_path.name}"
            if image_dest.exists() or label_dest.exists():
                raise FileExistsError(f"Nome duplicado no destino: {image_path.name}")
            image_dest.parent.mkdir(parents=True, exist_ok=True)
            label_dest.parent.mkdir(parents=True, exist_ok=True)
            image_dest.write_bytes(image_bytes)
            label_dest.write_text("\n".join(converted) + "\n", encoding="utf-8")
            images[split] += 1
            groups[split].add(base_name)


def prepare(source: Path, output: Path, gloves: Path | None = None, gloves_v2: Path | None = None, safety_glasses: Path | None = None, personal_ppe: Path | None = None) -> None:
    """Mescla fontes públicas relevantes no padrão canônico de oito classes."""
    if output.exists():
        raise FileExistsError(f"Destino já existe: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    boxes = Counter()
    images = Counter()
    groups = {split: set() for split in SPLITS}
    seen_hashes = set()
    stats = Counter()

    try:
        add_archive(source, temp, CLASS_MAP, "ppe03", boxes, images, groups, seen_hashes, stats)
        if gloves:
            add_archive(gloves, temp, GLOVES_CLASS_MAP, "gloves", boxes, images, groups, seen_hashes, stats, True)
        if gloves_v2:
            add_archive(gloves_v2, temp, GLOVES_V2_CLASS_MAP, "glovesv2", boxes, images, groups, seen_hashes, stats, True)
        if safety_glasses:
            add_archive(safety_glasses, temp, SAFETY_GLASSES_CLASS_MAP, "glasses", boxes, images, groups, seen_hashes, stats, True)
        if personal_ppe:
            add_archive(personal_ppe, temp, PERSONAL_PPE_CLASS_MAP, "personalppe", boxes, images, groups, seen_hashes, stats, True)

        names = [name for _, name in sorted(CLASS_MAP.values())]
        yaml = [
            f"path: {output.resolve()}",
            "train: train/images",
            "val: valid/images",
            "test: test/images",
            "",
            "names:",
            *(f"  {index}: {name}" for index, name in enumerate(names)),
        ]
        (temp / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
        report = {
            "sources": [
                {
                    "zip": str(source.resolve()),
                    "project": "https://universe.roboflow.com/kaue-henrique-rezende-foes/ppe-0.3-7d3ks",
                    "license": "Public Domain",
                },
                *([{
                    "zip": str(gloves.resolve()),
                    "project": "https://universe.roboflow.com/task-g-visual-activity/ppe-gloves-wozvf-fy20c",
                    "license": "CC BY 4.0",
                }] if gloves else []),
                *([{
                    "zip": str(gloves_v2.resolve()),
                    "project": "https://universe.roboflow.com/marks-workspace-zns5d/gloves-em4xn",
                    "license": "CC BY 4.0",
                    "excluded_class": "glove_not_worn",
                }] if gloves_v2 else []),
                *([{
                    "zip": str(safety_glasses.resolve()),
                    "project": "https://universe.roboflow.com/tiens-workspace-g0fps/safety-glasses-p7zzg",
                    "license": "CC BY 4.0",
                }] if safety_glasses else []),
                *([{
                    "zip": str(personal_ppe.resolve()),
                    "project": "https://universe.roboflow.com/training-dataset-ta/personal-protective-equipment-9clx4",
                    "license": "CC BY 4.0",
                    "included_classes": ["Earmuffs", "Gloves", "Hardhat", "No Earmuff", "No Glove", "No Hardhat"],
                }] if personal_ppe else []),
            ],
            "split_strategy": "Agrupado pelo nome original; hash SHA-256 determinístico 80/15/5",
            "images": dict(images),
            "source_groups": {split: len(groups[split]) for split in SPLITS},
            "deduplication": dict(stats),
            "boxes": {name: boxes[name] for name in names},
        }
        (temp / "dataset-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.rename(output)
    except Exception:
        shutil.rmtree(temp)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gloves", type=Path)
    parser.add_argument("--gloves-v2", type=Path)
    parser.add_argument("--safety-glasses", type=Path)
    parser.add_argument("--personal-ppe", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output, args.gloves, args.gloves_v2, args.safety_glasses, args.personal_ppe)
