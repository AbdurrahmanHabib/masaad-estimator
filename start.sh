#!/bin/bash
# Master Start Script for Railway
if [ "$SERVICE_TYPE" = "backend" ]; then
    cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
elif [ "$SERVICE_TYPE" = "frontend" ]; then
    cd frontend && npm start -- -p $PORT
else
    echo "Error: SERVICE_TYPE environment variable not set. Please set it to 'backend' or 'frontend'."
    exit 1
fi