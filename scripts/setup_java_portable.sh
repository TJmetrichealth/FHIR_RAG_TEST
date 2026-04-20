#!/usr/bin/env bash
# Download a portable JRE (Eclipse Temurin 21) into tools/jre/ — no admin required.
# Usage: bash scripts/setup_java_portable.sh
set -euo pipefail

TOOLS_DIR="tools"
JRE_DIR="${TOOLS_DIR}/jre"
MARKER="${JRE_DIR}/.installed"

if [[ -f "${MARKER}" ]]; then
  echo "Portable JRE already present at ${JRE_DIR}"
  "${JRE_DIR}/bin/java" -version
  exit 0
fi

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

case "${OS}" in
  MINGW*|CYGWIN*|MSYS*) PLATFORM="windows" ;;
  Darwin)               PLATFORM="mac" ;;
  Linux)                PLATFORM="linux" ;;
  *)                    echo "Unsupported OS: ${OS}" >&2; exit 1 ;;
esac

case "${ARCH}" in
  x86_64|amd64) ARCH_TAG="x64" ;;
  aarch64|arm64) ARCH_TAG="aarch64" ;;
  *)             echo "Unsupported arch: ${ARCH}" >&2; exit 1 ;;
esac

API_URL="https://api.adoptium.net/v3/binary/latest/21/ga/${PLATFORM}/${ARCH_TAG}/jre/hotspot/normal/eclipse"
ARCHIVE="${TOOLS_DIR}/jre21.zip"

mkdir -p "${TOOLS_DIR}"
echo "Downloading portable JRE 21 (${PLATFORM}/${ARCH_TAG}) — ~50 MB..."
curl -fsSL -L -o "${ARCHIVE}" "${API_URL}"

echo "Extracting..."

if [[ "${PLATFORM}" == "windows" ]]; then
  # PowerShell handles Windows ACLs and read-only flags that bash mv/rm cannot touch
  TMP_PS="tools\\jre_extract_tmp"
  ARCHIVE_WIN="$(cygpath -w "${ARCHIVE}" 2>/dev/null || echo "${ARCHIVE}")"

  powershell.exe -NoProfile -Command "
    \$ErrorActionPreference = 'Stop'
    \$tmp = '${TMP_PS}'
    \$dst = 'tools\\jre'
    # Clean up any previous partial attempts
    if (Test-Path \$tmp) { Remove-Item \$tmp -Recurse -Force }
    if (Test-Path \$dst) { Remove-Item \$dst -Recurse -Force }
    # Extract
    Expand-Archive -Path '${ARCHIVE_WIN}' -DestinationPath \$tmp -Force
    # The zip contains one top-level directory; move it to tools\jre
    \$inner = (Get-ChildItem \$tmp | Select-Object -First 1).FullName
    Move-Item \$inner \$dst
    Remove-Item \$tmp -Recurse -Force -ErrorAction SilentlyContinue
  "
else
  TMP="${TOOLS_DIR}/jre_extract_tmp"
  rm -rf "${TMP}" "${JRE_DIR}"
  mkdir -p "${TMP}"
  tar -xzf "${ARCHIVE}" -C "${TMP}"
  INNER="${TMP}/$(ls "${TMP}" | head -1)"
  mv "${INNER}" "${JRE_DIR}"
  rmdir "${TMP}"
fi

rm -f "${ARCHIVE}"
touch "${MARKER}"
echo "Portable JRE installed at ${JRE_DIR}"
"${JRE_DIR}/bin/java" -version
