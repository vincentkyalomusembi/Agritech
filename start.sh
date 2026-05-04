#!/usr/bin/env bash
set -euo pipefail

# Start script for Agritech: activates venv, starts uvicorn and ngrok.
# Usage: ./start.sh

cd "$(dirname "$0")"

# Load environment variables from .env if present
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# Activate virtual environment
if [ -f env/bin/activate ]; then
  # shellcheck disable=SC1090
  source env/bin/activate
else
  echo "Virtualenv not found at env/. Create it with: python -m venv env && source env/bin/activate && pip install -r requirements.txt"
  exit 1
fi

mkdir -p logs

echo "Starting uvicorn (app:app) on port 8000..."
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
UVICORN_PID=$!
echo "uvicorn pid=${UVICORN_PID}"

if [ -z "${NGROK_AUTHTOKEN:-}" ]; then
  echo "NGROK_AUTHTOKEN not set in .env — skipping ngrok. Set NGROK_AUTHTOKEN in .env to enable public tunnel."
else
  echo "Starting ngrok tunnel on port 8000..."
  nohup ngrok http 8000 --log=stdout > logs/ngrok.log 2>&1 &
  NGROK_PID=$!
  echo "ngrok pid=${NGROK_PID}"
fi

echo "Services started. Logs: logs/uvicorn.log logs/ngrok.log"

# Try to show public ngrok URL if available
sleep 2
if command -v curl >/dev/null 2>&1; then
  if curl --silent http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; then
    echo "Public ngrok URL:"
    curl --silent http://127.0.0.1:4040/api/tunnels | python -c 'import sys,json;data=json.load(sys.stdin); print(data.get("tunnels")[0].get("public_url") if data.get("tunnels") else "")'
  fi
fi

echo "Done. To stop: kill $UVICORN_PID ${NGROK_PID:-}" 
