#!/usr/bin/env bash
# ─────────────────────────────────────────────────────
#  Nexonic — backend indítása
#  Használat: ./start.sh
# ─────────────────────────────────────────────────────
set -e

PORT=${PORT:-5000}
HOST=${HOST:-0.0.0.0}

echo ""
echo "  ●  NEXONIC — Knowledge Preservation System"
echo "  ──────────────────────────────────────────"
echo "  Backend:  http://localhost:${PORT}"
echo "  Admin:    http://localhost:${PORT}/admin"
echo "            User: admin / Jelszó: admin"
echo "  SQL mappa: ./sql/"
echo "  ──────────────────────────────────────────"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
  echo "  ✗ Python3 not found. Please install Python 3.9+."
  exit 1
fi

# Install deps if needed
if ! python3 -c "import flask" 2>/dev/null; then
  echo "  Installing dependencies..."
  pip install -r requirements.txt --break-system-packages -q
fi

# Run
FLASK_ENV=development python3 app.py
