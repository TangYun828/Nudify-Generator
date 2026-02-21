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
    # Use empty apikey to disable authentication
    import threading
    
    process = subprocess.Popen(
        ["bash", "/content/entrypoint.sh", "--listen", "--apikey", ""],
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
    
    for i in range(max_retries):
        try:
            # Check if FastAPI server is running on port 7866
            response = requests.get("http://127.0.0.1:7866/docs", timeout=3)
            if response.status_code == 200:
                print(f"✓ Fooocus FastAPI is ready on port 7866! (waited {i+1}s)")
                # Wait 5 more seconds for model loading
                time.sleep(5)
                return process
        except Exception as e:
            if i % 20 == 0:
                print(f"Waiting for Fooocus FastAPI... ({i}s elapsed)")
            time.sleep(1)
    
    raise Exception("Failed to start Fooocus FastAPI after 240 seconds")

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
        "output": {
            "images": ["base64_data1", "base64_data2"],
            "progress": 100,
            "message": "Generation complete"
        }
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
                "output": {
                    "error": "Prompt is required",
                    "progress": 0
                }
            }
        
        print(f"Generating {num_images} image(s) with prompt: {prompt}")
        print(f"Model: {base_model}, Format: {output_format}, Aspect: {aspect_ratio}")
        
        # Call Fooocus FastAPI on port 7866
        fooocus_api = "http://127.0.0.1:7866"
        
        # Prepare payload matching CommonRequest model
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "base_model_name": base_model,
            "aspect_ratios_selection": aspect_ratio,
            "image_number": int(num_images),
            "output_format": output_format,
            "async_process": False,  # Synchronous for serverless
            "stream_output": False,  # No streaming in serverless
            "performance_selection": "Quality"
            # Note: require_base64 is not used according to FooocusAPI docs
        }
        
        # Call Fooocus FastAPI endpoint
        print(f"Calling Fooocus FastAPI at {fooocus_api}/v1/engine/generate/...")
        response = requests.post(
            f"{fooocus_api}/v1/engine/generate/",
            json=payload,
            headers={
                "Content-Type": "application/json"
                # No X-API-KEY header needed when apikey is empty
            },
            timeout=300
        )
        
        if response.status_code != 200:
            error_msg = f"Fooocus API error: {response.status_code} - {response.text}"
            print(error_msg)
            return {
                "output": {
                    "error": error_msg,
                    "progress": 0
                }
            }
        
        result = response.json()
        print(f"Fooocus API response type: {type(result)}")
        print(f"Response sample: {str(result)[:200]}")
        
        # FooocusAPI returns a list of file paths
        # Example: ["/content/app/outputs/2024-06-30/image_xxx.png"]
        images = []
        generated_files = []  # Track files to delete after encoding
        
        if isinstance(result, list):
            for img_path in result:
                # img_path is a file path
                if isinstance(img_path, str):
                    # Remove any URL prefix and get actual file path
                    file_path = img_path
                    if file_path.startswith('/outputs/'):
                        file_path = f"/content/app{file_path}"
                    elif not file_path.startswith('/'):
                        file_path = f"/content/app/outputs/{file_path}"
                    
                    print(f"Reading image from: {file_path}")
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            img_data = base64.b64encode(f.read()).decode("utf-8")
                            images.append(img_data)
                        generated_files.append(file_path)
                    else:
                        print(f"Warning: File not found: {file_path}")
        elif isinstance(result, dict):
            # Check for various possible response structures
            result_list = result.get('result') or result.get('results') or result.get('images') or []
            for img_path in result_list:
                if isinstance(img_path, str):
                    file_path = img_path
                    if file_path.startswith('/outputs/'):
                        file_path = f"/content/app{file_path}"
                    elif not file_path.startswith('/'):
                        file_path = f"/content/app/outputs/{file_path}"
                    
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            img_data = base64.b64encode(f.read()).decode("utf-8")
                            images.append(img_data)
                        generated_files.append(file_path)
        
        # Clean up generated files after encoding
        if generated_files:
            print(f"Cleaning up {len(generated_files)} generated files...")
            for file_path in generated_files:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not delete {file_path}: {e}")
        
        if not images:
            clean()  # Cleanup temp files
            return {
                "output": {
                    "error": "No images generated - check Fooocus API response",
                    "progress": 0
                }
            }
        
        # Success - cleanup temp files before returning
        clean()
        
        return {
            "output": {
                "images": images,
                "progress": 100,
                "message": f"Successfully generated {len(images)} image(s)"
            }
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
            "output": {
                "error": str(e),
                "progress": 0
            }
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

