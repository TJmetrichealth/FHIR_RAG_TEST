# Zenodo Release Tutorial — FHIR-RAG

Two Zenodo deposits, two different workflows. Read both sections before publishing either.

| Deposit | What gets archived | License | Trigger | Metadata source |
|---|---|---|---|---|
| **§1 Code** | The GitHub repo at a tagged release (snapshotted) | Apache-2.0 | A GitHub release | [`.zenodo.json`](../../.zenodo.json) at repo root |
| **§2 Dataset** | 200 patients + 13,800 questions + freeze manifests | CC-BY-4.0 | Manual upload to Zenodo | [`docs/zenodo/dataset_metadata.json`](dataset_metadata.json) (copy-paste template) |

Mint the code deposit **first**. The dataset deposit links to the code deposit's DOI in its `related_identifiers`.

---

## §1 — Code deposit (auto-archive via GitHub release)

Zenodo's GitHub integration archives any GitHub release of a linked repo and reads metadata from `.zenodo.json` at the repo root. Once linked, every future release auto-mints a new DOI in the same Concept DOI family.

### Prerequisites

1. The repo is public on GitHub (private repos are not eligible for the free Zenodo-GitHub integration).
2. You have a Zenodo account at https://zenodo.org (sign in with ORCID is easiest).
3. The arXiv preprint URL exists or you have a plan to update the DOI metadata after submission.

### Step 1: Link GitHub to Zenodo (one-time)

1. Sign in at https://zenodo.org.
2. Go to **Account → GitHub** (or directly: https://zenodo.org/account/settings/github/).
3. Click **Authorize Zenodo** and grant access to your GitHub account.
4. Find the FHIR-RAG repo in the list and flip its toggle to **ON**.

From this point on, every GitHub release of the repo creates a Zenodo deposit automatically.

### Step 2: Update placeholders in `.zenodo.json`

Before tagging the release, edit `.zenodo.json` and replace:

- `"identifier": "https://arxiv.org/abs/PLACEHOLDER"` → the real arXiv URL (e.g. `https://arxiv.org/abs/2605.XXXXX`).
- `"publication_date": "2026-05-17"` → bump to the actual release date if it changes.

If you don't yet have the arXiv URL, you can remove the `related_identifiers` block entirely and add it later via the Zenodo web UI on the deposit detail page (Edit → Save). The DOI does not change; only metadata is updated.

### Step 3: Tag and release on GitHub

```bash
# Option A: command-line (assumes you have a `gh` auth)
git tag -a v0.1.0-arxiv -m "Initial arXiv submission release"
git push origin v0.1.0-arxiv
gh release create v0.1.0-arxiv --title "v0.1.0-arxiv (Round 2 revision)" \
    --notes-file docs/zenodo/release_notes.md
```

```bash
# Option B: web UI
# Visit https://github.com/<USER>/<REPO>/releases/new
# Choose tag v0.1.0-arxiv, write release notes, click Publish release.
```

Tag-name convention used in this repo: `v<MAJOR>.<MINOR>.<PATCH>-<context>`. The first arXiv-tied release is `v0.1.0-arxiv`. Subsequent revisions follow semver. Internal data/results freezes use separate tags (`dataset-freeze-v1`, `results-freeze-v1`, `results-freeze-v2`) and are not Zenodo releases.

### Step 4: Verify the Zenodo deposit

Within ~1 minute of the GitHub release, check **https://zenodo.org/account/settings/github/** — the repo should show a fresh deposit with status `Published`. Click through to:

- Confirm the title, description, creators, license, keywords match `.zenodo.json`.
- Copy the **Concept DOI** (e.g. `10.5281/zenodo.12345678`). This is the DOI that resolves to the latest version regardless of release.
- Copy the **Version DOI** (e.g. `10.5281/zenodo.12345679`). This is the immutable DOI for v0.1.0-arxiv specifically.

Add both to:

- `paper/sections/07_reproducibility.tex` (replace the Zenodo placeholder).
- `README.md` if it has a "Cite this work" block.

### Step 5: Future releases

Just create a new GitHub release. Zenodo will:

1. Create a new Version DOI under the same Concept DOI.
2. Re-read `.zenodo.json` for updated metadata.
3. Archive the new repo state.

If you change `.zenodo.json` between releases (e.g. add an author, fix a typo), the changes only take effect from the next release onward; the existing Version DOI's metadata is frozen unless you edit it manually in the Zenodo UI.

---

## §2 — Dataset deposit (manual upload, CC-BY-4.0)

This is **separate from §1** and depends on:

1. Employer IP clearance for releasing the synthetic dataset.
2. The code deposit (§1) being live, so the dataset can link to its DOI.

### Step 0: Verify clearance

Confirm in writing (email, ticket, signed memo) that the 200-patient synthetic dataset and the 13,800-question bank can be released under CC-BY-4.0. The dataset is fully synthetic and contains no PHI, but employer review of synthetic-data IP terms is the gate noted in [`paper/sections/06_limitations.tex`](../../paper/sections/06_limitations.tex) and [`paper/sections/07_reproducibility.tex`](../../paper/sections/07_reproducibility.tex). Do not upload before clearance.

### Step 1: Stage the dataset bundle locally

The exact file layout is in `docs/zenodo/dataset_metadata.json` under `_files_planned_for_upload`. As of release-tag `dataset-freeze-v1` the canonical files are:

```text
data/freeze.json
data/freeze_v2.json
data/patients/*.json              (200 FHIR R4B bundles)
data/narratives_llm/*.txt         (200 LLM-generated narratives)
data/narratives_templated/*.txt   (200 deterministic templated narratives)
data/questions.jsonl              (13,800 questions with ground truth)
```

Bundle these into a single archive for the deposit, e.g.:

```powershell
# from repo root
$stage = "dist/zenodo_dataset_v1"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item data\freeze.json, data\freeze_v2.json $stage
Copy-Item -Recurse data\patients,
                   data\narratives_llm,
                   data\narratives_templated $stage
Copy-Item data\questions.jsonl $stage
Copy-Item LICENSE-CC-BY-4.0 $stage\LICENSE   # see Step 2
Copy-Item docs\zenodo\DATASET_README.md $stage\README.md   # see Step 2

Compress-Archive -Path $stage\* `
                 -DestinationPath dist\fhir_rag_dataset_v1.zip `
                 -CompressionLevel Optimal
```

Record the resulting zip's SHA-256 for the deposit description:

```powershell
Get-FileHash dist\fhir_rag_dataset_v1.zip -Algorithm SHA256
```

### Step 2: Write the dataset-only README and LICENSE

The dataset deposit must be **standalone-comprehensible** — a researcher who downloads the zip without ever visiting the GitHub repo needs to understand what it is.

Minimum contents for `dist/zenodo_dataset_v1/README.md`:

- Citation block (BibTeX of the arXiv preprint + Zenodo Concept DOI from §1).
- File-by-file description of what each subdirectory contains.
- The two SHA-256 freeze manifests printed inline (`4d0da93e...` and `2358e828...`).
- Reuse terms: CC-BY-4.0 summary plus a one-paragraph attribution requirement.
- Link to the code-deposit Zenodo DOI for reproducibility.
- "No PHI; synthetic only" disclosure.

For `dist/zenodo_dataset_v1/LICENSE`, drop in the full CC-BY-4.0 legal code from https://creativecommons.org/licenses/by/4.0/legalcode.txt.

### Step 3: Update placeholders in `dataset_metadata.json`

Edit [`docs/zenodo/dataset_metadata.json`](dataset_metadata.json) and replace:

- `"publication_date": "TBD-FILL-IN-AT-UPLOAD"` → today's date in `YYYY-MM-DD`.
- `"identifier": "https://arxiv.org/abs/PLACEHOLDER"` → the real arXiv URL.
- `"identifier": "10.5281/zenodo.PLACEHOLDER_CODE_DOI"` → the Concept DOI minted in §1 Step 4.

Work through the `_pre_upload_checklist` array; every item must be ticked.

### Step 4: Create the deposit

1. Go to https://zenodo.org/uploads/new.
2. Upload `dist/fhir_rag_dataset_v1.zip` (one big file is fine; Zenodo supports up to 50 GB).
3. In the metadata form, copy values from `dataset_metadata.json`:
   - Resource type: **Dataset**.
   - Title, creators, ORCID, affiliation, description, keywords, license (CC-BY-4.0), publication date.
   - Related identifiers: arXiv URL (`isSupplementTo`), code-archive Concept DOI (`isSupplementedBy`).
   - Notes: the no-PHI / synthetic disclosure.
4. Save as draft. Preview. If it looks right, click **Publish** (this mints the DOI and is irreversible for that version — you can publish new versions later).
5. Copy the dataset's Concept DOI and Version DOI.

### Step 5: Cross-link from the code deposit

Once the dataset deposit is live, go back to the code deposit (§1) and add a reciprocal `related_identifiers` entry:

```json
{
  "identifier": "10.5281/zenodo.DATASET_DOI_HERE",
  "relation": "isSupplementedBy",
  "resource_type": "dataset",
  "scheme": "doi"
}
```

You can edit this on the Zenodo deposit page directly (the published DOI doesn't change; just the metadata gets updated). Alternatively, add it to `.zenodo.json` so the next code release picks it up automatically.

### Step 6: Update the paper

In `paper/sections/07_reproducibility.tex`, the dataset-DOI placeholder block can now be filled in. Re-build the Overleaf zip ([`docs/zenodo/`](.) is not in the bundle — the bundle is at [`dist/overleaf_fhir_rag_v2/`](../../dist/overleaf_fhir_rag_v2/)) and re-upload to Overleaf.

---

## §3 — Maintenance and gotchas

### Versioning vs new deposits

- **Same Concept DOI, new Version DOI** (✓ what you want): use Zenodo's "New version" workflow on an existing deposit. For the code, this happens automatically on each GitHub release. For the dataset, click "New version" on the deposit page and upload an updated zip.
- **New Concept DOI** (✗ usually a mistake): only do this if the dataset semantics genuinely change and a fresh identity is warranted (e.g., a non-Synthea real-data follow-up cohort).

### The `.zenodo.json` schema

Authoritative reference: https://developers.zenodo.org/#representation. Common pitfalls in this repo's metadata files:

- `license` must be a SPDX identifier (e.g., `Apache-2.0`, `CC-BY-4.0`, `MIT`) — not free-text like "Apache License v2".
- `creators[].name` must be `"Last, First"`. Listing `"Tirthesh Jani"` instead of `"Jani, Tirthesh"` will display incorrectly.
- `upload_type` for code is `software`; for the dataset deposit it is `dataset`. Do not use `publication` for either of these — that's for the arXiv preprint itself, which arXiv handles, not Zenodo.
- `keywords` is a free-tag list, not a controlled vocabulary; choose the ones a researcher would actually search for.

### What does NOT belong in the code deposit

- Cache files in `eval/cache*/` (gitignored anyway).
- `results/raw_large/*.jsonl` and the other raw JSONLs (gitignored; too large for GitHub).
- The synthetic dataset itself (separate deposit, separate license).
- Any `__pycache__/`, `.venv/`, model weights, or local Groq logs.

`.gitignore` already excludes these. Zenodo archives whatever GitHub serves at the release tag, so a clean repo state is the right pre-release check.

### What does NOT belong in the dataset deposit

- Source code (separate deposit).
- Anything from `paper/`, `analysis/`, `figures/`, or `eval/` (those are code-archive territory).
- Anything generated by an LLM at evaluation time (cached answer JSONLs); those are reproducibility artifacts, not data.

### If the GitHub-Zenodo sync breaks

1. Check https://zenodo.org/account/settings/github/ — the repo should be ON and the latest release should show a green checkmark.
2. If the release didn't trigger Zenodo, click "Refresh" on the GitHub settings page in Zenodo. If still nothing, delete the GitHub release and re-create it (the Zenodo deposit will be created from scratch — no risk to existing deposits).
3. Common cause: a malformed `.zenodo.json`. Validate it with `python -m json.tool .zenodo.json` (or any JSON linter) before pushing the tag.

### Validate JSON before release

```bash
python -m json.tool .zenodo.json > /dev/null && echo "code metadata OK"
python -m json.tool docs/zenodo/dataset_metadata.json > /dev/null && echo "dataset metadata OK"
```

Or in PowerShell:

```powershell
Get-Content .zenodo.json | ConvertFrom-Json | Out-Null; "code metadata OK"
Get-Content docs\zenodo\dataset_metadata.json | ConvertFrom-Json | Out-Null; "dataset metadata OK"
```

If `ConvertFrom-Json` errors, the file has a syntax issue. Fix before tagging.

---

## §4 — Quick reference

| Action | File or URL |
|---|---|
| Edit code-archive metadata | [`.zenodo.json`](../../.zenodo.json) |
| Edit dataset-deposit template | [`docs/zenodo/dataset_metadata.json`](dataset_metadata.json) |
| Link GitHub repo to Zenodo | https://zenodo.org/account/settings/github/ |
| Create a new dataset deposit | https://zenodo.org/uploads/new |
| Zenodo metadata schema | https://developers.zenodo.org/#representation |
| SPDX license identifiers | https://spdx.org/licenses/ |
| CC-BY-4.0 license text | https://creativecommons.org/licenses/by/4.0/legalcode.txt |
| arXiv URL placeholder (replace) | `https://arxiv.org/abs/PLACEHOLDER` |
| Code DOI placeholder (replace) | `10.5281/zenodo.PLACEHOLDER_CODE_DOI` |
