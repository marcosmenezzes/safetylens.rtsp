.PHONY: start stop web api frontend dev test train train-resume train-status train-live

start: web

stop:
	@pkill -f '[p]ython.*-m src.web.app' 2>/dev/null || true
	@pkill -f '[v]ite.*127.0.0.1' 2>/dev/null || true

web:
	@npm --prefix SafetyLens.IPCAMERA-main/frontend run build
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/python -m src.web.app

api:
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/python -m src.web.app

frontend:
	@npm --prefix SafetyLens.IPCAMERA-main/frontend run dev

dev:
	@$(MAKE) --no-print-directory -j2 api frontend

test:
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/python -m unittest discover -s tests
	@npm --prefix SafetyLens.IPCAMERA-main/frontend run build
	@npm --prefix SafetyLens.IPCAMERA-main/frontend run test:e2e

train:
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/python scripts/train_personal.py

train-resume:
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/yolo train resume model=model/runs/safetylens-yolo26n-precision-v10/weights/last.pt device=mps

train-status:
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/python scripts/watch_training.py

train-live:
	@cd SafetyLens.IPCAMERA-main && ../.venv/bin/python scripts/watch_training.py --watch
