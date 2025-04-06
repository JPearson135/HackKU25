#!/bin/bash
set -e

# Clean install
pip install --upgrade pip
pip install --force-reinstall -r requirements.txt

# Verify installations
pip list