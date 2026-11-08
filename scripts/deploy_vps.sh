#!/usr/bin/env bash
# =============================================================================
# UGC Lemonaru - VPS Automated Deployment & Maintenance Script
# Target Directory: /home/ubuntu/apps/ugc-lemonaru
# =============================================================================
set -e

PROJECT_DIR="/home/ubuntu/apps/ugc-lemonaru"
cd "$PROJECT_DIR"

echo "🚀 [1/5] Pulling latest changes from Git..."
git pull origin main

echo "🐍 [2/5] Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "   Created new .venv at $PROJECT_DIR/.venv"
fi

source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "🎭 [3/5] Installing Playwright Chromium browser binary..."
playwright install chromium || true

echo "🎬 [4/5] Ensuring Remotion dependencies in remotion/..."
if [ -d "remotion" ]; then
    cd remotion
    npm install --silent
    cd "$PROJECT_DIR"
fi

echo "📁 [5/5] Ensuring isolated runtime directories exist..."
mkdir -p logs output ready_to_publish/pending ready_to_publish/posted data/temp

echo "=========================================================="
echo "✅ UGC Lemonaru deployment is up to date & isolated!"
echo "=========================================================="
