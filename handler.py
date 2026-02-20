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

# Add app directory to path
sys.path.insert(0, '/content/app')

# Start Fooocus on init
def start_fooocus():
    """Start Fooocus API in background"""
    print("Starting Fooocus API...")
    
    # Run entrypoint.sh to set up symlinks and start Fooocus
    process = subprocess.Popen(
        ["sh", "-c", "/content/entrypoint.sh"],
        cwd="/content",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for API to be ready
    max_retries = 120  # 2 minutes for model load
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:7865/config", timeout=5)
            if response.status_code == 200:
                print(f"✓ Fooocus API is ready! (attempt {i+1})")
                return process
        except Exception as e:
            if i % 10 == 0:
                print(f"Waiting for Fooocus... ({i}s elapsed)")
            time.sleep(1)
    
    raise Exception("Failed to start Fooocus API after 120 seconds")

# Initialize on import
FOOOCUS_PROCESS = None
try:
    FOOOCUS_PROCESS = start_fooocus()
except Exception as e:
    print(f"Warning: Could not auto-start Fooocus: {e}")


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
        
        # Call Fooocus API directly
        fooocus_api = "http://127.0.0.1:7865"
        
        # Prepare generation payload for Fooocus API
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "use_base_model": base_model,
            "performance": "Quality",
            "aspect_ratios_selection": aspect_ratio,
            "image_number": int(num_images),
            "style_selections": [],
            "quality": "High",
            "output_format": output_format
        }
        
        # Call Fooocus generation endpoint
        print("Calling Fooocus API...")
        response = requests.post(
            f"{fooocus_api}/v1/generation",
            json=payload,
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
        print(f"Fooocus response keys: {result.keys() if isinstance(result, dict) else 'list'}")
        
        # Extract image data from response
        images = []
        if isinstance(result, dict) and "results" in result:
            for img_path in result["results"]:
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode("utf-8")
                        images.append(img_data)
        elif isinstance(result, list) and len(result) > 0:
            for item in result:
                if isinstance(item, str) and os.path.exists(item):
                    with open(item, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode("utf-8")
                        images.append(img_data)
        
        if not images:
            return {
                "output": {
                    "error": "No images generated - check Fooocus API response",
                    "progress": 0
                }
            }
        
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

