# Environment Variables Configuration Guide

## Overview

The compliance watermarking system requires environment variables for C2PA credentials and configuration. This guide covers setup for local development and production.

---

## Quick Start (Local Development)

### Step 1: Create `.env.local` files

#### Backend: `Nudify-Generator/.env.local`
```bash
# C2PA Credentials (Base64 encoded)
C2PA_PRIVATE_KEY_BASE64="<paste base64 here>"
C2PA_CERT_BASE64="<paste base64 here>"

# Watermarking Configuration
WATERMARK_ENABLED=true
VISIBLE_BADGE_ENABLED=true
WATERMARK_SITE_ID="intimai_cc_ai_generated"

# Database (existing)
DATABASE_URL="postgresql://..."
```

#### Frontend: `nudify-app-nextjs/.env.local`
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_RUNPOD_URL=http://localhost:8000/api/runpod/generate

# Note: C2PA credentials are server-side only, not needed in frontend
```

### Step 2: Generate Base64-Encoded Credentials

Since credentials are already generated, encode them:

**On Linux/Mac:**
```bash
cd Nudify-Generator

# Encode private key
base64 c2pa_private_key.pem > /tmp/key.b64
cat /tmp/key.b64

# Encode certificate
base64 c2pa_certificate.pem > /tmp/cert.b64
cat /tmp/cert.b64
```

**On Windows PowerShell:**
```powershell
cd "c:\working folder\intimai\Nudify-Generator"

# Encode private key
$keyContent = Get-Content c2pa_private_key.pem -Raw
$keyBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($keyContent))
$keyBase64 | Out-File key.b64 -NoNewline

# Encode certificate
$certContent = Get-Content c2pa_certificate.pem -Raw
$certBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($certContent))
$certBase64 | Out-File cert.b64 -NoNewline

# Copy to clipboard for pasting into .env
Get-Content key.b64 | Set-Clipboard
Write-Host "Key copied to clipboard"

Get-Content cert.b64 | Set-Clipboard
Write-Host "Certificate copied to clipboard"
```

### Step 3: Paste into `.env.local`

```bash
# In Nudify-Generator/.env.local
C2PA_PRIVATE_KEY_BASE64="MIIEvQIBADANBgk..."  # Paste key.b64 content
C2PA_CERT_BASE64="MIIDXTCCAkWgAwIBAgI..."     # Paste cert.b64 content
```

### Step 4: Test Configuration

```bash
# Backend test
cd Nudify-Generator
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print('✓ Key loaded' if os.getenv('C2PA_PRIVATE_KEY_BASE64') else '✗ Key missing')"

# Should output: ✓ Key loaded
```

---

## Production Deployment

### Strategy 1: AWS Secrets Manager (Recommended for Cloud)

```bash
# 1. Create secret in AWS Console or CLI
aws secretsmanager create-secret \
  --name nudify/c2pa-credentials \
  --secret-string '{
    "C2PA_PRIVATE_KEY_BASE64": "'"$(cat c2pa_private_key.pem | base64)"'",
    "C2PA_CERT_BASE64": "'"$(cat c2pa_certificate.pem | base64)"'"
  }'

# 2. Update deployment to retrieve secret
# In your deployment script or Dockerfile:
```

**Docker Example:**
```dockerfile
FROM python:3.11

# Install AWS CLI
RUN pip install awscli

# Fetch secrets at runtime
RUN aws secretsmanager get-secret-value \
    --secret-id nudify/c2pa-credentials \
    --region us-east-1 \
    --query SecretString \
    --output json > /tmp/secrets.json

# Set environment variables from secrets
ENV C2PA_PRIVATE_KEY_BASE64=$(jq -r '.C2PA_PRIVATE_KEY_BASE64' /tmp/secrets.json)
ENV C2PA_CERT_BASE64=$(jq -r '.C2PA_CERT_BASE64' /tmp/secrets.json)

# Continue with app
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "test_api:app", "--host", "0.0.0.0"]
```

### Strategy 2: Environment Variables in Deployment Platform

#### Heroku
```bash
heroku config:set C2PA_PRIVATE_KEY_BASE64="<base64_key>"
heroku config:set C2PA_CERT_BASE64="<base64_cert>"
heroku config:set WATERMARK_ENABLED=true
heroku config:set VISIBLE_BADGE_ENABLED=true
```

#### Railway/Render
In deployment dashboard → Environment Variables:
```
C2PA_PRIVATE_KEY_BASE64 = MIIEvQIBADANBgk...
C2PA_CERT_BASE64 = MIIDXTCCAkWgAwIBAgI...
WATERMARK_ENABLED = true
VISIBLE_BADGE_ENABLED = true
```

#### Docker Compose (Self-Hosted)
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./Nudify-Generator
    environment:
      - C2PA_PRIVATE_KEY_BASE64=${C2PA_PRIVATE_KEY_BASE64}
      - C2PA_CERT_BASE64=${C2PA_CERT_BASE64}
      - WATERMARK_ENABLED=true
      - VISIBLE_BADGE_ENABLED=true
      - DATABASE_URL=${DATABASE_URL}
    env_file:
      - .env.production
```

Then create `.env.production`:
```bash
C2PA_PRIVATE_KEY_BASE64="..."
C2PA_CERT_BASE64="..."
DATABASE_URL="postgresql://..."
```

Run:
```bash
docker-compose up
```

---

## How to Load Env Vars in Python

### Current Implementation (test_api.py)

```python
from dotenv import load_dotenv
from pathlib import Path
import os

# Load from .env.local / .env.production
env_path = Path(__file__).parent / '.env.local'
load_dotenv(dotenv_path=env_path)

# Access variables
private_key_b64 = os.getenv('C2PA_PRIVATE_KEY_BASE64')
cert_b64 = os.getenv('C2PA_CERT_BASE64')
```

### In compliance_watermark.py (Update to Support Env Vars)

```python
import os
import base64
from pathlib import Path

class ComplianceWatermark:
    def __init__(self, org_name="intimai.cc", 
                 private_key_path="c2pa_private_key.pem",
                 cert_path="c2pa_certificate.pem"):
        """
        Initialize with either file paths or environment variables
        Priority:
          1. C2PA_PRIVATE_KEY_BASE64 env var
          2. File at private_key_path
          3. Fail with warning
        """
        self.org_name = org_name
        self.private_key = None
        self.certificate = None
        
        # Try environment variables first
        key_b64 = os.getenv('C2PA_PRIVATE_KEY_BASE64')
        cert_b64 = os.getenv('C2PA_CERT_BASE64')
        
        if key_b64 and cert_b64:
            self._load_from_base64(key_b64, cert_b64)
        elif Path(private_key_path).exists() and Path(cert_path).exists():
            self._load_from_files(private_key_path, cert_path)
        else:
            logger.warning("⚠ C2PA credentials not found (using test mode)")
    
    def _load_from_base64(self, key_b64: str, cert_b64: str):
        """Load credentials from base64 environment variables"""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            # Decode from base64
            key_pem = base64.b64decode(key_b64).decode('utf-8')
            cert_pem = base64.b64decode(cert_b64).decode('utf-8')
            
            # Load private key
            self.private_key = serialization.load_pem_private_key(
                key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            
            # Load certificate
            self.certificate = cert_pem
            
            logger.info("✓ C2PA credentials loaded from environment variables")
        except Exception as e:
            logger.error(f"✗ Error loading from environment: {e}")
    
    def _load_from_files(self, key_path: str, cert_path: str):
        """Load credentials from files (backward compatible)"""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            with open(key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            with open(cert_path, "rb") as f:
                self.certificate = f.read().decode('utf-8')
            
            logger.info("✓ C2PA credentials loaded from files")
        except Exception as e:
            logger.error(f"✗ Error loading from files: {e}")
```

---

## Complete Environment Variables Reference

### Required Variables
| Variable | Value | Example |
|----------|-------|---------|
| `C2PA_PRIVATE_KEY_BASE64` | Base64-encoded PEM private key | `MIIEvQIBADANBgkqhki...` |
| `C2PA_CERT_BASE64` | Base64-encoded PEM certificate | `MIIDXTCCAkWgAwIBAgI...` |

### Optional Configuration Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `WATERMARK_ENABLED` | `true` | Enable/disable watermarking |
| `VISIBLE_BADGE_ENABLED` | `true` | Show "AI GENERATED" badge |
| `WATERMARK_SITE_ID` | `intimai_cc_ai_generated` | Site identifier in watermark |

### Existing Database Variables (Keep These)
| Variable | Example |
|----------|---------|
| `DATABASE_URL` | `postgresql://user:pass@localhost/db` |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase API key |

---

## Verification Checklist

- [ ] `.env.local` created with base64 credentials
- [ ] Private key base64 is correct (starts with `MIIEvQIBADANBgk...`)
- [ ] Certificate base64 is correct (starts with `MIIDXTCCAkWgAwIBAgI...`)
- [ ] Test script shows `✓ Key loaded`
- [ ] `test_watermarking.py` passes all tests
- [ ] `WATERMARK_ENABLED=true` in production

---

## Troubleshooting

### Error: "Module not found: dotenv"
```bash
pip install python-dotenv
```

### Error: "C2PA credentials not loaded"
Check:
1. File exists: `ls c2pa_private_key.pem`
2. Base64 is valid: `base64 -d <<< "MIIEvQIBADA..." | head -c 50`
3. Environment variable set: `echo $C2PA_PRIVATE_KEY_BASE64`

### Error: "Invalid PEM format"
Check:
1. Base64 was encoded correctly: `base64 c2pa_private_key.pem | head -c 50`
2. No extra newlines: `base64 c2pa_private_key.pem | wc -l` (should be 1-2)
3. File not corrupted: `file c2pa_private_key.pem` (should say PEM RSA private key)

### Test All Variables Are Loaded
```bash
python -c "
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

print('Checking environment variables...')
print(f'C2PA_PRIVATE_KEY_BASE64: {\"✓\" if os.getenv(\"C2PA_PRIVATE_KEY_BASE64\") else \"✗\"}')
print(f'C2PA_CERT_BASE64: {\"✓\" if os.getenv(\"C2PA_CERT_BASE64\") else \"✗\"}')
print(f'WATERMARK_ENABLED: {os.getenv(\"WATERMARK_ENABLED\", \"true\")}')
print(f'VISIBLE_BADGE_ENABLED: {os.getenv(\"VISIBLE_BADGE_ENABLED\", \"true\")}')
"
```

---

## Security Best Practices

1. **Never commit credentials to git**
   ```bash
   # Already in .gitignore
   git check-ignore c2pa_private_key.pem  # Should say "ignored"
   ```

2. **Use `.env.local` for development**
   - Never share `.env.local` file
   - Add to `.gitignore` (already done)

3. **Use Secrets Manager for production**
   - AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault
   - Rotate keys annually
   - Audit access logs

4. **Separate credentials per environment**
   - Dev: Local file or test credentials
   - Staging: AWS Secrets
   - Production: Rotate separate credentials

5. **Monitor for leaks**
   ```bash
   # Search git history for leaks
   git log -p --all -S "PRIVATE KEY" | head -50
   ```

---

## Summary

**Local Development:**
```bash
# 1. Encode credentials to base64
base64 c2pa_private_key.pem > key.b64
base64 c2pa_certificate.pem > cert.b64

# 2. Create .env.local with base64 content
echo 'C2PA_PRIVATE_KEY_BASE64="'$(cat key.b64)'"' >> .env.local
echo 'C2PA_CERT_BASE64="'$(cat cert.b64)'"' >> .env.local

# 3. Test
python test_watermarking.py  # Should all pass ✓
```

**Production:**
- Use AWS Secrets Manager, Render, Railway, or Docker env vars
- Never paste base64 directly in code
- Rotate credentials annually
