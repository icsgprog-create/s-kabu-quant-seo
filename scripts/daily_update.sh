#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/s-kabu-quant-seo/backend"
source .venv/bin/activate
python3 batch_runner.py --all

cd "$HOME/s-kabu-quant-seo"
if [ -n "$(git status --porcelain frontend/data/)" ]; then
  git add frontend/data/
  git commit -m "Auto update stock metrics and AI enrichment $(date +'%Y-%m-%d')"
  git push origin main
fi
