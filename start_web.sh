#!/bin/bash
echo "Starting OURE Web API on port 8000..."
.venv/bin/uvicorn oure.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting OURE Streamlit Dashboard on port 8501..."
.venv/bin/streamlit run oure/dashboard/app.py &
DASH_PID=$!

echo "Web components are running."
echo "API Docs: http://localhost:8000/docs"
echo "Dashboard: http://localhost:8501"

# Wait for user to press Ctrl+C
trap "echo 'Shutting down...'; kill $API_PID; kill $DASH_PID; exit" INT
wait
