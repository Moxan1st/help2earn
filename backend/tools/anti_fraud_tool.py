"""
Anti-Fraud Tool - Duplicate and fraud detection

SpoonOS tool wrapper for the anti-fraud skill.
"""

import logging
from typing import Optional

from spoon_ai.tools import tool

logger = logging.getLogger(__name__)


@tool(name="anti_fraud_check", description="Check if a submission is potentially fraudulent")
async def check_fraud(
    latitude: float,
    longitude: float,
    facility_type: str
) -> dict:
    """
    Check if a submission is potentially fraudulent.

    Rules:
    1. If same type facility exists within 50m and was updated within 15 days:
       - Mark as duplicate (fraud)
       - No reward

    2. If same type facility exists within 50m but older than 15 days:
       - Mark as update
       - Reward 25 tokens

    3. If no similar facility exists:
       - Mark as new
       - Reward 50 tokens

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


@tool(name="anti_fraud_rate_check", description="Check if a user is submitting too frequently")
async def check_user_submission_rate(wallet_address: str) -> dict:
    """
    Check if a user is submitting too frequently (potential bot).

    Rate limits:
    - Max 10 submissions per hour
    - Max 50 submissions per day

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


@tool(name="anti_fraud_location_check", description="Validate location coordinates")
async def check_location_validity(latitude: float, longitude: float) -> dict:
    """
    Check if a location is valid for submission.

    Checks:
    - Coordinates are within valid ranges
    - Location is not (0, 0) which is in the ocean

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


@tool(name="anti_fraud_statistics", description="Get fraud detection statistics")
async def get_fraud_statistics(wallet_address: Optional[str] = None) -> dict:
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
