# Sync script for Windows - Self-updating agent helper
Set-Location -Path $PSScriptRoot
Write-Output "Syncing repository..."
git pull origin main --rebase
git add .
git commit -m "Auto-sync from Windows agent"
git push origin main
Write-Output "Sync complete!"
