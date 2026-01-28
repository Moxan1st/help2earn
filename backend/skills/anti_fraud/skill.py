"""
Anti-Fraud Skill - Duplicate and fraud detection

Handles all anti-fraud operations including:
- Checking for duplicate submissions
- Detecting suspicious patterns
- Determining appropriate reward amounts
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from skills.database.skill import DatabasePool, MOCK_DATABASE, MOCK_DATA

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/help2earn"
)

# Anti-fraud configuration
DUPLICATE_RADIUS_METERS = 50  # Same facility if within 50m
DUPLICATE_WINDOW_DAYS = 15    # Consider duplicate if within 15 days
NEW_FACILITY_REWARD = 50      # Tokens for new facility
UPDATE_FACILITY_REWARD = 25   # Tokens for updating existing facility


class FraudCheckResult:
    """Result of fraud check."""
    def __init__(
        self,
        is_fraud: bool,
        reward_amount: int,
        reason: str,
        existing_facility_id: Optional[str] = None
    ):
        self.is_fraud = is_fraud
        self.reward_amount = reward_amount
        self.reason = reason
        self.existing_facility_id = existing_facility_id

    def to_dict(self) -> dict:
        return {
            "is_fraud": self.is_fraud,
            "reward_amount": self.reward_amount,
            "reason": self.reason,
            "existing_facility_id": self.existing_facility_id
        }


async def check_fraud(lat: float, lng: float, facility_type: str) -> dict:
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
        lat: Latitude coordinate
        lng: Longitude coordinate
        facility_type: Type of facility (ramp/toilet/elevator/wheelchair)

    Returns:
        dict with:
        - is_fraud: Whether this is a fraudulent submission
        - reward_amount: Tokens to award (0 if fraud)
        - reason: Explanation of the determination
        - existing_facility_id: ID of existing facility if found
    """
    try:
        if MOCK_DATABASE:
            # Mock logic for fraud check
            for f in MOCK_DATA["facilities"]:
                if f["type"] == facility_type:
                    # Simple distance check
                    dist = ((f["latitude"] - lat)**2 + (f["longitude"] - lng)**2)**0.5 * 111000
                    if dist <= DUPLICATE_RADIUS_METERS:
                        days_since = (datetime.now() - f["updated_at"]).days
                        if days_since < DUPLICATE_WINDOW_DAYS:
                            return FraudCheckResult(
                                is_fraud=True,
                                reward_amount=0,
                                reason=f"duplicate_within_{DUPLICATE_WINDOW_DAYS}_days",
                                existing_facility_id=f["id"]
                            ).to_dict()
                        else:
                            return FraudCheckResult(
                                is_fraud=False,
                                reward_amount=UPDATE_FACILITY_REWARD,
                                reason="facility_update",
                                existing_facility_id=f["id"]
                            ).to_dict()
            
            # No duplicate found
            return FraudCheckResult(
                is_fraud=False,
                reward_amount=NEW_FACILITY_REWARD,
                reason="new_facility"
            ).to_dict()

        pool = await DatabasePool.get_pool()

        async with pool.acquire() as conn:
            # Check for existing facilities within radius
            row = await conn.fetchrow("""
                SELECT
                    id, type,
                    ST_X(location::geometry) as longitude,
                    ST_Y(location::geometry) as latitude,
                    updated_at,
                    EXTRACT(DAY FROM NOW() - updated_at) as days_since_update,
                    ST_Distance(
                    location,
                    ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography
                    ) as distance
                FROM facilities
                WHERE type = $3
                AND ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                    $4
                )
                ORDER BY distance ASC
                LIMIT 1
            """, lat, lng, facility_type, DUPLICATE_RADIUS_METERS)

        if row is None:
            # No existing facility - this is a new submission
            result = FraudCheckResult(
                is_fraud=False,
                reward_amount=NEW_FACILITY_REWARD,
                reason="new_facility"
            )
            logger.info(f"New facility submission at ({lat}, {lng})")
            return result.to_dict()

        days_since_update = int(row["days_since_update"]) if row["days_since_update"] else 0

        if days_since_update < DUPLICATE_WINDOW_DAYS:
            # Recent submission exists - this is a duplicate
            result = FraudCheckResult(
                is_fraud=True,
                reward_amount=0,
                reason=f"duplicate_within_{DUPLICATE_WINDOW_DAYS}_days",
                existing_facility_id=row["id"]
            )
            logger.warning(
                f"Duplicate submission detected at ({lat}, {lng}), "
                f"existing: {row['id']}, days since update: {days_since_update}"
            )
            return result.to_dict()

        # Older submission exists - this is an update
        result = FraudCheckResult(
            is_fraud=False,
            reward_amount=UPDATE_FACILITY_REWARD,
            reason="facility_update",
            existing_facility_id=row["id"]
        )
        logger.info(
            f"Facility update at ({lat}, {lng}), "
            f"existing: {row['id']}, days since update: {days_since_update}"
        )
        return result.to_dict()

    except Exception as e:
        logger.error(f"Error checking fraud: {e}")
        # On error, default to new facility to not block legitimate submissions
        return FraudCheckResult(
            is_fraud=False,
            reward_amount=NEW_FACILITY_REWARD,
            reason="check_failed_default_new"
        ).to_dict()


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
            pool = await DatabasePool.get_pool()

            async with pool.acquire() as conn:
                # Check hourly rate
                hourly_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM facilities
                    WHERE contributor_address = $1
                    AND created_at > NOW() - INTERVAL '1 hour'
                """, wallet_address)

                # Check daily rate
                daily_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM facilities
                    WHERE contributor_address = $1
                    AND created_at > NOW() - INTERVAL '1 day'
                """, wallet_address)

        max_hourly = 10
        max_daily = 50

        if hourly_count >= max_hourly:
            return {
                "allowed": False,
                "reason": f"Hourly limit reached ({max_hourly}/hour)",
                "hourly_count": hourly_count,
                "daily_count": daily_count,
                "wait_minutes": 60
            }

        if daily_count >= max_daily:
            return {
                "allowed": False,
                "reason": f"Daily limit reached ({max_daily}/day)",
                "hourly_count": hourly_count,
                "daily_count": daily_count,
                "wait_minutes": 1440
            }

        return {
            "allowed": True,
            "reason": "within_limits",
            "hourly_count": hourly_count,
            "daily_count": daily_count,
            "remaining_hourly": max_hourly - hourly_count,
            "remaining_daily": max_daily - daily_count
        }

    except Exception as e:
        logger.error(f"Error checking submission rate: {e}")
        return {
            "allowed": True,
            "reason": "check_failed_default_allow"
        }


async def check_location_validity(lat: float, lng: float) -> dict:
    """
    Check if a location is valid for submission.

    Checks:
    - Coordinates are within valid ranges
    - Location is on land (not in ocean)
    - Location is not in restricted areas

    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate

    Returns:
        dict with validity check results
    """
    # Basic coordinate validation
    if not (-90 <= lat <= 90):
        return {
            "valid": False,
            "reason": "Invalid latitude (must be -90 to 90)"
        }

    if not (-180 <= lng <= 180):
        return {
            "valid": False,
            "reason": "Invalid longitude (must be -180 to 180)"
        }

    # Check for obviously invalid coordinates (0,0 is in the ocean)
    if lat == 0 and lng == 0:
        return {
            "valid": False,
            "reason": "Invalid coordinates (0,0)"
        }

    # Could add more sophisticated checks here:
    # - Reverse geocoding to verify on land
    # - Check against known restricted areas
    # - Verify GPS accuracy

    return {
        "valid": True,
        "reason": "coordinates_valid"
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

        pool = await DatabasePool.get_pool()

        async with pool.acquire() as conn:
            if wallet_address:
                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_submissions,
                        COUNT(CASE WHEN created_at = updated_at THEN 1 END) as new_facilities,
                        COUNT(CASE WHEN created_at != updated_at THEN 1 END) as updates
                    FROM facilities
                    WHERE contributor_address = $1
                """, wallet_address)
            else:
                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_submissions,
                        COUNT(DISTINCT contributor_address) as unique_contributors,
                        COUNT(CASE WHEN created_at = updated_at THEN 1 END) as new_facilities,
                        COUNT(CASE WHEN created_at != updated_at THEN 1 END) as updates
                    FROM facilities
                """)

        return {
            "total_submissions": stats["total_submissions"],
            "new_facilities": stats["new_facilities"],
            "updates": stats["updates"],
            "unique_contributors": stats.get("unique_contributors")
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
