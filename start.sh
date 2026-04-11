#!/usr/bin/env bash
# Start both Flask API and React frontend

set -e

echo "=========================================="
echo "Starting codeAID..."
echo "=========================================="

# Check if Python environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔧 Activating Python environment..."
    source .venv/bin/activate || true
fi

# Install Python dependencies if needed
echo "📦 Checking Python dependencies..."
pip install -q -r requirements.txt

# Install Node dependencies if needed
echo "📦 Checking Node dependencies..."
cd frontend
npm install --silent
cd ..

# Start Flask API in background
echo "🚀 Starting Flask API on http://localhost:5001..."
export FLASK_ENV=development
export FLASK_APP=api.py
python api.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 2

# Start React frontend
echo "🚀 Starting React frontend on http://localhost:3000..."
cd frontend
npm run dev
cd ..

# Handle cleanup
trap "kill $FLASK_PID" EXIT
