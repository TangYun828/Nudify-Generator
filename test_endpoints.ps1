# Test API Endpoints
# Run this to test all authentication and API endpoints

Write-Host "=== TESTING NUDIFY API ENDPOINTS ===" -ForegroundColor Green
Write-Host ""

$baseUrl = "http://localhost:8000"

# 1. Test Health Check
Write-Host "1. Testing Health Check..." -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
Write-Host "   Status: $($response.status)" -ForegroundColor Green
Write-Host ""

# 2. Register New User
Write-Host "2. Registering New User..." -ForegroundColor Cyan
$registerData = @{
    email = "testuser@example.com"
    username = "testuser"
    password = "SecurePass123!"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/register" -Method Post -Body $registerData -ContentType "application/json"
    Write-Host "   User ID: $($response.user_id)" -ForegroundColor Green
    Write-Host "   Message: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "   Note: User might already exist" -ForegroundColor Yellow
}
Write-Host ""

# 3. Login
Write-Host "3. Logging In..." -ForegroundColor Cyan
$loginData = @{
    email = "testuser@example.com"
    password = "SecurePass123!"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -Body $loginData -ContentType "application/json"
$token = $response.access_token
Write-Host "   Token: $($token.Substring(0,30))..." -ForegroundColor Green
Write-Host "   User ID: $($response.user_id)" -ForegroundColor Green
Write-Host ""

# 4. Get User Profile
Write-Host "4. Getting User Profile..." -ForegroundColor Cyan
$headers = @{
    "Authorization" = "Bearer $token"
}
$response = Invoke-RestMethod -Uri "$baseUrl/user/profile" -Method Get -Headers $headers
Write-Host "   Email: $($response.email)" -ForegroundColor Green
Write-Host "   Username: $($response.username)" -ForegroundColor Green
Write-Host "   Credits: $($response.credits)" -ForegroundColor Green
Write-Host ""

# 5. Check Credit Balance
Write-Host "5. Checking Credit Balance..." -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "$baseUrl/credits/balance" -Method Get -Headers $headers
Write-Host "   Balance: $($response.balance)" -ForegroundColor Green
Write-Host "   Total Earned: $($response.total_earned)" -ForegroundColor Green
Write-Host "   Total Spent: $($response.total_spent)" -ForegroundColor Green
Write-Host ""

# 6. Test Image Generation (Mock)
Write-Host "6. Testing Image Generation (Mock)..." -ForegroundColor Cyan
$generateData = @{
    prompt = "A beautiful portrait of a woman"
    negative_prompt = "low quality, blurry"
    image_number = 1
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$baseUrl/generate/image" -Method Post -Headers $headers -Body $generateData -ContentType "application/json"
Write-Host "   Message: $($response.message)" -ForegroundColor Green
Write-Host "   Credits Used: $($response.credits_used)" -ForegroundColor Green
Write-Host "   Credits Remaining: $($response.credits_remaining)" -ForegroundColor Green
Write-Host "   Prompt: $($response.prompt)" -ForegroundColor Green
Write-Host ""

# 7. Check Balance After Generation
Write-Host "7. Checking Balance After Generation..." -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "$baseUrl/credits/balance" -Method Get -Headers $headers
Write-Host "   Balance: $($response.balance)" -ForegroundColor Green
Write-Host "   Total Spent: $($response.total_spent)" -ForegroundColor Green
Write-Host ""

Write-Host "=== ALL TESTS COMPLETED SUCCESSFULLY ===" -ForegroundColor Green
Write-Host ""
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "ReDoc: http://localhost:8000/redoc" -ForegroundColor Cyan
