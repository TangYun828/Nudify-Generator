# RunPod Endpoint Testing Script
# Tests deployed RunPod endpoint with AWS safety integration

param(
    [Parameter(Mandatory=$true)]
    [string]$EndpointId,
    
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    
    [Parameter(Mandatory=$false)]
    [switch]$TestUnsafe,
    
    [Parameter(Mandatory=$false)]
    [switch]$CheckS3,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 120
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  RunPod Endpoint Test Suite         " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$apiUrl = "https://api.runpod.ai/v2/$EndpointId/runsync"
$headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type" = "application/json"
}

# Test 1: Safe Prompt (Should Pass)
Write-Host "[Test 1/3] Safe Prompt Generation" -ForegroundColor Green
Write-Host "Testing with: 'A beautiful mountain landscape at sunset'" -ForegroundColor White
Write-Host ""

$safeRequest = @{
    input = @{
        prompt = "A beautiful mountain landscape at sunset, golden hour, cinematic lighting"
        negative_prompt = "blur, low quality, distorted"
        image_number = 1
        user_id = "test_user_safe_$(Get-Date -Format 'HHmmss')"
        base_model_name = "onlyfornsfw118_v20.safetensors"
    }
} | ConvertTo-Json

try {
    Write-Host "Sending request..." -ForegroundColor Yellow
    $startTime = Get-Date
    
    $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $headers -Body $safeRequest -TimeoutSec $Timeout
    
    $duration = ((Get-Date) - $startTime).TotalSeconds
    
    if ($response.status -eq "COMPLETED") {
        Write-Host "âœ" Test 1 PASSED" -ForegroundColor Green
        Write-Host "  Duration: $([math]::Round($duration, 1)) seconds" -ForegroundColor White
        Write-Host "  Images returned: $($response.output.images.Count)" -ForegroundColor White
        Write-Host "  Message: $($response.output.message)" -ForegroundColor White
        
        # Save first image to file
        if ($response.output.images.Count -gt 0) {
            $base64 = $response.output.images[0] -replace 'data:image/png;base64,', ''
            $imageBytes = [System.Convert]::FromBase64String($base64)
            $outputPath = "test_output_safe_$(Get-Date -Format 'HHmmss').png"
            [System.IO.File]::WriteAllBytes($outputPath, $imageBytes)
            Write-Host "  Saved to: $outputPath" -ForegroundColor Cyan
        }
    } else {
        Write-Host "âœ— Test 1 FAILED" -ForegroundColor Red
        Write-Host "  Status: $($response.status)" -ForegroundColor Yellow
        Write-Host "  Response: $($response | ConvertTo-Json -Depth 5)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "âœ— Test 1 FAILED" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""

# Test 2: Check Endpoint Health
Write-Host "[Test 2/3] Endpoint Health Check" -ForegroundColor Green

try {
    $healthUrl = "https://api.runpod.ai/v2/$EndpointId/health"
    $healthResponse = Invoke-RestMethod -Uri $healthUrl -Headers $headers -TimeoutSec 10
    
    Write-Host "âœ" Test 2 PASSED" -ForegroundColor Green
    Write-Host "  Workers: $($healthResponse.workers.Count)" -ForegroundColor White
    Write-Host "  Response: $($healthResponse | ConvertTo-Json -Depth 3)" -ForegroundColor White
} catch {
    Write-Host "âœ— Test 2 FAILED (or health endpoint not available)" -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""

# Test 3: Unsafe Prompt (Optional - Tests Safety Layer)
if ($TestUnsafe) {
    Write-Host "[Test 3/3] Unsafe Prompt (Safety Layer Test)" -ForegroundColor Green
    Write-Host "Testing prompt filtering and Rekognition..." -ForegroundColor White
    Write-Host ""
    
    $unsafeRequest = @{
        input = @{
            prompt = "explicit adult content, nudity"
            image_number = 1
            user_id = "test_user_unsafe_$(Get-Date -Format 'HHmmss')"
        }
    } | ConvertTo-Json
    
    try {
        Write-Host "Sending unsafe prompt..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $headers -Body $unsafeRequest -TimeoutSec $Timeout
        
        # Check if safety layers blocked it
        if ($response.output.images.Count -eq 0 -or $response.output.message -match 'blocked|flagged|unsafe') {
            Write-Host "âœ" Test 3 PASSED - Content blocked by safety layers" -ForegroundColor Green
            Write-Host "  Message: $($response.output.message)" -ForegroundColor White
        } else {
            Write-Host "âš ï¸ Test 3 WARNING - Unsafe content not blocked" -ForegroundColor Yellow
            Write-Host "  Check Rekognition confidence thresholds" -ForegroundColor Yellow
            Write-Host "  Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "âš ï¸ Test 3 ERROR" -ForegroundColor Yellow
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
    }
} else {
    Write-Host "[Test 3/3] Unsafe Prompt Test (Skipped)" -ForegroundColor Yellow
    Write-Host "Use --TestUnsafe flag to enable safety layer testing" -ForegroundColor Gray
}

Write-Host ""

# S3 Audit Check (Optional)
if ($CheckS3) {
    Write-Host "[Bonus] S3 Audit Trail Check" -ForegroundColor Green
    Write-Host ""
    
    # Check if AWS CLI is available
    try {
        $awsVersion = aws --version 2>&1
        Write-Host "AWS CLI found: $awsVersion" -ForegroundColor White
        
        Write-Host "Checking S3 bucket: intimai-audit-images..." -ForegroundColor Yellow
        $s3List = aws s3 ls s3://intimai-audit-images/audit/ --recursive --human-readable 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "âœ" S3 audit trail verified" -ForegroundColor Green
            Write-Host "Recent uploads:" -ForegroundColor White
            $s3List | Select-Object -Last 10 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        } else {
            Write-Host "âœ— S3 check failed" -ForegroundColor Yellow
            Write-Host "  Make sure AWS CLI is configured with credentials" -ForegroundColor Gray
        }
    } catch {
        Write-Host "âš ï¸ AWS CLI not available" -ForegroundColor Yellow
        Write-Host "Install AWS CLI to check S3 audit trail" -ForegroundColor Gray
        Write-Host "  https://aws.amazon.com/cli/" -ForegroundColor Cyan
    }
    
    Write-Host ""
}

# Summary
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Endpoint ID: $EndpointId" -ForegroundColor White
Write-Host "API URL: $apiUrl" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Check RunPod logs for detailed execution traces" -ForegroundColor White
Write-Host "   https://www.runpod.io/console/serverless" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Verify S3 audit trail (if not checked above):" -ForegroundColor White
Write-Host "   aws s3 ls s3://intimai-audit-images/audit/ --recursive" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Integrate with frontend:" -ForegroundColor White
Write-Host "   - Add RUNPOD_ENDPOINT_ID to Vercel env vars" -ForegroundColor White
Write-Host "   - Add RUNPOD_API_KEY to Vercel env vars" -ForegroundColor White
Write-Host "   - Update frontend API client to call RunPod" -ForegroundColor White
Write-Host ""
Write-Host "Testing completed! 🎉" -ForegroundColor Green
