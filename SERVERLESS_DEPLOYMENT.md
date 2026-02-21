# RunPod Serverless Deployment Guide

## Overview
This guide covers deploying the Fooocus handler as a RunPod serverless endpoint to serve app.html requests.

## Prerequisites
- Docker image built and pushed to GitHub Container Registry (ghcr.io)
- RunPod account with serverless capabilities
- Your app.html frontend ready to configure

## Step 1: Create RunPod Serverless Endpoint

1. Go to [RunPod Console](https://www.runpod.io/console)
2. Click "Serverless" → "New Template"
3. Configure:
   - **Container Image**: `ghcr.io/YOUR_USERNAME/fooocus-serverless:latest`
   - **Container Disk**: 40 GB (for models)
   - **GPU**: RTX 4090 or similar (NVIDIA required)
   - **vCPU**: 4
   - **Memory**: 16 GB
   - **Expose HTTP Ports**: 7865 (for Fooocus UI), 7866 (optional)

4. Click "Deploy" → Choose a region → Confirm

5. Wait for pod to start (5-10 minutes)

## Step 2: Get Endpoint Details

1. Once running, copy the **Endpoint ID** (format: `abc123def456...`)
2. Generate an **API Key**:
   - In RunPod Console → Account → API Keys
   - Create new API key
   - Copy the full key

## Step 3: Configure Frontend

Edit `app.html` (around line 525) in fetchStream function:

```javascript
const RUNPOD_ENDPOINT_ID = 'YOUR_ENDPOINT_ID'; // Paste your endpoint ID
const RUNPOD_API_KEY = 'YOUR_API_KEY';       // Paste your API key
```

Save the file.

## Step 4: Test with Frontend

1. Open `app.html` in browser
2. Configuration banner should show the setup reminder
3. Enter a prompt and click "Generate"
4. Wait 30-120 seconds for image

**Monitor Progress:**
- Check RunPod Console pod logs in real-time
- Handler logs will show generation details
- Status updates in browser

## API Response Format

The handler returns:
```json
{
  "output": {
    "images": ["data:image/png;base64,..."],
    "progress": 100,
    "message": "Successfully generated 1 image(s)"
  }
}
```

Images are base64-encoded and ready for display.

## Handler Input Format (app.html)

```json
{
  "input": {
    "prompt": "a beautiful sunset",
    "negative_prompt": "",
    "image_number": 1,
    "base_model_name": "onlyfornsfw118_v20.safetensors",
    "output_format": "png",
    "aspect_ratios_selection": "1024*1024"
  }
}
```

## Troubleshooting

### "Error: Configure RUNPOD_ENDPOINT_ID"
- You haven't replaced the placeholder endpoint ID in app.html
- Get the ID from RunPod Console

### "Error: 401 Unauthorized"
- API key is missing or incorrect
- Check your RunPod API key in Console → Account

### "Error: 503 Service Unavailable"
- Endpoint not running or still starting
- Check pod status in RunPod Console
- Restart the pod if needed

### "Failed to start Fooocus API" in logs
- Check pod logs in RunPod Console
- Verify container image has all dependencies
- Wait longer for pod initialization (up to 5 minutes)

### Image generation is slow (>120 seconds)
- Check pod specifications (RTX 4090+ recommended)
- Verify model loaded correctly (check pod logs)
- Larger aspect ratios take longer (try 768x768 first)

## Docker Build

If you need to rebuild the Docker image:

```bash
# Build locally (requires Docker + NVIDIA support)
docker build -t fooocus-serverless:latest .

# Or use GitHub Actions (push to repo):
# - File: .github/workflows/docker-build.yml
# - Workflow automatically builds and pushes to ghcr.io on every push
```

## Files

- `handler.py` - RunPod serverless handler (receives requests, calls Fooocus, returns images)
- `Dockerfile` - Container configuration with Fooocus + NSFW model
- `app.html` - Frontend that sends requests to your endpoint
- `entrypoint.sh` - Container startup script

## Model Management

The Dockerfile includes:
- `onlyfornsfw118_v20.safetensors` - 7GB NSFW-specialized model
- Auto-downloaded during image build

To change the model:
1. Edit Dockerfile, change HuggingFace URL
2. Rebuild and redeploy Docker image
3. Update `base_model_name` in app.html (around line 610)

## Cost Optimization

- Stop unused endpoints to save credits
- Use cheaper GPU types for testing
- Cache models in Docker layer (already done)
- Run during off-peak hours if available

## Next Steps

1. ✅ Docker image ready: `ghcr.io/YOUR_USERNAME/fooocus-serverless:latest`
2. ⏳ Deploy to RunPod Serverless
3. ⏳ Configure app.html with endpoint/key
4. ⏳ Test generation
5. ⏳ Share endpoint with users (share app.html, keep API key secure)
