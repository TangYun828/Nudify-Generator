#!/usr/bin/env python3
"""
Debug script to test Fooocus API responses
Run this on the RunPod instance to see actual response formats
"""

import json
import requests
import sys
import time

API_URL = "http://127.0.0.1:7866"
TEST_TIMEOUT = 30  # seconds

def test_api_connectivity():
    """Test if API is reachable"""
    print("\n" + "="*60)
    print("TEST 1: API Connectivity")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/docs", timeout=5)
        print(f"✓ API is responding (status {response.status_code})")
        return True
    except Exception as e:
        print(f"✗ API not responding: {e}")
        return False

def test_sync_generation():
    """Test synchronous image generation"""
    print("\n" + "="*60)
    print("TEST 2: Synchronous Generation (async_process=False)")
    print("="*60)
    
    payload = {
        "prompt": "a simple red square",
        "negative_prompt": "",
        "base_model_name": "onlyfornsfw118_v20.safetensors",
        "aspect_ratios_selection": "1024*1024",
        "image_number": 1,
        "output_format": "png",
        "async_process": False,  # SYNC MODE
        "stream_output": False,
        "performance_selection": "Quality"
    }
    
    print(f"Sending POST request to {API_URL}/v1/engine/generate/")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_URL}/v1/engine/generate/",
            json=payload,
            timeout=TEST_TIMEOUT
        )
        elapsed = time.time() - start
        
        print(f"\n✓ Response received in {elapsed:.1f}s")
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        data = response.json()
        print(f"\nResponse type: {type(data).__name__}")
        print(f"Response content:")
        print(json.dumps(data, indent=2))
        
        # Analyze response
        if isinstance(data, dict):
            print(f"\nResponse is dict with keys: {list(data.keys())}")
            if "task_id" in data:
                print(f"⚠️  Got task_id: {data['task_id']} (unexpected for sync mode)")
                return "async"
            elif "result" in data:
                print(f"✓ Got 'result' key with {len(data['result']) if isinstance(data['result'], list) else type(data['result'])} items")
                return "sync_with_result"
            else:
                print(f"⚠️  Unexpected structure")
                return "unknown"
        elif isinstance(data, list):
            print(f"✓ Response is direct list with {len(data)} items")
            print(f"First item: {str(data[0])[:100]}")
            return "sync_direct_list"
        else:
            print(f"⚠️  Response is unexpected type: {type(data)}")
            return "unknown"
            
    except requests.Timeout:
        print(f"✗ Request timed out after {TEST_TIMEOUT}s")
        return "timeout"
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        return "error"

def test_task_query(task_id):
    """Test querying task status"""
    print("\n" + "="*60)
    print("TEST 3: Query Task Status")
    print("="*60)
    
    print(f"Querying task: {task_id}")
    
    try:
        response = requests.get(
            f"{API_URL}/tasks/{task_id}",
            timeout=5
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data).__name__}")
            print(f"Response content:")
            print(json.dumps(data, indent=2))
            
            if isinstance(data, dict):
                print(f"\nKey fields:")
                print(f"  task_id: {data.get('task_id')}")
                print(f"  task_status: {data.get('task_status')}")
                print(f"  progress: {data.get('progress')}")
                print(f"  result: {type(data.get('result')).__name__} with {len(data.get('result', [])) if isinstance(data.get('result'), list) else 'N/A'} items")
        else:
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

def main():
    print("\n" + "="*60)
    print("FooocusAPI Response Format Debug Tool")
    print("="*60)
    
    # Test 1: Connectivity
    if not test_api_connectivity():
        print("\n✗ Cannot proceed without API connectivity")
        return
    
    # Test 2: Synchronous generation
    mode = test_sync_generation()
    
    if mode == "async":
        print("\n⚠️  Got async response (task_id) in sync mode")
        print("This means the API might have returned an async task instead of sync result")
    elif mode == "sync_direct_list":
        print("\n✓ Perfect! Got direct list of results (file paths)")
        print("This is the expected format for async_process=False")
    elif mode == "sync_with_result":
        print("\n✓ Got results in 'result' field")
        print("Response structure: {\"result\": [...]}")
    elif mode == "timeout":
        print("\n✗ Request timed out - generation may be taking too long")
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)

if __name__ == "__main__":
    main()
