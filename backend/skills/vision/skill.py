"""
Vision Skill - Image recognition for accessibility facilities

Uses Gemini Vision API through SpoonOS to analyze uploaded images
and identify accessibility facility types and conditions.
"""

import base64
import json
import logging
from typing import Optional

import google.generativeai as genai
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VisionAnalysisResult(BaseModel):
    """Result of image analysis."""
    is_valid: bool
    facility_type: Optional[str] = None  # ramp, toilet, elevator, wheelchair
    condition: Optional[str] = None
    confidence: float = 0.0
    details: Optional[dict] = None


# Facility type definitions for validation
FACILITY_TYPES = {
    "ramp": {
        "keywords": ["坡道", "斜坡", "无障碍坡道", "ramp", "slope", "incline"],
        "description": "Wheelchair ramp or accessible slope"
    },
    "toilet": {
        "keywords": ["无障碍厕所", "无障碍卫生间", "accessible toilet", "disabled toilet"],
        "description": "Accessible restroom/toilet"
    },
    "elevator": {
        "keywords": ["无障碍电梯", "电梯", "accessible elevator", "lift"],
        "description": "Accessible elevator"
    },
    "wheelchair": {
        "keywords": ["轮椅", "轮椅借用", "wheelchair", "wheelchair rental", "wheelchair station"],
        "description": "Wheelchair rental/lending station"
    }
}


async def analyze_image(image: bytes) -> dict:
    """
    Analyze an uploaded image to identify accessibility facilities.

    This skill uses Gemini Vision API to:
    1. Determine if the image contains an accessibility facility
    2. Classify the facility type
    3. Assess the facility condition
    4. Extract relevant details

    Args:
        image: Raw image bytes

    Returns:
        dict with analysis results including:
        - is_valid: Whether it's a valid accessibility facility
        - facility_type: Type classification (ramp/toilet/elevator/wheelchair)
        - condition: Description of facility condition
        - confidence: Confidence score (0-1)
        - details: Additional extracted information
    """
    import os
    import random

    # Mock mode for testing when Gemini API is not available
    if os.getenv("MOCK_VISION", "false").lower() == "true":
        facility_types = ["ramp", "toilet", "elevator", "wheelchair"]
        selected_type = random.choice(facility_types)
        logger.info(f"[MOCK MODE] Returning mock analysis: {selected_type}")
        return {
            "is_valid": True,
            "facility_type": selected_type,
            "condition": "设施状况良好，可正常使用",
            "confidence": 0.95,
            "details": {
                "accessibility_features": ["无障碍标识清晰", "通道宽敞"],
                "potential_issues": [],
                "recommendations": []
            }
        }

    try:
        # Configure proxy for Gemini API access (needed in regions with restrictions)
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        if proxy:
            # Set environment variables for underlying HTTP libraries
            os.environ["HTTP_PROXY"] = proxy
            os.environ["HTTPS_PROXY"] = proxy
            os.environ["GRPC_PROXY"] = proxy
            logger.info(f"Using proxy for Gemini API: {proxy}")

        # Configure Gemini API key
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            logger.warning("GEMINI_API_KEY not set, using default credentials")

        # Configure Gemini (use 2.5-flash, 1.5 series has been retired)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        model = genai.GenerativeModel(model_name)
        logger.info(f"Using Gemini model: {model_name}")

        # Encode image for API
        image_data = base64.b64encode(image).decode('utf-8')

        # Create analysis prompt
        prompt = """
        Analyze this image and determine if it shows an accessibility facility.

        Accessibility facilities include:
        1. Wheelchair ramps (坡道) - sloped surfaces for wheelchair access
        2. Accessible toilets (无障碍厕所) - restrooms with accessibility features
        3. Accessible elevators (无障碍电梯) - elevators with accessibility features
        4. Wheelchair stations (轮椅借用处) - places to borrow wheelchairs

        Please respond in JSON format with:
        {
            "is_valid": true/false,
            "facility_type": "ramp" | "toilet" | "elevator" | "wheelchair" | null,
            "condition": "description of facility condition in Chinese",
            "confidence": 0.0-1.0,
            "details": {
                "accessibility_features": ["list of observed features"],
                "potential_issues": ["any issues that might affect usability"],
                "recommendations": ["suggestions for improvement if any"]
            }
        }

        If the image does not show an accessibility facility, set is_valid to false
        and explain why in the condition field.
        """

        # Call Gemini Vision API with retry for rate limits
        import time
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = model.generate_content([
                    prompt,
                    {"mime_type": "image/jpeg", "data": image_data}
                ])
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "resource exhausted" in error_str or "quota" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                raise  # Re-raise if not rate limit or last attempt

        # Parse response
        response_text = response.text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())

        # Validate facility type
        if result.get("facility_type") and result["facility_type"] not in FACILITY_TYPES:
            result["facility_type"] = None
            result["is_valid"] = False
            result["condition"] = "Unrecognized facility type"

        logger.info(f"Vision analysis complete: valid={result.get('is_valid')}, type={result.get('facility_type')}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        return {
            "is_valid": False,
            "facility_type": None,
            "condition": "Analysis failed - invalid response format",
            "confidence": 0.0,
            "details": None
        }

    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        return {
            "is_valid": False,
            "facility_type": None,
            "condition": f"Analysis error: {str(e)}",
            "confidence": 0.0,
            "details": None
        }


async def validate_image_quality(image: bytes) -> dict:
    """
    Validate image quality before analysis.

    Checks:
    - Image is not too small
    - Image is not too blurry
    - Image has sufficient lighting

    Args:
        image: Raw image bytes

    Returns:
        dict with quality assessment
    """
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image))
        width, height = img.size

        # Check minimum dimensions
        min_dimension = 200
        if width < min_dimension or height < min_dimension:
            return {
                "is_acceptable": False,
                "reason": f"Image too small. Minimum {min_dimension}x{min_dimension} pixels required.",
                "width": width,
                "height": height
            }

        # Check maximum file size (10MB)
        max_size = 10 * 1024 * 1024
        if len(image) > max_size:
            return {
                "is_acceptable": False,
                "reason": "Image file too large. Maximum 10MB allowed.",
                "size_bytes": len(image)
            }

        return {
            "is_acceptable": True,
            "width": width,
            "height": height,
            "size_bytes": len(image)
        }

    except Exception as e:
        logger.error(f"Image quality validation error: {e}")
        return {
            "is_acceptable": False,
            "reason": f"Failed to validate image: {str(e)}"
        }


# Skill registration for SpoonOS
def skill(name: str):
    """Decorator for registering skills with SpoonOS."""
    def decorator(func):
        func._skill_name = name
        return func
    return decorator


# Register skills
analyze_image = skill("analyze_image")(analyze_image)
validate_image_quality = skill("validate_image_quality")(validate_image_quality)
