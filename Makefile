PYTHON ?= python3
EVENT_GENERATOR := events/001-building-with-ai/artwork/generate.py

.PHONY: build check

build:
	$(PYTHON) $(EVENT_GENERATOR)

check:
	$(PYTHON) scripts/verify_assets.py
