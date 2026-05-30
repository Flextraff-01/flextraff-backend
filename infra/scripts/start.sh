#!/bin/bash
# Render startup script for FlexTraff Backend

echo "Starting FlexTraff Backend on Render..."

# Set default port if not provided
export PORT=${PORT:-10000}

echo "Port set to: $PORT"
echo "Python path: $PYTHONPATH"

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1