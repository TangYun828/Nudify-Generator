# Docker build and run script for Fooocus Serverless
# Run as Administrator if needed

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("build", "up", "down", "logs", "push", "test")]
    [string]$Command = "up"
)

$ProjectName = "fooocus-serverless"
$ProjectPath = "c:\working folder\nudify-backend"
$ImageName = "$ProjectName`:latest"
$ContainerName = "$ProjectName"
$DockerHubUsername = "yourusername"  # Change this

function Show-Menu {
    Write-Host "`n=== Fooocus Docker Manager ===" -ForegroundColor Cyan
    Write-Host "1. Build Docker image"
    Write-Host "2. Start container (docker-compose up)"
    Write-Host "3. Stop container (docker-compose down)"
    Write-Host "4. View logs"
    Write-Host "5. Test API"
    Write-Host "6. Push to Docker Hub"
    Write-Host "0. Exit`n"
}

function Build-Image {
    Write-Host "Building Docker image..." -ForegroundColor Green
    Set-Location $ProjectPath
    docker build -t $ImageName .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Build successful!" -ForegroundColor Green
    } else {
        Write-Host "✗ Build failed!" -ForegroundColor Red
    }
}

function Start-Container {
    Write-Host "Starting container with docker-compose..." -ForegroundColor Green
    Set-Location $ProjectPath
    docker-compose up -d
    Write-Host "✓ Container started!" -ForegroundColor Green
    Write-Host "API available at: http://localhost:7866" -ForegroundColor Yellow
}

function Stop-Container {
    Write-Host "Stopping container..." -ForegroundColor Yellow
    Set-Location $ProjectPath
    docker-compose down
    Write-Host "✓ Container stopped!" -ForegroundColor Green
}

function Show-Logs {
    Write-Host "Showing logs..." -ForegroundColor Green
    Set-Location $ProjectPath
    docker-compose logs -f
}

function Test-API {
    Write-Host "Testing Fooocus API..." -ForegroundColor Green
    
    $payload = @{
        "prompt" = "A beautiful sunset over mountains, cinematic lighting, 8k"
        "base_model_name" = "juggernautXL_v8Rundiffusion.safetensors"
        "image_number" = 1
    } | ConvertTo-Json

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:7866/v1/engine/generation" `
            -Method POST `
            -ContentType "application/json" `
            -Body $payload `
            -TimeoutSec 300
        
        Write-Host "✓ API Response:" -ForegroundColor Green
        Write-Host ($response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10)
    } catch {
        Write-Host "✗ API Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Make sure container is running: docker-compose logs" -ForegroundColor Yellow
    }
}

function Push-Registry {
    Write-Host "Pushing to Docker Hub..." -ForegroundColor Green
    Write-Host "Update `$DockerHubUsername variable first!" -ForegroundColor Yellow
    
    $dockerHubImage = "$DockerHubUsername/$ProjectName`:latest"
    Write-Host "Target: $dockerHubImage"
    
    $confirm = Read-Host "Continue? (y/n)"
    if ($confirm -eq 'y') {
        docker tag $ImageName $dockerHubImage
        docker push $dockerHubImage
        Write-Host "✓ Push complete!" -ForegroundColor Green
    }
}

# Handle command line argument
switch ($Command) {
    "build" { Build-Image }
    "up" { Start-Container }
    "down" { Stop-Container }
    "logs" { Show-Logs }
    "test" { Test-API }
    "push" { Push-Registry }
    default {
        # Interactive menu
        do {
            Show-Menu
            $choice = Read-Host "Enter choice"
            
            switch ($choice) {
                "1" { Build-Image }
                "2" { Start-Container }
                "3" { Stop-Container }
                "4" { Show-Logs }
                "5" { Test-API }
                "6" { Push-Registry }
                "0" { exit }
                default { Write-Host "Invalid choice!" -ForegroundColor Red }
            }
        } while ($true)
    }
}
