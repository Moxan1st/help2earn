"""Anti-Fraud Skill - Duplicate and fraud detection."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import os

from skills.database.skill import check_existing_facility, SupabaseManager, MOCK_DATABASE, MOCK_DATA

logger = logging.getLogger(__name__)

async def check_fraud(lat: float, lng: float, type: str) -> dict:
    """
    Check if a submission is potentially fraudulent or a duplicate.
    
    Args:
        lat: Latitude
        lng: Longitude
        type: Facility type
        
    Returns:
        dict with fraud check results
    """
    try:
        # Check for existing facility nearby (50m radius)
        existing = await check_existing_facility(type, lat, lng, 50)
        
        if existing:
            # Found existing facility
            days_since_update = existing.get("days_since_update", 0)
            
            if days_since_update < 15:
                # Less than 15 days: Reject as duplicate/spam
                return {
                    "is_fraud": True,
                    "reason": "Facility verified recently (less than 15 days)",
                    "existing_facility_id": existing["id"]
                }
            else:
                # More than 15 days: Allow as update, but reduced reward
                return {
                    "is_fraud": False,
                    "reason": "update_existing",
                    "reward_amount": 25,
                    "existing_facility_id": existing["id"]
                }
        
        # No existing facility: New submission
        return {
            "is_fraud": False,
            "reason": "new_facility",
            "reward_amount": 50,
            "existing_facility_id": None
        }
        
    except Exception as e:
        logger.error(f"Error in check_fraud: {e}")
        # Fail safe: allow it but log error
        return {
            "is_fraud": False,
            "reason": "error_bypass",
            "reward_amount": 50,
            "existing_facility_id": None
        }

async def check_user_submission_rate(wallet_address: str) -> dict:
    """
    Check if a user is submitting too frequently (potential bot).

    Rate limits:
    - Max 10 submissions per hour
    - Max 50 submissions per day

    Args:
        wallet_address: User's wallet address

    Returns:
        dict with rate check results
    """
    try:
        if MOCK_DATABASE:
            hourly_count = 0
            daily_count = 0
            now = datetime.now()
            for f in MOCK_DATA["facilities"]:
                if f["contributor_address"] == wallet_address:
                    if (now - f["created_at"]).total_seconds() < 3600:
                        hourly_count += 1
                    if (now - f["created_at"]).total_seconds() < 86400:
                        daily_count += 1
        else:
            client = SupabaseManager.get_client()
            
            response = client.rpc(
                "check_user_submission_rate",
                {"p_wallet_address": wallet_address}
            ).execute()
            
            data = response.data[0] if response.data else {"hourly_count": 0, "daily_count": 0}
            hourly_count = data["hourly_count"]
            daily_count = data["daily_count"]

        is_rate_limited = False
        reason = None

        if hourly_count >= 10:
            is_rate_limited = True
            reason = "hourly_limit_exceeded"
        elif daily_count >= 50:
            is_rate_limited = True
            reason = "daily_limit_exceeded"

        return {
            "is_rate_limited": is_rate_limited,
            "hourly_count": hourly_count,
            "daily_count": daily_count,
            "reason": reason
        }

    except Exception as e:
        logger.error(f"Error checking submission rate: {e}")
        return {"error": str(e), "is_rate_limited": False}


async def check_location_validity(lat: float, lng: float) -> dict:
    """
    Check if location is valid (e.g. in Shanghai).
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        dict with validity check
    """
    # Simple bounding box for Shanghai (approximate)
    # 30.40 - 31.53 N, 120.52 - 122.12 E
    is_valid = (30.40 <= lat <= 31.53) and (120.52 <= lng <= 122.12)
    
    return {
        "is_valid": is_valid,
        "reason": "outside_service_area" if not is_valid else None
    }


async def get_fraud_statistics(wallet_address: Optional[str] = None) -> dict:
    """
    Get fraud detection statistics.

    Args:
        wallet_address: Optional filter by wallet

    Returns:
        dict with fraud statistics
    """
    try:
        if MOCK_DATABASE:
            total = len(MOCK_DATA["facilities"])
            unique = len(set(f["contributor_address"] for f in MOCK_DATA["facilities"]))
            new_fac = 0
            updates = 0
            for f in MOCK_DATA["facilities"]:
                if wallet_address and f["contributor_address"] != wallet_address:
                    continue
                if f["created_at"] == f["updated_at"]:
                    new_fac += 1
                else:
                    updates += 1
            
            return {
                "total_submissions": new_fac + updates,
                "new_facilities": new_fac,
                "updates": updates,
                "unique_contributors": unique
            }

        client = SupabaseManager.get_client()
        
        response = client.rpc(
            "get_fraud_stats",
            {"p_wallet_address": wallet_address}
        ).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
            
        return {
            "total_submissions": 0,
            "new_facilities": 0,
            "updates": 0,
            "unique_contributors": 0
        }

    except Exception as e:
        logger.error(f"Error getting fraud statistics: {e}")
        return {"error": str(e)}


# Skill registration for SpoonOS
def skill(name: str):
    """Decorator for registering skills with SpoonOS."""
    def decorator(func):
        func._skill_name = name
        return func
    return decorator


# Register skills
check_fraud = skill("check_fraud")(check_fraud)
check_user_submission_rate = skill("check_user_submission_rate")(check_user_submission_rate)
check_location_validity = skill("check_location_validity")(check_location_validity)
get_fraud_statistics = skill("get_fraud_statistics")(get_fraud_statistics)
