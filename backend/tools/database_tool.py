"""
Database Tool - PostgreSQL + PostGIS operations

SpoonOS tool using BaseTool class for the database skill.
"""

import logging
from typing import Any, Optional

from spoon_ai.tools import BaseTool

logger = logging.getLogger(__name__)


class DatabaseSaveFacilityTool(BaseTool):
    """Save a new accessibility facility to the database."""

    name: str = "database_save_facility"
    description: str = """Save a new facility to the database.
Records facility type, coordinates, image URL, contributor address, and AI analysis."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "facility_type": {
                "type": "string",
                "description": "Type of facility (ramp/toilet/elevator/wheelchair)"
            },
            "latitude": {
                "type": "number",
                "description": "Latitude coordinate"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude coordinate"
            },
            "image_url": {
                "type": "string",
                "description": "URL of the uploaded image"
            },
            "contributor_address": {
                "type": "string",
                "description": "Wallet address of the contributor"
            },
            "ai_analysis": {
                "type": "string",
                "description": "JSON string of AI analysis results (optional)"
            }
        },
        "required": ["facility_type", "latitude", "longitude", "image_url", "contributor_address"]
    }

    async def execute(
        self,
        facility_type: str,
        latitude: float,
        longitude: float,
        image_url: str,
        contributor_address: str,
        ai_analysis: Optional[str] = None,
        **kwargs: Any
    ) -> dict:
        """
        Save a new facility to the database.

        Args:
            facility_type: Type of facility (ramp/toilet/elevator/wheelchair)
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            image_url: URL of the uploaded image
            contributor_address: Wallet address of the contributor
            ai_analysis: JSON string of AI analysis results (optional)

        Returns:
            dict with:
            - success: Whether the save was successful
            - facility_id: UUID of the created facility
        """
        from skills.database.skill import save_facility as _save_facility

        try:
            data = {
                "type": facility_type,
                "latitude": latitude,
                "longitude": longitude,
                "image_url": image_url,
                "contributor_address": contributor_address,
                "ai_analysis": ai_analysis or "{}"
            }

            facility_id = await _save_facility(data)
            logger.info(f"Saved facility: {facility_id}")

            return {
                "success": True,
                "facility_id": facility_id
            }

        except Exception as e:
            logger.error(f"Error saving facility: {e}")
            return {
                "success": False,
                "facility_id": None,
                "error": str(e)
            }


class DatabaseUpdateFacilityTool(BaseTool):
    """Update an existing facility record."""

    name: str = "database_update_facility"
    description: str = """Update an existing facility record.
Can update image URL and/or AI analysis."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "facility_id": {
                "type": "string",
                "description": "UUID of the facility to update"
            },
            "image_url": {
                "type": "string",
                "description": "New image URL (optional)"
            },
            "ai_analysis": {
                "type": "string",
                "description": "New AI analysis JSON (optional)"
            }
        },
        "required": ["facility_id"]
    }

    async def execute(
        self,
        facility_id: str,
        image_url: Optional[str] = None,
        ai_analysis: Optional[str] = None,
        **kwargs: Any
    ) -> dict:
        """
        Update an existing facility record.

        Args:
            facility_id: UUID of the facility to update
            image_url: New image URL (optional)
            ai_analysis: New AI analysis JSON (optional)

        Returns:
            dict with:
            - success: Whether the update was successful
            - facility_id: UUID of the updated facility
        """
        from skills.database.skill import update_facility as _update_facility

        try:
            data = {}
            if image_url:
                data["image_url"] = image_url
            if ai_analysis:
                data["ai_analysis"] = ai_analysis

            success = await _update_facility(facility_id, data)

            return {
                "success": success,
                "facility_id": facility_id
            }

        except Exception as e:
            logger.error(f"Error updating facility: {e}")
            return {
                "success": False,
                "facility_id": facility_id,
                "error": str(e)
            }


class DatabaseQueryFacilitiesTool(BaseTool):
    """Query facilities near a location."""

    name: str = "database_query_facilities"
    description: str = """Query facilities within a radius of the given coordinates.
Uses PostGIS for geospatial queries."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Center latitude"
            },
            "longitude": {
                "type": "number",
                "description": "Center longitude"
            },
            "radius": {
                "type": "integer",
                "description": "Search radius in meters (default 200)"
            },
            "facility_type": {
                "type": "string",
                "description": "Optional filter by type (ramp/toilet/elevator/wheelchair)"
            }
        },
        "required": ["latitude", "longitude"]
    }

    async def execute(
        self,
        latitude: float,
        longitude: float,
        radius: int = 200,
        facility_type: Optional[str] = None,
        **kwargs: Any
    ) -> dict:
        """
        Query facilities within a radius of the given coordinates.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Search radius in meters (default 200)
            facility_type: Optional filter by type (ramp/toilet/elevator/wheelchair)

        Returns:
            dict with:
            - facilities: List of nearby facilities
            - count: Number of facilities found
        """
        from skills.database.skill import query_facilities_nearby

        try:
            facilities = await query_facilities_nearby(
                lat=latitude,
                lng=longitude,
                radius=radius,
                facility_type=facility_type
            )

            return {
                "facilities": facilities,
                "count": len(facilities)
            }

        except Exception as e:
            logger.error(f"Error querying facilities: {e}")
            return {
                "facilities": [],
                "count": 0,
                "error": str(e)
            }


class DatabaseSaveRewardTool(BaseTool):
    """Save a reward record to the database."""

    name: str = "database_save_reward"
    description: str = """Save a reward record to the database.
Records wallet address, facility ID, token amount, and transaction hash."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "Recipient wallet address"
            },
            "facility_id": {
                "type": "string",
                "description": "Associated facility UUID"
            },
            "amount": {
                "type": "integer",
                "description": "Token amount"
            },
            "tx_hash": {
                "type": "string",
                "description": "Blockchain transaction hash (optional)"
            }
        },
        "required": ["wallet_address", "facility_id", "amount"]
    }

    async def execute(
        self,
        wallet_address: str,
        facility_id: str,
        amount: int,
        tx_hash: Optional[str] = None,
        **kwargs: Any
    ) -> dict:
        """
        Save a reward record to the database.

        Args:
            wallet_address: Recipient wallet address
            facility_id: Associated facility UUID
            amount: Token amount
            tx_hash: Blockchain transaction hash (optional)

        Returns:
            dict with:
            - success: Whether the save was successful
            - reward_id: UUID of the reward record
        """
        from skills.database.skill import save_reward as _save_reward

        try:
            data = {
                "wallet_address": wallet_address,
                "facility_id": facility_id,
                "amount": amount,
                "tx_hash": tx_hash
            }

            reward_id = await _save_reward(data)
            logger.info(f"Saved reward: {reward_id}")

            return {
                "success": True,
                "reward_id": reward_id
            }

        except Exception as e:
            logger.error(f"Error saving reward: {e}")
            return {
                "success": False,
                "reward_id": None,
                "error": str(e)
            }


class DatabaseGetUserRewardsTool(BaseTool):
    """Get all rewards for a wallet address."""

    name: str = "database_get_user_rewards"
    description: str = """Get all rewards for a wallet address.
Returns reward history, total earned, and contribution count."""
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
        Get all rewards for a wallet address.

        Args:
            wallet_address: User's wallet address

        Returns:
            dict with:
            - rewards: List of reward records
            - total_earned: Total tokens earned
            - contribution_count: Number of contributions
        """
        from skills.database.skill import get_user_rewards as _get_user_rewards

        try:
            result = await _get_user_rewards(wallet_address)
            return result

        except Exception as e:
            logger.error(f"Error getting user rewards: {e}")
            return {
                "rewards": [],
                "total_earned": 0,
                "contribution_count": 0,
                "error": str(e)
            }


class DatabaseGetFacilityTool(BaseTool):
    """Get a facility by its ID."""

    name: str = "database_get_facility"
    description: str = """Get a facility by its UUID.
Returns facility details or None if not found."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "facility_id": {
                "type": "string",
                "description": "UUID of the facility"
            }
        },
        "required": ["facility_id"]
    }

    async def execute(self, facility_id: str, **kwargs: Any) -> dict:
        """
        Get a facility by its ID.

        Args:
            facility_id: UUID of the facility

        Returns:
            dict with facility data or None if not found
        """
        from skills.database.skill import get_facility_by_id as _get_facility_by_id

        try:
            facility = await _get_facility_by_id(facility_id)

            if facility:
                return {
                    "found": True,
                    "facility": facility
                }
            else:
                return {
                    "found": False,
                    "facility": None
                }

        except Exception as e:
            logger.error(f"Error getting facility: {e}")
            return {
                "found": False,
                "facility": None,
                "error": str(e)
            }


class DatabaseCheckExistingTool(BaseTool):
    """Check if a similar facility exists at a location."""

    name: str = "database_check_existing"
    description: str = """Check if a similar facility exists at the given location.
Uses PostGIS to find facilities within 50m with the same type."""
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
                "description": "Type of facility to check"
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
        Check if a similar facility exists at the given location.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            facility_type: Type of facility to check

        Returns:
            dict with:
            - exists: Whether a similar facility exists
            - facility: Existing facility data if found
            - last_updated: When the facility was last updated
            - days_since_update: Days since last update
        """
        from skills.database.skill import check_existing as _check_existing

        try:
            result = await _check_existing(latitude, longitude, facility_type)
            return result

        except Exception as e:
            logger.error(f"Error checking existing facility: {e}")
            return {
                "exists": False,
                "facility": None,
                "error": str(e)
            }
