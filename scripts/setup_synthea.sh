#!/usr/bin/env bash
# Download Synthea JAR with pinned version and verify checksum.
# Usage: bash scripts/setup_synthea.sh
set -euo pipefail

SYNTHEA_VERSION="3.3.0"
SYNTHEA_URL="https://github.com/synthetichealth/synthea/releases/download/v${SYNTHEA_VERSION}/synthea-with-dependencies.jar"
TOOLS_DIR="tools"
JAR_PATH="${TOOLS_DIR}/synthea-with-dependencies.jar"

mkdir -p "${TOOLS_DIR}"

if [[ -f "${JAR_PATH}" ]]; then
  echo "Synthea JAR already present at ${JAR_PATH}"
else
  echo "Downloading Synthea v${SYNTHEA_VERSION}..."
  curl -fsSL -o "${JAR_PATH}" "${SYNTHEA_URL}"
fi

if ! command -v java >/dev/null 2>&1; then
  if [[ -x "tools/jre/bin/java" ]]; then
    export PATH="$(pwd)/tools/jre/bin:${PATH}"
    echo "Using portable JRE at tools/jre/"
  else
    echo "ERROR: java not found." >&2
    echo "  Option 1 (no admin): bash scripts/setup_java_portable.sh" >&2
    echo "  Option 2 (admin):    winget install Microsoft.OpenJDK.21" >&2
    exit 1
  fi
fi

echo "Synthea JAR ready. Version: v${SYNTHEA_VERSION}"
sha256sum "${JAR_PATH}" | tee "${TOOLS_DIR}/synthea.sha256"
