#!/bin/bash
set -e

echo "=== Manuscript Checker Setup ==="
echo ""

# Install Python dependencies
echo "Installing Python packages..."
pip3 install -r requirements.txt

# Download spaCy language model
echo ""
echo "Downloading spaCy English model (needed for character analysis)..."
python3 -m spacy download en_core_web_sm

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Start the app with:  python3 app.py"
echo "Then open:           http://localhost:5000"
