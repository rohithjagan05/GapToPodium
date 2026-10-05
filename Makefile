# One-word commands for the pipeline. Run them inside the activated virtual environment.
# NFR-3: a fresh clone plus `make setup && make phase1` rebuilds the raw data.
# Recipe lines must start with a TAB character, not spaces.

PYTHON ?= python

.PHONY: help setup lint test check olympedia worlds wa validate phase1

help:
	@echo "make setup      install pinned requirements"
	@echo "make lint       ruff code checks"
	@echo "make test       offline tests (pytest)"
	@echo "make check      lint, then tests"
	@echo "make olympedia  scrape Olympic results 2000-2024 (cached, polite)"
	@echo "make worlds     scrape World Championships podiums 2013-2025"
	@echo "make wa         scrape World Athletics profiles for seeded athletes"
	@echo "make validate   check the latest raw data from all sources"
	@echo "make phase1     all three scrapers, then validation"
	@echo "make load       validate, then load the latest raw files into BigQuery"
	@echo "make dbt-build  build and test all dbt models in BigQuery"

setup:
	$(PYTHON) -m pip install -r requirements.txt

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest

check: lint test

olympedia:
	$(PYTHON) -m src.scrapers.olympedia

worlds:
	$(PYTHON) -m src.scrapers.wikipedia_worlds

wa:
	$(PYTHON) -m src.scrapers.world_athletics

validate:
	$(PYTHON) -m src.validate

phase1: olympedia worlds wa validate

load: validate
	$(PYTHON) -m src.load_bigquery
dbt-build:
	cd dbt && dbt build