"""
AWS Rekognition-based content safety checker (Layer 3: Inference)

This module checks generated images for policy violations using AWS Rekognition's
DetectModerationLabels API before they are returned to users or stored.

Part of the 4-layer safety architecture:
- Layer 1 (Gateway): Prompt keyword filtering (in Next.js)
- Layer 2 (Injection): Negative prompts hardcoded (in Next.js)
- Layer 3 (Inference): AWS Rekognition output checking ← THIS FILE
- Layer 4 (Audit): Comprehensive logging (in Next.js + this file)
"""

import os
import json
import boto3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result from AWS Rekognition safety check"""
    is_safe: bool
    confidence: float
    flagged_categories: List[str]
    moderation_labels: List[Dict]
    checked_at: str
    error: Optional[str] = None


class AWSRekognitionChecker:
    """AWS Rekognition content moderation checker"""
    
    # Confidence thresholds (AWS Rekognition DetectModerationLabels range: 0-100)
    CONFIDENCE_THRESHOLD = 75.0  # Flag if ≥75% confidence of policy violation
    
    # Critical categories that should be blocked immediately
    CRITICAL_CATEGORIES = {
        'Explicit Nudity',
        'Graphic Male Nudity',
        'Graphic Female Nudity',
        'Sexual Activity',
        'Illustrated Explicit Nudity',
        'Violence',
        'Visually Disturbing',
        'Suggestive',
        'Hate Symbols',
        'Drugs'
    }
    
    # Subcategories to monitor (lower threshold)
    MONITORED_SUBCATEGORIES = {
        'Nudity',
        'Revealing Clothes',
        'Partial Nudity'
    }
    
    def __init__(self):
        """Initialize AWS Rekognition client"""
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not aws_access_key or not aws_secret_key:
            logger.error("❌ AWS credentials not found in environment variables")
            raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set")
        
        try:
            self.client = boto3.client(
                'rekognition',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            logger.info(f"✓ AWS Rekognition client initialized (region: {aws_region})")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS Rekognition: {e}")
            raise
    
    def check_image_from_bytes(self, image_bytes: bytes) -> SafetyResult:
        """
        Check image safety from raw bytes
        
        Args:
            image_bytes: Raw image bytes (PNG/JPEG)
        
        Returns:
            SafetyResult with safety assessment
        """
        try:
            response = self.client.detect_moderation_labels(
                Image={'Bytes': image_bytes},
                MinConfidence=self.CONFIDENCE_THRESHOLD
            )
            
            return self._process_response(response)
            
        except Exception as e:
            logger.error(f"❌ AWS Rekognition API error: {e}")
            return SafetyResult(
                is_safe=False,  # Fail closed for safety
                confidence=0.0,
                flagged_categories=['API_ERROR'],
                moderation_labels=[],
                checked_at=datetime.now(timezone.utc).isoformat(),
                error=str(e)
            )
    
    def check_image_from_file(self, file_path: str) -> SafetyResult:
        """
        Check image safety from local file path
        
        Args:
            file_path: Absolute path to image file
        
        Returns:
            SafetyResult with safety assessment
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ Image file not found: {file_path}")
            return SafetyResult(
                is_safe=False,
                confidence=0.0,
                flagged_categories=['FILE_NOT_FOUND'],
                moderation_labels=[],
                checked_at=datetime.now(timezone.utc).isoformat(),
                error=f"File not found: {file_path}"
            )
        
        try:
            with open(file_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            return self.check_image_from_bytes(image_bytes)
            
        except Exception as e:
            logger.error(f"❌ Error reading file {file_path}: {e}")
            return SafetyResult(
                is_safe=False,
                confidence=0.0,
                flagged_categories=['FILE_READ_ERROR'],
                moderation_labels=[],
                checked_at=datetime.now(timezone.utc).isoformat(),
                error=str(e)
            )
    
    def _process_response(self, response: Dict) -> SafetyResult:
        """
        Process AWS Rekognition API response
        
        Args:
            response: API response from detect_moderation_labels()
        
        Returns:
            SafetyResult with parsed data
        """
        moderation_labels = response.get('ModerationLabels', [])
        checked_at = datetime.now(timezone.utc).isoformat()
        
        if not moderation_labels:
            # No moderation labels = safe image
            logger.info("✓ Image passed safety check (no moderation labels)")
            return SafetyResult(
                is_safe=True,
                confidence=100.0,
                flagged_categories=[],
                moderation_labels=[],
                checked_at=checked_at
            )
        
        # Extract flagged categories
        flagged_categories = []
        max_confidence = 0.0
        
        for label in moderation_labels:
            name = label.get('Name', '')
            confidence = label.get('Confidence', 0.0)
            parent_name = label.get('ParentName', '')
            
            # Track highest confidence violation
            if confidence > max_confidence:
                max_confidence = confidence
            
            # Check if critical category
            if name in self.CRITICAL_CATEGORIES or parent_name in self.CRITICAL_CATEGORIES:
                flagged_categories.append(name)
                logger.warning(f"⚠ CRITICAL: {name} detected ({confidence:.1f}% confidence)")
            
            # Check monitored subcategories (lower threshold)
            elif name in self.MONITORED_SUBCATEGORIES and confidence >= 60.0:
                flagged_categories.append(name)
                logger.warning(f"⚠ MONITORED: {name} detected ({confidence:.1f}% confidence)")
        
        # Determine if unsafe
        is_safe = len(flagged_categories) == 0
        
        if not is_safe:
            logger.warning(f"❌ Image FAILED safety check: {', '.join(flagged_categories)}")
        else:
            logger.info("✓ Image passed safety check (below thresholds)")
        
        return SafetyResult(
            is_safe=is_safe,
            confidence=max_confidence,
            flagged_categories=flagged_categories,
            moderation_labels=moderation_labels,
            checked_at=checked_at
        )


# Global instance (initialized once per worker)
_checker_instance: Optional[AWSRekognitionChecker] = None


def get_checker() -> AWSRekognitionChecker:
    """Get or create global AWS Rekognition checker instance"""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = AWSRekognitionChecker()
    return _checker_instance


def check_image_safety(file_path: str) -> Dict:
    """
    Convenience function to check image safety from file path
    
    Args:
        file_path: Absolute path to image file
    
    Returns:
        Dict with safety result (JSON-serializable)
    """
    checker = get_checker()
    result = checker.check_image_from_file(file_path)
    return asdict(result)


def check_image_safety_bytes(image_bytes: bytes) -> Dict:
    """
    Convenience function to check image safety from bytes
    
    Args:
        image_bytes: Raw image bytes
    
    Returns:
        Dict with safety result (JSON-serializable)
    """
    checker = get_checker()
    result = checker.check_image_from_bytes(image_bytes)
    return asdict(result)


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python safety_checker.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print(f"\n🔍 Checking image: {image_path}\n")
    result = check_image_safety(image_path)
    
    print(json.dumps(result, indent=2))
    
    if result['is_safe']:
        print(f"\n✅ Image is SAFE")
    else:
        print(f"\n❌ Image is UNSAFE")
        print(f"Flagged categories: {', '.join(result['flagged_categories'])}")
        print(f"Max confidence: {result['confidence']:.1f}%")
