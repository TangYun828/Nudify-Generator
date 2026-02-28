#!/usr/bin/env python3
"""
RunPod Deployment Setup Helper
Generates configuration details and instructions for RunPod deployment
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def main():
    print("\n" + "="*70)
    print("RUNPOD DEPLOYMENT SETUP HELPER")
    print("="*70)
    
    # Load environment variables from .env.local
    env_file = Path(".env.local")
    if not env_file.exists():
        print("\n⚠️  ERROR: .env.local not found!")
        print("   Run this first: python setup_env_vars.py\n")
        return
    
    load_dotenv(".env.local")
    
    # Extract credentials
    private_key_b64 = os.getenv('C2PA_PRIVATE_KEY_BASE64', '')
    cert_b64 = os.getenv('C2PA_CERT_BASE64', '')
    watermark_enabled = os.getenv('WATERMARK_ENABLED', 'true')
    visible_badge = os.getenv('VISIBLE_BADGE_ENABLED', 'true')
    
    if not private_key_b64 or not cert_b64:
        print("\n❌ Missing credentials in .env.local")
        print("   Ensure C2PA_PRIVATE_KEY_BASE64 and C2PA_CERT_BASE64 are set\n")
        return
    
    # Display setup instructions
    print("\n✅ Credentials found!")
    print(f"   Private Key: {len(private_key_b64)} chars")
    print(f"   Certificate: {len(cert_b64)} chars")
    
    print("\n" + "-"*70)
    print("STEP 1: Build & Push Docker Image")
    print("-"*70)
    print("""
docker build -t nudify-backend:runpod .
docker tag nudify-backend:runpod yourusername/nudify-backend:runpod
docker login
docker push yourusername/nudify-backend:runpod
""")
    
    print("-"*70)
    print("STEP 2: Add Environment Variables in RunPod Console")
    print("-"*70)
    print("\nGo to: RunPod Console → Serverless → Create Endpoint")
    print("Advanced Settings → Environment Variables → Add these:\n")
    
    print("┌─ Variable 1")
    print("│ Name: C2PA_PRIVATE_KEY_BASE64")
    print(f"│ Value: {private_key_b64[:50]}...")
    print("├─ Variable 2")
    print("│ Name: C2PA_CERT_BASE64")
    print(f"│ Value: {cert_b64[:50]}...")
    print("├─ Variable 3")
    print("│ Name: WATERMARK_ENABLED")
    print("│ Value: true")
    print("└─ Variable 4")
    print("│ Name: VISIBLE_BADGE_ENABLED")
    print("│ Value: true")
    
    print("\n" + "-"*70)
    print("STEP 3: Copy Full Environment Variables")
    print("-"*70)
    print("\nFor easy copy-paste into RunPod Console:\n")
    
    print("C2PA_PRIVATE_KEY_BASE64:")
    print(private_key_b64)
    print("\nC2PA_CERT_BASE64:")
    print(cert_b64)
    print("\n")
    
    print("-"*70)
    print("STEP 4: Update Frontend Configuration")
    print("-"*70)
    print("""
Once your RunPod endpoint is created, update:
    ../nudify-app-nextjs/.env.local

Add these lines:
    NEXT_PUBLIC_API_URL=https://api-xxxxx.runpod.io
    NEXT_PUBLIC_RUNPOD_URL=https://api-xxxxx.runpod.io/api/runpod/generate

Replace 'xxxxx' with your actual RunPod endpoint ID.
""")
    
    print("-"*70)
    print("STEP 5: Verify Setup")
    print("-"*70)
    print("""
After endpoint is running (takes ~1 minute), test:

    # Check health
    curl https://api-xxxxx.runpod.io/health
    
    # Generate image
    curl -X POST https://api-xxxxx.runpod.io/api/runpod/generate \\
      -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{"input":{"prompt":"test","image_number":1}}'
    
    # Check logs
    RunPod Console → Endpoints → Logs (filter by "watermark")
""")
    
    print("-"*70)
    print("REFERENCE")
    print("-"*70)
    print("""
  Full Guide: RUNPOD_DEPLOYMENT.md
  Quick Setup: RUNPOD_QUICK_START.md
  RunPod Console: https://www.runpod.io/console
  RunPod Docs: https://docs.runpod.io/
""")
    
    print("="*70)
    print("✅ Ready for RunPod deployment!")
    print("="*70 + "\n")
    
    # Optional: Save to file
    save_option = input("Save instructions to runpod_setup_instructions.txt? (y/n): ").strip().lower()
    if save_option == 'y':
        with open("runpod_setup_instructions.txt", "w") as f:
            f.write("RUNPOD DEPLOYMENT INSTRUCTIONS\n")
            f.write("="*70 + "\n\n")
            f.write("CREDENTIALS (Add to RunPod Console → Environment)\n")
            f.write("-"*70 + "\n")
            f.write(f"C2PA_PRIVATE_KEY_BASE64={private_key_b64}\n")
            f.write(f"C2PA_CERT_BASE64={cert_b64}\n")
            f.write("WATERMARK_ENABLED=true\n")
            f.write("VISIBLE_BADGE_ENABLED=true\n\n")
            f.write("See RUNPOD_DEPLOYMENT.md for detailed instructions.\n")
        print("✅ Saved to runpod_setup_instructions.txt")

if __name__ == "__main__":
    main()
