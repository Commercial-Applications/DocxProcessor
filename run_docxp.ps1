# run_docxp.ps1

# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Build the paths using the script directory as base
$configPath = Join-Path -Path $scriptDir -ChildPath "config.yml"
$sourceDir = Join-Path -Path $scriptDir -ChildPath "docs_in"
$destDir = Join-Path -Path $scriptDir -ChildPath "docs_out"
$logFile = Join-Path -Path $scriptDir -ChildPath "process.log"

# Try using docx-processor directly if it's installed as a command
$arguments = @(
    "--config", $configPath,
    "--source-dir", $sourceDir,
    "--dest-dir", $destDir,
    "--log-file", $logFile,
    "--workers", "10",
    "-v",
    "run"
)

# Execute the command
try {
    $process = Start-Process -FilePath "docx-processor" -ArgumentList $arguments -NoNewWindow -Wait -PassThru
    exit $process.ExitCode
}
catch {
    Write-Error "Error executing docx-processor: $_"
    exit 1
}
