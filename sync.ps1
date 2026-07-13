# Sync script for Windows - Self-updating agent helper
$ScriptDir = "$env:USERPROFILE\muse-spark-python"
Set-Location -Path $ScriptDir
Write-Output "Syncing repository..."
git pull origin main --rebase
git add .
git commit -m "Auto-sync from Windows agent"
git push origin main
Write-Output "Sync complete!"
