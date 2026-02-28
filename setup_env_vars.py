#!/usr/bin/env python3
"""
Automated Environment Variable Setup Script
Encodes C2PA credentials to base64 and generates .env.local
"""

import base64
import os
from pathlib import Path

def setup_env_vars():
    """Setup environment variables for compliance watermarking"""
    
    print("=" * 70)
    print("ENVIRONMENT VARIABLE SETUP - COMPLIANCE WATERMARKING")
    print("=" * 70)
    print()
    
    # Check if certificate files exist
    private_key_file = Path("c2pa_private_key.pem")
    cert_file = Path("c2pa_certificate.pem")
    
    if not private_key_file.exists():
        print("✗ Error: c2pa_private_key.pem not found")
        print("  Run: python generate_c2pa_credentials.py")
        return False
    
    if not cert_file.exists():
        print("✗ Error: c2pa_certificate.pem not found")
        print("  Run: python generate_c2pa_credentials.py")
        return False
    
    print("[1/4] Reading certificate files...")
    try:
        with open(private_key_file, 'r') as f:
            private_key_content = f.read()
        with open(cert_file, 'r') as f:
            cert_content = f.read()
        print("✓ Files read successfully")
    except Exception as e:
        print(f"✗ Error reading files: {e}")
        return False
    
    print("\n[2/4] Encoding to base64...")
    try:
        key_b64 = base64.b64encode(private_key_content.encode()).decode()
        cert_b64 = base64.b64encode(cert_content.encode()).decode()
        print(f"✓ Private key: {len(key_b64)} chars")
        print(f"✓ Certificate: {len(cert_b64)} chars")
    except Exception as e:
        print(f"✗ Error encoding to base64: {e}")
        return False
    
    print("\n[3/4] Creating .env.local...")
    env_content = f"""# C2PA Legal Compliance Watermarking Configuration
# Generated: {Path.cwd()}
# DO NOT COMMIT THIS FILE - Add to .gitignore

# C2PA Credentials (Base64 Encoded)
C2PA_PRIVATE_KEY_BASE64="{key_b64}"
C2PA_CERT_BASE64="{cert_b64}"

# Watermarking Configuration
WATERMARK_ENABLED=true
VISIBLE_BADGE_ENABLED=true
WATERMARK_SITE_ID="intimai_cc_ai_generated"

# Database (Add your existing config)
# DATABASE_URL="postgresql://..."
# SUPABASE_URL="..."
# SUPABASE_KEY="..."
"""
    
    try:
        env_file = Path(".env.local")
        env_file.write_text(env_content)
        print(f"✓ Created .env.local ({len(env_content)} bytes)")
    except Exception as e:
        print(f"✗ Error creating .env.local: {e}")
        return False
    
    print("\n[4/4] Verifying setup...")
    try:
        # Test by loading
        from dotenv import load_dotenv
        load_dotenv(".env.local")
        
        key_check = os.getenv("C2PA_PRIVATE_KEY_BASE64")
        cert_check = os.getenv("C2PA_CERT_BASE64")
        
        if key_check and cert_check:
            print("✓ Environment variables loaded successfully")
            print(f"  - C2PA_PRIVATE_KEY_BASE64: {len(key_check)} chars ✓")
            print(f"  - C2PA_CERT_BASE64: {len(cert_check)} chars ✓")
            print(f"  - WATERMARK_ENABLED: {os.getenv('WATERMARK_ENABLED')} ✓")
            print(f"  - VISIBLE_BADGE_ENABLED: {os.getenv('VISIBLE_BADGE_ENABLED')} ✓")
        else:
            print("✗ Variables not loaded correctly")
            return False
    except Exception as e:
        print(f"✗ Error verifying setup: {e}")
        return False
    
    print()
    print("=" * 70)
    print("✓ SETUP COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Verify .gitignore includes .env.local:")
    print("     grep '.env.local' .gitignore")
    print()
    print("  2. Test watermarking system:")
    print("     python test_watermarking.py")
    print()
    print("  3. For production, set these variables in your deployment platform:")
    print(f"     C2PA_PRIVATE_KEY_BASE64={key_b64[:50]}...")
    print(f"     C2PA_CERT_BASE64={cert_b64[:50]}...")
    print()
    print("⚠ Security Reminder:")
    print("  - Never commit .env.local to git")
    print("  - Store credentials in secure vault (AWS Secrets, Vault, etc)")
    print("  - Rotate credentials annually")
    print("=" * 70)
    
    return True


def verify_gitignore():
    """Verify .env.local is in .gitignore"""
    gitignore = Path(".gitignore")
    
    if not gitignore.exists():
        print("⚠ Warning: .gitignore not found")
        return False
    
    content = gitignore.read_text()
    if ".env.local" in content:
        return True
    
    print("\nUpdating .gitignore to include .env.local...")
    with open(gitignore, "a") as f:
        f.write("\n# Environment variables (SECURITY SENSITIVE)\n")
        f.write(".env.local\n")
    
    print("✓ Updated .gitignore")
    return True


if __name__ == "__main__":
    try:
        # Ensure .gitignore is updated
        verify_gitignore()
        
        # Setup env vars
        success = setup_env_vars()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
