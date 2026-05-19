"""Single source of truth for every tunable hyperparameter.

All retrieval systems (A, B, C), the embedding client, and the eval harness
import from here. There are NO magic numbers in system code.

Hyperparameters are locked. Any change here requires a tagged release.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Project root (absolute so imports work from any cwd)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
ANSWER_LLM_MODEL: str = "qwen/qwen3-32b"         # Qwen 3 32B via Groq free tier
# NOTE: Groq's public model ID for Qwen 3 32B verified 2026-04-21.
# If Groq renames this, update here ONLY.
EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"  # local via sentence-transformers
NARRATIVE_LLM_MODEL: str = "llama-3.3-70b-versatile"  # narrative gen only

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K: int = 5                  # k=5
CHUNK_TOKENS: int = 500         # chunk=500 tokens
CHUNK_OVERLAP_TOKENS: int = 50  # 10% overlap

# ---------------------------------------------------------------------------
# Answer LLM generation
# ---------------------------------------------------------------------------
ANSWER_TEMPERATURE: float = 0.0   # single run, temperature 0
ANSWER_MAX_TOKENS: int = 512       # max tokens for answer generation
# Seed: Groq's chat completions API does not expose a deterministic seed
# parameter for open-weights models at free tier.  Determinism is provided
# by temperature=0 + caching (every call with the same prompt returns the
# cached response).  This is a Groq API constraint, not a choice.

# ---------------------------------------------------------------------------
# Answer-LLM system prompt (held constant across A, B, C)
# ---------------------------------------------------------------------------
ANSWER_SYSTEM_PROMPT: str = (
    "You are a clinical data assistant answering questions about a patient's "
    "specialty medication regimen. Answer concisely and precisely based only "
    "on the context provided. If the answer is not present in the context, "
    "respond with exactly: N/A"
)

# Answer user-prompt template.  {context} and {question} are filled at
# call time by the answer wrapper.
ANSWER_USER_PROMPT_TEMPLATE: str = (
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)

# ---------------------------------------------------------------------------
# Groq rate-limit parameters
# Developer-plan ceilings for qwen/qwen3-32b: 1000 RPM, 300K TPM.
# Local bucket is set 15-20% below the ceiling so server-side 429 is rare.
# ---------------------------------------------------------------------------
GROQ_RPM: int = 800              # 80% of Developer-plan 1000 RPM
GROQ_TPM: int = 250_000          # 83% of Developer-plan 300K TPM
GROQ_MAX_RETRIES: int = 6        # retry attempts on 429
GROQ_BACKOFF_BASE: float = 2.0   # seconds
GROQ_BACKOFF_MAX: float = 60.0   # seconds

# ---------------------------------------------------------------------------
# Cache directories (gitignored per .gitignore; must be preserved locally)
# ---------------------------------------------------------------------------
CACHE_ROOT: Path = PROJECT_ROOT / "eval" / "cache"
ANSWER_CACHE_DIR: Path = CACHE_ROOT / "answers"
EMBEDDING_CACHE_DIR: Path = CACHE_ROOT / "embeddings"

# ---------------------------------------------------------------------------
# Data paths (data/ is frozen — do not write here)
# ---------------------------------------------------------------------------
FHIR_BUNDLES_DIR: Path = PROJECT_ROOT / "data" / "fhir_bundles"
LLM_NARRATIVES_DIR: Path = PROJECT_ROOT / "narratives" / "llm_narratives"
TEMPLATED_NARRATIVES_DIR: Path = PROJECT_ROOT / "narratives" / "templated_narratives"
QUESTIONS_PATH: Path = PROJECT_ROOT / "questions" / "questions.jsonl"

# ---------------------------------------------------------------------------
# Results directory
# ---------------------------------------------------------------------------
RESULTS_RAW_DIR: Path = PROJECT_ROOT / "results" / "raw"
