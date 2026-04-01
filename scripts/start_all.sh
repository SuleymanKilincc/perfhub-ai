#!/bin/bash

echo "========================================"
echo "PerfHub AI - Starting All Services"
echo "========================================"
echo ""

echo "[1/2] Starting Backend..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

sleep 3

echo "[2/2] Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "Services started!"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services..."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

wait
