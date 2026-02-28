# RunPod Deployment Guide

## Quick Start

### Option 1: Serverless Endpoint (Recommended)

1. **Create RunPod Account** → https://www.runpod.io/
2. **Upload Docker Image To Registry**
   ```bash
   docker build -t nudify-backend:runpod .
   docker tag nudify-backend:runpod yourusername/nudify-backend:runpod
   docker login
   docker push yourusername/nudify-backend:runpod
   ```

3. **Create Serverless Endpoint**
   - RunPod Console → Serverless → New Endpoint
   - **Name**: nudify-backend
   - **Container Image**: yourusername/nudify-backend:runpod
   - **Container Port**: 8000
   - **GPU**: Select GPU type (RTX 4090, A5000, etc.)
   - **Environment Variables**:
     ```
     C2PA_PRIVATE_KEY_BASE64=MIIEvQIBADANBgkqhk...
     C2PA_CERT_BASE64=MIIDXTCCAkWgAwIBAg...
     WATERMARK_ENABLED=true
     VISIBLE_BADGE_ENABLED=true
     ```

4. **Update Frontend → Use RunPod Endpoint**
   In `nudify-app-nextjs/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=https://api-xxxxx.runpod.io
   NEXT_PUBLIC_RUNPOD_URL=https://api-xxxxx.runpod.io/api/runpod/generate
   ```

---

### Option 2: RunPod Pod (VPS-Style)

Similar to Serverless but keeps instance running 24/7.

1. **Create RunPod Pod**
   - RunPod Console → Pods → Deploy
   - **Container Image**: yourusername/nudify-backend:runpod
   - **GPU**: Select GPU
   - **Port Expose**: 8000
   - **Environment Variables**: (same as serverless)

2. **Connect to Pod**
   ```bash
   # Get SSH connection details from RunPod dashboard
   ssh user@your-pod-hostname
   
   # Pull latest image
   docker pull yourusername/nudify-backend:runpod
   docker run -p 8000:8000 \
     -e C2PA_PRIVATE_KEY_BASE64="..." \
     -e C2PA_CERT_BASE64="..." \
     -e WATERMARK_ENABLED=true \
     yourusername/nudify-backend:runpod
   ```

---

## Environment Variables Setup for RunPod

### Method 1: RunPod Docker Environment (Recommended)

In RunPod Console → Endpoint → Environment:

```
C2PA_PRIVATE_KEY_BASE64=MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJT...
C2PA_CERT_BASE64=MIIDXTCCAkWgAwIBAgIJAKoJHROzI5HDMA0GCSqGSIb3DQEBAQUADDB...
WATERMARK_ENABLED=true
VISIBLE_BADGE_ENABLED=true
DATABASE_URL=postgresql://user:pass@host/db
```

### Method 2: RunPod Secrets (Most Secure)

```bash
# Add secrets in RunPod Console → Account → Secrets
runpod secret create C2PA_PRIVATE_KEY_BASE64 "MIIEvQIBADANBgkqhk..."
runpod secret create C2PA_CERT_BASE64 "MIIDXTCCAkWgAwIBAg..."

# In docker-compose.yml or environment
C2PA_PRIVATE_KEY_BASE64=${RUNPOD_SECRET_C2PA_PRIVATE_KEY}
C2PA_CERT_BASE64=${RUNPOD_SECRET_C2PA_CERT}
```

### Method 3: Base64 File Mount

```bash
# Create base64 secret files
echo "MIIEvQIBADAN..." | base64 > /secrets/c2pa_key.b64
echo "MIIDXTCCAk..." | base64 > /secrets/c2pa_cert.b64

# Mount in RunPod → Volumes
# Container: /secrets/c2pa_key.b64
# Host: /root/.runpod/secrets/c2pa_key.b64

# In Python:
import os
key = open('/secrets/c2pa_key.b64').read().strip()
os.environ['C2PA_PRIVATE_KEY_BASE64'] = key
```

---

## Set Environment Variables in RunPod

### Step 1: Get Base64 Credentials

```bash
# If using setup_env_vars.py from local
cd Nudify-Generator
python setup_env_vars.py

# Extract from .env.local
cat .env.local | grep C2PA_PRIVATE_KEY_BASE64
cat .env.local | grep C2PA_CERT_BASE64
# Copy these values
```

### Step 2: Add to RunPod Console

1. Go to **RunPod Dashboard** → **Endpoints** (or Pods)
2. Click on your endpoint → **Settings** → **Environment**
3. Add environment variables:
   ```
   C2PA_PRIVATE_KEY_BASE64 = (paste full base64 string)
   C2PA_CERT_BASE64 = (paste full base64 string)
   WATERMARK_ENABLED = true
   VISIBLE_BADGE_ENABLED = true
   ```
4. Save and restart endpoint

### Step 3: Verify Setup

```bash
# From your local machine
RUNPOD_API_KEY="your-api-key" runpod env list
# Should show your environment variables

# Or test via API
curl -X POST https://api-xxxxx.runpod.io/api/runpod/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"test"}}'
```

---

## Dockerfile Optimized for RunPod

Existing Dockerfile works, but for RunPod consider:

```dockerfile
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3.11 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set Python to unbuffered
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "test_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## API Integration with RunPod

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=https://api-xxxxx.runpod.io
NEXT_PUBLIC_RUNPOD_URL=https://api-xxxxx.runpod.io/api/runpod/generate
```

### Frontend API Call

```typescript
// lib/api.ts
const RUNPOD_ENDPOINT = process.env.NEXT_PUBLIC_RUNPOD_URL;

export async function generateImage(prompt: string, token: string) {
  const response = await fetch(RUNPOD_ENDPOINT, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      input: {
        prompt: prompt,
        image_number: 1
      }
    })
  });
  
  return response.json();
}
```

### Test RunPod Integration

```bash
# Login
TOKEN=$(curl -X POST https://api-xxxxx.runpod.io/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}' \
  | jq -r '.access_token')

# Generate image
curl -X POST https://api-xxxxx.runpod.io/api/runpod/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "beautiful sunset",
      "image_number": 1
    }
  }' | jq .
```

---

## Verify Watermarking on RunPod

### Option 1: SSH into Pod

```bash
# If using Pod (not serverless)
ssh user@your-pod-ip

# Test watermarking
python test_watermarking.py
# Should show: ✓ ALL TESTS PASSED

# Check logs
docker logs <container-id> | grep -i watermark
# Should show: ✓ Applied compliance watermarks
```

### Option 2: API Test

```bash
# Send request and check response
curl -X POST https://api-xxxxx.runpod.io/api/runpod/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"test"}}' \
  -o output.png

# Check metadata
file output.png
# Should show: PNG image

# Verify watermark exists (latent watermark is invisible)
# Download and inspect with Python:
# from PIL import Image
# img = Image.open('output.png')
# print(img.info)  # Should have C2PA metadata
```

---

## RunPod: Serverless vs Pod Comparison

| Feature | Serverless | Pod |
|---------|-----------|-----|
| **Cost** | Pay per request | Pay per hour |
| **Startup Time** | 10-30 seconds | Instant (always running) |
| **Scaling** | Automatic | Manual |
| **Best For** | Bursty traffic | Continuous service |
| **Setup** | Easier | More control |
| **Type** | Lambda-like | VPS-like |

**Recommendation**: Start with **Serverless** for cost savings, upgrade to **Pod** if you exceed 100 requests/day.

---

## RunPod Monitoring

### Check Endpoint Health

```bash
# Get endpoint status
curl -X GET https://api-xxxxx.runpod.io/health
# Expected: {"status": "ok"}

# Check if credentials loaded
curl -X GET https://api-xxxxx.runpod.io/debug/credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### View Logs

**In RunPod Console**:
1. Endpoint → Logs
2. Filter by: "watermark", "error", "compliance"
3. Look for: "✓ C2PA credentials loaded"

### Endpoint Metrics

- **Requests/hour**: RunPod Dashboard → Metrics
- **Response time**: Should be < 5s (includes GPU processing)
- **Error rate**: Should be < 0.1%

---

## Troubleshooting RunPod

### Problem: Credentials Not Loading

```bash
# Check if env vars set
curl -X POST https://api-xxxxx.runpod.io/debug/env \
  -H "Authorization: Bearer $TOKEN"

# If missing, add to RunPod Console → Environment

# Restart endpoint
# Dashboard → Endpoint → Restart
```

### Problem: High Latency

```bash
# Check GPU utilization
# Dashboard → Pod → Monitor

# Options:
# 1. Switch to faster GPU (A100, RTX 4090)
# 2. Enable Pod (not serverless) for consistent load
# 3. Reduce image resolution
```

### Problem: Out of Memory

```bash
# Reduce batch size
# Edit test_api.py → num_images = 1 (not higher)

# Or upgrade GPU memory
# Dashboard → Edit Pod → Select GPU with more VRAM
```

### Problem: Watermark Not Applied

```bash
# SSH into pod
ssh user@pod-ip

# Check logs
docker logs <container-id> | tail -50

# Run test
python test_watermarking.py

# If fails, check:
# - C2PA_PRIVATE_KEY_BASE64 set correctly
# - C2PA_CERT_BASE64 set correctly
# - Base64 strings not truncated
```

---

## Security Best Practices for RunPod

1. **Never expose base64 in code**
   ✓ Use environment variables only
   ```python
   import os
   key = os.getenv('C2PA_PRIVATE_KEY_BASE64')  # Good
   key = "MIIEvQI..."  # Bad
   ```

2. **Use RunPod Secrets for sensitive data**
   ```bash
   runpod secret create C2PA_PRIVATE_KEY "base64string"
   ```

3. **Restrict API Access**
   - Only allow requests from your frontend domain
   - Use JWT tokens (already implemented)
   - Rate limit per user

4. **Enable HTTPS**
   - RunPod automatically provides SSL
   - Verify certificate: `curl https://api-xxxxx.runpod.io`

5. **Disable Debug Endpoints in Production**
   ```python
   # test_api.py
   if os.getenv('ENVIRONMENT') == 'production':
       # Remove debug routes
       app.openapi = lambda: {}  # Hide API docs
   ```

---

## Complete RunPod Deployment Checklist

- [ ] Generate credentials: `python setup_env_vars.py`
- [ ] Build Docker image: `docker build -t nudify-backend:runpod .`
- [ ] Push to Docker Hub: `docker push yourusername/nudify-backend:runpod`
- [ ] Create RunPod account and add payment method
- [ ] Create Serverless Endpoint (or Pod)
- [ ] Set environment variables in RunPod console
- [ ] Update frontend `.env.local` with RunPod endpoint URL
- [ ] Test API: `curl https://api-xxxxx.runpod.io/health`
- [ ] Test authentication: Login via frontend
- [ ] Test image generation: Generate image and verify watermark
- [ ] Test watermarking: Check output has C2PA metadata
- [ ] Monitor logs: Check for compliance watermarking messages
- [ ] Verify compliance: Output has visible watermark badge

---

## RunPod Cost Estimation

**Serverless Example:**
- GPU: RTX 4090 ($0.90/hour)
- 10 requests/hour × 30 seconds each = 5 minutes/hour
- Cost per image: ($0.90 × 5 min / 60 min) / 10 requests = **$0.0075/image**
- 1000 images/month = $7.50

**Pod Example:**
- RTX 4090: $0.90/hour × 730 hours/month = **$657/month**
- Unlimited images (per pod capacity)

**Recommendation**: 
- < 100 requests/day → Use Serverless
- > 100 requests/day → Use Pod

---

## Quick RunPod Setup (5 minutes)

```bash
# 1. Get credentials
cd Nudify-Generator
python setup_env_vars.py
export PRIVATE_KEY=$(grep C2PA_PRIVATE_KEY_BASE64 .env.local | cut -d= -f2)
export CERT=$(grep C2PA_CERT_BASE64 .env.local | cut -d= -f2)

# 2. Build and push image
docker build -t nudify-backend:runpod .
docker tag nudify-backend:runpod yourusername/nudify-backend:runpod
docker login
docker push yourusername/nudify-backend:runpod

# 3. In RunPod Console:
# - Create Serverless Endpoint
# - Image: yourusername/nudify-backend:runpod
# - Port: 8000
# - GPU: RTX 4090
# - Environment Variables:
#   C2PA_PRIVATE_KEY_BASE64=$PRIVATE_KEY
#   C2PA_CERT_BASE64=$CERT
#   WATERMARK_ENABLED=true
#   VISIBLE_BADGE_ENABLED=true

# 4. Update frontend
cd ../nudify-app-nextjs
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=https://api-xxxxx.runpod.io
NEXT_PUBLIC_RUNPOD_URL=https://api-xxxxx.runpod.io/api/runpod/generate
EOF

# 5. Test
npm run dev
# Visit http://localhost:3000 and generate an image
```

---

## References

- **RunPod Docs**: https://docs.runpod.io/
- **RunPod API**: https://docs.runpod.io/api/serverless/
- **Docker Registry**: https://hub.docker.com/
- **Uvicorn**: https://www.uvicorn.org/
- **C2PA Standard**: https://c2pa.org/
