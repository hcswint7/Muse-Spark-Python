#!/bin/zsh
# Sync script for macOS - Self-updating agent helper
cd "$HOME/muse-spark-python"
echo "Syncing repository..."
git pull origin main --rebase
git add .
git commit -m "Auto-sync from macOS agent"
git push origin main
echo "Sync complete!"
