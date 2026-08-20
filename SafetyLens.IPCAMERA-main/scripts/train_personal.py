#!/usr/bin/env python3
"""Fine-tuning de precisão e instalação automática do melhor peso."""

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "model/runs/safetylens-yolo26n-precision-v10"


def main():
    """Executa o fine-tuning v10 e instala o melhor peso ao concluir."""
    YOLO(ROOT / "model/best.pt").train(
        data=ROOT / "datasets/safetylens-precision-v10/data.yaml",
        epochs=80,
        imgsz=768,
        batch=8,
        device="mps",
        workers=0,
        patience=20,
        optimizer="AdamW",
        lr0=0.0002,
        freeze=10,
        cos_lr=True,
        close_mosaic=10,
        save_period=10,
        project=ROOT / "model/runs",
        name=RUN.name,
    )
    install_and_open()


def install_and_open():
    """Preserva o peso atual, instala o novo e abre o painel web."""
    completion = RUN / "completion.json"
    if completion.exists():
        return
    best = RUN / "weights/best.pt"
    if not best.is_file():
        raise FileNotFoundError(best)
    active = ROOT / "model/best.pt"
    backup = ROOT / "model/backups" / f"best-before-precision-v10-{datetime.now():%Y%m%d-%H%M%S}.pt"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(active, backup)
    shutil.copy2(best, active)
    completion.write_text(json.dumps({"best": str(best), "installed": str(active), "backup": str(backup)}, indent=2) + "\n")
    subprocess.Popen([sys.executable, "-m", "src.web.app"], cwd=ROOT, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
