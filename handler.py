"""
RunPod Serverless Handler for Fooocus Image Generation
Processes generation requests and returns base64-encoded images
"""

import os
import sys
import json
import base64
import subprocess
import time
import requests
import threading
from runpod.serverless.utils.rp_cleanup import clean
from safety_checker import check_image_safety
from s3_uploader import upload_safe_image

# Try to import watermarking module
try:
    from compliance_watermark import compliance_watermark
    WATERMARKING_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Watermarking module not available: {e}")
    compliance_watermark = None
    WATERMARKING_AVAILABLE = False

# Configuration
FOOOCUS_API_URL = "http://127.0.0.1:7866"
FOOOCUS_API_PORT = 7866
OUTPUTS_BASE_PATH = "/content/app/outputs"
API_STARTUP_TIMEOUT = 240  # seconds
MODEL_LOAD_DELAY = 10  # seconds

sys.path.insert(0, '/content/app')


def start_fooocus():
    """Initialize Fooocus API server in background"""
    print("=" * 60)
    print("Starting Fooocus API...")
    
    process = subprocess.Popen(
        ["bash", "/content/entrypoint.sh", "--listen", "0.0.0.0", "--port", "7865", "--nowebui"],
        cwd="/content",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Stream logs in background
    def stream_logs():
        try:
            for line in process.stdout:
                print(f"[Fooocus] {line.rstrip()}")
        except:
            pass
    
    threading.Thread(target=stream_logs, daemon=True).start()
    
    # Wait for API ready
    for i in range(API_STARTUP_TIMEOUT):
        try:
            if requests.get(f"{FOOOCUS_API_URL}/docs", timeout=3).status_code == 200:
                if i > 30:  # Ensure model is loaded
                    print(f"✓ Fooocus API ready (waited {i+1}s)")
                    print("Allowing time for model initialization...")
                    time.sleep(MODEL_LOAD_DELAY)
                    print("=" * 60)
                    return process
        except:
            if i % 30 == 0:
                print(f"Waiting for API... ({i}s elapsed)")
        time.sleep(1)
    
    raise Exception(f"Fooocus API failed to start after {API_STARTUP_TIMEOUT}s")


def poll_for_completion(task_id, timeout=300, poll_interval=3):
    """Poll Fooocus API for task completion"""
    start_time = time.time()
    poll_count = 0
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{FOOOCUS_API_URL}/tasks/{task_id}",
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("task_status", "")
                
                poll_count += 1
                if poll_count % 5 == 1:
                    progress = task_data.get("progress", 0)
                    print(f"Poll #{poll_count}: {status} ({progress*100:.1f}%)")
                
                if status == "finished":
                    print(f"✓ Task completed (polls: {poll_count}, time: {time.time()-start_time:.1f}s)")
                    return task_data.get("result", [])
                elif status in ["stop", "skip"]:
                    print(f"⚠ Task {status}ped")
                    return task_data.get("result", [])
                elif status in ["failed", "error"]:
                    print(f"✗ Task failed: {task_data.get('error', 'Unknown error')}")
                    return None
            
            time.sleep(poll_interval)
        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(poll_interval)
    
    print(f"✗ Polling timeout after {timeout}s")
    return None


def url_to_filepath(img_url):
    """Convert Fooocus API URL to local file path"""
    if not isinstance(img_url, str) or '/outputs/' not in img_url:
        return None
    
    # Extract relative path: http://127.0.0.1:7866/outputs/2026-02-21/img.png → 2026-02-21/img.png
    relative_path = img_url.split('/outputs/')[-1].lstrip('/')
    
    # Try known base paths
    base_paths = [
        OUTPUTS_BASE_PATH,
        '/content/outputs',
        '/content/Fooocus/outputs',
        '/workspace/Fooocus/outputs',
        '/app/outputs',
        '/outputs'
    ]
    
    for base in base_paths:
        full_path = os.path.join(base, relative_path)
        if os.path.exists(full_path):
            return full_path
    
    print(f"✗ File not found: {relative_path}")
    return None


def encode_image(file_path=None, img_url=None):
    """Encode image to base64 from file or URL with watermarking"""
    # Try local file first
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            
            # Apply watermarking if available
            if WATERMARKING_AVAILABLE and compliance_watermark:
                try:
                    watermarked_bytes = compliance_watermark.apply_full_compliance(
                        img_bytes,
                        include_visible_badge=True  # Add the "AI GENERATED" badge
                    )
                    print(f"   ✓ Watermarking applied: visible badge + C2PA metadata + latent watermark")
                except Exception as e:
                    print(f"   ⚠ Watermarking failed (returning original): {e}")
                    watermarked_bytes = img_bytes  # Fallback to original if watermarking fails
            else:
                print(f"   ℹ Watermarking not available, returning unwatermarked image")
                watermarked_bytes = img_bytes
            
            data = base64.b64encode(watermarked_bytes).decode("utf-8")
            return data, file_path
        except Exception as e:
            print(f"✗ File read error: {e}")
    
    # Fallback to HTTP
    if img_url and img_url.startswith("http"):
        try:
            response = requests.get(img_url, timeout=20)
            if response.status_code == 200:
                img_bytes = response.content
                
                # Apply watermarking if available
                if WATERMARKING_AVAILABLE and compliance_watermark:
                    try:
                        watermarked_bytes = compliance_watermark.apply_full_compliance(
                            img_bytes,
                            include_visible_badge=True
                        )
                        print(f"   ✓ Watermarking applied: visible badge + C2PA metadata + latent watermark")
                    except Exception as e:
                        print(f"   ⚠ Watermarking failed (returning original): {e}")
                        watermarked_bytes = img_bytes
                else:
                    print(f"   ℹ Watermarking not available, returning unwatermarked image")
                    watermarked_bytes = img_bytes
                
                data = base64.b64encode(watermarked_bytes).decode("utf-8")
                return data, None
        except Exception as e:
            print(f"✗ HTTP fetch error: {e}")
    
    return None, None


def process_results(result_data, user_id: str = "unknown", prompt: str = ""):
    """Extract and encode images from API result with AWS Rekognition safety check"""
    images = []
    files_to_cleanup = []
    safety_violations = []
    
    # Normalize result to list
    if isinstance(result_data, dict):
        result_list = result_data.get('result') or result_data.get('images') or []
    elif isinstance(result_data, list):
        result_list = result_data
    else:
        print(f"✗ Unexpected result type: {type(result_data)}")
        return []
    
    # Process each image URL
    for img_url in result_list:
        if not isinstance(img_url, str):
            continue
        
        file_path = url_to_filepath(img_url)
        
        if not file_path:
            print(f"⚠ Skipping - file not found: {img_url}")
            continue
        
        # ============================================
        # LAYER 3: AWS Rekognition Safety Check
        # ============================================
        try:
            print(f"🔍 Checking image safety: {os.path.basename(file_path)}")
            safety_result = check_image_safety(file_path)
            
            if not safety_result['is_safe']:
                # Image failed safety check - log and skip
                print(f"❌ BLOCKED: {', '.join(safety_result['flagged_categories'])}")
                print(f"   Confidence: {safety_result['confidence']:.1f}%")
                
                safety_violations.append({
                    'file_path': file_path,
                    'flagged_categories': safety_result['flagged_categories'],
                    'confidence': safety_result['confidence'],
                    'moderation_labels': safety_result['moderation_labels']
                })
                
                # Delete unsafe image immediately
                try:
                    os.remove(file_path)
                    print(f"   Deleted unsafe image: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"   Warning: Failed to delete {file_path}: {e}")
                
                continue  # Skip encoding this image
            
            print(f"✓ Image passed safety check")
            
        except Exception as e:
            print(f"⚠ Safety check failed (will block): {e}")
            # Fail closed - if safety check errors, don't return the image
            safety_violations.append({
                'file_path': file_path,
                'flagged_categories': ['SAFETY_CHECK_ERROR'],
                'confidence': 0.0,
                'error': str(e)
            })
            continue
        
        # ============================================
        # LAYER 4: Upload to S3/R2 for audit trail
        # ============================================
        try:
            print(f"📤 Uploading to S3 for audit trail...")
            s3_url = upload_safe_image(
                file_path=file_path,
                user_id=user_id,
                prompt=prompt,
                metadata={
                    'safety_confidence': safety_result['confidence'],
                    'checked_at': safety_result['checked_at']
                }
            )
            if s3_url:
                print(f"   ✓ Uploaded: {s3_url}")
        except Exception as e:
            # S3 upload is non-critical - log but don't fail
            print(f"   ⚠ S3 upload failed (non-critical): {e}")
        
        # ============================================
        # Image is safe - proceed with encoding
        # ============================================
        img_data, used_path = encode_image(file_path, img_url)
        
        if img_data:
            images.append(img_data)
            if used_path:
                files_to_cleanup.append(used_path)
    
    # Cleanup files
    for path in files_to_cleanup:
        try:
            os.remove(path)
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    # Log safety violations summary
    if safety_violations:
        print(f"\n⚠ SAFETY SUMMARY: {len(safety_violations)} image(s) blocked")
        for violation in safety_violations:
            categories = violation.get('flagged_categories', [])
            print(f"   - {os.path.basename(violation['file_path'])}: {', '.join(categories)}")
    
    return images


def handler(event):
    """
    Main handler for RunPod serverless
    
    Input: {"input": {"prompt": str, "image_number": int, ...}}
    Output: {"images": [base64_str], "progress": 100, "message": str}
    """
    try:
        job_input = event.get("input", {})
        
        # Extract parameters
        prompt = job_input.get("prompt", "")
        if not prompt:
            return {"error": "Prompt is required", "progress": 0}
        
        user_id = job_input.get("user_id", "unknown")  # Extract user_id for audit trail
        num_images = job_input.get("image_number") or job_input.get("num_images", 1)
        negative_prompt = job_input.get("negative_prompt", "")
        base_model = job_input.get("base_model_name", "onlyfornsfw118_v20.safetensors")
        output_format = job_input.get("output_format", "png").lower()
        aspect_ratio = job_input.get("aspect_ratios_selection", "1024*1024")
        
        print(f"Generating {num_images} image(s): {prompt[:50]}...")
        
        # Call Fooocus API
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "base_model_name": base_model,
            "aspect_ratios_selection": aspect_ratio,
            "image_number": int(num_images),
            "output_format": output_format,
            "async_process": False,
            "stream_output": False,
            "performance_selection": "Quality"
        }
        
        response = requests.post(
            f"{FOOOCUS_API_URL}/v1/engine/generate/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if response.status_code != 200:
            return {"error": f"API error: {response.status_code}", "progress": 0}
        
        response_data = response.json()
        
        # Handle async response (shouldn't happen with async_process=False)
        if isinstance(response_data, dict) and "task_id" in response_data:
            print("⚠ Got task_id (unexpected)")
            result = poll_for_completion(response_data["task_id"])
        elif isinstance(response_data, dict) and "result" in response_data:
            result = response_data["result"]
        else:
            result = response_data
        
        if not result:
            return {"error": "No result from API", "progress": 0}
        
        # Allow disk I/O to complete
        time.sleep(1)
        
        # Process and encode images (with safety check and S3 upload)
        images = process_results(result, user_id=user_id, prompt=prompt)
        
        if not images:
            clean()
            return {"error": "No images generated", "progress": 0}
        
        print(f"✓ SUCCESS: {len(images)} image(s) encoded")
        clean()
        
        return {
            "images": images,
            "progress": 100,
            "message": f"Generated {len(images)} image(s)"
        }
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            clean()
        except:
            pass
        
        return {"error": str(e), "progress": 0}


# Initialize Fooocus on startup
FOOOCUS_PROCESS = None
try:
    FOOOCUS_PROCESS = start_fooocus()
except Exception as e:
    print(f"✗ CRITICAL: Fooocus initialization failed: {e}")
    import traceback
    traceback.print_exc()


# RunPod entry point
if __name__ == "__main__":
    try:
        import runpod
        print("Starting RunPod serverless handler...")
        runpod.serverless.start({"handler": handler})
    except ImportError:
        print("Test mode - RunPod SDK not available")
        test_input = {
            "input": {
                "prompt": "A beautiful sunset",
                "image_number": 1,
                "base_model_name": "onlyfornsfw118_v20.safetensors"
            }
        }
        result = handler(test_input)
        print(json.dumps(result, indent=2)[:500])
