#!/bin/bash
# Script to run NutriSolver

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 could not be found. Please install Python 3."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Activating virtual environment and installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the application
echo "Starting NutriSolver..."
python3 -m streamlit run app.py
