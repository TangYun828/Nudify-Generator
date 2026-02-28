#!/usr/bin/env python3
"""
Test script to verify RunPod endpoint safety checker mode
This sends a test request and checks the logs for safety mode
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_runpod_safety_mode():
    """Test if RunPod endpoint has correct safety mode configured"""
    
    print("\n" + "="*70)
    print("RunPod Safety Mode Verification")
    print("="*70)
    
    # Check if RunPod credentials are set
    endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
    api_key = os.getenv('RUNPOD_API_KEY')
    
    if not endpoint_id or not api_key:
        print("\n⚠️  RunPod credentials not found in .env")
        print("\nYou have two testing options:")
        print("\n1. LOCAL TESTING (current setup):")
        print("   - Your backend is running at http://localhost:8000")
        print("   - Safety mode: Check with 'python check_env.py'")
        print("\n2. RUNPOD TESTING (when deployed):")
        print("   - Set RUNPOD_ENDPOINT_ID in .env")
        print("   - Set RUNPOD_API_KEY in .env")
        print("   - Re-run this script")
        return
    
    print(f"\n✓ RunPod Endpoint ID: {endpoint_id[:15]}...")
    print(f"✓ API Key configured: {api_key[:10]}...")
    
    # Test endpoint URL
    url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
    
    # Test payload - simple safe prompt
    payload = {
        "input": {
            "prompt": "A beautiful sunset over mountains",
            "negative_prompt": "",
            "image_number": 1
        }
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("\n🚀 Sending test request to RunPod...")
    print(f"   Endpoint: {url}")
    print(f"   Prompt: {payload['input']['prompt']}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('id')
            status = data.get('status')
            
            print(f"\n✓ Request accepted!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {status}")
            
            print("\n📋 To verify safety mode:")
            print("   1. Go to RunPod Dashboard → Your Endpoint")
            print("   2. Click 'Logs' tab")
            print("   3. Look for lines like:")
            print("      '🔧 Safety Checker Mode: PERMISSIVE_NSFW' or")
            print("      '🔧 Safety Checker Mode: STRICT'")
            print("\n   If you see PERMISSIVE_NSFW → Adult content allowed ✓")
            print("   If you see STRICT → Adult content blocked")
            print("\n   If missing → SAFETY_CHECKER_MODE env var not set!")
            print("      Fix: Add it in RunPod Template → Environment Variables")
            
        else:
            print(f"\n✗ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("\n⚠️  Request timed out (this is normal for cold starts)")
        print("   The job was queued, check RunPod dashboard for logs")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "="*70)
    print()


def test_local_backend():
    """Test local backend safety mode"""
    
    print("\n" + "="*70)
    print("Local Backend Safety Mode Check")
    print("="*70)
    
    local_url = "http://localhost:8000/api/runpod/generate"
    
    print(f"\n🔍 Testing: {local_url}")
    
    # Check if local backend is running
    try:
        health = requests.get("http://localhost:8000/health", timeout=2)
        if health.status_code == 200:
            print("✓ Local backend is running")
        else:
            print("⚠️  Backend responded but health check failed")
    except:
        print("✗ Local backend not running")
        print("\nStart it with: python test_api.py")
        return
    
    # Check env configuration
    from safety_checker import get_checker
    print("\n🔧 Initializing safety checker...")
    checker = get_checker()
    
    mode = os.getenv('SAFETY_CHECKER_MODE', 'strict')
    print(f"\n✅ Safety Mode: {mode.upper()}")
    
    if mode == 'permissive_nsfw':
        print("   → Adult content ALLOWED")
        print("   → Violence/hate/drugs BLOCKED")
    else:
        print("   → All adult content BLOCKED")
    
    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "runpod":
        test_runpod_safety_mode()
    else:
        test_local_backend()
        print("\nTo test RunPod endpoint instead: python test_runpod_safety_mode.py runpod")
