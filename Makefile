.PHONY: process enrich pipeline dashboard api web web-install all install

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
	PYTHONPATH=. $(VENV)/uvicorn src.radar.api.main:app --reload --port 8000

web-install:
	cd zenscout && npm install

web:
	cd zenscout && npm run dev

all: process pipeline
