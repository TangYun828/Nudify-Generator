# RunPod Backend Build & Deploy Script
# Complete automation for building Docker image and deploying to RunPod

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUsername,
    
    [Parameter(Mandatory=$false)]
    [string]$GitHubToken,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet('github', 'dockerhub')]
    [string]$Registry = 'github',
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipPush,
    
    [Parameter(Mandatory=$false)]
    [switch]$TestLocal
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  RunPod Backend Deployment Script   " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$REPO_NAME = "intimai-backend"
$IMAGE_TAG = "latest"
$DOCKERFILE_PATH = "."

if ($Registry -eq 'github') {
    $IMAGE_FULL_NAME = "ghcr.io/$GitHubUsername/$REPO_NAME`:$IMAGE_TAG"
} else {
    $IMAGE_FULL_NAME = "$GitHubUsername/$REPO_NAME`:$IMAGE_TAG"
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Registry: $Registry" -ForegroundColor White
Write-Host "  Image: $IMAGE_FULL_NAME" -ForegroundColor White
Write-Host "  GitHub User: $GitHubUsername" -ForegroundColor White
Write-Host ""

# Step 1: Login to Registry
if (-not $SkipBuild -and -not $SkipPush) {
    Write-Host "[1/5] Logging into $Registry..." -ForegroundColor Green
    
    if ($Registry -eq 'github') {
        if (-not $GitHubToken) {
            Write-Host "Error: GitHub token required for GHCR" -ForegroundColor Red
            Write-Host "Get token from: https://github.com/settings/tokens" -ForegroundColor Yellow
            Write-Host "Required scopes: write:packages, read:packages" -ForegroundColor Yellow
            exit 1
        }
        
        $env:CR_PAT = $GitHubToken
        echo $env:CR_PAT | docker login ghcr.io -u $GitHubUsername --password-stdin
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "âœ— Login failed" -ForegroundColor Red
            exit 1
        }
    } else {
        docker login
        if ($LASTEXITCODE -ne 0) {
            Write-Host "âœ— Login failed" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "âœ" Logged in successfully" -ForegroundColor Green
    Write-Host ""
}

# Step 2: Verify Prerequisites
Write-Host "[2/5] Checking prerequisites..." -ForegroundColor Green

# Check Docker is running
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "âœ— Docker is not running" -ForegroundColor Red
    Write-Host "Start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}
Write-Host "âœ" Docker is running" -ForegroundColor White

# Check disk space (need ~30 GB)
$drive = (Get-Location).Drive.Name
$freeSpace = (Get-PSDrive $drive).Free / 1GB
Write-Host "âœ" Free disk space: $([math]::Round($freeSpace, 2)) GB" -ForegroundColor White

if ($freeSpace -lt 30) {
    Write-Host "âš ï¸ Warning: Less than 30 GB free (recommended for build)" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit 1
    }
}

# Check critical files exist
$requiredFiles = @(
    "Dockerfile",
    "handler.py",
    "safety_checker.py",
    "s3_uploader.py",
    "requirements_versions.txt"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "âœ— Missing required file: $file" -ForegroundColor Red
        exit 1
    }
}
Write-Host "âœ" All required files present" -ForegroundColor White
Write-Host ""

# Step 3: Build Docker Image
if (-not $SkipBuild) {
    Write-Host "[3/5] Building Docker image..." -ForegroundColor Green
    Write-Host "This will take 20-40 minutes..." -ForegroundColor Yellow
    Write-Host ""
    
    $buildStart = Get-Date
    
    docker build -t $IMAGE_FULL_NAME $DOCKERFILE_PATH
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "âœ— Build failed" -ForegroundColor Red
        exit 1
    }
    
    $buildEnd = Get-Date
    $buildDuration = ($buildEnd - $buildStart).TotalMinutes
    
    Write-Host ""
    Write-Host "âœ" Build completed in $([math]::Round($buildDuration, 1)) minutes" -ForegroundColor Green
    
    # Show image size
    $imageInfo = docker images $IMAGE_FULL_NAME --format "{{.Size}}"
    Write-Host "âœ" Image size: $imageInfo" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[3/5] Skipping build (--SkipBuild flag)" -ForegroundColor Yellow
    Write-Host ""
}

# Step 4: Test Locally (Optional)
if ($TestLocal) {
    Write-Host "[4/5] Testing image locally..." -ForegroundColor Green
    Write-Host "Starting container (this will test if it runs)..." -ForegroundColor Yellow
    
    # Check if .env exists
    if (Test-Path ".env") {
        Write-Host "Loading AWS credentials from .env..." -ForegroundColor White
        
        # Parse .env file
        $envVars = @{}
        Get-Content .env | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
                $envVars[$matches[1].Trim()] = $matches[2].Trim()
            }
        }
        
        # Run container with env vars
        docker run --rm `
            -e AWS_ACCESS_KEY_ID="$($envVars['AWS_ACCESS_KEY_ID'])" `
            -e AWS_SECRET_ACCESS_KEY="$($envVars['AWS_SECRET_ACCESS_KEY'])" `
            -e AWS_REGION="$($envVars['AWS_REGION'])" `
            -e AWS_S3_BUCKET="$($envVars['AWS_S3_BUCKET'])" `
            --gpus all `
            -p 8000:8000 `
            $IMAGE_FULL_NAME `
            timeout 30
        
        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 1) {
            Write-Host "âœ" Container started successfully (timed out as expected)" -ForegroundColor Green
        } else {
            Write-Host "âœ— Container test failed" -ForegroundColor Red
            Write-Host "Check logs above for errors" -ForegroundColor Yellow
        }
    } else {
        Write-Host "âš ï¸ No .env file found, skipping local test" -ForegroundColor Yellow
        Write-Host "Create .env with AWS credentials to test locally" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "[4/5] Skipping local test (use --TestLocal to enable)" -ForegroundColor Yellow
    Write-Host ""
}

# Step 5: Push to Registry
if (-not $SkipPush) {
    Write-Host "[5/5] Pushing image to $Registry..." -ForegroundColor Green
    Write-Host "This will take 10-20 minutes (uploading ~25 GB)..." -ForegroundColor Yellow
    Write-Host ""
    
    $pushStart = Get-Date
    
    docker push $IMAGE_FULL_NAME
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "âœ— Push failed" -ForegroundColor Red
        exit 1
    }
    
    $pushEnd = Get-Date
    $pushDuration = ($pushEnd - $pushStart).TotalMinutes
    
    Write-Host ""
    Write-Host "âœ" Push completed in $([math]::Round($pushDuration, 1)) minutes" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[5/5] Skipping push (--SkipPush flag)" -ForegroundColor Yellow
    Write-Host ""
}

# Summary
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Deployment Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "âœ" Docker image ready: $IMAGE_FULL_NAME" -ForegroundColor Green
Write-Host ""

if ($Registry -eq 'github' -and -not $SkipPush) {
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Make image public:" -ForegroundColor White
    Write-Host "   https://github.com/users/$GitHubUsername/packages/container/$REPO_NAME/settings" -ForegroundColor Cyan
    Write-Host "   â†' Change visibility to 'Public'" -ForegroundColor White
    Write-Host ""
}

Write-Host "2. Create RunPod endpoint:" -ForegroundColor White
Write-Host "   https://www.runpod.io/console/serverless" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Configure endpoint with:" -ForegroundColor White
Write-Host "   - Container Image: $IMAGE_FULL_NAME" -ForegroundColor Cyan
Write-Host "   - Container Disk: 40 GB" -ForegroundColor Cyan
Write-Host "   - GPU: RTX 4090 or RTX 4080" -ForegroundColor Cyan
Write-Host "   - Environment Variables:" -ForegroundColor Cyan
Write-Host "       AWS_ACCESS_KEY_ID=your_key" -ForegroundColor Gray
Write-Host "       AWS_SECRET_ACCESS_KEY=your_secret" -ForegroundColor Gray
Write-Host "       AWS_REGION=us-east-1" -ForegroundColor Gray
Write-Host "       AWS_S3_BUCKET=intimai-audit-images" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Test endpoint with:" -ForegroundColor White
Write-Host '   Invoke-RestMethod -Uri "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" ` ' -ForegroundColor Cyan
Write-Host '     -Method Post ` ' -ForegroundColor Cyan
Write-Host '     -Headers @{"Authorization" = "Bearer YOUR_API_KEY"; "Content-Type" = "application/json"} ` ' -ForegroundColor Cyan
Write-Host '     -Body ''{"input":{"prompt":"test landscape","user_id":"test"}}''' -ForegroundColor Cyan
Write-Host ""
Write-Host "For detailed instructions, see: RUNPOD_DEPLOYMENT_GUIDE.md" -ForegroundColor Yellow
Write-Host ""
Write-Host "Deployment script completed successfully! 🚀" -ForegroundColor Green
