"""
RunPod Serverless Handler for Fooocus
Handles requests from RunPod serverless and returns images to frontend
"""

import os
import sys
import json
import base64
import subprocess
import time
import requests
from io import BytesIO
from PIL import Image
from runpod.serverless.utils.rp_cleanup import clean

# Add app directory to path
sys.path.insert(0, '/content/app')

# Start Fooocus on init
def start_fooocus():
    """Start Fooocus API in background"""
    print("Starting Fooocus API...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Content directory exists: {os.path.exists('/content')}")
    print(f"App directory exists: {os.path.exists('/content/app')}")
    
    # Start Fooocus with FastAPI using entrypoint.sh
    # entrypoint.sh sets up model symlinks, then calls launch.py
    # API will run on port 7866 (WebUI port + 1)
    # No WebUI (--nowebui), only API
    import threading
    
    process = subprocess.Popen(
        ["bash", "/content/entrypoint.sh", "--listen", "0.0.0.0", "--port", "7865", "--nowebui"],
        cwd="/content",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Print startup logs in background
    def print_logs():
        try:
            for line in process.stdout:
                print(f"[Fooocus] {line.rstrip()}")
        except:
            pass
    
    log_thread = threading.Thread(target=print_logs, daemon=True)
    log_thread.start()
    
    # Wait for FastAPI to be ready on port 7866 (240 seconds = 4 minutes)
    max_retries = 240
    api_ready = False
    
    for i in range(max_retries):
        try:
            # First check if API is responding
            response = requests.get("http://127.0.0.1:7866/docs", timeout=3)
            if response.status_code == 200:
                # API is up, wait a bit more for model loading
                if i > 30:  # Only after 30 seconds of attempting
                    print(f"✓ Fooocus FastAPI is responding! (waited {i+1}s)")
                    api_ready = True
                    break
        except Exception as e:
            if i % 30 == 0:
                print(f"Waiting for Fooocus FastAPI... ({i}s elapsed)")
            time.sleep(1)
    
    if not api_ready:
        raise Exception("Failed to start Fooocus FastAPI after 240 seconds")
    
    # Wait additional time for model file loading
    print("Allowing time for model initialization...")
    time.sleep(10)  # Extended wait for NSFW model loading
    
    return process

# Initialize on import
FOOOCUS_PROCESS = None
try:
    print("=" * 60)
    print("RunPod Handler Starting - Initializing Fooocus")
    print("=" * 60)
    FOOOCUS_PROCESS = start_fooocus()
    print("=" * 60)
    print("Fooocus initialized successfully!")
    print("=" * 60)
except Exception as e:
    print("=" * 60)
    print(f"ERROR: Could not start Fooocus:")
    print(f"{str(e)}")
    print("=" * 60)
    import traceback
    traceback.print_exc()


def poll_for_completion(api_url, task_id, timeout=300, poll_interval=3):
    """
    Poll the FooocusAPI task endpoint until completion
    
    Args:
        api_url: Base URL of Fooocus API (e.g., http://127.0.0.1:7866)
        task_id: Task ID from the initial POST request
        timeout: Maximum time to wait in seconds (5 minutes)
        poll_interval: Seconds between polls
    
    Returns:
        Result data if completed successfully, None if timeout
    """
    import time
    
    start_time = time.time()
    poll_count = 0
    
    while time.time() - start_time < timeout:
        try:
            # Poll /tasks/{task_id} endpoint - NOTE: Requires API key header
            response = requests.get(
                f"{api_url}/tasks/{task_id}",
                headers={
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("task_status", "")  # Values: pending, running, success, failed
                progress = task_data.get("progress", 0)
                
                poll_count += 1
                if poll_count % 5 == 1:  # Log every 5 polls
                    print(f"Poll #{poll_count}: Status={status}, Progress={progress*100:.1f}%")
                
                # Task completion states from FooocusAPI post_worker.py:
                # - "finished" = successful completion
                # - "stop" = task was explicitly stopped
                # - "skip" = task was skipped
                # See: https://github.com/mrhan1993/FooocusAPI/blob/main/apis/utils/post_worker.py
                if status == "finished":
                    elapsed = time.time() - start_time
                    print(f"✓ Task completed! Status={status}, Retrieved after {poll_count} polls ({elapsed:.1f}s)")
                    # Result contains HTTP URLs from post_worker's url_path() conversion
                    # Example: ["http://127.0.0.1:7866/outputs/2024-06-30/image.png"]
                    result = task_data.get("result", [])
                    print(f"  Result type: {type(result)}, length: {len(result) if isinstance(result, list) else 'N/A'}")
                    return result
                elif status in ["stop", "skip"]:
                    # Task stopped/skipped but may have partial results
                    elapsed = time.time() - start_time
                    print(f"⚠ Task {status}ped (status={status}), retrieved after {poll_count} polls ({elapsed:.1f}s)")
                    result = task_data.get("result", [])
                    if result:
                        print(f"  Partial results: {len(result)} item(s)")
                    return result if result else None
                elif status in ["failed", "FAILED", "error"]:
                    print(f"✗ Task failed with status: {status}")
                    print(f"  Full response: {json.dumps(task_data, indent=2)[:500]}")
                    return None
                # Still pending or running - continue polling
            elif response.status_code == 404:
                print(f"Task not found (404): {task_id} - API may not support polling")
                return None
            else:
                print(f"Unexpected status {response.status_code}: {response.text[:100]}")
            
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"Poll error: {type(e).__name__}: {e}")
            time.sleep(poll_interval)
    
    elapsed = time.time() - start_time
    print(f"✗ Task polling timed out after {elapsed:.1f}s ({poll_count} polls, {timeout}s limit)")
    return None


def handler(event):
    """
    RunPod Serverless Handler - matches frontend expectations
    
    Input format (from frontend):
    {
        "input": {
            "prompt": "A beautiful sunset",
            "negative_prompt": "",
            "base_model_name": "onlyfornsfw118_v20.safetensors",
            "image_number": 1,
            "output_format": "png",
            "aspect_ratios_selection": "1024*1024"
        }
    }
    
    Output format (to frontend via RunPod):
    {
        "images": ["base64_data1", "base64_data2"],
        "progress": 100,
        "message": "Generation complete"
    }
    """
    try:
        # Extract input (works with both formats)
        job_input = event.get("input", {})
        
        prompt = job_input.get("prompt", "")
        negative_prompt = job_input.get("negative_prompt", "")
        base_model = job_input.get("base_model_name", "onlyfornsfw118_v20.safetensors")
        num_images = job_input.get("num_images") or job_input.get("image_number", 1)
        output_format = job_input.get("output_format", "png").lower()
        aspect_ratio = job_input.get("aspect_ratios_selection", "1024*1024")
        
        if not prompt:
            return {
                "error": "Prompt is required",
                "progress": 0
            }
        
        print(f"Generating {num_images} image(s) with prompt: {prompt}")
        print(f"Model: {base_model}, Format: {output_format}, Aspect: {aspect_ratio}")
        
        # Call Fooocus FastAPI on port 7866
        fooocus_api = "http://127.0.0.1:7866"
        
        # Prepare payload matching CommonRequest model
        # IMPORTANT: When async_process=False, API returns results directly (no task_id)
        # When async_process=True, API returns {"task_id": "..."} for async polling
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "base_model_name": base_model,
            "aspect_ratios_selection": aspect_ratio,
            "image_number": int(num_images),
            "output_format": output_format,
            "async_process": False,  # Synchronous: returns results directly
            "stream_output": False,  # No streaming in serverless
            "performance_selection": "Quality"
        }
        
        # Call Fooocus FastAPI endpoint
        print(f"Calling Fooocus FastAPI at {fooocus_api}/v1/engine/generate/ (sync mode)...")
        response = requests.post(
            f"{fooocus_api}/v1/engine/generate/",
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=300
        )
        
        if response.status_code != 200:
            error_msg = f"Fooocus API error: {response.status_code} - {response.text}"
            print(error_msg)
            return {
                "error": error_msg,
                "progress": 0
            }
        
        response_data = response.json()
        print(f"Response type: {type(response_data)}")
        print(f"Response keys: {response_data.keys() if isinstance(response_data, dict) else 'N/A'}")
        print(f"Response preview: {json.dumps(response_data, indent=2)[:300]}")
        
        result = None
        
        # Handle different response types
        if isinstance(response_data, dict):
            # Check if it's a task_id response (async mode) - this shouldn't happen with async_process=False
            if "task_id" in response_data:
                print(f"Got task_id: {response_data['task_id']}")
                print("WARNING: Received task_id despite async_process=False. This is unexpected.")
                print("Attempting to poll anyway...")
                task_id = response_data["task_id"]
                result = poll_for_completion(fooocus_api, task_id)
            # Check for direct result in response
            elif "result" in response_data:
                print(f"Got result directly in response (key='result')")
                result = response_data.get("result")
            elif "images" in response_data:
                print(f"Got images directly in response (key='images')")
                result = response_data.get("images")
            else:
                # For sync requests, the entire response might be file paths
                print(f"Unexpected response structure. Full response: {response_data}")
                # Try to extract any list-like data
                for key in ["outputs", "files", "data", "image_paths"]:
                    if key in response_data and isinstance(response_data[key], list):
                        result = response_data[key]
                        break
        elif isinstance(response_data, list):
            # Direct list of results
            print(f"Received result as direct list")
            result = response_data
        else:
            print(f"Unexpected response type: {type(response_data)}")
        
        if result is None:
            return {
                "error": "No result or task_id in API response",
                "progress": 0
            }
        
        print(f"Final result type: {type(result)}, is list: {isinstance(result, list)}")
        if isinstance(result, list):
            print(f"Result list length: {len(result)}")
            if result:
                print(f"First result item type: {type(result[0])}")
                print(f"First result: {str(result[0])[:150]}")
        
        # FooocusAPI returns HTTP URLs (from post_worker.py's url_path() function)
        # See: https://github.com/mrhan1993/FooocusAPI/blob/main/apis/utils/file_utils.py#L64
        # Example URLs: ["http://127.0.0.1:7866/outputs/2024-06-30/image_xxx.png"]
        # We need to extract the file path and read from local disk
        images = []
        generated_files = []  # Track files to delete after encoding
        
        def parse_api_url_to_filepath(img_url):
            """Convert FooocusAPI HTTP URL to local file path
            
            Tries multiple possible locations for Fooocus outputs:
            1. /content/outputs/ (Fooocus running from /content)
            2. /content/app/outputs/ (Alternative app structure)
            3. /workspace/Fooocus/outputs/ (RunPod standard)
            4. /app/outputs/ (Docker standard)
            5. /outputs/ (Bare outputs directory)
            """
            if not isinstance(img_url, str):
                return None
            
            # Extract the relative path from HTTP URL
            # e.g., http://127.0.0.1:7866/outputs/2026-02-21/image.png → /outputs/2026-02-21/image.png
            relative_path = None
            
            if img_url.startswith('http://127.0.0.1:7866/outputs/'):
                relative_path = img_url.replace('http://127.0.0.1:7866', '')
            elif img_url.startswith('http'):
                # Extract /outputs/date/filename pattern
                if '/outputs/' in img_url:
                    relative_path = '/' + '/'.join(img_url.split('/outputs/')[-1].split('/'))
                    relative_path = '/outputs/' + '/'.join(relative_path.split('/')[1:])
            elif img_url.startswith('/outputs/'):
                relative_path = img_url
            else:
                relative_path = f"/outputs/{img_url}"
            
            if not relative_path:
                return None
            
            # Try each possible base directory
            possible_bases = [
                '/content/outputs',              # If outputs is directly in /content
                '/content/Fooocus/outputs',      # If Fooocus root is /content/Fooocus (most likely!)
                '/content/fooocusapi/outputs',   # Alternative casing
                '/content/app/outputs',          # Alternative app structure
                '/workspace/Fooocus/outputs',    # RunPod standard
                '/app/outputs',                  # Docker standard
                '/outputs',                      # Bare outputs
            ]
            
            for base in possible_bases:
                full_path = base + relative_path
                if os.path.exists(full_path):
                    print(f"✓ Found image at: {full_path}")
                    return full_path
            
            # If not found, try the most likely default
            print(f"Warning: Image not found in any standard location")
            print(f"  Tried: {possible_bases}")
            print(f"  Relative path: {relative_path}")
            return None

        def encode_image_from_path_or_url(file_path, img_url):
            """Encode image from local path or fallback to HTTP URL."""
            if file_path and os.path.exists(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    print(f"  File size: {file_size} bytes")
                    with open(file_path, "rb") as f:
                        raw_data = f.read()
                    print(f"  Read {len(raw_data)} bytes from disk")
                    img_data = base64.b64encode(raw_data).decode("utf-8")
                    print(f"  Base64 encoded: {len(img_data)} characters")
                    return img_data, file_path
                except Exception as e:
                    import traceback
                    print(f"✗ Error reading file: {e}")
                    traceback.print_exc()

            if isinstance(img_url, str) and img_url.startswith("http"):
                try:
                    print(f"  Fallback: fetching via HTTP: {img_url}")
                    response = requests.get(img_url, timeout=20)
                    if response.status_code == 200:
                        raw_data = response.content
                        print(f"  Read {len(raw_data)} bytes from HTTP")
                        img_data = base64.b64encode(raw_data).decode("utf-8")
                        print(f"  Base64 encoded: {len(img_data)} characters")
                        return img_data, None
                    else:
                        print(f"✗ HTTP fetch failed: {response.status_code}")
                except Exception as e:
                    print(f"✗ HTTP fetch error: {e}")

            return None, None
        
        if isinstance(result, list):
            for img_url in result:
                if isinstance(img_url, str):
                    file_path = parse_api_url_to_filepath(img_url)
                    
                    if not file_path:
                        print(f"Warning: Could not parse image URL: {img_url}")
                        continue
                    
                    print(f"Reading image from: {file_path}")
                    img_data, used_path = encode_image_from_path_or_url(file_path, img_url)
                    if img_data:
                        images.append(img_data)
                        print(f"  ✓ Added to images list (total: {len(images)})")
                        if used_path:
                            generated_files.append(used_path)
                    else:
                        print(f"✗ Unable to load image from disk or URL")
        elif isinstance(result, dict):
            # Check for various possible response structures
            result_list = result.get('result') or result.get('results') or result.get('images') or []
            for img_url in result_list:
                if isinstance(img_url, str):
                    file_path = parse_api_url_to_filepath(img_url)
                    
                    if not file_path:
                        continue
                    
                    print(f"Reading image from: {file_path}")
                    img_data, used_path = encode_image_from_path_or_url(file_path, img_url)
                    if img_data:
                        images.append(img_data)
                        print(f"  ✓ Added to images list (total: {len(images)})")
                        if used_path:
                            generated_files.append(used_path)
                    else:
                        print(f"✗ Unable to load image from disk or URL")
        
        if not images:
            clean()  # Cleanup temp files
            print(f"✗ ERROR: No images were successfully encoded")
            return {
                "error": "No images generated - check Fooocus API response",
                "progress": 0
            }
        
        print(f"\n✓ SUCCESS: Encoded {len(images)} image(s) to base64")

        # Optional: dump Fooocus log.html if it exists (debugging)
        log_candidates = [
            "/content/outputs/log.html",
            "/content/app/outputs/log.html",
            "/content/Fooocus/outputs/log.html",
            "/workspace/Fooocus/outputs/log.html",
            "/app/outputs/log.html",
            "/outputs/log.html",
        ]
        for log_path in log_candidates:
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        print("--- FOOOCUS LOG START ---")
                        print(f.read())
                        print("--- FOOOCUS LOG END ---")
                except Exception as e:
                    print(f"Warning: Could not read log file {log_path}: {e}")
                break
        
        # Clean up generated files after encoding (AFTER base64 is complete)
        if generated_files:
            print(f"Cleaning up {len(generated_files)} generated files...")
            for file_path in generated_files:
                try:
                    os.remove(file_path)
                    print(f"  ✓ Deleted: {file_path}")
                except Exception as e:
                    print(f"  Warning: Could not delete {file_path}: {e}")
        
        # Final cleanup of RunPod temp files
        clean()
        
        print(f"Returning response with {len(images)} image(s)...")
        return {
            "images": images,
            "progress": 100,
            "message": f"Successfully generated {len(images)} image(s)"
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        traceback.print_exc()
        
        # Cleanup even on error
        try:
            clean()
        except:
            pass
        
        return {
            "error": str(e),
            "progress": 0
        }


# Initialize RunPod serverless handler
if __name__ == "__main__":
    try:
        import runpod
        
        print("Starting RunPod serverless handler...")
        runpod.serverless.start(
            {
                "handler": handler
            }
        )
    except ImportError:
        print("RunPod SDK not available. Running in test mode...")
        # Test with sample input
        test = {
            "input": {
                "prompt": "A beautiful sunset, cinematic",
                "negative_prompt": "blurry",
                "base_model_name": "onlyfornsfw118_v20.safetensors",
                "image_number": 1,
                "output_format": "png",
                "aspect_ratios_selection": "1024*1024"
            }
        }
        
        result = handler(test)
        print(json.dumps(result, indent=2))

