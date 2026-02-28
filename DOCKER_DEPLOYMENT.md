# Docker Deployment Guide with Environment Variables

## Quick Start (Docker + Environment Variables)

### Local Development with Docker

```bash
cd Nudify-Generator

# 1. Generate environment variables
python setup_env_vars.py

# 2. Build Docker image
docker build -t nudify-backend:latest .

# 3. Run container with .env.local
docker run -p 8000:8000 \
  --env-file .env.local \
  nudify-backend:latest

# Done! API running at http://localhost:8000
```

### Production with Docker Compose

```bash
# .env.production (source of truth for prod)
docker-compose -f docker-compose.yml --env-file .env.production up -d
```

---

## Option 1: Dockerfile (Simple)

Create `Dockerfile` in `Nudify-Generator/`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment defaults (will be overridden at runtime)
ENV PYTHONUNBUFFERED=1
ENV WATERMARK_ENABLED=true
ENV VISIBLE_BADGE_ENABLED=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "test_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build & Run:**
```bash
docker build -t nudify-backend:latest .

# With .env.local
docker run -p 8000:8000 --env-file .env.local nudify-backend:latest

# Or individual variables
docker run -p 8000:8000 \
  -e C2PA_PRIVATE_KEY_BASE64="$(cat .env.local | grep C2PA_PRIVATE_KEY_BASE64 | cut -d= -f2)" \
  -e C2PA_CERT_BASE64="$(cat .env.local | grep C2PA_CERT_BASE64 | cut -d= -f2)" \
  -e WATERMARK_ENABLED=true \
  nudify-backend:latest
```

---

## Option 2: Docker Compose (Recommended)

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./Nudify-Generator
      dockerfile: Dockerfile
    container_name: nudify-backend
    ports:
      - "8000:8000"
    environment:
      # Load from .env.local or .env.production
      - C2PA_PRIVATE_KEY_BASE64=${C2PA_PRIVATE_KEY_BASE64}
      - C2PA_CERT_BASE64=${C2PA_CERT_BASE64}
      - WATERMARK_ENABLED=${WATERMARK_ENABLED:-true}
      - VISIBLE_BADGE_ENABLED=${VISIBLE_BADGE_ENABLED:-true}
      - DATABASE_URL=${DATABASE_URL}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./Nudify-Generator:/app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    networks:
      - nudify-network

  # Optional: Frontend service
  frontend:
    build:
      context: ./nudify-app-nextjs
      dockerfile: Dockerfile
    container_name: nudify-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_RUNPOD_URL=http://backend:8000/api/runpod/generate
    depends_on:
      - backend
    networks:
      - nudify-network

networks:
  nudify-network:
    driver: bridge
```

**Deploy:**
```bash
# Local development
docker-compose up

# Production (with separate .env.production)
docker-compose --env-file .env.production up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

---

## Option 3: Multi-Stage Build (Production)

For smaller, optimized production images:

```dockerfile
# Stage 1: Build
FROM python:3.11 as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY . .

# Set environment
ENV PYTHONUNBUFFERED=1
ENV WATERMARK_ENABLED=true

# Run
CMD ["uvicorn", "test_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build (smaller image):**
```bash
docker build -t nudify-backend:prod -f Dockerfile.prod .
```

---

## Environment Variable Setup for Docker

### Step 1: Generate .env.local (Local Dev)
```bash
python setup_env_vars.py

# This creates .env.local with base64 credentials
cat .env.local
```

### Step 2: Create .env.production (Production)
```bash
# Copy template
cp .env.local .env.production

# OR manually set (for production deployment):
cat > .env.production << EOF
C2PA_PRIVATE_KEY_BASE64="MIIEvQIBADANBgk..."
C2PA_CERT_BASE64="MIIDXTCCAkWgAwIBAgI..."
WATERMARK_ENABLED=true
VISIBLE_BADGE_ENABLED=true
DATABASE_URL="postgresql://prod-user:password@prod-host/prod-db"
EOF
```

### Step 3: Run Docker with Environment
```bash
# Option A: Using --env-file
docker run -p 8000:8000 --env-file .env.local nudify-backend:latest

# Option B: Using docker-compose
docker-compose --env-file .env.production up -d

# Option C: AWS/Cloud (see below)
```

---

## Cloud Deployment with Docker

### AWS ECR + ECS

```bash
# 1. Push image to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag nudify-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/nudify-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/nudify-backend:latest

# 2. In ECS Task Definition, add environment variables:
# - C2PA_PRIVATE_KEY_BASE64: From Secrets Manager
# - C2PA_CERT_BASE64: From Secrets Manager
# - WATERMARK_ENABLED: true
# - VISIBLE_BADGE_ENABLED: true
```

### Docker Hub

```bash
# Push to Docker Hub
docker tag nudify-backend:latest yourusername/nudify-backend:latest
docker push yourusername/nudify-backend:latest

# Pull and run on any machine
docker run -p 8000:8000 \
  --env-file .env.production \
  yourusername/nudify-backend:latest
```

### Heroku

```bash
# Create heroku.yml
cat > heroku.yml << EOF
build:
  docker:
    web: Dockerfile
run:
  web: uvicorn test_api:app --host 0.0.0.0 --port \$PORT
EOF

# Deploy
heroku container:push web
heroku container:release web

# Set config variables
heroku config:set C2PA_PRIVATE_KEY_BASE64="..."
heroku config:set C2PA_CERT_BASE64="..."
heroku config:set WATERMARK_ENABLED=true
```

### Railway / Render

1. Connect GitHub repository
2. In dashboard → Environment Variables:
   ```
   C2PA_PRIVATE_KEY_BASE64 = MIIEvQIBADA...
   C2PA_CERT_BASE64 = MIIDXTCCAkWg...
   WATERMARK_ENABLED = true
   VISIBLE_BADGE_ENABLED = true
   ```
3. Deploy automatically

---

## Docker + Environment Variables Workflow

### Local Development
```bash
# 1. Setup environment variables
python setup_env_vars.py
# Creates: .env.local

# 2. Build image
docker build -t nudify-backend .

# 3. Run with env file
docker run -p 8000:8000 --env-file .env.local nudify-backend

# 4. Or use docker-compose
docker-compose up
```

### Production Deployment
```bash
# 1. Generate production env file
python setup_env_vars.py  # Use on secure machine
# Creates: .env.local (copy to .env.production)

# 2. Push to registry
docker build -t nudify-backend:prod .
docker push registry.example.com/nudify-backend:prod

# 3. Deploy with environment
# Option A: Via env file
docker run -p 8000:8000 \
  --env-file /secure/path/.env.production \
  registry.example.com/nudify-backend:prod

# Option B: Via secrets manager
docker run -p 8000:8000 \
  -e C2PA_PRIVATE_KEY_BASE64="$(aws secretsmanager get-secret-value --secret-id nudify/c2pa-key --query SecretString --output text)" \
  -e C2PA_CERT_BASE64="$(aws secretsmanager get-secret-value --secret-id nudify/c2pa-cert --query SecretString --output text)" \
  registry.example.com/nudify-backend:prod

# Option C: Via docker-compose with .env.production
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## Verification Inside Docker

### Check if credentials loaded:
```bash
docker exec <container-id> python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('✓ C2PA_PRIVATE_KEY_BASE64' if os.getenv('C2PA_PRIVATE_KEY_BASE64') else '✗ Missing')
print('✓ C2PA_CERT_BASE64' if os.getenv('C2PA_CERT_BASE64') else '✗ Missing')
print('✓ WATERMARK_ENABLED' if os.getenv('WATERMARK_ENABLED') else '✗ Missing')
"
```

### Run watermarking test:
```bash
docker exec <container-id> python test_watermarking.py
```

### Check logs:
```bash
docker logs -f <container-id>

# Should show:
# ✓ C2PA credentials loaded from environment variables
# ✓ Applied compliance watermarks
```

---

## Complete docker-compose.prod.yml (Production-Ready)

```yaml
version: '3.8'

services:
  backend:
    image: registry.example.com/nudify-backend:v1.0.0
    container_name: nudify-backend-prod
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    environment:
      # Compliance Watermarking
      C2PA_PRIVATE_KEY_BASE64: ${C2PA_PRIVATE_KEY_BASE64}
      C2PA_CERT_BASE64: ${C2PA_CERT_BASE64}
      WATERMARK_ENABLED: ${WATERMARK_ENABLED:-true}
      VISIBLE_BADGE_ENABLED: ${VISIBLE_BADGE_ENABLED:-true}
      
      # Database
      DATABASE_URL: ${DATABASE_URL}
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_KEY: ${SUPABASE_KEY}
      
      # Python
      PYTHONUNBUFFERED: 1
      PYTHONBUFFERED: 0
    
    ports:
      - "8000:8000"
    
    networks:
      - production
    
    # Optional: Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: nudify-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    networks:
      - production

networks:
  production:
    driver: bridge

volumes:
  db_data:
```

**Deploy:**
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Monitor
docker-compose -f docker-compose.prod.yml logs -f backend

# Stop
docker-compose -f docker-compose.prod.yml down
```

---

## Security Best Practices for Docker

1. **Never** commit `.env.local` or `.env.production` to git
   ```bash
   # Verify .gitignore
   git check-ignore .env.local  # Should say "ignored"
   ```

2. **Use secrets manager** for production credentials
   ```bash
   # AWS
   aws secretsmanager create-secret --name nudify/c2pa-credentials \
     --secret-string '{"C2PA_PRIVATE_KEY_BASE64":"...","C2PA_CERT_BASE64":"..."}'
   ```

3. **Run as non-root**:
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER 1000
   ```

4. **Use minimal base images**:
   ```dockerfile
   FROM python:3.11-slim  # 160MB instead of 900MB+
   ```

5. **Scan for vulnerabilities**:
   ```bash
   docker scan nudify-backend:latest
   ```

---

## Summary

| Scenario | Command |
|----------|---------|
| **Local dev** | `docker run -p 8000:8000 --env-file .env.local nudify-backend` |
| **Local with compose** | `docker-compose up` |
| **Production** | `docker-compose -f docker-compose.prod.yml --env-file .env.production up -d` |
| **Cloud (AWS/Render)** | Set env vars in dashboard, push image |
| **Check credentials loaded** | `docker exec <id> python test_watermarking.py` |

All Docker deployments use the same environment variable system (`C2PA_PRIVATE_KEY_BASE64`, `C2PA_CERT_BASE64`, etc).
