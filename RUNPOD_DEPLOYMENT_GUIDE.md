# RunPod Backend Endpoint Deployment Guide

Complete step-by-step guide to deploy the Fooocus backend with AWS safety checks to RunPod Serverless.

## Prerequisites

✅ **Completed:**
- AWS IAM user created (`intimai-rekognition-bot`)
- S3 bucket created (`intimai-audit-images` in `us-east-1`)
- AWS credentials available
- Backend code with safety checks committed to GitHub

📋 **Required:**
- Docker Desktop installed (with WSL2 on Windows)
- GitHub account
- RunPod account ([Sign up](https://www.runpod.io))
- 30 GB free disk space for Docker build

---

## Step 1: Prepare Container Registry

### Option A: GitHub Container Registry (Recommended - Free)

1. **Create GitHub Personal Access Token:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `write:packages`, `read:packages`, `delete:packages`
   - Copy the token (starts with `ghp_...`)

2. **Login to GitHub Container Registry:**
   ```powershell
   # In PowerShell
   $env:CR_PAT = "YOUR_GITHUB_TOKEN"
   echo $env:CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   ```

### Option B: Docker Hub (Alternative)

```powershell
docker login
# Enter your Docker Hub username and password
```

---

## Step 2: Build Docker Image

This will take 20-40 minutes and requires ~30 GB disk space.

### Build Command:

```powershell
# Navigate to backend folder
cd "C:\working folder\intimai\Nudify-Generator"

# Build image (replace YOUR_GITHUB_USERNAME with your actual GitHub username)
docker build -t ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest .

# Alternative: If using Docker Hub
# docker build -t YOUR_DOCKERHUB_USERNAME/intimai-backend:latest .
```

### What happens during build:
- ✅ Installs CUDA 12.4 + Python dependencies
- ✅ Downloads 7GB NSFW model (`onlyfornsfw118_v20.safetensors`)
- ✅ Installs boto3 for AWS integration
- ✅ Copies handler.py with safety checks
- ✅ Configures RunPod serverless entry point

### Monitor progress:
```powershell
# Check Docker is building correctly (in another terminal)
docker ps -a

# Check image size after build
docker images | Select-String "intimai-backend"
# Expected size: ~25-30 GB
```

---

## Step 3: Push Image to Registry

### Push to GitHub Container Registry:

```powershell
# Push the image
docker push ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest

# Make image public (go to GitHub)
# https://github.com/users/YOUR_GITHUB_USERNAME/packages/container/intimai-backend/settings
# → Change visibility to "Public"
```

### Push to Docker Hub:

```powershell
docker push YOUR_DOCKERHUB_USERNAME/intimai-backend:latest
```

**Expected push time:** 10-20 minutes (uploading ~25 GB)

---

## Step 4: Create RunPod Serverless Endpoint

### 4.1 Create Template

1. **Go to RunPod Console:**
   - Visit: https://www.runpod.io/console/serverless

2. **Click "New Endpoint"**

3. **Configure Endpoint Settings:**

   ```yaml
   Endpoint Name: intimai-backend-prod
   
   Container Image:
     - ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest
   
   Container Disk: 40 GB
   
   GPU Selection:
     - RTX 4090 (Recommended)
     - RTX 4080
     - A5000 (Cheaper alternative)
   
   Worker Configuration:
     - Min Workers: 0 (auto-scale down to save costs)
     - Max Workers: 3 (adjust based on expected load)
     - Idle Timeout: 5 seconds
     - Execution Timeout: 300 seconds (5 minutes)
   
   Environment Variables (CRITICAL - ADD THESE):
     AWS_ACCESS_KEY_ID: your_aws_access_key
     AWS_SECRET_ACCESS_KEY: your_aws_secret_key
     AWS_REGION: us-east-1
     AWS_S3_BUCKET: intimai-audit-images
     SAFETY_CHECKER_MODE: permissive_nsfw
   ```

### 4.2 Add Environment Variables

**In the "Environment Variables" section:**

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | `AKIAY2RL...` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | `lADhazz...` | AWS IAM secret key |
| `AWS_REGION` | `us-east-1` | AWS region for Rekognition & S3 |
| `AWS_S3_BUCKET` | `intimai-audit-images` | S3 bucket name |
| `SAFETY_CHECKER_MODE` | `permissive_nsfw` | Allow adult content (use `strict` to block) |

⚠️ **Security Note:** These credentials are stored securely by RunPod and only accessible to your endpoint workers.

### 4.3 Deploy Endpoint

1. Click **"Deploy"**
2. Wait for initialization (5-10 minutes for first worker)
3. Status will change: `Initializing` → `Ready`

---

## Step 5: Test the Endpoint

### 5.1 Get Endpoint Details

From RunPod Console:
1. Copy **Endpoint ID** (e.g., `abc123def456...`)
2. Copy or create **API Key** (Settings → API Keys)

### 5.2 Test with cURL

```powershell
# Set environment variables
$ENDPOINT_ID = "YOUR_ENDPOINT_ID"
$API_KEY = "YOUR_RUNPOD_API_KEY"

# Test request (safe prompt)
$body = @{
    input = @{
        prompt = "A beautiful mountain landscape at sunset"
        negative_prompt = "blur, low quality"
        image_number = 1
        user_id = "test_user_123"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" `
    -Method Post `
    -Headers @{
        "Authorization" = "Bearer $API_KEY"
        "Content-Type" = "application/json"
    } `
    -Body $body
```

### 5.3 Expected Response (Success)

```json
{
  "id": "sync-abc123...",
  "status": "COMPLETED",
  "output": {
    "images": ["data:image/png;base64,iVBORw0KGg..."],
    "progress": 100,
    "message": "Generated 1 image(s)"
  },
  "executionTime": 18234
}
```

### 5.4 Test Safety Check (Unsafe Prompt)

```powershell
# Test with inappropriate prompt to verify safety layer
$unsafeBody = @{
    input = @{
        prompt = "explicit adult content"
        image_number = 1
        user_id = "test_user_456"
    }
} | ConvertTo-Json

# This should either:
# 1. Block generation at Layer 1 (keyword filter)
# 2. Block at Layer 3 (Rekognition) if image generated
# 3. Log to S3 at Layer 4

Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" `
    -Method Post `
    -Headers @{
        "Authorization" = "Bearer $API_KEY"
        "Content-Type" = "application/json"
    } `
    -Body $unsafeBody
```

---

## Step 6: Verify AWS Integration

### 6.1 Check S3 Audit Trail

```powershell
# View S3 bucket contents (using AWS CLI)
aws s3 ls s3://intimai-audit-images/audit/ --recursive

# Expected structure:
# audit/test_user_123/2026-02-27/20260227_153045_image.png
# audit/test_user_456/2026-02-27/20260227_153120_image.png
```

### 6.2 Check Rekognition Logs

In RunPod Console → Endpoint Logs, you should see:

```
✓ AWS Rekognition check passed (confidence: 15.2%)
✓ Uploaded safe image to S3: audit/test_user_123/2026-02-27/...
✓ Image passed all safety checks
```

Or for unsafe content:

```
✗ AWS Rekognition flagged image (confidence: 92.5%)
✗ Flagged categories: Explicit Nudity
✗ Image deleted, not returning to client
```

---

## Step 7: Integrate with Frontend

### Update Frontend API Configuration

In your Next.js frontend (`nudify-app-nextjs`):

```typescript
// app/lib/runpod.ts or similar

export const RUNPOD_CONFIG = {
  endpointId: process.env.RUNPOD_ENDPOINT_ID,
  apiKey: process.env.RUNPOD_API_KEY,
  apiUrl: `https://api.runpod.ai/v2/${process.env.RUNPOD_ENDPOINT_ID}`
};

export async function generateImage(prompt: string, userId: string) {
  const response = await fetch(`${RUNPOD_CONFIG.apiUrl}/runsync`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RUNPOD_CONFIG.apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: {
        prompt,
        user_id: userId,
        image_number: 1,
      }
    })
  });
  
  return response.json();
}
```

### Environment Variables for Frontend (Vercel)

Add to Vercel project settings:

```bash
RUNPOD_ENDPOINT_ID=your_endpoint_id
RUNPOD_API_KEY=your_api_key
```

---

## Cost Estimation

### RunPod Serverless Pricing (Pay-per-use)

**RTX 4090:**
- Active generation: $0.00034/second (~$0.006 per 18-second image)
- Idle time: Free (with 0 min workers)

**Monthly estimate (10,000 images):**
- Generation cost: 10,000 × $0.006 = **$60/month**
- AWS Rekognition: 10,000 × $0.001 = **$10/month**
- S3 storage: ~**$2/month** (auto-delete after 6 months)

**Total: ~$72/month for 10,000 generations**

### Cost Optimization Tips:

1. Set `Min Workers: 0` (auto-scale to zero when idle)
2. Use `Execution Timeout: 180` (3 minutes) to prevent stuck workers
3. Choose cheaper GPU for testing (A5000 is 40% cheaper than RTX 4090)
4. Enable CloudWatch alarms for budget tracking

---

## Monitoring & Maintenance

### View Logs

```powershell
# In RunPod Console
# Go to: Endpoints → intimai-backend-prod → Logs (real-time)
```

### Check Worker Status

```powershell
# API request to check endpoint health
Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT_ID/health" `
    -Headers @{"Authorization" = "Bearer $API_KEY"}
```

### Update Deployment

When you make code changes:

```powershell
# 1. Rebuild Docker image
docker build -t ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest .

# 2. Push updated image
docker push ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest

# 3. In RunPod Console:
#    - Go to Endpoint Settings
#    - Click "Refresh Image" (pulls latest from registry)
#    - Workers will restart with new code
```

---

## Troubleshooting

### Issue: "Container failed to start"

**Check:**
1. Docker image is public (ghcr.io package settings)
2. Image name is correct in endpoint configuration
3. RunPod logs show the actual error

**Solution:**
```powershell
# Test image locally first
docker run --gpus all -p 8000:8000 `
  -e AWS_ACCESS_KEY_ID="..." `
  -e AWS_SECRET_ACCESS_KEY="..." `
  -e AWS_REGION="us-east-1" `
  -e AWS_S3_BUCKET="intimai-audit-images" `
  ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest
```

### Issue: "AWS credentials not found"

**Check:**
1. Environment variables are set correctly in RunPod template
2. No typos in variable names (must be exact: `AWS_ACCESS_KEY_ID`)
3. RunPod logs show what env vars are loaded

**Solution:**
- Edit endpoint → Environment Variables → Verify all 4 AWS vars are present

### Issue: "ModuleNotFoundError: No module named 'runpod'"

**Cause:** Dockerfile didn't install runpod SDK

**Solution:**
```dockerfile
# Add to Dockerfile (should already be there at line 33)
RUN pip install --no-cache-dir runpod
```

### Issue: "Timeout waiting for Fooocus API"

**Cause:** Model loading takes too long or GPU not available

**Check RunPod logs for:**
```
[Fooocus] Loading model...
[Fooocus] Model loaded successfully
```

**Solution:** Increase `API_STARTUP_TIMEOUT` in handler.py from 240s to 360s

### Issue: "S3 upload failed"

**Check:**
1. S3 bucket exists: `intimai-audit-images`
2. IAM user has `s3:PutObject` permission
3. AWS region matches bucket region (`us-east-1`)

**Debug:**
```python
# In handler.py logs, look for:
✓ Uploaded safe image to S3: s3://intimai-audit-images/audit/...
# Or error message with details
```

---

## Security Checklist

Before going to production:

- [ ] Docker image is stored in private registry (or public with no secrets)
- [ ] AWS credentials are only in RunPod environment variables (not in code)
- [ ] `.env` file is in `.gitignore` (never committed)
- [ ] RunPod API key is stored securely (in frontend env vars, not hardcoded)
- [ ] S3 bucket has lifecycle rule (auto-delete after 180 days)
- [ ] IAM user has minimal permissions (only Rekognition + S3)
- [ ] Frontend only sends user-generated prompts (sanitize input)
- [ ] Consider rotating AWS keys every 90 days

---

## Next Steps

1. ✅ **Build & Push Docker Image** (Steps 1-3 above)
2. ✅ **Create RunPod Endpoint** (Step 4)
3. ✅ **Test Endpoint** (Step 5)
4. ✅ **Verify AWS Integration** (Step 6)
5. ⏳ **Integrate with Frontend** (Step 7)
6. ⏳ **Production Deployment** (Deploy frontend to Vercel)
7. ⏳ **Monitor & Optimize** (Track costs and performance)

---

## Quick Reference Commands

```powershell
# Build Docker image
docker build -t ghcr.io/YOUR_USERNAME/intimai-backend:latest .

# Push to GitHub Container Registry
docker push ghcr.io/YOUR_USERNAME/intimai-backend:latest

# Test endpoint (replace variables)
$ENDPOINT_ID = "your_endpoint_id"
$API_KEY = "your_api_key"
Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" `
  -Method Post `
  -Headers @{"Authorization" = "Bearer $API_KEY"; "Content-Type" = "application/json"} `
  -Body '{"input":{"prompt":"test","user_id":"test123"}}'

# Check S3 audit trail
aws s3 ls s3://intimai-audit-images/audit/ --recursive

# View RunPod logs
# Go to: https://www.runpod.io/console/serverless
```

---

## Support Resources

- **RunPod Docs:** https://docs.runpod.io/serverless/overview
- **GitHub Container Registry:** https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- **AWS Rekognition:** https://docs.aws.amazon.com/rekognition/
- **Session Handoff:** See [docs/handoff/SESSION_HANDOFF_2026-02-27.md](docs/handoff/SESSION_HANDOFF_2026-02-27.md)

---

**Deployment Status:**
- Created: February 27, 2026
- AWS Safety Layers: ✅ Implemented (Layer 3 + 4)
- Backend Code: ✅ Committed to GitHub
- Docker Image: ⏳ Ready to build
- RunPod Endpoint: ⏳ Ready to deploy
