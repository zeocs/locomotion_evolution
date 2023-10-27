#!/usr/bin/env bash

set -e

USE_VENV=1
INSTALL_EDITABLE=0


# ----------- Installation Routines -----------

# Create and activate Python virtual environment
if [[ $USE_VENV -eq 1 ]]; then
	python3 -m venv .venv
	source .venv/bin/activate
fi

# Install project
if [[ $INSTALL_EDITABLE -eq 1 ]]; then
	pip install -e .
else
	pip install .
fi

