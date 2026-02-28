# Quick Docker Setup

## Local Development (30 seconds)

```bash
# 1. Generate environment variables
cd Nudify-Generator
python setup_env_vars.py

# 2. Go to project root and start containers
cd ..
docker-compose up

# 3. Done! Access services:
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:3000
```

**That's it!** Both backend and frontend start automatically with your watermarking credentials.

---

## Production Deployment

### Step 1: Build Images

```bash
# Backend
docker build -t nudify-backend:prod ./Nudify-Generator

# Frontend (if using Next.js)
docker build -t nudify-frontend:prod ./nudify-app-nextjs
```

### Step 2: Create .env.production

```bash
# Option A: Use setup script to generate, then rename
cd Nudify-Generator
python setup_env_vars.py
mv .env.local ../.env.production
cd ..

# Option B: Manually create (on secure machine)
cat > .env.production << EOF
C2PA_PRIVATE_KEY_BASE64="MIIEvQIBADANBgkqhk..."
C2PA_CERT_BASE64="MIIDXTCCAkWgAwIBAg..."
WATERMARK_ENABLED=true
VISIBLE_BADGE_ENABLED=true
DATABASE_URL="postgresql://user:pass@host/db"
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIs..."
RUNPOD_API_KEY="optional-api-key"
NEXTAUTH_SECRET="your-random-secret-key"
NEXTAUTH_URL="https://youromain.com"
NEXT_PUBLIC_API_URL="https://api.yourdomain.com"
EOF
```

### Step 3: Deploy with Docker Compose

```bash
# Start services
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Check if running
docker ps

# Stop services
docker-compose -f docker-compose.prod.yml down
```

---

## Verify Everything Works

### Check Backend
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### Check Watermarking
```bash
docker exec nudify-backend-prod python test_watermarking.py
# Expected: ✓ ALL TESTS PASSED
```

### Check Frontend
```bash
# Visit http://localhost:3000
# Should load the Nudify app
```

---

## Docker Commands Quick Reference

| Task | Command |
|------|---------|
| Start all services | `docker-compose up` |
| Start in background | `docker-compose up -d` |
| Stop all services | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Run command in container | `docker exec nudify-backend-prod <command>` |
| Build backend image | `docker build -t nudify-backend:prod ./Nudify-Generator` |
| Push to registry | `docker push registry.example.com/nudify-backend:prod` |
| Production deployment | `docker-compose -f docker-compose.prod.yml --env-file .env.production up -d` |

---

## Where to Deploy (Cloud Options)

### AWS (ECR + ECS)
```bash
# Push to AWS ECR
aws ecr get-login-password | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag nudify-backend:prod 123456789.dkr.ecr.us-east-1.amazonaws.com/nudify-backend:prod
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/nudify-backend:prod

# In ECS Task Definition, set environment variables from Secrets Manager
```

### Docker Hub
```bash
docker login
docker tag nudify-backend:prod yourusername/nudify-backend:prod
docker push yourusername/nudify-backend:prod
```

### Heroku
```bash
heroku container:login
heroku container:push web
heroku container:release web

# Set config variables in dashboard or:
heroku config:set C2PA_PRIVATE_KEY_BASE64="..."
```

### Railway / Render
1. Connect GitHub repo
2. Set environment variables in dashboard
3. Deploy (automatic on git push)

---

## Environment Variables Reference

Required for watermarking:
```
C2PA_PRIVATE_KEY_BASE64     # From setup_env_vars.py
C2PA_CERT_BASE64            # From setup_env_vars.py
WATERMARK_ENABLED=true
VISIBLE_BADGE_ENABLED=true
```

Optional:
```
DATABASE_URL                # PostgreSQL connection
SUPABASE_URL               # Supabase auth
SUPABASE_KEY               # Supabase API key
RUNPOD_API_KEY             # RunPod serverless API
NEXTAUTH_SECRET            # Next.js auth secret
NEXTAUTH_URL               # Frontend domain
NEXT_PUBLIC_API_URL        # Backend API endpoint
```

---

## Troubleshooting

**Port already in use?**
```bash
# Kill process using port
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux:
lsof -i :8000
kill -9 <PID>
```

**Credentials not loading?**
```bash
# Check if env file exists
ls -la .env.local
docker-compose config | grep C2PA_PRIVATE_KEY_BASE64

# Should show the base64 string
```

**Container won't start?**
```bash
docker logs nudify-backend-prod
# Look for: "C2PA_PRIVATE_KEY_BASE64" in the output
```

**Need to rebuild?**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

---

## Summary

1. **Local Dev**: `python setup_env_vars.py` → `docker-compose up`
2. **Production**: Generate `.env.production` → `docker-compose -f docker-compose.prod.yml --env-file .env.production up -d`
3. **Verify**: `curl http://localhost:8000/health` or visit http://localhost:3000
