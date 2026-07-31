# PowerShell script to run Robot Brain locally
param(
    [int]$Port = 8000,
    [string]$Host = "0.0.0.0",
    [switch]$SkipInstall,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\run_local.ps1 [-Port <port>] [-Host <host>] [-SkipInstall] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Port <port>        Port to run the server on (default: 8000)"
    Write-Host "  -Host <host>        Host to bind to (default: 0.0.0.0)"
    Write-Host "  -SkipInstall        Skip dependency installation"
    Write-Host "  -Help               Show this help message"
    exit 0
}

Write-Host "Starting Robot Brain locally..." -ForegroundColor Green
Write-Host ""

# Check if Python is installed
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan

# Check if virtual environment exists
$venvPath = "..\venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Yellow
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "$venvPath\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}

# Install/Update dependencies
if (-not $SkipInstall) {
    Write-Host ""
    Write-Host "Installing/Updating dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Check if Redis is required and running (optional check)
Write-Host "Checking Redis connection..." -ForegroundColor Cyan
try {
    $redisCheck = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($redisCheck.TcpTestSucceeded) {
        Write-Host "Redis is running on localhost:6379" -ForegroundColor Green
    } else {
        Write-Host "Warning: Redis may not be running on localhost:6379" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Warning: Could not check Redis status" -ForegroundColor Yellow
}

# Start Uvicorn server
Write-Host ""
Write-Host "Starting Uvicorn server on $Host`:$Port..." -ForegroundColor Green
Write-Host "API Documentation will be available at: http://localhost:$Port/docs" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:$Port/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

uvicorn app.main:app --host $Host --port $Port --reload



