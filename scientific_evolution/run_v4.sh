#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$ROOT_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}"
exec python "$ROOT_DIR/runtime/scientific_v4_clean_baseline.py" "$@"
