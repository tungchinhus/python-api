#!/bin/bash

echo "Starting Python Vectorize API..."
echo ""

# Kiểm tra virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Kiểm tra dependencies
echo "Checking dependencies..."
if ! pip show flask &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Chạy server
echo "Starting server on http://localhost:5005..."
echo "Press Ctrl+C to stop"
echo ""
python app.py
