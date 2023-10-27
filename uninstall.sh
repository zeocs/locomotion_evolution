#!/usr/bin/env bash

if [ -a ".venv" ]; then
	# Activate Python virtual environment
	source .venv/bin/activate
fi

pip uninstall -y locomotion_evolution

rm -rf .venv
rm -rf locomotion_evolution.egg-info
rm -rf build
