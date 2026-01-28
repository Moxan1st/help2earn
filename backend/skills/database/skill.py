"""
Database Skill - Supabase operations for facility data

Handles all database operations including:
- Saving new facilities
- Querying facilities by location
- Updating facility records
- Managing reward records
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from supabase import create_client, Client
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Database connection settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MOCK_DATABASE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# In-memory storage for mock mode
MOCK_DATA = {
    "facilities": [],
    "rewards": []
}

class SupabaseManager:
    _client: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
            cls._client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return cls._client

async def save_facility(
    facility_type: str,
    lat: float,
    lng: float,
    image_url: str,
    ai_analysis: str,
    contributor_address: str
) -> Optional[str]:
    """
    Save a new facility record.
    
    Args:
        facility_type: Type of facility
        lat: Latitude
        lng: Longitude
        image_url: URL of the facility image
        ai_analysis: JSON string of AI analysis
        contributor_address: Wallet address of contributor
        
    Returns:
        Facility ID if successful, None otherwise
    """
    try:
        if MOCK_DATABASE:
            import uuid
            f_id = str(uuid.uuid4())
            MOCK_DATA["facilities"].append({
                "id": f_id,
                "type": facility_type,
                "latitude": lat,
                "longitude": lng,
                "image_url": image_url,
                "ai_analysis": ai_analysis,
                "contributor_address": contributor_address,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            return f_id

        client = SupabaseManager.get_client()
        
        # Use RPC to handle PostGIS insertion
        response = client.rpc(
            "insert_facility",
            {
                "p_type": facility_type,
                "p_lat": lat,
                "p_lng": lng,
                "p_image_url": image_url,
                "p_ai_analysis": ai_analysis,
                "p_contributor_address": contributor_address
            }
        ).execute()
        
        # response.data is the UUID
        return response.data

    except Exception as e:
        logger.error(f"Error saving facility: {e}")
        return None


async def get_facilities_nearby(
    lat: float, 
    lng: float, 
    radius_meters: float = 200
) -> List[Dict[str, Any]]:
    """
    Get facilities within a radius.
    
    Args:
        lat: Center latitude
        lng: Center longitude
        radius_meters: Radius in meters
        
    Returns:
        List of facility records
    """
    try:
        if MOCK_DATABASE:
            results = []
            for f in MOCK_DATA["facilities"]:
                dist = ((f["latitude"] - lat)**2 + (f["longitude"] - lng)**2)**0.5 * 111000
                if dist <= radius_meters:
                    f_copy = f.copy()
                    f_copy["distance"] = dist
                    results.append(f_copy)
            return results

        client = SupabaseManager.get_client()
        
        response = client.rpc(
            "get_facilities_nearby",
            {
                "p_lat": lat,
                "p_lng": lng,
                "p_radius_meters": radius_meters
            }
        ).execute()
        
        return response.data or []

    except Exception as e:
        logger.error(f"Error getting facilities: {e}")
        return []


async def check_existing_facility(
    facility_type: str,
    lat: float,
    lng: float,
    radius_meters: float = 50
) -> Optional[Dict[str, Any]]:
    """
    Check if a facility of same type exists nearby.
    
    Args:
        facility_type: Type to check
        lat: Latitude
        lng: Longitude
        radius_meters: Check radius
        
    Returns:
        Facility record if exists, None otherwise
    """
    try:
        if MOCK_DATABASE:
            for f in MOCK_DATA["facilities"]:
                if f["type"] == facility_type:
                    dist = ((f["latitude"] - lat)**2 + (f["longitude"] - lng)**2)**0.5 * 111000
                    if dist <= radius_meters:
                        res = f.copy()
                        res["days_since_update"] = (datetime.now() - f["updated_at"]).days
                        res["distance"] = dist
                        return res
            return None

        client = SupabaseManager.get_client()
        
        response = client.rpc(
            "check_existing_facility",
            {
                "p_type": facility_type,
                "p_lat": lat,
                "p_lng": lng,
                "p_radius_meters": radius_meters
            }
        ).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Error checking existing facility: {e}")
        return None


async def update_facility(
    facility_id: str,
    updates: Dict[str, Any]
) -> bool:
    """
    Update a facility record.
    
    Args:
        facility_id: UUID of facility
        updates: Dictionary of fields to update
        
    Returns:
        True if successful
    """
    try:
        if MOCK_DATABASE:
            for f in MOCK_DATA["facilities"]:
                if f["id"] == facility_id:
                    f.update(updates)
                    f["updated_at"] = datetime.now()
                    return True
            return False

        client = SupabaseManager.get_client()
        
        # Standard update
        # If updating location, we might need special handling, but usually updates are for other fields
        # If 'ai_analysis' or 'image_url' is updated
        
        # Filter out keys that might not exist or are read-only
        valid_updates = {k: v for k, v in updates.items() if k in ['image_url', 'ai_analysis', 'contributor_address', 'type']}
        valid_updates['updated_at'] = datetime.now().isoformat()
        
        response = client.table("facilities").update(valid_updates).eq("id", facility_id).execute()
        
        return len(response.data) > 0

    except Exception as e:
        logger.error(f"Error updating facility: {e}")
        return False


async def save_reward(
    wallet_address: str,
    facility_id: str,
    amount: int,
    tx_hash: str,
    reward_type: str = "new_facility"
) -> bool:
    """
    Save a reward record.
    
    Args:
        wallet_address: User wallet
        facility_id: Related facility ID
        amount: Token amount
        tx_hash: Blockchain transaction hash
        reward_type: Type of reward
        
    Returns:
        True if successful
    """
    try:
        if MOCK_DATABASE:
            MOCK_DATA["rewards"].append({
                "wallet_address": wallet_address,
                "facility_id": facility_id,
                "amount": amount,
                "tx_hash": tx_hash,
                "reward_type": reward_type,
                "created_at": datetime.now()
            })
            return True

        client = SupabaseManager.get_client()
        
        response = client.table("rewards").insert({
            "wallet_address": wallet_address,
            "facility_id": facility_id,
            "amount": amount,
            "tx_hash": tx_hash,
            "reward_type": reward_type
        }).execute()
        
        return len(response.data) > 0

    except Exception as e:
        logger.error(f"Error saving reward: {e}")
        return False


async def get_user_rewards(wallet_address: str) -> List[Dict[str, Any]]:
    """Get rewards for a user."""
    try:
        if MOCK_DATABASE:
            return [r for r in MOCK_DATA["rewards"] if r["wallet_address"] == wallet_address]

        client = SupabaseManager.get_client()
        
        response = client.rpc(
            "get_user_rewards",
            {"p_wallet_address": wallet_address}
        ).execute()
        
        return response.data or []

    except Exception as e:
        logger.error(f"Error getting rewards: {e}")
        return []


async def get_total_rewards(wallet_address: str) -> int:
    """Get total tokens earned by user."""
    try:
        if MOCK_DATABASE:
            return sum(r["amount"] for r in MOCK_DATA["rewards"] if r["wallet_address"] == wallet_address)

        client = SupabaseManager.get_client()
        
        response = client.rpc(
            "get_total_rewards",
            {"p_wallet_address": wallet_address}
        ).execute()
        
        return response.data or 0

    except Exception as e:
        logger.error(f"Error getting total rewards: {e}")
        return 0


async def get_facility_by_id(facility_id: str) -> Optional[Dict[str, Any]]:
    """Get facility by ID."""
    try:
        if MOCK_DATABASE:
            for f in MOCK_DATA["facilities"]:
                if f["id"] == facility_id:
                    return f
            return None

        client = SupabaseManager.get_client()
        
        response = client.table("facilities").select("*").eq("id", facility_id).single().execute()
        
        return response.data

    except Exception as e:
        logger.error(f"Error getting facility: {e}")
        return None


# Skill registration for SpoonOS
def skill(name: str):
    """Decorator for registering skills with SpoonOS."""
    def decorator(func):
        func._skill_name = name
        return func
    return decorator

# Register skills
save_facility = skill("save_facility")(save_facility)
get_facilities_nearby = skill("get_facilities_nearby")(get_facilities_nearby)
check_existing_facility = skill("check_existing_facility")(check_existing_facility)
update_facility = skill("update_facility")(update_facility)
save_reward = skill("save_reward")(save_reward)
get_user_rewards = skill("get_user_rewards")(get_user_rewards)
get_total_rewards = skill("get_total_rewards")(get_total_rewards)
get_facility_by_id = skill("get_facility_by_id")(get_facility_by_id)
