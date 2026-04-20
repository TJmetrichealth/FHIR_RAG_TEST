#!/usr/bin/env bash
# Generate a deterministic Synthea population.
# Usage: bash scripts/generate_synthea.sh [SEED] [POPULATION]
set -euo pipefail

SEED="${1:-20260427}"
POP="${2:-200}"
STATE="${SYNTHEA_STATE:-Massachusetts}"
OUT_DIR="data/synthea_base"
JAR_PATH="tools/synthea-with-dependencies.jar"

if [[ ! -f "${JAR_PATH}" ]]; then
  echo "Synthea JAR missing. Run: bash scripts/setup_synthea.sh" >&2
  exit 1
fi

# Use portable JRE if system java isn't available
if ! command -v java >/dev/null 2>&1; then
  if [[ -x "tools/jre/bin/java" ]]; then
    export PATH="$(pwd)/tools/jre/bin:${PATH}"
    echo "Using portable JRE at tools/jre/"
  else
    echo "ERROR: java not found. Run: bash scripts/setup_java_portable.sh" >&2
    exit 1
  fi
fi

mkdir -p "${OUT_DIR}"

echo "Generating ${POP} patients with seed ${SEED} (state=${STATE})..."
java -jar "${JAR_PATH}" \
  -s "${SEED}" \
  -cs "${SEED}" \
  -r "${SEED}" \
  -p "${POP}" \
  --exporter.baseDirectory="${OUT_DIR}" \
  --exporter.fhir.export=true \
  --exporter.fhir.use_us_core_ig=false \
  --exporter.hospital.fhir.export=false \
  --exporter.practitioner.fhir.export=false \
  --exporter.ccda.export=false \
  --exporter.csv.export=false \
  --exporter.text.export=false \
  --generate.only_alive_patients=true \
  "${STATE}"

echo "Generation complete. Output: ${OUT_DIR}/fhir"
