#!/usr/bin/env bash

set -e


# Activate Python virtual environment
if [ -a ".venv" ]; then
	source .venv/bin/activate
fi

./src/main.py "$@"

