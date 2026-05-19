.PHONY: help setup synthea overlay narratives fidelity fidelity-templated templated questions freeze dataset smoke clean reproduce fhir-validate fhir-reaggregate

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
	@echo "  fidelity     Run programmatic fidelity audit on LLM narratives"
	@echo "  fidelity-templated  Run fidelity audit on templated narratives -> reports/fidelity_audit_templated.md"
	@echo "  templated    Generate templated narratives (deterministic, no LLM)"
	@echo "  questions    Build question bank + programmatic ground truth"
	@echo "  freeze       Compute SHA-256 manifest -> data/freeze.json"
	@echo "  dataset      Full dataset build (synthea -> overlay -> narratives -> fidelity -> fidelity-templated -> templated -> questions -> freeze)"
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
	  --seed $(SEED) \
	  --reference-today 2026-04-27

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
	  --output reports/fidelity_audit_llm.md

fidelity-templated:
	$(PY) -m narratives.fidelity_audit \
	  --bundles data/fhir_bundles \
	  --narratives narratives/templated_narratives \
	  --output narratives/fidelity_reports_templated
	$(PY) -m narratives.fidelity_aggregate \
	  --reports narratives/fidelity_reports_templated \
	  --output reports/fidelity_audit_templated.md

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
	$(PY) scripts/freeze_dataset.py --output data/freeze.json --strict

dataset: synthea overlay narratives fidelity fidelity-templated templated questions freeze

SMOKE_DIR := data/fhir_bundles_smoke
SMOKE_NARR_DIR := narratives/templated_narratives_smoke
SMOKE_Q := questions/questions_smoke.jsonl

smoke:
	@echo ">>> smoke writes to $(SMOKE_DIR) / $(SMOKE_NARR_DIR) / $(SMOKE_Q) — frozen data/fhir_bundles is NOT touched"
	$(PY) -m overlay.specialty_regimen_generator \
	  --input data/synthea_base/fhir \
	  --output $(SMOKE_DIR) \
	  --seed $(SEED) --sample $(SAMPLE) \
	  --reference-today 2026-04-27
	$(PY) -m narratives.gen_templated_narrative \
	  --bundles $(SMOKE_DIR) \
	  --output $(SMOKE_NARR_DIR) \
	  --sample $(SAMPLE)
	$(PY) -m questions.gen_question_bank \
	  --bundles $(SMOKE_DIR) \
	  --output $(SMOKE_Q) \
	  --seed $(SEED) --sample $(SAMPLE)

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__ build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

reproduce:
	@if [ ! -d eval/cache ] || [ -z "$$(ls -A eval/cache 2>/dev/null)" ]; then \
	  echo ">>> WARNING: eval/cache/ is empty or missing."; \
	  echo ">>> 'make reproduce' will issue live Groq API calls and burn rate-limit budget."; \
	  echo ">>> Byte-reproducible rebuild requires the cached narrative responses."; \
	  echo ">>> Press Ctrl-C within 5 seconds to abort."; \
	  sleep 5; \
	fi
	$(MAKE) dataset

fhir-validate:
	bash scripts/setup_java_portable.sh
	bash scripts/setup_hl7_validator.sh
	$(PY) scripts/run_fhir_validation.py \
	  --bundles data/fhir_bundles \
	  --output-dir results \
	  --reports-dir reports

fhir-reaggregate:
	$(PY) scripts/reaggregate_fhir_validation.py
