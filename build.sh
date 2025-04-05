#!/bin/bash
set -e  # Exit on error

# Upgrade pip first
python -m pip install --upgrade pip

# Install dependencies with resolution
pip install --no-cache-dir -r requirements.txt

# Verify installations
pip list