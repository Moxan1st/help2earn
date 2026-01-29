"""
Vision Tool - Image analysis for accessibility facilities

SpoonOS tool using BaseTool class for the vision skill.
"""

import base64
import logging
from typing import Any

from spoon_ai.tools import BaseTool

logger = logging.getLogger(__name__)


class VisionAnalyzeTool(BaseTool):
    """Analyze image for accessibility facilities."""

    name: str = "vision_analyze"
    description: str = """Analyze an uploaded image to identify accessibility facilities.
Uses Gemini Vision API to determine if the image contains an accessibility facility,
classify the facility type (ramp, toilet, elevator, wheelchair), assess condition,
and extract relevant details."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "image_base64": {
                "type": "string",
                "description": "Base64 encoded image data"
            }
        },
        "required": ["image_base64"]
    }

    async def execute(self, image_base64: str, **kwargs: Any) -> dict:
        """
        Analyze an uploaded image to identify accessibility facilities.

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


class VisionValidateQualityTool(BaseTool):
    """Validate image quality before analysis."""

    name: str = "vision_validate_quality"
    description: str = """Validate image quality before analysis.
Checks if image is not too small (min 200x200) and not too large (max 10MB)."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "image_base64": {
                "type": "string",
                "description": "Base64 encoded image data"
            }
        },
        "required": ["image_base64"]
    }

    async def execute(self, image_base64: str, **kwargs: Any) -> dict:
        """
        Validate image quality before analysis.

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
