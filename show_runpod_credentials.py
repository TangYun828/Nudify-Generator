"""
Display complete C2PA credentials for RunPod environment variables
"""
import base64
from pathlib import Path

def show_credentials():
    """Display complete base64-encoded credentials"""
    
    print("=" * 80)
    print("RUNPOD ENVIRONMENT VARIABLES - COPY & PASTE")
    print("=" * 80)
    print()
    
    # Read credential files
    private_key_path = Path("c2pa_private_key.pem")
    cert_path = Path("c2pa_certificate.pem")
    
    if not private_key_path.exists() or not cert_path.exists():
        print("❌ Error: Credential files not found!")
        print("   Run: python generate_c2pa_credentials.py")
        return
    
    # Read and encode
    with open(private_key_path, "rb") as f:
        private_key_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    with open(cert_path, "rb") as f:
        cert_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Display full values
    print("1. C2PA_PRIVATE_KEY_BASE64")
    print("-" * 80)
    print(private_key_b64)
    print()
    print()
    
    print("2. C2PA_CERT_BASE64")
    print("-" * 80)
    print(cert_b64)
    print()
    print()
    
    print("=" * 80)
    print("INSTRUCTIONS FOR RUNPOD")
    print("=" * 80)
    print()
    print("1. Go to your RunPod Serverless Endpoint")
    print("2. Click 'Settings' → 'Environment Variables'")
    print("3. Add these two variables:")
    print()
    print("   Variable Name: C2PA_PRIVATE_KEY_BASE64")
    print(f"   Value: {private_key_b64}")
    print()
    print("   Variable Name: C2PA_CERT_BASE64")
    print(f"   Value: {cert_b64}")
    print()
    print("4. Save and rebuild your endpoint")
    print()
    print("=" * 80)
    print("✓ Credentials ready for deployment")
    print("=" * 80)
    
    # Also save to file for easy copying
    output_file = Path("runpod_env_vars.txt")
    with open(output_file, "w") as f:
        f.write("# RunPod Environment Variables - Watermarking Credentials\n\n")
        f.write("C2PA_PRIVATE_KEY_BASE64=")
        f.write(private_key_b64)
        f.write("\n\n")
        f.write("C2PA_CERT_BASE64=")
        f.write(cert_b64)
        f.write("\n")
    
    print()
    print(f"💾 Full credentials also saved to: {output_file.absolute()}")
    print("   You can copy from this file")

if __name__ == "__main__":
    show_credentials()
