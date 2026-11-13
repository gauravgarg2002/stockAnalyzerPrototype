.PHONY: help setup dev test verify-local sample-data docker-up docker-down clean

help:
	@echo "make setup         install dependencies for all three services"
	@echo "make dev           run all three services (mock mode by default)"
	@echo "make test          full test suites (pytest, mvn test, npm test)"
	@echo "make verify-local  checks that need no package downloads"
	@echo "make sample-data   regenerate the bundled sample data"
	@echo "make docker-up     build and run with docker compose"
	@echo "make docker-down   stop docker compose"
	@echo "make clean         remove build output and local data"

setup:
	cd backend-python && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	-cd backend-python && .venv/bin/pip install -r requirements-optional.txt
	cd backend-java && mvn -q -DskipTests package
	cd frontend && npm install

dev:
	./run-dev.sh

test:
	cd backend-python && python3 -m pytest -q
	cd backend-java && mvn -q test
	cd frontend && npm test

# Everything here runs with only Python (pydantic, starlette, uvicorn, pytest, PyYAML, requests,
# pdfplumber, pypdf), a JDK and global tsc/tsx: no Maven, npm or pip downloads.
verify-local:
	cd backend-python && python3 -m pytest -q
	cd backend-python && python3 scripts/smoke_internal.py
	./backend-java/tools/engine-check.sh
	cd frontend && tsc -p tsconfig.lib.json && tsx --test src/lib/*.test.ts

sample-data:
	cd backend-python && python3 scripts/generate_sample_data.py && python3 scripts/make_sample_cas_pdf.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf backend-java/target backend-java/out backend-java/data frontend/dist frontend/node_modules \
	       backend-python/.venv backend-python/.cache .run
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
