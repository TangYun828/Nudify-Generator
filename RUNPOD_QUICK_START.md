# RunPod Quick Setup (5 Minutes)

## Start Here

### Step 1: Get Credentials (1 minute)
```bash
cd Nudify-Generator
python setup_env_vars.py

# Copy these values:
cat .env.local
```

### Step 2: Build & Push Image (2 minutes)
```bash
docker build -t nudify-backend:runpod .
docker tag nudify-backend:runpod yourusername/nudify-backend:runpod
docker login
docker push yourusername/nudify-backend:runpod
```

### Step 3: Create RunPod Endpoint (2 minutes)

1. Go to https://www.runpod.io/ → Sign in
2. **Serverless** → **Create Endpoint**
3. Fill in:
   - **Name**: nudify-backend
   - **Docker Image**: yourusername/nudify-backend:runpod
   - **Container Port**: 8000
   - **GPU**: RTX 4090 (or your choice)

4. **Advanced Settings** → **Environment Variables**:
   ```
   C2PA_PRIVATE_KEY_BASE64=MIIEvQIBADANBgk... (paste from .env.local)
   C2PA_CERT_BASE64=MIIDXTCCAkWgAwIBAg... (paste from .env.local)
   WATERMARK_ENABLED=true
   VISIBLE_BADGE_ENABLED=true
   ```

5. Click **Create Endpoint**
6. Wait ~1 minute, copy the endpoint URL: `https://api-xxxxx.runpod.io`

### Step 4: Update Frontend (.env.local)
```bash
cd ../nudify-app-nextjs
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=https://api-xxxxx.runpod.io
NEXT_PUBLIC_RUNPOD_URL=https://api-xxxxx.runpod.io/api/runpod/generate
EOF
```

### Step 5: Test
```bash
npm run dev
# Visit http://localhost:3000
# Login and generate an image!
```

---

## Verify Setup

### Check Endpoint Health
```bash
curl https://api-xxxxx.runpod.io/health
# Response: {"status": "ok"}
```

### Check Watermarking
```bash
# Generate test image via API
TOKEN="your-jwt-token"
curl -X POST https://api-xxxxx.runpod.io/api/runpod/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"test"}}'

# Should return image with watermark
```

### Check Logs
- RunPod Console → **Endpoints** → **Logs**
- Filter by "watermark" or "C2PA"
- Should see: "✓ Applied compliance watermarks"

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Module not found" | Docker image missing dependencies. Rebuild: `docker build --no-cache -t ...` |
| "Credentials not loaded" | Base64 strings truncated in env vars. Copy entire value from `.env.local` |
| "Port 8000 not accessible" | Endpoint still starting. Wait 60 seconds and retry |
| "High latency (>30s)" | Pod initializing. Switch to faster GPU or use Pod instead of Serverless |
| "Out of memory" | Reduce `image_number` to 1 in requests |

---

## Cost Saving Tips

1. **Use Serverless** (not Pod) for sporadic use
2. **RTX 4090 is fastest** but A5000 is more affordable
3. **Monitor usage**: RunPod → Endpoints → Usage
4. **Set auto-scaler**: Endpoints → Settings → Max Instances

---

## Next Steps

- ✅ Endpoint running on RunPod
- ✅ Frontend configured
- [ ] Monitor logs daily for errors
- [ ] Set up payment method notification
- [ ] Scale GPU if response time > 10s
- [ ] Add custom domain (Optional)

**Support**: If stuck, check [RunPod Docs](https://docs.runpod.io/)
