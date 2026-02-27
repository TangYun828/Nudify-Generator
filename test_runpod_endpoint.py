#!/usr/bin/env python3
"""
RunPod Serverless Handler Integration Test
Test your handler code running on a live RunPod serverless endpoint
"""

import requests
import json
import sys
import time
import base64
from datetime import datetime

# Configuration - UPDATE THESE
SERVERLESS_ENDPOINT = "https://your-endpoint-xxxxx.runpod.io/run"  # Your RunPod serverless endpoint
# Get this from: https://www.runpod.io/console/serverless -> your endpoint -> API ID

# Test parameters
TEST_TIMEOUT = 620  # 10+ minutes max wait (RunPod limit is 600s)
TEST_POLL_INTERVAL = 5  # Poll every 5 seconds

def test_simple_generation():
    """Test basic image generation via handler"""
    print("\n" + "="*70)
    print("TEST 1: Simple Image Generation")
    print("="*70)
    
    payload = {
        "prompt": "a beautiful sunset over mountains",
        "negative_prompt": "blurry",
        "base_model_name": "onlyfornsfw118_v20.safetensors",
        "image_number": 1,
        "output_format": "png",
        "aspect_ratios_selection": "1024*1024"
    }
    
    print(f"Endpoint: {SERVERLESS_ENDPOINT}")
    print(f"Prompt: {payload['prompt']}")
    print(f"Model: {payload['base_model_name']}")
    print("\nSending request to your handler...")
    
    try:
        start_time = time.time()
        response = requests.post(
            SERVERLESS_ENDPOINT,
            json=payload,
            timeout=TEST_TIMEOUT
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Response received in {elapsed:.1f} seconds")
        print(f"Status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"✗ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        result = response.json()
        
        # Handler returns output key or direct images
        output = result.get("output")
        if not output:
            output = result
        
        images = output.get("images", []) if isinstance(output, dict) else output
        
        print(f"\nResponse structure (first 500 chars):")
        response_str = json.dumps(result, indent=2)
        print(response_str[:500])
        
        if isinstance(images, list) and len(images) > 0:
            print(f"\n✓ SUCCESS: Generated {len(images)} image(s)")
            first_image = images[0]
            if isinstance(first_image, str) and len(first_image) > 100:
                print(f"  First image base64 length: {len(first_image)} characters")
                return True
            else:
                print(f"  WARNING: Image format unexpected")
                return False
        else:
            print(f"\n✗ FAILED: No images in response")
            if isinstance(output, dict) and output.get("error"):
                print(f"  Error: {output.get('error')}")
            return False
            
    except requests.Timeout:
        print(f"✗ Request timed out after {TEST_TIMEOUT} seconds")
        print("  Tip: Image generation can take a while. Check your pod's GPU usage.")
        return False
    except Exception as e:
        print(f"✗ Exception: {type(e).__name__}: {e}")
        return False

def test_multiple_images():
    """Test generating multiple images via handler"""
    print("\n" + "="*70)
    print("TEST 2: Multiple Image Generation")
    print("="*70)
    
    payload = {
        "prompt": "abstract colorful shapes",
        "negative_prompt": "",
        "base_model_name": "onlyfornsfw118_v20.safetensors",
        "image_number": 3,  # Request 3 images
        "output_format": "png",
        "aspect_ratios_selection": "1024*1024"
    }
    
    print(f"Requesting {payload['image_number']} images...")
    
    try:
        response = requests.post(
            SERVERLESS_ENDPOINT,
            json=payload,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            print(f"✗ HTTP Error: {response.status_code}")
            return False
        
        result = response.json()
        output = result.get("output")
        if not output:
            output = result
        
        images = output.get("images", []) if isinstance(output, dict) else output
        
        if isinstance(images, list) and len(images) == 3:
            print(f"✓ SUCCESS: Generated all {len(images)} requested images")
            return True
        elif isinstance(images, list):
            print(f"✗ Expected 3 images, got {len(images)}")
            return False
        else:
            print(f"✗ Images not in expected format")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

def test_error_handling():
    """Test error handling with invalid input"""
    print("\n" + "="*70)
    print("TEST 3: Error Handling (Invalid Prompt)")
    print("="*70)
    
    payload = {
        "input": {
            "prompt": "",  # Empty prompt - should be rejected
            "negative_prompt": "",
            "base_model_name": "onlyfornsfw118_v20.safetensors",
            "image_number": 1,
            "output_format": "png",
            "aspect_ratios_selection": "1024*1024"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("Sending invalid request (empty prompt)...")
    
    try:
        response = requests.post(
            f"{RUNPOD_ENDPOINT}/api/generate",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            error = response.json().get("output", {}).get("error")
            print(f"✓ Handler correctly rejected invalid input")
            print(f"  Error message: {error}")
            return True
        else:
            print(f"✗ Should have rejected empty prompt")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_response_format():
    """Validate response format matches expectations"""
    print("\n" + "="*70)
    print("TEST 4: Response Format Validation")
    print("="*70)
    
    payload = {
        "input": {
            "prompt": "test image",
            "negative_prompt": "",
            "base_model_name": "onlyfornsfw118_v20.safetensors",
            "image_number": 1,
            "output_format": "png",
            "aspect_ratios_selection": "1024*1024"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{RUNPOD_ENDPOINT}/api/generate",
            json=payload,
            headers=headers,
            timeout=TEST_TIMEOUT
        )
        
        result = response.json()
        
        # Validate response structure
        checks = [
            ("Has 'output' key", "output" in result),
            ("Output has 'images' key", "images" in result.get("output", {})),
            ("Output has 'progress' key", "progress" in result.get("output", {})),
            ("Output has 'message' key", "message" in result.get("output", {})),
            ("Images is a list", isinstance(result.get("output", {}).get("images"), list)),
            ("Progress is 100", result.get("output", {}).get("progress") == 100),
        ]
        
        all_pass = True
        for check_name, check_result in checks:
            status = "✓" if check_result else "✗"
            print(f"{status} {check_name}")
            all_pass = all_pass and check_result
        
        return all_pass
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

def validate_config():
    """Validate configuration before running tests"""
    print("Validating configuration...")
    
    if RUNPOD_ENDPOINT == "https://your-pod-id-xxxxx.runpod.io":
        print("✗ RUNPOD_ENDPOINT not configured")
        print("  Edit this file and set RUNPOD_ENDPOINT to your pod URL")
        return False
    
    if RUNPOD_API_KEY == "your_api_key_here":
        print("✗ RUNPOD_API_KEY not configured")
        print("  Edit this file and set RUNPOD_API_KEY to your API key")
        return False
    
    print("✓ Configuration looks good")
    print(f"  Endpoint: {RUNPOD_ENDPOINT}")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("RUNPOD ENDPOINT INTEGRATION TEST")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Validate config first
    if not validate_config():
        print("\nPlease configure RUNPOD_ENDPOINT and RUNPOD_API_KEY")
        sys.exit(1)
    
    # Test connectivity
    print("\nTesting connectivity...")
    try:
        requests.get(f"{RUNPOD_ENDPOINT}/api", timeout=5)
        print("✓ Endpoint is reachable")
    except Exception as e:
        print(f"✗ Cannot reach endpoint: {e}")
        print(f"  Check your RUNPOD_ENDPOINT URL")
        sys.exit(1)
    
    # Run tests
    results = {
        "Simple Generation": test_simple_generation(),
        "Multiple Images": test_multiple_images(),
        "Error Handling": test_error_handling(),
        "Response Format": test_response_format(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n✓ All tests passed! Handler is working correctly.")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    # Instructions for configuration
    if RUNPOD_ENDPOINT == "https://your-pod-id-xxxxx.runpod.io":
        print("="*70)
        print("SETUP INSTRUCTIONS")
        print("="*70)
        print("\n1. Get your RunPod endpoint URL:")
        print("   - Go to https://www.runpod.io/console/pods")
        print("   - Find your pod")
        print("   - Copy the 'Connect' URL")
        print("\n2. Get your API key:")
        print("   - Go to https://www.runpod.io/console/user/settings")
        print("   - Copy your API key")
        print("\n3. Edit this file and update:")
        print("   RUNPOD_ENDPOINT = 'your-url-here'")
        print("   RUNPOD_API_KEY = 'your-key-here'")
        print("\n4. Run the test again")
        sys.exit(1)
    
    main()
