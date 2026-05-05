# Resuming on a CUDA-GPU machine

CPU indexing of Systems B and C on a 4-core i5-1155G7 measured ~24 min/patient,
projecting ~6 days for the remaining 375 patient-system combos. On a CUDA GPU,
BGE-large-en-v1.5 runs ~10-50× faster — full 200-patient re-index across all
three systems takes ~30-90 min. This doc is the resume runbook from tag
`w2-cpu-handoff` (commit `48e1e5f`).

## What ships in the repo (already on GitHub)

- All 200 FHIR bundles under `data/fhir_bundles/` (pushed via plain git, no LFS)
- 200 LLM-generated narratives + per-call metadata under `narratives/llm_narratives/`
- 200 templated narratives under `narratives/templated_narratives/`
- Partial eval results under `results/raw/{a,b,c}.jsonl`
- All code: systems/, eval/, narratives/, scripts/, tests/

## What does NOT ship (regenerate locally on the GPU machine)

- Chroma DBs for all three systems (`systems/{system_a,structured_naive,structured_aware}/chroma/`)
- Embedding cache (`eval/cache/embeddings/`)

Both are gitignored. The indexing scripts will rebuild them on first run.

## Setup

```bash
git clone https://github.com/TJmetrichealth/FHIR_RAG_TEST.git
cd FHIR_RAG_TEST
git checkout w2-cpu-handoff   # or main; both point to the same SHA right now

# Create venv and install deps
python -m venv .venv
source .venv/bin/activate          # PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
```

### Install CUDA-enabled torch (critical — do this BEFORE first BGE load)

Default `pip install torch` on most Linux/Windows boxes pulls a CPU-only wheel.
Replace it with the matching CUDA build for your machine. Example for CUDA 12.1:

```bash
pip uninstall -y torch
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Verify:
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Expected: True <your GPU name>
```

If `torch.cuda.is_available()` is False, **stop and fix this first** — otherwise
indexing falls back to CPU and you're back where the laptop was.

### Environment

```bash
export GROQ_API_KEY=...            # required for the answer LLM (qwen-3-32b on Groq)
# HF_HUB_OFFLINE unset on first run so BGE-large (~1.3 GB) downloads from HF;
# set HF_HUB_OFFLINE=1 on subsequent runs to keep things deterministic.
```

## Resume preconditions

```bash
ls data/fhir_bundles/*.json | wc -l       # expect 200 patient bundles (+2 metadata files = 202 total)
ls narratives/llm_narratives/*.txt | wc -l # expect 200
ls narratives/templated_narratives/*.txt | wc -l # expect 200
```

## Re-index

```bash
python scripts/index_all_bc.py            # rebuilds System B + System C, idempotent
# System A indexing is triggered lazily by eval.harness on first run
```

Expected throughput on GPU: 1-3 patients/min for B, similar for C. Watch peak GPU memory; BGE-large is small (~1.3 GB), so any consumer GPU with 6+ GB has headroom.

## Smoke check before full eval

```bash
pytest tests/smoke/                                # all four smoke tests should pass
python -m eval.harness --system b --limit 3        # 3 patients, completes in minutes
```

## Full evaluation

```bash
python -m eval.harness --system a
python -m eval.harness --system b
python -m eval.harness --system c
```

Then hand off to the statistician agent / scoring scripts.

## Notes

- The chroma DBs left on the laptop are partial (B=15/200, C=10/200) and not
  shipped. They'll be re-created from scratch on the GPU machine; deltas
  shouldn't matter because indexing is deterministic given a fixed bundle +
  embedding model.
- Embedding cache is also rebuilt from scratch. On GPU this adds ~30 min vs.
  shipping it; the simplicity of plain-git outweighs the saving.
- No LFS in the repo. Don't introduce it without a decision-log entry.
