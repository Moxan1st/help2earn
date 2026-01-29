"""
Anti-Fraud Tool - Duplicate and fraud detection

SpoonOS tool using BaseTool class for the anti-fraud skill.
"""

import logging
from typing import Any, Optional

from spoon_ai.tools import BaseTool

logger = logging.getLogger(__name__)


class AntiFraudCheckTool(BaseTool):
    """Check if a submission is potentially fraudulent."""

    name: str = "anti_fraud_check"
    description: str = """Check if a submission is potentially fraudulent.
Rules:
1. Same type facility within 50m updated within 15 days: duplicate (fraud), no reward
2. Same type facility within 50m older than 15 days: update, reward 25 tokens
3. No similar facility: new, reward 50 tokens"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude coordinate"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude coordinate"
            },
            "facility_type": {
                "type": "string",
                "description": "Type of facility (ramp/toilet/elevator/wheelchair)"
            }
        },
        "required": ["latitude", "longitude", "facility_type"]
    }

    async def execute(
        self,
        latitude: float,
        longitude: float,
        facility_type: str,
        **kwargs: Any
    ) -> dict:
        """
        Check if a submission is potentially fraudulent.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            facility_type: Type of facility (ramp/toilet/elevator/wheelchair)

        Returns:
            dict with:
            - is_fraud: Whether this is a fraudulent submission
            - reward_amount: Tokens to award (0 if fraud)
            - reason: Explanation of the determination
            - existing_facility_id: ID of existing facility if found
        """
        from skills.anti_fraud.skill import check_fraud as _check_fraud

        try:
            result = await _check_fraud(latitude, longitude, facility_type)
            logger.info(f"Fraud check: is_fraud={result.get('is_fraud')}, reason={result.get('reason')}")
            return result

        except Exception as e:
            logger.error(f"Fraud check error: {e}")
            # Default to new facility on error to not block legitimate submissions
            return {
                "is_fraud": False,
                "reward_amount": 50,
                "reason": "check_failed_default_new",
                "error": str(e)
            }


class AntiFraudRateCheckTool(BaseTool):
    """Check if a user is submitting too frequently."""

    name: str = "anti_fraud_rate_check"
    description: str = """Check if a user is submitting too frequently (potential bot).
Rate limits: Max 10 submissions per hour, max 50 submissions per day."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "User's wallet address"
            }
        },
        "required": ["wallet_address"]
    }

    async def execute(self, wallet_address: str, **kwargs: Any) -> dict:
        """
        Check if a user is submitting too frequently (potential bot).

        Args:
            wallet_address: User's wallet address

        Returns:
            dict with:
            - allowed: Whether the submission is allowed
            - reason: Explanation
            - hourly_count: Submissions in the last hour
            - daily_count: Submissions in the last day
            - remaining_hourly: Remaining submissions this hour
            - remaining_daily: Remaining submissions today
            - wait_minutes: Minutes to wait if rate limited
        """
        from skills.anti_fraud.skill import check_user_submission_rate as _check_rate

        try:
            result = await _check_rate(wallet_address)
            return result

        except Exception as e:
            logger.error(f"Rate check error: {e}")
            # Default to allow on error
            return {
                "allowed": True,
                "reason": "check_failed_default_allow",
                "error": str(e)
            }


class AntiFraudLocationCheckTool(BaseTool):
    """Validate location coordinates."""

    name: str = "anti_fraud_location_check"
    description: str = """Check if a location is valid for submission.
Validates coordinates are within valid ranges and not at (0, 0) which is in the ocean."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude coordinate (-90 to 90)"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude coordinate (-180 to 180)"
            }
        },
        "required": ["latitude", "longitude"]
    }

    async def execute(
        self,
        latitude: float,
        longitude: float,
        **kwargs: Any
    ) -> dict:
        """
        Check if a location is valid for submission.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)

        Returns:
            dict with:
            - valid: Whether the location is valid
            - reason: Explanation
        """
        from skills.anti_fraud.skill import check_location_validity as _check_location

        try:
            result = await _check_location(latitude, longitude)
            return result

        except Exception as e:
            logger.error(f"Location check error: {e}")
            return {
                "valid": False,
                "reason": f"Check failed: {str(e)}"
            }


class AntiFraudStatisticsTool(BaseTool):
    """Get fraud detection statistics."""

    name: str = "anti_fraud_statistics"
    description: str = """Get fraud detection statistics.
Returns total submissions, new facilities count, updates count, and unique contributors."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "Optional filter by wallet address"
            }
        },
        "required": []
    }

    async def execute(
        self,
        wallet_address: Optional[str] = None,
        **kwargs: Any
    ) -> dict:
        """
        Get fraud detection statistics.

        Args:
            wallet_address: Optional filter by wallet

        Returns:
            dict with:
            - total_submissions: Total number of submissions
            - new_facilities: Number of new facilities
            - updates: Number of facility updates
            - unique_contributors: Number of unique contributors (if not filtered by wallet)
        """
        from skills.anti_fraud.skill import get_fraud_statistics as _get_stats

        try:
            result = await _get_stats(wallet_address)
            return result

        except Exception as e:
            logger.error(f"Error getting fraud statistics: {e}")
            return {
                "error": str(e)
            }
