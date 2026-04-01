#!/bin/bash

echo "========================================"
echo "PerfHub AI - Installing Dependencies"
echo "========================================"
echo ""

echo "[1/3] Installing Python packages..."
pip install fastapi uvicorn google-genai python-dotenv pydantic wmi psutil GPUtil requests

echo ""
echo "[2/3] Installing Frontend packages..."
cd frontend
npm install
cd ..

echo ""
echo "[3/3] Initializing database..."
python scripts/populate_db.py

echo ""
echo "========================================"
echo "Installation complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Create .env file with your GEMINI_API_KEY"
echo "2. Run: python scripts/check_setup.py"
echo "3. Start app: ./scripts/start_all.sh"
echo ""
