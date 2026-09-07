#!/bin/bash
# Runs the test suite in the project virtualenv.
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./run.sh first to create .venv" >&2; exit 1; }
exec .venv/bin/python -m tests.run_tests "$@"
