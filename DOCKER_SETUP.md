# Docker Setup Guide for Fooocus Serverless

## Prerequisites
- Docker Desktop for Windows installed
- At least 8GB of RAM allocated to Docker
- NVIDIA GPU (optional but recommended) with NVIDIA Container Toolkit

## Quick Start

### 1. Build the Docker Image
```powershell
cd c:\working folder\nudify-backend
docker build -t fooocus-serverless:latest .
```

### 2. Run with Docker Compose (Recommended)
```powershell
cd c:\working folder\nudify-backend
docker-compose up -d
```

### 3. Run Standalone
```powershell
docker run -it --name fooocus -p 7866:7866 -v fooocus_models:/app/models fooocus-serverless:latest
```

### 4. Test the API
```powershell
$payload = @{
    "prompt" = "A beautiful sunset over mountains"
    "base_model_name" = "juggernautXL_v8Rundiffusion.safetensors"
    "image_number" = 1
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:7866/v1/engine/generation" `
  -Method POST `
  -ContentType "application/json" `
  -Body $payload
```

## Deployment on RunPod Serverless

### Method 1: Using Docker Registry

1. **Push to Docker Hub:**
   ```powershell
   docker tag fooocus-serverless:latest yourusername/fooocus-serverless:latest
   docker push yourusername/fooocus-serverless:latest
   ```

2. **Create RunPod Serverless Endpoint:**
   - Go to https://www.runpod.io/console/serverless
   - Click "New Endpoint"
   - Select "Browse all" and search for your image
   - Or manually specify: `yourusername/fooocus-serverless:latest`
   - Configure:
     - GPU: Select appropriate GPU (A40, A6000, etc.)
     - Memory: 8GB minimum
     - Container Disk: 50GB minimum (for models)
   - Deploy

### Method 2: Upload Dockerfile

1. Create a `.tar` file of your project:
   ```powershell
   cd c:\working folder
   tar -czf fooocus-serverless.tar.gz nudify-backend\
   ```

2. Upload to RunPod and deploy

## Environment Variables

Configure these in your RunPod endpoint:
```
CUDA_VISIBLE_DEVICES=0
PYTHONUNBUFFERED=1
PORT=7866
```

## Model Management

Models are stored in `/app/models` inside the container. For persistent storage on RunPod:

```json
{
  "input": {
    "prompt": "A beautiful sunset",
    "base_model_name": "juggernautXL_v8Rundiffusion.safetensors"
  }
}
```

## Troubleshooting

### GPU not detected in Docker
- Ensure NVIDIA Container Toolkit is installed: `nvidia-ctk --version`
- Add to docker-compose.yml or docker run:
  ```
  --gpus all
  ```

### Port already in use
```powershell
netstat -ano | findstr :7866
taskkill /PID <PID> /F
```

### Out of memory
- Increase Docker's memory allocation in Docker Desktop Settings
- Or reduce batch size in Fooocus launch.py

## Integration with Frontend

Update your `index.html` API_BASE:

**Local:**
```javascript
const API_BASE = "http://localhost:7866";
```

**RunPod Serverless:**
```javascript
const API_URL = "https://api.runpod.io/v1/YOUR_ENDPOINT_ID/run";
const RUNPOD_API_KEY = "YOUR_API_KEY";
```

Then modify the generate function to use RunPod's request format.

## Next Steps

1. ✅ Build the Docker image
2. ✅ Test locally with docker-compose
3. ✅ Push to Docker Hub
4. ✅ Create RunPod Serverless endpoint
5. ✅ Update frontend to call the endpoint
6. ✅ Monitor and scale as needed
