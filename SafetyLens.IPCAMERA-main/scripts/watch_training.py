#!/usr/bin/env python3
"""Mostra as métricas mais recentes do fine-tuning."""

import csv
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "model/runs/safetylens-yolo26n-precision-v10/results.csv"
PID = ROOT / "model/runs/training-v10.pid"


def running():
    """Verifica se o PID salvo ainda pertence a um processo em execução."""
    try:
        os.kill(int(PID.read_text().strip()), 0)
        return True
    except (OSError, ValueError, FileNotFoundError):
        return False


def show():
    """Mostra a última época e as métricas principais em formato amigável."""
    if not CSV.is_file():
        print("Treino iniciando; métricas ainda não disponíveis.")
        return
    with CSV.open(newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        print("Primeira época em processamento.")
        return
    row = rows[-1]
    percent = lambda key: f"{float(row[key]) * 100:.1f}%"
    print(f"Época {row['epoch']}/80 | precisão {percent('metrics/precision(B)')} | recall {percent('metrics/recall(B)')} | mAP50 {percent('metrics/mAP50(B)')} | mAP50-95 {percent('metrics/mAP50-95(B)')} | {'rodando' if running() else 'finalizado'}")


if __name__ == "__main__":
    if "--finish" in sys.argv:
        while running():
            time.sleep(10)
        from train_personal import install_and_open

        install_and_open()
        raise SystemExit
    watch = "--watch" in sys.argv
    while True:
        show()
        if not watch or not running():
            break
        time.sleep(10)
