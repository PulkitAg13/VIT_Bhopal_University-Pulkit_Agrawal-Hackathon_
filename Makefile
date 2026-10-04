PYTHON ?= python
BACKEND ?= backend
FRONTEND ?= frontend

.PHONY: install backend-tests frontend-build docker-up docker-down

install:
	python -m pip install --upgrade pip
	pip install -r $(BACKEND)/requirements.txt
	cd $(FRONTEND) && npm install

backend-tests:
	cd $(BACKEND) && pytest -q

frontend-build:
	cd $(FRONTEND) && npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
