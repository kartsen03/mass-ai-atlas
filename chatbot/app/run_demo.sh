#!/usr/bin/env bash
# Demo: the Atlas site from this repo, with the chatbot floating on top.
# Opens http://localhost:8000/chatbot/app/demo.html  (Ctrl+C stops both servers)
set -e
cd "$(dirname "$0")/../.."
PY=python3; ST=streamlit
[ -x .venv/bin/python ] && PY=.venv/bin/python && ST=.venv/bin/streamlit

$PY -m http.server 8000 --bind 127.0.0.1 >/dev/null 2>&1 &
WEB=$!
trap 'kill $WEB 2>/dev/null' EXIT
echo "Atlas + chatbot: http://localhost:8000/chatbot/app/demo.html"
( sleep 3; open "http://localhost:8000/chatbot/app/demo.html" 2>/dev/null || true ) &
$ST run chatbot/app/main.py --server.headless true --server.port 8501 \
  --theme.base dark --theme.primaryColor "#facc15" \
  --theme.backgroundColor "#0b1020" --theme.secondaryBackgroundColor "#111827" --theme.textColor "#e5e7eb"
