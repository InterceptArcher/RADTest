#!/bin/bash
set -e

# Check if we're in the backend directory or root
if [ -f "demo_main.py" ]; then
    # Already in backend directory
    exec uvicorn demo_main:app --host 0.0.0.0 --port ${PORT:-8000}
elif [ -d "backend" ]; then
    # In root directory, cd to backend
    cd backend
    exec uvicorn demo_main:app --host 0.0.0.0 --port ${PORT:-8000}
else
    echo "Error: Cannot find backend directory or demo_main.py"
    exit 1
fi
