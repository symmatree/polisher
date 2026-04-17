#!/usr/bin/env bash
# Purge Drive folder Gemini-from-facts/rekon and upload listed Markdown as Google Docs.
# Requires FACTS_REPO pointing at the facts git checkout (paths below are repo-relative).
set -euo pipefail

if [[ -z "${FACTS_REPO:-}" ]]; then
  echo "Set FACTS_REPO to your facts repository root, e.g.:" >&2
  echo "  export FACTS_REPO=/path/to/facts" >&2
  exit 1
fi
REPO_ROOT="$(cd "$FACTS_REPO" && pwd)"

REMOTE="${RCLONE_REMOTE:-gdrive}"
ROOT="${RCLONE_GEMINI_ROOT:-Gemini-from-facts}"
BUNDLE="rekon"
REMOTE_PATH="${REMOTE}:${ROOT}/${BUNDLE}"

mapfile -t SOURCES <<'END_SOURCES'
fables/Drones/rekon10/arm-pods.md
fables/Drones/rekon10/canopy-ops.md
fables/Drones/rekon10/central-hub.md
fables/Drones/rekon10/flight-platform.md
fables/Drones/rekon10/gps-mount.md
fables/Drones/rekon10/ground-station.md
fables/Drones/rekon10/oak-d-mount.md
fables/Drones/rekon10/README.md
fables/Drones/rekon10/rekon-design.md
fables/Datasets/experiments-house-model.md
END_SOURCES

tmpdir="$(mktemp -d)"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

command -v pandoc >/dev/null 2>&1 || { echo "pandoc not found; install pandoc" >&2; exit 1; }
command -v rclone >/dev/null 2>&1 || { echo "rclone not found; install rclone and configure ${REMOTE}" >&2; exit 1; }

echo "Purging ${REMOTE_PATH} ..."
rclone purge "${REMOTE_PATH}" 2>/dev/null || true
rclone mkdir "${REMOTE_PATH}"

for rel in "${SOURCES[@]}"; do
  src="${REPO_ROOT}/${rel}"
  if [[ ! -f "$src" ]]; then
    echo "Missing: ${rel}" >&2
    exit 1
  fi
  base="$(basename "$rel" .md)"
  docx="${tmpdir}/${base}.docx"
  echo "Converting ${rel} ..."
  pandoc "$src" -o "$docx"
  echo "Uploading ${base}.docx as Google Doc ..."
  rclone copy "$docx" "${REMOTE_PATH}" --drive-import-formats docx
done

echo "Done. Open Drive folder: ${ROOT}/${BUNDLE}"
