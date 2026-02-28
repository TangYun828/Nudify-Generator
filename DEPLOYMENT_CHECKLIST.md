# RunPod Backend Deployment Checklist

Quick reference for deploying the IntimAI backend to RunPod with AWS safety integration.

## Prerequisites Checklist

### ✅ Completed (From Previous Session)
- [x] AWS IAM user created (`intimai-rekognition-bot`)
- [x] AWS S3 bucket created (`intimai-audit-images`, region: `us-east-1`)
- [x] AWS credentials obtained
- [x] Backend code with safety layers committed to GitHub
- [x] Local testing validated (Rekognition + S3 working)

### 📋 Required Before Building
- [ ] Docker Desktop installed and running
- [ ] GitHub account (for container registry)
- [ ] GitHub Personal Access Token with `write:packages` scope
- [ ] 30 GB free disk space
- [ ] RunPod account created

---

## Deployment Steps

### Step 1: Build Docker Image (30-40 minutes)

```powershell
# Navigate to backend folder
cd "C:\working folder\intimai\Nudify-Generator"

# Option A: Use automated script (recommended)
.\build-and-deploy.ps1 -GitHubUsername "YOUR_GITHUB_USERNAME" -GitHubToken "ghp_your_token"

# Option B: Manual build
docker build -t ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest .
```

**Expected result:** Docker image ~25-30 GB

### Step 2: Push to Registry (10-20 minutes)

```powershell
# Login to GitHub Container Registry
$env:CR_PAT = "ghp_your_github_token"
echo $env:CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Push image
docker push ghcr.io/YOUR_GITHUB_USERNAME/intimai-backend:latest
```

**Then:** Make image public at:
- https://github.com/users/YOUR_GITHUB_USERNAME/packages/container/intimai-backend/settings
- Change visibility to "Public"

### Step 3: Create RunPod Endpoint (5 minutes)

1. Go to: https://www.runpod.io/console/serverless
2. Click "New Endpoint"
3. Configure:

| Setting | Value |
|---------|-------|
| **Endpoint Name** | `intimai-backend-prod` |
| **Container Image** | `ghcr.io/YOUR_USERNAME/intimai-backend:latest` |
| **Container Disk** | `40 GB` |
| **GPU** | RTX 4090 (or RTX 4080, A5000) |
| **Min Workers** | `0` (auto-scale to save costs) |
| **Max Workers** | `3` |
| **Idle Timeout** | `5 seconds` |
| **Execution Timeout** | `300 seconds` |

4. **Add Environment Variables:**

```
AWS_ACCESS_KEY_ID = your_access_key_from_aws
AWS_SECRET_ACCESS_KEY = your_secret_key_from_aws
AWS_REGION = us-east-1
AWS_S3_BUCKET = intimai-audit-images
```

5. Click "Deploy"

**Expected result:** Endpoint status changes to "Ready" in 5-10 minutes

### Step 4: Test Endpoint (2 minutes)

```powershell
# Use test script
.\test-runpod-endpoint.ps1 -EndpointId "YOUR_ENDPOINT_ID" -ApiKey "YOUR_API_KEY"

# Or manual test
$ENDPOINT_ID = "your_endpoint_id"
$API_KEY = "your_api_key"

$body = @{
    input = @{
        prompt = "A beautiful mountain landscape at sunset"
        user_id = "test_user_123"
        image_number = 1
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

**Expected result:**
```json
{
  "status": "COMPLETED",
  "output": {
    "images": ["data:image/png;base64,..."],
    "progress": 100,
    "message": "Generated 1 image(s)"
  }
}
```

### Step 5: Verify AWS Integration (2 minutes)

```powershell
# Check S3 audit trail
aws s3 ls s3://intimai-audit-images/audit/ --recursive

# Check RunPod logs for:
# ✓ AWS Rekognition check passed (confidence: XX%)
# ✓ Uploaded safe image to S3: audit/test_user_123/...
```

### Step 6: Integrate with Frontend

1. Add to Vercel environment variables:
   ```
   RUNPOD_ENDPOINT_ID=your_endpoint_id
   RUNPOD_API_KEY=your_api_key
   ```

2. Update frontend API client (example):
   ```typescript
   // app/lib/runpod.ts
   export async function generateImage(prompt: string, userId: string) {
     const response = await fetch(
       `https://api.runpod.ai/v2/${process.env.RUNPOD_ENDPOINT_ID}/runsync`,
       {
         method: 'POST',
         headers: {
           'Authorization': `Bearer ${process.env.RUNPOD_API_KEY}`,
           'Content-Type': 'application/json',
         },
         body: JSON.stringify({
           input: { prompt, user_id: userId, image_number: 1 }
         })
       }
     );
     return response.json();
   }
   ```

3. Deploy frontend to Vercel

---

## Quick Commands Reference

```powershell
# Build and deploy (automated)
.\build-and-deploy.ps1 -GitHubUsername "YOUR_USERNAME" -GitHubToken "ghp_token"

# Test endpoint
.\test-runpod-endpoint.ps1 -EndpointId "abc123" -ApiKey "key123" -TestUnsafe -CheckS3

# Check S3 audit trail
aws s3 ls s3://intimai-audit-images/audit/ --recursive --human-readable

# View RunPod logs
# Go to: https://www.runpod.io/console/serverless → Your Endpoint → Logs

# Update deployment (after code changes)
docker build -t ghcr.io/YOUR_USERNAME/intimai-backend:latest .
docker push ghcr.io/YOUR_USERNAME/intimai-backend:latest
# Then in RunPod Console: Endpoint Settings → Refresh Image
```

---

## Files Reference

| File | Purpose |
|------|---------|
| [RUNPOD_DEPLOYMENT_GUIDE.md](RUNPOD_DEPLOYMENT_GUIDE.md) | Complete deployment guide with troubleshooting |
| [build-and-deploy.ps1](build-and-deploy.ps1) | Automated build & push script |
| [test-runpod-endpoint.ps1](test-runpod-endpoint.ps1) | Endpoint testing utility |
| [handler.py](handler.py) | RunPod serverless handler with AWS integration |
| [safety_checker.py](safety_checker.py) | AWS Rekognition wrapper |
| [s3_uploader.py](s3_uploader.py) | S3 audit trail uploader |
| [Dockerfile](Dockerfile) | Container configuration |
| [.env.example](.env.example) | AWS credentials template |

---

## Cost Estimate

**RunPod Serverless (RTX 4090):**
- Per generation: ~$0.006 (18 seconds active time)
- Monthly (10,000 images): ~$60

**AWS Services:**
- Rekognition: 10,000 checks × $0.001 = $10/month
- S3 storage: ~$2/month (with 6-month auto-delete)

**Total: ~$72/month for 10,000 generations**

Savings: Min workers = 0 (no idle GPU costs)

---

## Security Checklist

Before production:
- [ ] AWS credentials only in RunPod env vars (not in code)
- [ ] `.env` file in `.gitignore`
- [ ] Docker image is public (or private with RunPod registry auth)
- [ ] RunPod API key stored in Vercel env vars (not hardcoded)
- [ ] S3 lifecycle rule active (180-day auto-delete)
- [ ] IAM user has minimal permissions
- [ ] Consider rotating AWS keys every 90 days

---

## Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| Container failed to start | Check if image is public, verify in RunPod logs |
| AWS credentials not found | Verify all 4 env vars in RunPod template settings |
| Timeout waiting for API | Increase `API_STARTUP_TIMEOUT` in handler.py |
| S3 upload failed | Check IAM permissions, verify bucket region |
| ModuleNotFoundError: runpod | Rebuild image (pip install runpod in Dockerfile) |

See [RUNPOD_DEPLOYMENT_GUIDE.md](RUNPOD_DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

---

## Status Tracking

- [x] AWS IAM user created
- [x] S3 bucket created with lifecycle rule
- [x] Backend code with safety layers completed
- [x] Local testing validated
- [x] Deployment guides created
- [ ] **→ Docker image built**
- [ ] **→ Image pushed to registry**
- [ ] **→ RunPod endpoint created**
- [ ] **→ Endpoint tested with AWS integration**
- [ ] **→ Frontend integrated**
- [ ] **→ Production deployment**

**Current Step:** Build Docker image using `build-and-deploy.ps1`

---

## Support & Documentation

- **Full Guide:** [RUNPOD_DEPLOYMENT_GUIDE.md](RUNPOD_DEPLOYMENT_GUIDE.md)
- **Session Handoff:** [docs/handoff/SESSION_HANDOFF_2026-02-27.md](docs/handoff/SESSION_HANDOFF_2026-02-27.md)
- **RunPod Docs:** https://docs.runpod.io/serverless/overview
- **GitHub Container Registry:** https://docs.github.com/packages

---

**Last Updated:** February 27, 2026  
**Status:** Ready for deployment 🚀
