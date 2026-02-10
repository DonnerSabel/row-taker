#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q src
ruff check .
pytest -q
echo "OK"
