$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$pythonEnvironment = Join-Path $backend ".venv\Scripts\python.exe"

try {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.12 or later is required. Install it from https://www.python.org/downloads/windows/ and try again."
    }

    $pythonVersion = & $pythonCommand.Source --version 2>&1
    if ($pythonVersion -notmatch "Python (\d+)\.(\d+)" -or [int]$Matches[1] -lt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -lt 12)) {
        throw "Python 3.12 or later is required. Detected: $pythonVersion"
    }

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $nodeCommand -or -not $npmCommand) {
        $packageRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
        $nodePackage = Get-ChildItem $packageRoot -Directory -Filter "OpenJS.NodeJS.LTS*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($nodePackage) {
            $nodeFolder = Get-ChildItem $nodePackage.FullName -Directory -Filter "node-v*-win-x64" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($nodeFolder -and (Test-Path (Join-Path $nodeFolder.FullName "node.exe")) -and (Test-Path (Join-Path $nodeFolder.FullName "npm.cmd"))) {
                $env:Path = "$($nodeFolder.FullName);$env:Path"
                $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
                $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
            }
        }
    }
    if (-not $nodeCommand -or -not $npmCommand) {
        throw "Node.js LTS (with npm) is required. Install it with 'winget install --id OpenJS.NodeJS.LTS --exact --scope user', then try again."
    }

    Write-Host "Preparing Yorimichi..."
    if (-not (Test-Path $pythonEnvironment)) {
        & $pythonCommand.Source -m venv (Join-Path $backend ".venv")
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create the Python virtual environment."
        }
    }

    & $pythonEnvironment -c "import fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $pythonEnvironment -m pip install -r (Join-Path $backend "requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            throw "Could not install the Python dependencies listed in backend\requirements.txt."
        }
    }

    if (-not (Test-Path (Join-Path $frontend "node_modules\vite\bin\vite.js"))) {
        Push-Location $frontend
        try {
            & $npmCommand.Source ci
            if ($LASTEXITCODE -ne 0) {
                throw "Could not install the frontend dependencies listed in frontend\package-lock.json."
            }
        }
        finally {
            Pop-Location
        }
    }

    function Test-LocalEndpoint([string]$Url) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
            return $response.StatusCode -eq 200
        }
        catch {
            return $false
        }
    }

    $pythonLiteral = $pythonEnvironment.Replace("'", "''")
    $backendLiteral = $backend.Replace("'", "''")
    $npmLiteral = $npmCommand.Source.Replace("'", "''")
    $frontendLiteral = $frontend.Replace("'", "''")

    if (Test-LocalEndpoint "http://127.0.0.1:8000/api/health") {
        Write-Host "API server is already running."
    }
    else {
        $apiCommand = "Set-Location -LiteralPath '$backendLiteral'; & '$pythonLiteral' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
        $apiEncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($apiCommand))
        Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoLogo", "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $apiEncodedCommand) -WorkingDirectory $backend | Out-Null
        Write-Host "Starting API server..."
    }

    if (Test-LocalEndpoint "http://127.0.0.1:8000/api/health") {
        $apiReady = $true
    }
    else {
        $apiReady = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            Start-Sleep -Seconds 1
            if (Test-LocalEndpoint "http://127.0.0.1:8000/api/health") {
                $apiReady = $true
                break
            }
        }
    }
    if (-not $apiReady) {
        throw "The API did not start. Check the API server window for errors."
    }

    if (Test-LocalEndpoint "http://127.0.0.1:5173/") {
        Write-Host "Website server is already running."
    }
    else {
        $websiteCommand = "Set-Location -LiteralPath '$frontendLiteral'; & '$npmLiteral' run dev"
        $websiteEncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($websiteCommand))
        Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoLogo", "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $websiteEncodedCommand) -WorkingDirectory $frontend | Out-Null
        Write-Host "Starting website server..."
    }

    $websiteReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if (Test-LocalEndpoint "http://127.0.0.1:5173/") {
            $websiteReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $websiteReady) {
        throw "The website did not start. Check the website server window for errors."
    }

    Write-Host "Opening http://localhost:5173 ..."
    Start-Process "http://localhost:5173"
    Write-Host "Yorimichi is ready. Close the API and website server windows to stop it."
}
catch {
    Write-Error $_
    exit 1
}
