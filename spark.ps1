# Spark launcher for Windows (PowerShell)
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

Set-Location -Path $ScriptDir
& npx @ai-sdk/openai-compatible@latest $args
