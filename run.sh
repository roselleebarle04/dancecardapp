#!/bin/bash

echo "Starting Dance Card app..."
echo "Server will be available at http://localhost:8000"
echo ""

uv run hypercorn main:app --bind "0.0.0.0:8000" --reload
