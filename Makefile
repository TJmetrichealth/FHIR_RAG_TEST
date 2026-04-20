.PHONY: help setup synthea overlay narratives fidelity templated questions freeze dataset smoke clean reproduce

PY := python
SEED := 20260427
POP := 200
SAMPLE ?= 10

help:
	@echo "Targets:"
	@echo "  setup        Install package in editable mode with dev extras"
	@echo "  synthea      Download Synthea JAR and generate raw patients"
	@echo "  overlay      Apply specialty-regimen overlay to Synthea bundles"
	@echo "  narratives   Generate LLM narratives via Groq (needs GROQ_API_KEY)"
	@echo "  fidelity     Run programmatic fidelity audit on narratives"
	@echo "  templated    Generate templated narratives (deterministic, no LLM)"
	@echo "  questions    Build question bank + programmatic ground truth"
	@echo "  freeze       Compute SHA-256 manifest → data/freeze.json"
	@echo "  dataset      Full Week 1 pipeline (synthea → overlay → narratives → fidelity → templated → questions → freeze)"
	@echo "  smoke        Run on SAMPLE=10 patients for a quick end-to-end check"
	@echo "  clean        Remove caches and build artefacts (keeps data/)"
	@echo "  reproduce    Full dataset rebuild from fixed seeds (uses cached LLM calls if present)"

setup:
	pip install --upgrade pip
	pip install -e ".[dev]"

synthea:
	bash scripts/setup_synthea.sh
	bash scripts/generate_synthea.sh $(SEED) $(POP)

overlay:
	$(PY) -m overlay.specialty_regimen_generator \
	  --input data/synthea_base/fhir \
	  --output data/fhir_bundles \
	  --seed $(SEED)

narratives:
	$(PY) -m narratives.gen_llm_narrative \
	  --bundles data/fhir_bundles \
	  --output narratives/llm_narratives

fidelity:
	$(PY) -m narratives.fidelity_audit \
	  --bundles data/fhir_bundles \
	  --narratives narratives/llm_narratives \
	  --output narratives/fidelity_reports
	$(PY) -m narratives.fidelity_aggregate \
	  --reports narratives/fidelity_reports \
	  --output reports/fidelity_audit.md

templated:
	$(PY) -m narratives.gen_templated_narrative \
	  --bundles data/fhir_bundles \
	  --output narratives/templated_narratives

questions:
	$(PY) -m questions.gen_question_bank \
	  --bundles data/fhir_bundles \
	  --output questions/questions.jsonl \
	  --seed $(SEED)

freeze:
	$(PY) scripts/freeze_dataset.py --output data/freeze.json

dataset: synthea overlay narratives fidelity templated questions freeze

smoke:
	$(PY) -m overlay.specialty_regimen_generator \
	  --input data/synthea_base/fhir \
	  --output data/fhir_bundles \
	  --seed $(SEED) --sample $(SAMPLE)
	$(PY) -m narratives.gen_templated_narrative \
	  --bundles data/fhir_bundles \
	  --output narratives/templated_narratives \
	  --sample $(SAMPLE)
	$(PY) -m questions.gen_question_bank \
	  --bundles data/fhir_bundles \
	  --output questions/questions.jsonl \
	  --seed $(SEED) --sample $(SAMPLE)

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__ build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

reproduce: dataset
