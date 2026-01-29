"""
Vision Tool - Image analysis for accessibility facilities

SpoonOS tool wrapper for the vision skill.
"""

import base64
import logging
from typing import Optional

from spoon_ai.tools import tool

logger = logging.getLogger(__name__)


@tool(name="vision_analyze", description="Analyze image for accessibility facilities")
async def analyze_image(image_base64: str) -> dict:
    """
    Analyze an uploaded image to identify accessibility facilities.

    This tool uses Gemini Vision API to:
    1. Determine if the image contains an accessibility facility
    2. Classify the facility type (ramp, toilet, elevator, wheelchair)
    3. Assess the facility condition
    4. Extract relevant details

    Args:
        image_base64: Base64 encoded image data

    Returns:
        dict with analysis results including:
        - is_valid: Whether it's a valid accessibility facility
        - facility_type: Type classification (ramp/toilet/elevator/wheelchair)
        - condition: Description of facility condition
        - confidence: Confidence score (0-1)
        - details: Additional extracted information
    """
    from skills.vision.skill import analyze_image as _analyze_image

    try:
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)

        # Call the existing skill implementation
        result = await _analyze_image(image_bytes)

        logger.info(f"Vision analysis complete: valid={result.get('is_valid')}, type={result.get('facility_type')}")
        return result

    except Exception as e:
        logger.error(f"Vision tool error: {e}")
        return {
            "is_valid": False,
            "facility_type": None,
            "condition": f"Analysis error: {str(e)}",
            "confidence": 0.0,
            "details": None
        }


@tool(name="vision_validate_quality", description="Validate image quality before analysis")
async def validate_image_quality(image_base64: str) -> dict:
    """
    Validate image quality before analysis.

    Checks:
    - Image is not too small (min 200x200)
    - Image is not too large (max 10MB)

    Args:
        image_base64: Base64 encoded image data

    Returns:
        dict with quality assessment
    """
    from skills.vision.skill import validate_image_quality as _validate

    try:
        image_bytes = base64.b64decode(image_base64)
        return await _validate(image_bytes)
    except Exception as e:
        logger.error(f"Image quality validation error: {e}")
        return {
            "is_acceptable": False,
            "reason": f"Failed to validate image: {str(e)}"
        }
