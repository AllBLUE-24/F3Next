#!/bin/bash

# Run the backend locally on port 8000
cd "$(dirname "$0")"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload