#!/bin/bash
set -e

# Clean install
pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements.txt

# Verify installations
pip list