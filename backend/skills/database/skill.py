"""
Database Skill - PostgreSQL + PostGIS operations for facility data

Handles all database operations including:
- Saving new facilities
- Querying facilities by location
- Updating facility records
- Managing reward records
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List

import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/help2earn"
)


class Facility(BaseModel):
    """Facility data model."""
    id: Optional[str] = None
    type: str  # ramp, toilet, elevator, wheelchair
    latitude: float
    longitude: float
    image_url: str
    ai_analysis: Optional[str] = None
    contributor_address: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Reward(BaseModel):
    """Reward record model."""
    id: Optional[str] = None
    wallet_address: str
    facility_id: str
    amount: int
    tx_hash: Optional[str] = None
    created_at: Optional[datetime] = None


class DatabasePool:
    """Singleton database connection pool."""
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if cls._pool is None:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            cls._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                ssl=ssl_context
            )
        return cls._pool

    @classmethod
    async def close(cls):
        """Close the connection pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None


async def save_facility(data: dict) -> str:
    """
    Save a new facility to the database.

    Args:
        data: dict containing:
            - type: Facility type (ramp/toilet/elevator/wheelchair)
            - latitude: Latitude coordinate
            - longitude: Longitude coordinate
            - image_url: URL of uploaded image
            - ai_analysis: JSON string of AI analysis results
            - contributor_address: Wallet address of contributor

    Returns:
        str: UUID of the created facility
    """
    try:
        pool = await DatabasePool.get_pool()
        facility_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO facilities (
                    id, type, location, image_url,
                    ai_analysis, contributor_address, created_at, updated_at
                ) VALUES (
                    $1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326),
                    $5, $6, $7, NOW(), NOW()
                )
            """,
                facility_id,
                data["type"],
                data["longitude"],
                data["latitude"],
                data["image_url"],
                data.get("ai_analysis", "{}"),
                data["contributor_address"]
            )

        logger.info(f"Saved facility: {facility_id}")
        return facility_id

    except Exception as e:
        logger.error(f"Error saving facility: {e}")
        raise


async def check_existing(lat: float, lng: float, facility_type: str) -> dict:
    """
    Check if a similar facility exists at the given location.

    Uses PostGIS to find facilities within 50m of the coordinates
    with the same type.

    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        facility_type: Type of facility to check

    Returns:
        dict with:
            - exists: Whether a similar facility exists
            - facility: Existing facility data if found
            - last_updated: When the facility was last updated
            - days_since_update: Days since last update
    """
    try:
        pool = await DatabasePool.get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, type,
                    ST_X(location::geometry) as longitude,
                    ST_Y(location::geometry) as latitude,
                    image_url, ai_analysis, contributor_address,
                    created_at, updated_at,
                    EXTRACT(DAY FROM NOW() - updated_at) as days_since_update
                FROM facilities
                WHERE type = $1
                AND ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography,
                    50  -- 50 meters radius
                )
                ORDER BY updated_at DESC
                LIMIT 1
            """, facility_type, lng, lat)

        if row:
            return {
                "exists": True,
                "facility": {
                    "id": row["id"],
                    "type": row["type"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "image_url": row["image_url"],
                    "contributor_address": row["contributor_address"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                },
                "last_updated": row["updated_at"].isoformat() if row["updated_at"] else None,
                "days_since_update": int(row["days_since_update"]) if row["days_since_update"] else 0
            }

        return {
            "exists": False,
            "facility": None,
            "last_updated": None,
            "days_since_update": None
        }

    except Exception as e:
        logger.error(f"Error checking existing facility: {e}")
        raise


async def query_facilities_nearby(
    lat: float,
    lng: float,
    radius: int = 200,
    facility_type: Optional[str] = None
) -> List[dict]:
    """
    Query facilities within a radius of the given coordinates.

    Args:
        lat: Center latitude
        lng: Center longitude
        radius: Search radius in meters (default 200m)
        facility_type: Optional filter by type

    Returns:
        List of facility dicts
    """
    try:
        pool = await DatabasePool.get_pool()

        async with pool.acquire() as conn:
            if facility_type:
                rows = await conn.fetch("""
                    SELECT
                        id, type,
                        ST_X(location::geometry) as longitude,
                        ST_Y(location::geometry) as latitude,
                        ST_Distance(
                            location,
                            ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography
                        ) as distance,
                        image_url, ai_analysis, contributor_address,
                        created_at, updated_at
                    FROM facilities
                    WHERE type = $4
                    AND ST_DWithin(
                        location,
                        ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                        $3
                    )
                    ORDER BY distance
                """, lat, lng, radius, facility_type)
            else:
                rows = await conn.fetch("""
                    SELECT
                        id, type,
                        ST_X(location::geometry) as longitude,
                        ST_Y(location::geometry) as latitude,
                        ST_Distance(
                            location,
                            ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography
                        ) as distance,
                        image_url, ai_analysis, contributor_address,
                        created_at, updated_at
                    FROM facilities
                    ST_DWithin(
                        location,
                        ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                        $3
                    )
                    ORDER BY distance
                """, lat, lng, radius)

        facilities = []
        for row in rows:
            facilities.append({
                "id": row["id"],
                "type": row["type"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "distance": round(row["distance"], 1),
                "image_url": row["image_url"],
                "ai_analysis": row["ai_analysis"],
                "contributor_address": row["contributor_address"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            })

        logger.info(f"Found {len(facilities)} facilities within {radius}m")
        return facilities

    except Exception as e:
        logger.error(f"Error querying facilities: {e}")
        raise


async def update_facility(facility_id: str, data: dict) -> bool:
    """
    Update an existing facility record.

    Args:
        facility_id: UUID of facility to update
        data: Fields to update

    Returns:
        bool: Success status
    """
    try:
        pool = await DatabasePool.get_pool()

        # Build dynamic update query
        updates = []
        values = [facility_id]
        param_idx = 2

        if "image_url" in data:
            updates.append(f"image_url = ${param_idx}")
            values.append(data["image_url"])
            param_idx += 1

        if "ai_analysis" in data:
            updates.append(f"ai_analysis = ${param_idx}")
            values.append(data["ai_analysis"])
            param_idx += 1

        updates.append("updated_at = NOW()")

        async with pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE facilities
                SET {', '.join(updates)}
                WHERE id = $1
            """, *values)

        logger.info(f"Updated facility: {facility_id}")
        return True

    except Exception as e:
        logger.error(f"Error updating facility: {e}")
        return False


async def save_reward(data: dict) -> str:
    """
    Save a reward record.

    Args:
        data: dict containing:
            - wallet_address: Recipient wallet
            - facility_id: Associated facility
            - amount: Token amount
            - tx_hash: Blockchain transaction hash

    Returns:
        str: UUID of the reward record
    """
    try:
        pool = await DatabasePool.get_pool()
        reward_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rewards (
                    id, wallet_address, facility_id, amount, tx_hash, created_at
                ) VALUES ($1, $2, $3, $4, $5, NOW())
            """,
                reward_id,
                data["wallet_address"],
                data["facility_id"],
                data["amount"],
                data.get("tx_hash")
            )

        logger.info(f"Saved reward: {reward_id}")
        return reward_id

    except Exception as e:
        logger.error(f"Error saving reward: {e}")
        raise


async def get_user_rewards(wallet_address: str) -> dict:
    """
    Get all rewards for a wallet address.

    Args:
        wallet_address: User's wallet address

    Returns:
        dict with rewards list and totals
    """
    try:
        pool = await DatabasePool.get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    r.id, r.facility_id, r.amount, r.tx_hash, r.created_at,
                    f.type as facility_type
                FROM rewards r
                LEFT JOIN facilities f ON r.facility_id = f.id
                WHERE r.wallet_address = $1
                ORDER BY r.created_at DESC
            """, wallet_address)

            total = await conn.fetchval("""
                SELECT COALESCE(SUM(amount), 0)
                FROM rewards
                WHERE wallet_address = $1
            """, wallet_address)

        rewards = []
        for row in rows:
            rewards.append({
                "id": row["id"],
                "facility_id": row["facility_id"],
                "facility_type": row["facility_type"],
                "amount": row["amount"],
                "tx_hash": row["tx_hash"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })

        return {
            "rewards": rewards,
            "total_earned": int(total),
            "contribution_count": len(rewards)
        }

    except Exception as e:
        logger.error(f"Error getting user rewards: {e}")
        raise


async def get_facility_by_id(facility_id: str) -> Optional[dict]:
    """
    Get a facility by its ID.

    Args:
        facility_id: UUID of the facility

    Returns:
        dict with facility data or None if not found
    """
    try:
        pool = await DatabasePool.get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, type,
                    ST_X(location::geometry) as longitude,
                    ST_Y(location::geometry) as latitude,
                    image_url, ai_analysis, contributor_address,
                    created_at, updated_at
                FROM facilities
                WHERE id = $1
            """, facility_id)

        if row:
            return {
                "id": row["id"],
                "type": row["type"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "image_url": row["image_url"],
                "ai_analysis": row["ai_analysis"],
                "contributor_address": row["contributor_address"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }

        return None

    except Exception as e:
        logger.error(f"Error getting facility: {e}")
        raise


# Skill registration for SpoonOS
def skill(name: str):
    """Decorator for registering skills with SpoonOS."""
    def decorator(func):
        func._skill_name = name
        return func
    return decorator


# Register skills
save_facility = skill("save_facility")(save_facility)
check_existing = skill("check_existing")(check_existing)
query_facilities_nearby = skill("query_facilities_nearby")(query_facilities_nearby)
update_facility = skill("update_facility")(update_facility)
save_reward = skill("save_reward")(save_reward)
get_user_rewards = skill("get_user_rewards")(get_user_rewards)
get_facility_by_id = skill("get_facility_by_id")(get_facility_by_id)
