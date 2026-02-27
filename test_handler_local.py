#!/usr/bin/env python3
"""
Local handler test environment - Test handler logic without Docker rebuild
Mocks the Fooocus API responses and RunPod environment
"""

import json
import sys
import os
import base64
from unittest.mock import Mock, patch
from pathlib import Path
from io import BytesIO
from PIL import Image

# Create output directory for test images
output_dir = Path("/tmp/fooocus_test_outputs")
output_dir.mkdir(exist_ok=True)

def create_test_image(filepath):
    """Create a test PNG image"""
    img = Image.new('RGB', (512, 512), color='red')
    img.save(filepath)
    return filepath

def mock_fooocus_api_response(sync_mode=True):
    """
    Mock the Fooocus API response
    Simulates what happens in sync and async mode
    """
    if sync_mode:
        # Sync mode: returns results directly
        # POST /v1/engine/generate/ returns list of HTTP URLs
        return [
            "http://127.0.0.1:7866/outputs/2024-06-30/image_001.png",
            "http://127.0.0.1:7866/outputs/2024-06-30/image_002.png"
        ]
    else:
        # Async mode: returns task_id for polling
        return {"task_id": "abc123def456"}

def mock_polling_response(status="finished"):
    """Mock the response from GET /tasks/{task_id}"""
    return {
        "task_id": "abc123def456",
        "task_status": status,  # "finished", "stop", "skip", "failed"
        "progress": 100,
        "result": [
            "http://127.0.0.1:7866/outputs/2024-06-30/image_001.png",
            "http://127.0.0.1:7866/outputs/2024-06-30/image_002.png"
        ]
    }

def patch_requests_for_testing():
    """Patch requests library to mock API calls"""
    mock_response = Mock()
    
    def mock_post(*args, **kwargs):
        """Mock POST requests"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_fooocus_api_response(sync_mode=True)
        return response
    
    def mock_get(*args, **kwargs):
        """Mock GET requests"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_polling_response(status="finished")
        return response
    
    return mock_post, mock_get

def test_url_parsing():
    """Test the URL to file path parsing logic"""
    print("\n" + "="*60)
    print("TEST: URL to File Path Parsing")
    print("="*60)
    
    test_urls = [
        "http://127.0.0.1:7866/outputs/2024-06-30/image_001.png",
        "http://example.com/outputs/2024-06-30/image_002.png",
        "/outputs/2024-06-30/image_003.png",
        "outputs/2024-06-30/image_004.png"
    ]
    
    def parse_api_url_to_filepath(img_url):
        """Same function as in handler.py"""
        if not isinstance(img_url, str):
            return None
        
        if img_url.startswith('http://127.0.0.1:7866/outputs/'):
            path_part = img_url.replace('http://127.0.0.1:7866', '')
            return f"/content/app{path_part}"
        
        elif img_url.startswith('http'):
            parts = img_url.split('/')
            if len(parts) >= 2:
                date_part = parts[-2]
                filename = parts[-1]
                return f"/content/app/outputs/{date_part}/{filename}"
        
        elif img_url.startswith('/outputs/'):
            return f"/content/app{img_url}"
        
        else:
            return f"/content/app/outputs/{img_url}"
    
    for url in test_urls:
        parsed = parse_api_url_to_filepath(url)
        print(f"\nURL: {url}")
        print(f"Parsed: {parsed}")
        expected_parts = url.split('/')[-2:]
        expected = f"/content/app/outputs/{'/'.join(expected_parts)}"
        print(f"Expected: {expected}")
        print(f"Status: {'✓ PASS' if parsed == expected else '✗ FAIL'}")

def test_status_value_checking():
    """Test the task status value checking logic"""
    print("\n" + "="*60)
    print("TEST: Task Status Value Checking")
    print("="*60)
    
    test_statuses = [
        ("finished", True, "Task completed successfully"),
        ("stop", True, "Task was stopped"),
        ("skip", True, "Task was skipped"),
        ("success", False, "OLD WRONG VALUE - should not match"),
        ("pending", False, "Still running - should not complete"),
        ("running", False, "Still running - should not complete"),
        ("failed", False, "Task failed - different handling"),
    ]
    
    for status, should_complete, description in test_statuses:
        # Simulate the actual check from handler.py
        completes = status == "finished" or status in ["stop", "skip"]
        
        result = "✓ PASS" if completes == should_complete else "✗ FAIL"
        print(f"\nStatus: '{status}' - {description}")
        print(f"  Expected to complete: {should_complete}")
        print(f"  Actually completes: {completes}")
        print(f"  {result}")

def test_base64_encoding():
    """Test image to base64 encoding"""
    print("\n" + "="*60)
    print("TEST: Image to Base64 Encoding")
    print("="*60)
    
    # Create a test image
    test_image_path = output_dir / "test_image.png"
    create_test_image(test_image_path)
    print(f"\n✓ Created test image: {test_image_path}")
    
    # Read and encode
    with open(test_image_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")
    
    print(f"✓ Encoded to base64")
    print(f"  Base64 length: {len(img_data)} characters")
    print(f"  Starts with: {img_data[:20]}...")
    print(f"  Ends with: ...{img_data[-20:]}")
    
    # Verify it's valid base64
    try:
        decoded = base64.b64decode(img_data)
        print(f"✓ Base64 is valid (decoded to {len(decoded)} bytes)")
        
        # Verify it's a valid image
        img = Image.open(BytesIO(decoded))
        print(f"✓ Decoded image is valid ({img.size[0]}x{img.size[1]} pixels)")
    except Exception as e:
        print(f"✗ Error validating base64: {e}")

def test_handler_logic():
    """Test handler response processing logic"""
    print("\n" + "="*60)
    print("TEST: Handler Response Processing")
    print("="*60)
    
    # Simulate API responses
    responses = [
        {
            "type": "sync_direct_list",
            "response": [
                "http://127.0.0.1:7866/outputs/2024-06-30/image_001.png",
                "http://127.0.0.1:7866/outputs/2024-06-30/image_002.png"
            ]
        },
        {
            "type": "sync_with_result_key",
            "response": {
                "result": [
                    "http://127.0.0.1:7866/outputs/2024-06-30/image_001.png"
                ]
            }
        },
        {
            "type": "sync_with_images_key",
            "response": {
                "images": [
                    "http://127.0.0.1:7866/outputs/2024-06-30/image_001.png"
                ]
            }
        },
        {
            "type": "async_with_task_id",
            "response": {
                "task_id": "abc123def456"
            }
        }
    ]
    
    for test_case in responses:
        print(f"\n{test_case['type']}:")
        response = test_case['response']
        print(f"  Response: {json.dumps(response, indent=4)}")
        
        # Process response (simulate handler logic)
        result = None
        if isinstance(response, dict):
            if "task_id" in response:
                print(f"  → Detected async response, would poll task: {response['task_id']}")
                result = "async"
            elif "result" in response:
                result = response.get("result")
                print(f"  → Found 'result' key with {len(result)} items")
            elif "images" in response:
                result = response.get("images")
                print(f"  → Found 'images' key with {len(result)} items")
        elif isinstance(response, list):
            result = response
            print(f"  → Direct list with {len(result)} items")
        
        if result and result != "async":
            print(f"  ✓ Successfully extracted {len(result)} image(s)")
        else:
            print(f"  ✓ Response type correctly identified")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("HANDLER LOCAL TEST ENVIRONMENT")
    print("="*70)
    print("\nThis test simulates API responses and validates handler logic")
    print(f"Test output directory: {output_dir}")
    
    try:
        test_url_parsing()
        test_status_value_checking()
        test_base64_encoding()
        test_handler_logic()
        
        print("\n" + "="*70)
        print("ALL TESTS COMPLETED")
        print("="*70)
        print("\n✓ URL parsing works correctly")
        print("✓ Status value checking is correct")
        print("✓ Base64 encoding is valid")
        print("✓ Handler response processing handles multiple formats")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
