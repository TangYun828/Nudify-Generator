"""
Integrated Handler: RunPod Serverless + FastAPI + User Management
Combines Fooocus image generation with authentication, credits, and usage tracking
"""

import os
import sys
import json
import base64
import subprocess
import time
import requests
import threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Optional RunPod import (only available on RunPod platform)
try:
    from runpod.serverless.utils.rp_cleanup import clean
    HAS_RUNPOD = True
except ImportError:
    HAS_RUNPOD = False
    def clean():
        """Dummy cleanup for local testing"""
        pass

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Import FastAPI and user management
from fastapi import FastAPI, HTTPException, Depends, Header, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import SessionLocal, init_db
from security import PasswordHandler, APIKeyHandler, JWTHandler
from schemas import UserRegister, UserLogin, GenerateImageRequest, UserProfile
from db_models.user import User
from db_models.credits import Credits
from db_models.usage_log import UsageLog

# ============================================================
# FastAPI Setup
# ============================================================

app = FastAPI(
    title="Nudify API",
    description="NSFW Image Generation with User Management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Fooocus Configuration (from original handler.py)
# ============================================================

FOOOCUS_API_URL = "http://127.0.0.1:7866"
FOOOCUS_API_PORT = 7866
OUTPUTS_BASE_PATH = "/content/app/outputs"
API_STARTUP_TIMEOUT = 240
MODEL_LOAD_DELAY = 10

# Credit costs
CREDIT_COST_PER_IMAGE = 1
FREE_CREDITS_ON_SIGNUP = 10


# ============================================================
# Database Dependency
# ============================================================

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: str = Header(None),
    db=Depends(get_db)
) -> User:
    """Verify JWT token and return current user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTHandler.decode_token(token)
        
        if "error" in payload:
            raise HTTPException(status_code=401, detail=payload["error"])
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ============================================================
# Fooocus Functions (from original handler.py)
# ============================================================

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
                if i > 30:
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
    
    relative_path = img_url.split('/outputs/')[-1].lstrip('/')
    
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
    """Encode image to base64 from file or URL"""
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return data, file_path
        except Exception as e:
            print(f"✗ File read error: {e}")
    
    if img_url and img_url.startswith("http"):
        try:
            response = requests.get(img_url, timeout=20)
            if response.status_code == 200:
                data = base64.b64encode(response.content).decode("utf-8")
                return data, None
        except Exception as e:
            print(f"✗ HTTP fetch error: {e}")
    
    return None, None


def process_results(result_data):
    """Extract and encode images from API result"""
    images = []
    files_to_cleanup = []
    
    if isinstance(result_data, dict):
        result_list = result_data.get('result') or result_data.get('images') or []
    elif isinstance(result_data, list):
        result_list = result_data
    else:
        print(f"✗ Unexpected result type: {type(result_data)}")
        return []
    
    for img_url in result_list:
        if not isinstance(img_url, str):
            continue
        
        file_path = url_to_filepath(img_url)
        img_data, used_path = encode_image(file_path, img_url)
        
        if img_data:
            images.append(img_data)
            if used_path:
                files_to_cleanup.append(used_path)
    
    for path in files_to_cleanup:
        try:
            os.remove(path)
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    return images


# ============================================================
# Authentication Endpoints
# ============================================================

@app.post("/auth/register")
def register(user_data: UserRegister, db=Depends(get_db)):
    """Register new user with free credits"""
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    password_handler = PasswordHandler()
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=password_handler.hash_password(user_data.password)
    )
    
    db.add(user)
    db.flush()  # Get the user ID
    
    # Create credit account with free credits
    credits = Credits(
        user_id=user.id,
        balance=FREE_CREDITS_ON_SIGNUP,
        total_earned=FREE_CREDITS_ON_SIGNUP,
        total_spent=0
    )
    db.add(credits)
    db.commit()
    
    return {"message": "User registered successfully", "user_id": user.id}


@app.post("/auth/login")
def login(user_data: UserLogin, db=Depends(get_db)):
    """Login user and return JWT token"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    password_handler = PasswordHandler()
    if not password_handler.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate JWT token
    token = JWTHandler.create_access_token({"sub": str(user.id)})
    
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}


@app.get("/user/profile")
def get_profile(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Get current user profile"""
    credits = db.query(Credits).filter(Credits.user_id == current_user.id).first()
    
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "credits": credits.balance if credits else 0,
        "created_at": current_user.created_at.isoformat()
    }


# ============================================================
# Image Generation Endpoints
# ============================================================

@app.post("/generate/image")
def generate_image(
    request_data: GenerateImageRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Generate image(s) and deduct credits"""
    
    # Get user credits
    credits = db.query(Credits).filter(Credits.user_id == current_user.id).first()
    if not credits:
        raise HTTPException(status_code=400, detail="No credit account found")
    
    # Calculate total cost
    num_images = request_data.image_number or 1
    total_cost = num_images * CREDIT_COST_PER_IMAGE
    
    # Check if user has enough credits
    if credits.balance < total_cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {total_cost}, have {credits.balance}"
        )
    
    try:
        # Call Fooocus API
        payload = {
            "prompt": request_data.prompt,
            "negative_prompt": request_data.negative_prompt or "",
            "base_model_name": request_data.base_model_name or "onlyfornsfw118_v20.safetensors",
            "aspect_ratios_selection": request_data.aspect_ratio or "1024*1024",
            "image_number": int(num_images),
            "output_format": (request_data.output_format or "png").lower(),
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
            raise Exception(f"API error: {response.status_code}")
        
        response_data = response.json()
        
        # Handle async response
        if isinstance(response_data, dict) and "task_id" in response_data:
            result = poll_for_completion(response_data["task_id"])
        elif isinstance(response_data, dict) and "result" in response_data:
            result = response_data["result"]
        else:
            result = response_data
        
        if not result:
            raise Exception("No result from API")
        
        # Allow disk I/O to complete
        time.sleep(1)
        
        # Process and encode images
        images = process_results(result)
        
        if not images:
            raise Exception("No images generated")
        
        # Deduct credits
        credits.balance -= total_cost
        credits.total_spent += total_cost
        
        # Log usage
        usage_log = UsageLog(
            user_id=current_user.id,
            endpoint="/generate/image",
            method="POST",
            prompt=request_data.prompt,
            credits_deducted=total_cost,
            status="completed",
            request_metadata={"num_images": num_images}
        )
        
        db.add(usage_log)
        db.commit()
        
        print(f"✓ SUCCESS: {len(images)} image(s) generated for user {current_user.id}")
        
        return {
            "images": images,
            "credits_used": total_cost,
            "credits_remaining": credits.balance,
            "message": f"Generated {len(images)} image(s)"
        }
        
    except Exception as e:
        # Log failed request
        usage_log = UsageLog(
            user_id=current_user.id,
            endpoint="/generate/image",
            method="POST",
            prompt=request_data.prompt,
            credits_deducted=0,
            status="failed",
            request_metadata={"error": str(e)}
        )
        db.add(usage_log)
        db.commit()
        
        print(f"✗ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/credits/balance")
def get_credits(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Get user credit balance"""
    credits = db.query(Credits).filter(Credits.user_id == current_user.id).first()
    
    return {
        "balance": credits.balance if credits else 0,
        "total_earned": credits.total_earned if credits else 0,
        "total_spent": credits.total_spent if credits else 0
    }


# ============================================================
# RunPod Serverless Handler Wrapper
# ============================================================

def handler(event):
    """
    RunPod serverless handler for backward compatibility
    Routes to FastAPI endpoints
    """
    try:
        job_input = event.get("input", {})
        
        # Extract parameters
        prompt = job_input.get("prompt", "")
        if not prompt:
            return {"error": "Prompt is required", "progress": 0}
        
        num_images = job_input.get("image_number", 1)
        user_id = job_input.get("user_id")
        token = job_input.get("token")
        
        if not token:
            return {"error": "Authentication token required", "progress": 0}
        
        # Verify token and get user
        try:
            payload = JWTHandler.decode_token(token)
            if "error" in payload:
                return {"error": payload["error"], "progress": 0}
            user_id = payload.get("sub")
        except:
            return {"error": "Invalid token", "progress": 0}
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found", "progress": 0}
            
            # Get credits
            credits = db.query(Credits).filter(Credits.user_id == user_id).first()
            total_cost = num_images * CREDIT_COST_PER_IMAGE
            
            if not credits or credits.balance < total_cost:
                return {"error": "Insufficient credits", "progress": 0}
            
            # Call Fooocus API
            payload = {
                "prompt": prompt,
                "negative_prompt": job_input.get("negative_prompt", ""),
                "base_model_name": job_input.get("base_model_name", "onlyfornsfw118_v20.safetensors"),
                "aspect_ratios_selection": job_input.get("aspect_ratio", "1024*1024"),
                "image_number": int(num_images),
                "output_format": job_input.get("output_format", "png").lower(),
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
            
            if isinstance(response_data, dict) and "task_id" in response_data:
                result = poll_for_completion(response_data["task_id"])
            elif isinstance(response_data, dict) and "result" in response_data:
                result = response_data["result"]
            else:
                result = response_data
            
            if not result:
                return {"error": "No result from API", "progress": 0}
            
            time.sleep(1)
            images = process_results(result)
            
            if not images:
                clean()
                return {"error": "No images generated", "progress": 0}
            
            # Deduct credits
            credits.balance -= total_cost
            credits.total_spent += total_cost
            
            usage_log = UsageLog(
                user_id=user_id,
                endpoint="/generate/image",
                method="POST",
                prompt=prompt,
                credits_deducted=total_cost,
                status="completed"
            )
            
            db.add(usage_log)
            db.commit()
            
            print(f"✓ SUCCESS: {len(images)} image(s) encoded")
            clean()
            
            return {
                "images": images,
                "progress": 100,
                "message": f"Generated {len(images)} image(s)",
                "credits_remaining": credits.balance
            }
            
        finally:
            db.close()
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            clean()
        except:
            pass
        
        return {"error": str(e), "progress": 0}


# ============================================================
# Startup
# ============================================================

FOOOCUS_PROCESS = None
UVICORN_THREAD = None

def startup():
    """Initialize database and start services"""
    global FOOOCUS_PROCESS, UVICORN_THREAD
    
    print("=" * 60)
    print("Initializing Nudify Integrated Handler")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database init warning: {e}")
    
    # Start Fooocus
    try:
        FOOOCUS_PROCESS = start_fooocus()
    except Exception as e:
        print(f"✗ CRITICAL: Fooocus initialization failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        import runpod
        
        # Initialize on startup
        startup()
        
        # Start RunPod serverless
        print("Starting RunPod serverless handler...")
        runpod.serverless.start({"handler": handler})
        
    except ImportError:
        # Local testing with FastAPI
        print("RunPod SDK not available - starting FastAPI server for local testing...")
        startup()
        
        print("=" * 60)
        print("Starting FastAPI server on http://localhost:8000")
        print("=" * 60)
        print("API Documentation: http://localhost:8000/docs")
        print("=" * 60)
        
        uvicorn.run(app, host="0.0.0.0", port=8000)
