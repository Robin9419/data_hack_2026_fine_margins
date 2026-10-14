.DEFAULT_GOAL := help
PYTHON ?= python3

.PHONY: help install dev backend frontend

help:
	@echo "make install   Install backend and frontend dependencies"
	@echo "make dev       Start both servers (Ctrl+C stops both)"
	@echo "make backend   Start only the backend"
	@echo "make frontend  Start only the frontend"

install:
	$(PYTHON) -m venv backend/.venv
	backend/.venv/bin/python -m pip install -r backend/requirements.txt
	npm --prefix frontend ci

dev:
	$(PYTHON) scripts/dev.py

backend:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
