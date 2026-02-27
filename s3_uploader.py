"""
S3/Cloudflare R2 uploader for audit trail (Layer 4: Audit)

Uploads safe images to cloud storage for:
- Payment processor compliance (6-month retention)
- Legal audit trail
- User dispute resolution
- Pattern analysis

Compatible with:
- AWS S3
- Cloudflare R2 (S3-compatible)
- DigitalOcean Spaces (S3-compatible)
"""

import os
import boto3
from typing import Optional
from datetime import datetime, timedelta, timezone
import logging
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class S3Uploader:
    """S3/R2 uploader for generated images"""
    
    def __init__(self):
        """Initialize S3 client from environment variables"""
        self.bucket_name = os.getenv('AWS_S3_BUCKET')
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Cloudflare R2 endpoint (optional)
        r2_endpoint = os.getenv('R2_ENDPOINT_URL')
        
        if not self.bucket_name:
            logger.warning("⚠ AWS_S3_BUCKET not set - S3 upload disabled")
            self.client = None
            return
        
        if not aws_access_key or not aws_secret_key:
            logger.warning("⚠ AWS credentials not set - S3 upload disabled")
            self.client = None
            return
        
        try:
            # Use R2 endpoint if provided, otherwise AWS S3
            client_config = {
                'aws_access_key_id': aws_access_key,
                'aws_secret_access_key': aws_secret_key,
            }
            
            if r2_endpoint:
                client_config['endpoint_url'] = r2_endpoint
                logger.info(f"✓ Using Cloudflare R2: {r2_endpoint}")
            else:
                client_config['region_name'] = aws_region
                logger.info(f"✓ Using AWS S3 (region: {aws_region})")
            
            self.client = boto3.client('s3', **client_config)
            logger.info(f"✓ S3 uploader initialized (bucket: {self.bucket_name})")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {e}")
            self.client = None
    
    def upload_image(
        self,
        file_path: str,
        user_id: str,
        prompt: str,
        metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        Upload image to S3/R2 with metadata
        
        Args:
            file_path: Local path to image file
            user_id: User ID for folder organization
            prompt: Generation prompt (for metadata)
            metadata: Additional metadata to attach
        
        Returns:
            S3 URL if successful, None if failed or disabled
        """
        if not self.client:
            logger.debug("S3 upload skipped (not configured)")
            return None
        
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None
        
        try:
            # Generate S3 key: audit/{user_id}/{YYYY-MM-DD}/{timestamp}_{filename}
            now = datetime.now(timezone.utc)
            date_str = now.strftime('%Y-%m-%d')
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(file_path)
            
            s3_key = f"audit/{user_id}/{date_str}/{timestamp}_{filename}"
            
            # Prepare metadata
            s3_metadata = {
                'user-id': user_id,
                'uploaded-at': now.isoformat(),
                'prompt': prompt[:1000],  # Truncate to S3 metadata limit
                'retention-until': (now + timedelta(days=180)).isoformat()  # 6 months
            }
            
            # Add custom metadata if provided
            if metadata:
                for key, value in metadata.items():
                    # S3 metadata keys must be lowercase and alphanumeric
                    safe_key = key.lower().replace('_', '-')
                    s3_metadata[safe_key] = str(value)[:1000]
            
            # Set content type based on file extension
            _, ext = os.path.splitext(filename)
            content_type = 'image/png' if ext.lower() == '.png' else 'image/jpeg'
            
            # Upload file
            with open(file_path, 'rb') as f:
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=f,
                    ContentType=content_type,
                    Metadata=s3_metadata,
                    # Optional: Set lifecycle rule for automatic deletion after 6 months
                    # This requires bucket lifecycle configuration
                )
            
            # Generate URL
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"✓ Uploaded to S3: {s3_key}")
            
            return s3_url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"❌ S3 upload failed ({error_code}): {e}")
            return None
        except Exception as e:
            logger.error(f"❌ S3 upload failed: {e}")
            return None
    
    def get_presigned_url(self, s3_url: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for temporary access
        
        Args:
            s3_url: S3 URL (s3://bucket/key)
            expiration: URL validity in seconds (default: 1 hour)
        
        Returns:
            HTTPS presigned URL or None if failed
        """
        if not self.client:
            return None
        
        try:
            # Parse s3:// URL
            if not s3_url.startswith('s3://'):
                return None
            
            parts = s3_url[5:].split('/', 1)
            if len(parts) != 2:
                return None
            
            bucket, key = parts
            
            # Generate presigned URL
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            
            return url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None


# Global instance
_uploader_instance: Optional[S3Uploader] = None


def get_uploader() -> S3Uploader:
    """Get or create global S3 uploader instance"""
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = S3Uploader()
    return _uploader_instance


def upload_safe_image(
    file_path: str,
    user_id: str,
    prompt: str,
    metadata: Optional[dict] = None
) -> Optional[str]:
    """
    Convenience function to upload safe image to S3/R2
    
    Args:
        file_path: Local path to image
        user_id: User ID
        prompt: Generation prompt
        metadata: Additional metadata
    
    Returns:
        S3 URL or None
    """
    uploader = get_uploader()
    return uploader.upload_image(file_path, user_id, prompt, metadata)


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python s3_uploader.py <image_path> <user_id> <prompt>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    user_id = sys.argv[2]
    prompt = ' '.join(sys.argv[3:])
    
    print(f"\n📤 Uploading image to S3...")
    print(f"   User: {user_id}")
    print(f"   Prompt: {prompt[:50]}...")
    
    url = upload_safe_image(image_path, user_id, prompt)
    
    if url:
        print(f"\n✅ Upload successful!")
        print(f"   URL: {url}")
    else:
        print(f"\n❌ Upload failed (check logs)")
