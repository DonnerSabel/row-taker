#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q src
ruff check .
ruff format --check .
mypy
pytest -q
echo "OK"
