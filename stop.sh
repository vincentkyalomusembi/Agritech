#!/usr/bin/env bash
set -euo pipefail

# Stop script for Agritech: kills uvicorn/ngrok and clears ports used by the app.
cd "$(dirname "$0")"

echo "Stopping Agritech services..."

# Kill by common process names
pkill -f "uvicorn app:app" || true
pkill -f "python -m uvicorn" || true
pkill -f ngrok || true

# Kill any process listening on ports we use
if command -v lsof >/dev/null 2>&1; then
  lsof -ti:8000 | xargs -r kill -9 || true
  lsof -ti:8001 | xargs -r kill -9 || true
  lsof -ti:4040 | xargs -r kill -9 || true
fi

sleep 1

echo "Remaining listeners (if any):"
if command -v lsof >/dev/null 2>&1; then
  lsof -i :8000 -sTCP:LISTEN || true
  lsof -i :4040 -sTCP:LISTEN || true
fi

echo "Stopped."
