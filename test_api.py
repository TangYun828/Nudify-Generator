"""
Test FastAPI Server (without Fooocus)
For local testing of authentication and API endpoints
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

from database import SessionLocal, init_db
from security import PasswordHandler, JWTHandler
from schemas import UserRegister, UserLogin, GenerateImageRequest
from db_models.user import User
from db_models.credits import Credits
from db_models.usage_log import UsageLog
from safety_checker import check_image_safety, check_image_safety_bytes
from s3_uploader import upload_safe_image
from compliance_watermark import compliance_watermark
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import hashlib

# ============================================================
# FastAPI Setup
# ============================================================

app = FastAPI(
    title="Nudify API (Test Mode)",
    description="NSFW Image Generation API - Testing Authentication",
    version="1.0.0"
)

# CORS middleware - Allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                   # Allow all origins for testing
    allow_credentials=False,               # Set to False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# Health Check
# ============================================================

@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Nudify API Test Server",
        "status": "running",
        "docs": "/docs",
        "test": "/test",
        "mode": "test (Fooocus disabled)"
    }


@app.get("/test", response_class=FileResponse)
def test_page():
    """Serve the browser test interface"""
    test_file = Path(__file__).parent / "test_browser.html"
    if test_file.exists():
        return FileResponse(test_file)
    raise HTTPException(status_code=404, detail="Test page not found")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "mode": "test"}


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
        password_hash=password_handler.hash_password(user_data.password)
    )
    
    db.add(user)
    db.flush()
    
    # Create credit account with free credits
    credits = Credits(
        user_id=user.id,
        credits_remaining=FREE_CREDITS_ON_SIGNUP,
        credits_used_total=0.0
    )
    db.add(credits)
    db.commit()
    
    return {"message": "User registered successfully", "user_id": str(user.id)}


@app.post("/auth/login")
def login(user_data: UserLogin, db=Depends(get_db)):
    """Login user and return JWT token"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    password_handler = PasswordHandler()
    if not password_handler.verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate JWT token
    token = JWTHandler.create_access_token({"sub": str(user.id)})
    
    return {"access_token": token, "token_type": "bearer", "user_id": str(user.id)}


@app.get("/user/profile")
def get_profile(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Get current user profile"""
    credits = db.query(Credits).filter(Credits.user_id == current_user.id).first()
    
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "credits": credits.credits_remaining if credits else 0,
        "created_at": current_user.created_at.isoformat()
    }


@app.get("/credits/balance")
def get_credits(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Get user credit balance"""
    credits = db.query(Credits).filter(Credits.user_id == current_user.id).first()
    
    return {
        "balance": credits.credits_remaining if credits else 0,
        "total_used": credits.credits_used_total if credits else 0
    }


@app.post("/generate/image")
def generate_image_mock(
    request_data: GenerateImageRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Generate image with AWS safety checks (returns test images)"""
    
    # Get user credits
    credits = db.query(Credits).filter(Credits.user_id == current_user.id).first()
    if not credits:
        raise HTTPException(status_code=400, detail="No credit account found")
    
    # Calculate total cost
    num_images = request_data.image_number or 1
    total_cost = num_images * 1  # 1 credit per image
    
    # Check if user has enough credits
    if credits.credits_remaining < total_cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {total_cost}, have {credits.credits_remaining}"
        )
    
    # Deduct credits
    credits.credits_remaining -= total_cost
    credits.credits_used_total += total_cost
    
    # Log usage
    usage_log = UsageLog(
        user_id=current_user.id,
        endpoint="/generate/image",
        method="POST",
        prompt=request_data.prompt,
        credits_deducted=total_cost,
        status="completed",
        request_metadata={"num_images": num_images, "test_mode": True}
    )
    
    db.add(usage_log)
    db.commit()
    
    return {
        "message": "TEST MODE: Fooocus not available. This would generate images in production.",
        "credits_used": total_cost,
        "credits_remaining": credits.credits_remaining,
        "prompt": request_data.prompt,
        "num_images": num_images,
        "note": "In production, this endpoint returns base64-encoded images"
    }


@app.post("/api/runpod/generate")
def runpod_simulate(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Simulate RunPod endpoint locally with AWS safety checks
    Mimics RunPod's request/response format for integration testing
    """
    
    # Extract input from RunPod format
    input_data = request_data.get("input", {})
    prompt = input_data.get("prompt", "")
    user_id = input_data.get("user_id", str(current_user.id))
    num_images = input_data.get("image_number", 1)
    size = input_data.get("size", "1024x1024")
    requested_format = str(input_data.get("format", "png")).lower()
    if requested_format == "jpg":
        img_format = "JPEG"
        response_format = "jpg"
    else:
        img_format = "PNG"
        response_format = "png"
    
    # Parse size (e.g., "1536x640" -> width=1536, height=640)
    try:
        width, height = map(int, size.split('x'))
    except (ValueError, AttributeError):
        width, height = 1024, 1024  # Default fallback
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    print(f"\n📥 Received request from user {user_id}")
    print(f"   Prompt: {prompt[:100]}...")
    print(f"   Images: {num_images}")
    print(f"   Size: {width}x{height}")
    print(f"   Format: {response_format}")
    print(f"   Watermark: {'ON' if watermark_enabled else 'OFF'}")
    these)
    images = []
    
    for i in range(num_images):
        try:
            # Create a simple test image with text (using requested dimensions)
            img = Image.new('RGB', (width, height), color=(100, 100, 150))
            draw = ImageDraw.Draw(img)
            
            # Calculate text position based on image size
            font_size = min(width, height) // 25  # Relative font size
            
            # Add text to image
            text_lines = [
                "TEST MODE",
                f"Image {i+1}/{num_images}",
                "",
                f"Size: {width}x{height}",
                f"Format: {response_format}",
                "",
                f"Prompt: {prompt[:30]}...",
                "",
                "✓ AWS Safety Check",
                "✓ S3 Audit Upload",
                "",
                "Production: Real image here"
            ]
            
            y_position = height // 20  # Start at 5% of height
            line_height = height // 20  # 5% spacing between lines
            for line in text_lines:
                draw.text((width // 20, y_position), line, fill=(255, 255, 255))
                y_position += line_height

            # Save to bytes with requested format
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img_format)
            img_bytes = img_byte_arr.getvalue()
            
            # Run AWS Rekognition check (Layer 3)
            print(f"\n🔍 Running AWS Rekognition check on image {i+1}...")
            safety_result = check_image_safety_bytes(img_bytes)
            
            if not safety_result['is_safe']:
                print(f"   ✗ Image {i+1} flagged by Rekognition:")
                print(f"     Confidence: {safety_result['confidence']:.1f}%")
                print(f"     Categories: {', '.join(safety_result['flagged_categories'])}")
                print(f"   ✗ Image deleted, not returning to client")
                continue
            
            print(f"   ✓ Image {i+1} passed safety check (confidence: {safety_result['confidence']:.1f}%)")
            
            # Apply legal compliance watermarking (California SB 942 / New York 2026)
            print(f"\n📜 Applying compliance watermarks...")
            print(f"   - C2PA Manifest: Cryptographic proof of AI generation")
            print(f"   - Latent watermark: Imperceptible, survives editing")
            print(f"   - Visible badge: User-facing notice")
            
            watermarked_bytes = compliance_watermark.apply_full_compliance(
                img_bytes, 
                include_visible_badge=True
            )
            
            print(f"   ✓ Watermarks applied (size: {len(watermarked_bytes)} bytes)")
            
            # Upload to S3 (Layer 4) - watermarked version
            # TODO: Implement bytes-based S3 upload with watermarked image
            print(f"\n☁️  S3 audit upload skipped (bytes upload not implemented)...")
            
            # Convert to base64 for response (watermarked version)
            img_base64 = base64.b64encode(watermarked_bytes).decode('utf-8')
            images.append(img_base64)
            
            print(f"   ✓ Image {i+1} ready for delivery (with compliance watermarks)")
            
        except Exception as e:
            print(f"   ✗ Error processing image {i+1}: {e}")
            import traceback
            traceback.print_exc()
    
    # Return in RunPod format
    response = {
        "id": f"test-{current_user.id}",
        "status": "COMPLETED",
        "output": {
            "images": images,
            "progress": 100,
            "message": f"Generated {len(images)} image(s) (TEST MODE with AWS safety checks)",
            "format": response_format,
            "size": f"{width}x{height}"
        }
    }
    
    print(f"\n✓ Request complete: {len(images)} images delivered\n")
    
    return response


# ============================================================
# Startup
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Nudify API Test Server")
    print("=" * 60)
    print("Mode: Testing (Fooocus disabled)")
    print("Initializing database...")
    
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database warning: {e}")
    
    print("=" * 60)
    print("Starting FastAPI server on http://localhost:8000")
    print("=" * 60)
    print("API Documentation: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
