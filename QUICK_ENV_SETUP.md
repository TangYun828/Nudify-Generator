# Quick Reference: Environment Variable Setup

## 2-Minute Setup (Local Development)

```bash
cd Nudify-Generator

# 1. Generate .env.local automatically
python setup_env_vars.py

# 2. Verify everything works
python test_watermarking.py

# Done! ✓
```

That's it. `.env.local` will be created with all the base64-encoded credentials.

---

## What Just Happened?

The setup script did this automatically:

1. **Read** certificate files (`c2pa_private_key.pem`, `c2pa_certificate.pem`)
2. **Encoded** them to base64
3. **Created** `.env.local` with:
   ```
   C2PA_PRIVATE_KEY_BASE64="MIIEvQIBADANBgk..."
   C2PA_CERT_BASE64="MIIDXTCCAkWgAwIBAgI..."
   WATERMARK_ENABLED=true
   VISIBLE_BADGE_ENABLED=true
   ```
4. **Verified** credentials load correctly

---

## For Production

### Option 1: AWS Secrets Manager (Recommended)
```bash
# Store credentials securely
aws secretsmanager create-secret \
  --name nudify/c2pa-credentials \
  --secret-string '{
    "C2PA_PRIVATE_KEY_BASE64": "MIIEvQIBADA...",
    "C2PA_CERT_BASE64": "MIIDXTCCAkWg..."
  }'

# Your deployment automatically retrieves them
```

### Option 2: Render / Railway / Heroku
Just set environment variables in dashboard:
```
C2PA_PRIVATE_KEY_BASE64 = MIIEvQIBADANBgk...
C2PA_CERT_BASE64 = MIIDXTCCAkWgAwIBAgI...
WATERMARK_ENABLED = true
VISIBLE_BADGE_ENABLED = true
```

### Option 3: Docker Compose
```yaml
services:
  backend:
    environment:
      - C2PA_PRIVATE_KEY_BASE64=${C2PA_PRIVATE_KEY_BASE64}
      - C2PA_CERT_BASE64=${C2PA_CERT_BASE64}
```

Then run:
```bash
export C2PA_PRIVATE_KEY_BASE64="MIIEvQIBADA..."
export C2PA_CERT_BASE64="MIIDXTCCAkWg..."
docker-compose up
```

---

## How Credentials Are Loaded

**Priority Order:**
1. **Environment variable** → `C2PA_PRIVATE_KEY_BASE64`
2. **File** → `c2pa_private_key.pem`
3. **Test mode** → Watermarking still works (manifest not signed)

This means:
- **Local dev:** Use `.env.local` (file-based)
- **Production:** Use environment variables (much more secure)

---

## Complete File Overview

| File | Purpose |
|------|---------|
| `c2pa_private_key.pem` | Private key (SECRET, in .gitignore) |
| `c2pa_certificate.pem` | Public cert (safe) |
| `.env.local` | Base64-encoded credentials (LOCAL DEV ONLY, in .gitignore) |
| `ENV_VARS_SETUP.md` | Complete environment variable guide |
| `setup_env_vars.py` | Automated setup script |
| `compliance_watermark.py` | Watermarking engine (loads from env or files) |

---

## Security Checklist

- [ ] `.env.local` is in `.gitignore` ✓
- [ ] `.env.local` never committed to git ✓
- [ ] Private key file in `.gitignore` ✓
- [ ] Never paste base64 in code ✓
- [ ] Use `.env.local` for local dev
- [ ] Use environment variables for production
- [ ] Rotate credentials annually

---

## Verify It Works

```bash
python test_watermarking.py
```

Should output:
```
✓ ALL TESTS PASSED
  ✓ Latent watermarking: FUNCTIONAL
  ✓ C2PA manifest creation: FUNCTIONAL
  ✓ PNG metadata embedding: FUNCTIONAL
  ✓ Visible badge: FUNCTIONAL
```

---

## Troubleshooting

**Q: Setup script says "credentials not found"**
```bash
# First run certificate generation
python generate_c2pa_credentials.py

# Then generate .env.local
python setup_env_vars.py
```

**Q: Tests fail after setup**
```bash
# Make sure .env.local was created
ls -la .env.local

# Check credentials loaded
grep C2PA .env.local | head -c 50

# Verify format
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('C2PA_PRIVATE_KEY_BASE64')[:50])"
```

**Q: How do I get the base64 for production?**
```bash
# If you only need to see the values (don't do this in production!)
cat .env.local

# For AWS Secrets Manager, use setup_env_vars.py output
python setup_env_vars.py | grep "C2PA_PRIVATE_KEY_BASE64"
```

---

## Summary

| Scenario | Steps |
|----------|-------|
| **Local Dev** | `python setup_env_vars.py` → Done |
| **Production (AWS)** | Copy base64 to Secrets Manager → Done |
| **Production (Docker)** | Set env vars in docker-compose.yml → Done |
| **Production (Render/Railway)** | Paste base64 in dashboard → Done |

All scenarios load credentials the same way — the code doesn't care where they come from.

---

## More Info

- See `ENV_VARS_SETUP.md` for detailed guides
- See `IMPLEMENTATION_SUMMARY.md` for production deployment
- Run `python setup_env_vars.py` to get started immediately
