# Antigravity browser agent launcher for Windows (PowerShell)
$ScriptDir = "$env:USERPROFILE\muse-spark-python"

# Load .env variables
if (Test-Path "$ScriptDir\.env") {
    foreach ($line in Get-Content "$ScriptDir\.env") {
        if ($line -match "^\s*[^#]") {
            $name, $value = $line -split '=', 2
            Set-Item -Path env:$($name.Trim()) -Value $value.Trim()
        }
    }
}

# Clean stale Chrome locks
$ProfileDir = "$env:USERPROFILE\chrome-debug-profile"
Remove-Item -Path "$ProfileDir\Singleton*" -Force -ErrorAction SilentlyContinue

Set-Location -Path $ScriptDir
& "$ScriptDir\.venv\Scripts\python.exe" antigrav_agent_win.py $args
