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

from dotenv import load_dotenv
load_dotenv()

import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/help2earn"
)
MOCK_DATABASE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# In-memory storage for mock mode
MOCK_DATA = {
    "facilities": [],
    "rewards": []
}


class MockRecord(dict):
    """Mock database record that behaves like asyncpg Record."""
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"No such attribute: {name}")


class MockConnection:
    """Mock database connection."""
    async def execute(self, query, *args):
        # specific handling for INSERT/UPDATE
        if "INSERT INTO facilities" in query:
            # Extract values from args based on query structure
            # args: id, type, longitude, latitude, image_url, ai_analysis, contributor_address
            facility = {
                "id": args[0],
                "type": args[1],
                "longitude": args[2],
                "latitude": args[3],
                "image_url": args[4],
                "ai_analysis": args[5],
                "contributor_address": args[6],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            MOCK_DATA["facilities"].append(facility)
        
        elif "INSERT INTO rewards" in query:
            # args: id, wallet_address, facility_id, amount, tx_hash
            reward = {
                "id": args[0],
                "wallet_address": args[1],
                "facility_id": args[2],
                "amount": args[3],
                "tx_hash": args[4],
                "created_at": datetime.now()
            }
            MOCK_DATA["rewards"].append(reward)
            
        elif "UPDATE facilities" in query:
            # args: values..., facility_id
            facility_id = args[-1]
            for f in MOCK_DATA["facilities"]:
                if f["id"] == facility_id:
                    # simplistic update - we don't parse the query fully, 
                    # but we know what update_facility passes
                    # This is a bit fragile but works for the specific usage in update_facility
                    if len(args) > 1 and "image_url" in query:
                        # Assuming the first arg is image_url or ai_analysis depending on query
                        # This mock is very specific to the current usage
                        pass 
                    f["updated_at"] = datetime.now()
                    break

    async def fetch(self, query, *args):
        # Mock query logic
        results = []
        if "FROM facilities" in query:
            # Simple radius check mock
            lat = args[0]
            lng = args[1]
            radius = args[2]
            
            for f in MOCK_DATA["facilities"]:
                # Simple distance calc (Euclidean approximation for mock)
                # In real app PostGIS does this
                dist = ((f["latitude"] - lat)**2 + (f["longitude"] - lng)**2)**0.5 * 111000
                if dist <= radius:
                    f_copy = f.copy()
                    f_copy["distance"] = dist
                    results.append(MockRecord(f_copy))
                    
        elif "FROM rewards" in query:
            wallet = args[0]
            for r in MOCK_DATA["rewards"]:
                if r["wallet_address"] == wallet:
                    # Join facility info
                    r_copy = r.copy()
                    fac = next((f for f in MOCK_DATA["facilities"] if f["id"] == r["facility_id"]), None)
                    if fac:
                        r_copy["facility_type"] = fac["type"]
                    results.append(MockRecord(r_copy))
                    
        return results

    async def fetchrow(self, query, *args):
        if "FROM facilities" in query and "LIMIT 1" in query:
            # check_existing mock
            # args: facility_type, lng, lat
            if len(args) >= 3:
                f_type = args[0]
                lng = args[1]
                lat = args[2]
                for f in MOCK_DATA["facilities"]:
                    if f["type"] == f_type:
                        dist = ((f["latitude"] - lat)**2 + (f["longitude"] - lng)**2)**0.5 * 111000
                        if dist < 50: # 50m check
                            res = f.copy()
                            res["days_since_update"] = (datetime.now() - f["updated_at"]).days
                            return MockRecord(res)
                            
        if "FROM facilities" in query and "WHERE id =" in query:
            # get_facility_by_id
            f_id = args[0]
            for f in MOCK_DATA["facilities"]:
                if f["id"] == f_id:
                    return MockRecord(f)

        if "SELECT COALESCE(SUM(amount), 0)" in query:
            wallet = args[0]
            total = sum(r["amount"] for r in MOCK_DATA["rewards"] if r["wallet_address"] == wallet)
            return total
            
        return None

    async def fetchval(self, query, *args):
        row = await self.fetchrow(query, *args)
        if row is not None and not isinstance(row, MockRecord):
            return row
        return None


class MockPool:
    """Mock database pool."""
    def acquire(self):
        return self

    async def __aenter__(self):
        return MockConnection()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def close(self):
        pass


class DatabasePool:
    """Singleton database connection pool."""
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls):
        """Get or create the connection pool."""
        if MOCK_DATABASE:
            return MockPool()
            
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
                    WHERE ST_DWithin(
                        location,
                        ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                        $3
                    )
                    ORDER BY distance
                """, lat, lng, radius)

        facilities = []
        for row in rows:
            facilities.append({
                "id": str(row["id"]),
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
                "id": str(row["id"]),
                "facility_id": str(row["facility_id"]) if row["facility_id"] else None,
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
