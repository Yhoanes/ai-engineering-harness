param(
    [ValidateSet("User", "Portable", "Development")]
    [string]$Mode = "User",
    [switch]$Check,
    [switch]$Repair
)

$ErrorActionPreference = "Stop"

# 1. Resolve Location Securely (works with spaces)
$ScriptDir = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent -Path $ScriptDir

Set-Location -Path $RepoRoot

Write-Host "AI Engineering Harness Installer"
Write-Host "================================"
Write-Host "Root: $RepoRoot"

# 2. Find Base Python
# We don't download Python, just check if it's available.
$BasePython = "python"
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    # If standard 'py' launcher exists, prefer it
    $BasePython = "py"
}

try {
    $PyVersion = & $BasePython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($LASTEXITCODE -ne 0) { throw "Python execution failed" }
    
    $versionParts = $PyVersion.Split('.')
    if ($versionParts.Length -ge 2) {
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            Write-Host "ERROR: PYTHON_VERSION_UNSUPPORTED: Python 3.11 or newer is required. Found $PyVersion." -ForegroundColor Red
            Write-Host "Please install a supported Python version and ensure it is in your PATH." -ForegroundColor Yellow
            exit 2
        }
    } else {
        throw "Could not parse Python version."
    }
} catch {
    Write-Host "ERROR: PYTHON_REQUIRED: A compatible Python installation could not be found." -ForegroundColor Red
    Write-Host "Please install Python 3.11 or newer and add it to your PATH." -ForegroundColor Yellow
    exit 2
}

# 3. Check Venv
$VenvDir = Join-Path -Path $RepoRoot -ChildPath ".venv"
$VenvPython = Join-Path -Path (Join-Path -Path $VenvDir -ChildPath "Scripts") -ChildPath "python.exe"

$VenvExists = Test-Path -Path $VenvPython

if ($Check) {
    $AgyCommand = Get-Command agy -ErrorAction SilentlyContinue
    if ($AgyCommand) {
        Write-Host "Antigravity CLI ........ PASS" -ForegroundColor Green
    } else {
        Write-Host "Antigravity CLI ........ NOT INSTALLED" -ForegroundColor Yellow
    }

    if (-not $VenvExists) {
        Write-Host "STATUS: NOT_INSTALLED" -ForegroundColor Yellow
        exit 2
    }
    Write-Host "Running Check Mode..."
    & $VenvPython -m engine.diagnostics --repo-root $RepoRoot
    $DiagCode = $LASTEXITCODE

    exit $DiagCode
}

if (-not $VenvExists) {
    Write-Host "Creating Virtual Environment (.venv)..."
    try {
        & $BasePython -m venv $VenvDir
    } catch {
        Write-Error "INSTALLATION_ERROR: Failed to create virtual environment."
        exit 1
    }
} else {
    Write-Host "Using existing Virtual Environment."
}

# 4. Verify PIP Availability
$PipExists = & $VenvPython -m pip --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PIP_REQUIRED: Virtual environment is broken or missing pip." -ForegroundColor Red
    Write-Host "Remediation: You may need to recreate the environment manually if -Repair doesn't work." -ForegroundColor Yellow
    exit 2
}

# 5. Dependency Installation (unless Already Healthy and not Repairing)
$AlreadyHealthy = $false
if (-not $Repair) {
    # Run a quick check to see if we can skip installation
    try {
        $checkOut = & $VenvPython -m engine.diagnostics --repo-root $RepoRoot 2>&1
    } catch {
        # Ignore
    }
    if ($LASTEXITCODE -eq 0) {
        $AlreadyHealthy = $true
    }
}

if ($AlreadyHealthy) {
    Write-Host "ALREADY_HEALTHY: Harness is already installed and healthy." -ForegroundColor Green
} else {
    Write-Host "Installing Package..."
    if ($Mode -eq "Development") {
        Write-Host "Mode: Development (Editable with dev dependencies)"
        & $VenvPython -m pip install -e ".[dev]"
    } else {
        Write-Host "Mode: Portable/User"
        & $VenvPython -m pip install .
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "DEPENDENCY_DOWNLOAD_MAY_BE_REQUIRED: pip install failed." -ForegroundColor Red
        Write-Host "If you are offline, ensure dependencies are cached." -ForegroundColor Yellow
        exit 2
    }
}

# 6. Run Final Diagnostics
Write-Host "`nRunning Final Diagnostics..."
& $VenvPython -m engine.diagnostics --repo-root $RepoRoot
$DiagCode = $LASTEXITCODE

$AgyCommand = Get-Command agy -ErrorAction SilentlyContinue
if ($AgyCommand) {
    Write-Host "Antigravity CLI ........ PASS" -ForegroundColor Green
} else {
    Write-Host "Antigravity CLI ........ NOT INSTALLED" -ForegroundColor Yellow
    Write-Host "`nNOTICE: Antigravity provider execution is unavailable until agy is installed." -ForegroundColor Yellow
    Write-Host "To install, follow the official Google Antigravity guide." -ForegroundColor Yellow
}

if ($DiagCode -eq 0) {
    Write-Host "`nNext Step: Run '.venv\Scripts\python -m engine.diagnostics' or start using the Harness." -ForegroundColor Green
}

exit $DiagCode
