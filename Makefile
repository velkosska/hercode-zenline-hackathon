.PHONY: process enrich pipeline dashboard api all install

VENV = .venv/bin
PYTHON = PYTHONPATH=. $(VENV)/python
PIP = $(VENV)/pip

install:
	$(PIP) install -r requirements.txt

process:
	$(PYTHON) process_trends.py

enrich:
	$(PYTHON) -m src.radar.pipeline.enrich

pipeline:
	$(PYTHON) -m src.radar.pipeline.run

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

api:
	$(VENV)/uvicorn src.radar.api.main:app --reload --port 8000

all: process pipeline
