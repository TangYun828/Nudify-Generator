"""
Serverless handler for RunPod Fooocus API
"""
import os
import json
import base64
import subprocess
import time
from io import BytesIO
from PIL import Image
import requests

# Start Fooocus service on container startup
def start_fooocus():
    """Start the Fooocus API in the background"""
    process = subprocess.Popen(
        ["python", "launch.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait for API to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:7866/v1/models/list")
            if response.status_code == 200:
                print("Fooocus API is ready!")
                return process
        except:
            time.sleep(1)
    raise Exception("Failed to start Fooocus API")

# Initialize API on first import
try:
    API_PROCESS = start_fooocus()
except:
    print("Warning: Could not auto-start Fooocus. Make sure it's running on port 7866")
    API_PROCESS = None

def handler(event):
    """
    RunPod serverless handler for Fooocus image generation
    
    Expected input:
    {
        "prompt": "A beautiful sunset",
        "base_model_name": "juggernautXL_v8Rundiffusion.safetensors",
        "num_images": 1,
        "seed": -1,
        "negative_prompt": ""
    }
    """
    try:
        # Extract parameters from input
        prompt = event.get("prompt", "")
        base_model = event.get("base_model_name", "juggernautXL_v8Rundiffusion.safetensors")
        num_images = event.get("num_images", 1)
        seed = event.get("seed", -1)
        negative_prompt = event.get("negative_prompt", "")
        
        if not prompt:
            return {
                "status": "error",
                "message": "Prompt is required"
            }
        
        # Call Fooocus API
        api_url = "http://localhost:7866/v1/engine/generation"
        payload = {
            "prompt": prompt,
            "base_model_name": base_model,
            "image_number": num_images,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "async_process": False
        }
        
        response = requests.post(api_url, json=payload, timeout=300)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"API error: {response.text}"
            }
        
        data = response.json()
        
        # Process response
        if not isinstance(data, list) or len(data) == 0:
            return {
                "status": "error",
                "message": "No image generated"
            }
        
        # Return first image URL
        return {
            "status": "success",
            "image_url": data[0].get("url") if isinstance(data[0], dict) else str(data[0]),
            "data": data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    # For local testing
    test_input = {
        "prompt": "A beautiful sunset over mountains",
        "base_model_name": "juggernautXL_v8Rundiffusion.safetensors",
        "num_images": 1
    }
    result = handler(test_input)
    print(json.dumps(result, indent=2))
