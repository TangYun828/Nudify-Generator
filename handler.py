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

# Start Fooocus on init
def start_fooocus():
    """Start Fooocus API in background"""
    print("Starting Fooocus API...")
    process = subprocess.Popen(
        ["python", "/content/app/launch.py", "--listen", "127.0.0.1", "--port", "7865"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for API to be ready
    max_retries = 60
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:7865/config", timeout=5)
            if response.status_code == 200:
                print("✓ Fooocus API is ready!")
                return process
        except:
            time.sleep(1)
    
    raise Exception("Failed to start Fooocus API after 60 seconds")

# Initialize on import
FOOOCUS_PROCESS = None
try:
    FOOOCUS_PROCESS = start_fooocus()
except Exception as e:
    print(f"Warning: Could not auto-start Fooocus: {e}")


def handler(event):
    """
    RunPod Serverless Handler for Fooocus
    Handles both index-docker.html and app.html frontend formats
    
    Input formats (from frontends):
    - Index-docker format: {"input": {"prompt": "...", "base_model_name": "...", "num_images": 1, ...}}
    - App.html format: {"input": {"prompt": "...", "image_number": 1, "base_model_name": "...", ...}}
    
    Output format (to RunPod API):
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
        print(f"Fooocus response: {result}")
        
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
                    "error": "No images generated",
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


if __name__ == "__main__":
    # Test with frontend format
    test = {
        "input": {
            "prompt": "A beautiful sunset, cinematic",
            "negative_prompt": "blurry",
            "base_model_name": "juggernautXL_v8Rundiffusion.safetensors",
            "num_images": 1
        }
    }
    
    result = handler(test)
    print(json.dumps(result, indent=2))
