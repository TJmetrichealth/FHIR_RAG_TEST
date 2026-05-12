#!/usr/bin/env bash
# Download the HL7 official FHIR Validator CLI jar into tools/hl7-validator/ -- no admin required.
# Pins version 6.5.18 (stable release 2025-12; check https://github.com/hapifhir/org.hl7.fhir.core/releases
# for newer stable tags and update VERSION and DOWNLOAD_URL accordingly).
# Usage: bash scripts/setup_hl7_validator.sh
set -euo pipefail

TOOLS_DIR="tools"
HL7_DIR="${TOOLS_DIR}/hl7-validator"
MARKER="${HL7_DIR}/.installed"
JAR="${HL7_DIR}/validator_cli.jar"
SHA_FILE="${HL7_DIR}/validator_cli.sha256"

# Pinned version -- update both variables together
VERSION="6.5.18"
DOWNLOAD_URL="https://github.com/hapifhir/org.hl7.fhir.core/releases/download/${VERSION}/validator_cli.jar"

if [[ -f "${MARKER}" ]]; then
  echo "HL7 FHIR Validator already present at ${HL7_DIR}"
  # Verify the jar still runs
  if command -v java &>/dev/null; then
    java -jar "${JAR}" -version 2>&1 | head -3 || true
  elif [[ -f "tools/jre/bin/java" ]]; then
    tools/jre/bin/java -jar "${JAR}" -version 2>&1 | head -3 || true
  elif [[ -f "tools/jre/bin/java.exe" ]]; then
    tools/jre/bin/java.exe -jar "${JAR}" -version 2>&1 | head -3 || true
  fi
  exit 0
fi

mkdir -p "${HL7_DIR}"

echo "Downloading HL7 FHIR Validator ${VERSION} -- ~120 MB..."
curl -fsSL -L -o "${JAR}" "${DOWNLOAD_URL}"

# Compute SHA-256 cross-platform
OS="$(uname -s)"
case "${OS}" in
  Linux)
    COMPUTED_SHA="$(sha256sum "${JAR}" | awk '{print $1}')"
    ;;
  Darwin)
    COMPUTED_SHA="$(shasum -a 256 "${JAR}" | awk '{print $1}')"
    ;;
  MINGW*|CYGWIN*|MSYS*)
    # Use PowerShell for SHA-256 on Windows Git Bash / MSYS2
    JAR_WIN="$(cygpath -w "${JAR}" 2>/dev/null || echo "${JAR}")"
    COMPUTED_SHA="$(powershell.exe -NoProfile -Command \
      "(Get-FileHash '${JAR_WIN}' -Algorithm SHA256).Hash.ToLower()" 2>/dev/null | tr -d '[:space:]')"
    ;;
  *)
    echo "WARNING: unsupported OS '${OS}' for SHA-256 computation; skipping pin verification." >&2
    COMPUTED_SHA=""
    ;;
esac

if [[ -n "${COMPUTED_SHA}" ]]; then
  echo "Computed SHA-256: ${COMPUTED_SHA}"

  # Read existing pin (skip comment lines)
  STORED_SHA=""
  if [[ -f "${SHA_FILE}" ]]; then
    STORED_SHA="$(grep -v '^#' "${SHA_FILE}" | tr -d '[:space:]' || true)"
  fi

  if [[ -n "${STORED_SHA}" ]]; then
    # Pin exists -- verify
    if [[ "${COMPUTED_SHA}" != "${STORED_SHA}" ]]; then
      echo "PIN MISMATCH: expected ${STORED_SHA} but got ${COMPUTED_SHA}" >&2
      echo "Remove ${JAR} and ${SHA_FILE} to re-download with a new pin." >&2
      rm -f "${JAR}"
      exit 1
    fi
    echo "SHA-256 verified against pin."
  else
    # No pin yet -- write the initial pin
    # Preserve any leading comment lines already in the file
    if [[ -f "${SHA_FILE}" ]]; then
      COMMENTS="$(grep '^#' "${SHA_FILE}" || true)"
    else
      COMMENTS=""
    fi
    {
      [[ -n "${COMMENTS}" ]] && echo "${COMMENTS}"
      echo "${COMPUTED_SHA}"
    } > "${SHA_FILE}"
    echo "INITIAL PIN: SHA-256 written to ${SHA_FILE}; commit this file to lock the version."
  fi
fi

touch "${MARKER}"
echo "HL7 FHIR Validator ${VERSION} installed at ${HL7_DIR}"
