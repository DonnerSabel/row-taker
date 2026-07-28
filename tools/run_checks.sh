#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q src
ruff check .
ruff format --check .
pytest -q
echo "OK"
