#!/bin/bash
set -e  # Exit on error

# Show Python and pip versions
python --version
pip --version

# Upgrade pip and setuptools first
python -m pip install --upgrade pip setuptools wheel

# Install dependencies with exact versions
pip install --no-cache-dir --force-reinstall -r requirements.txt

# Verify installations
pip list