"""
Help2Earn Agent - Core business logic driver

This agent handles the complete upload verification workflow:
- Image validation (Vision Skill)
- Anti-fraud detection (Anti-Fraud Skill)
- Database operations (Database Skill)
- Token distribution (Blockchain Skill)
"""

import json
import logging
from typing import Optional

from skills.vision.skill import analyze_image
from skills.anti_fraud.skill import check_fraud
from skills.database.skill import (
    save_facility,
    update_facility,
    save_reward,
    query_facilities_nearby,
    get_user_rewards as db_get_user_rewards,
    get_facility_by_id
)
from skills.blockchain.skill import send_reward

logger = logging.getLogger(__name__)


class Help2EarnAgent:
    """
    Core Agent that drives the complete business workflow.

    Directly orchestrates the skills to process uploads and queries.
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize the Help2Earn Agent."""
        self.config = config or {}
        logger.info("Help2EarnAgent initialized")

    async def process_upload(
        self,
        image: bytes,
        lat: float,
        lng: float,
        wallet: str,
        image_url: Optional[str] = None
    ) -> dict:
        """
        Process a facility upload through the complete verification workflow.

        Steps:
        1. Analyze image using Vision Skill
        2. Check for fraud/duplicates using Anti-Fraud Skill
        3. Store facility data using Database Skill
        4. Distribute token rewards using Blockchain Skill

        Args:
            image: Raw image bytes
            lat: Latitude coordinate
            lng: Longitude coordinate
            wallet: User's wallet address for rewards
            image_url: Optional URL where image is stored

        Returns:
            dict with success status, facility info, and reward details
        """
        try:
            # Step 1: Analyze image
            logger.info("Step 1: Analyzing image...")
            vision_result = await analyze_image(image)

            if not vision_result.get("is_valid"):
                return {
                    "success": False,
                    "reason": vision_result.get("condition", "Not a valid accessibility facility")
                }

            facility_type = vision_result.get("facility_type")
            condition = vision_result.get("condition")

            logger.info(f"Image analysis: type={facility_type}, condition={condition}")

            # Step 2: Check for fraud/duplicates
            logger.info("Step 2: Checking for duplicates...")
            fraud_result = await check_fraud(lat, lng, facility_type)

            if fraud_result.get("is_fraud"):
                return {
                    "success": False,
                    "reason": f"Duplicate submission: {fraud_result.get('reason')}"
                }

            reward_amount = fraud_result.get("reward_amount", 50)
            existing_facility_id = fraud_result.get("existing_facility_id")

            logger.info(f"Fraud check passed: reward={reward_amount}, existing={existing_facility_id}")

            # Step 3: Save to database
            logger.info("Step 3: Saving to database...")
            if existing_facility_id:
                # Update existing facility
                await update_facility(existing_facility_id, {
                    "image_url": image_url or "pending",
                    "ai_analysis": json.dumps(vision_result)
                })
                facility_id = existing_facility_id
            else:
                # Create new facility
                facility_id = await save_facility({
                    "type": facility_type,
                    "latitude": lat,
                    "longitude": lng,
                    "image_url": image_url or "pending",
                    "ai_analysis": json.dumps(vision_result),
                    "contributor_address": wallet
                })

            logger.info(f"Facility saved: {facility_id}")

            # Step 4: Send reward
            logger.info("Step 4: Sending reward...")
            try:
                tx_hash = await send_reward(wallet, reward_amount)
                logger.info(f"Reward sent: {reward_amount} tokens, tx={tx_hash}")
            except Exception as e:
                logger.error(f"Reward sending failed: {e}")
                tx_hash = None

            # Save reward record
            await save_reward({
                "wallet_address": wallet,
                "facility_id": facility_id,
                "amount": reward_amount,
                "tx_hash": tx_hash
            })

            return {
                "success": True,
                "facility_id": facility_id,
                "facility_type": facility_type,
                "condition": condition,
                "reward_amount": reward_amount,
                "tx_hash": tx_hash
            }

        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            return {
                "success": False,
                "reason": f"Processing error: {str(e)}"
            }

    async def query_facilities(
        self,
        lat: float,
        lng: float,
        radius: int = 200
    ) -> dict:
        """
        Query nearby accessibility facilities.

        Args:
            lat: Center latitude
            lng: Center longitude
            radius: Search radius in meters (default 200m)

        Returns:
            dict with list of facilities
        """
        try:
            facilities = await query_facilities_nearby(lat, lng, radius)
            return {
                "facilities": facilities,
                "count": len(facilities)
            }
        except Exception as e:
            logger.error(f"Error querying facilities: {e}")
            return {"facilities": [], "error": str(e)}

    async def get_user_rewards(self, wallet: str) -> dict:
        """
        Get reward history for a wallet address.

        Args:
            wallet: User's wallet address

        Returns:
            dict with reward history and totals
        """
        try:
            return await db_get_user_rewards(wallet)
        except Exception as e:
            logger.error(f"Error getting rewards: {e}")
            return {"rewards": [], "total_earned": 0, "error": str(e)}

    async def get_facility_details(self, facility_id: str) -> dict:
        """
        Get detailed information about a specific facility.

        Args:
            facility_id: UUID of the facility

        Returns:
            dict with facility details
        """
        try:
            facility = await get_facility_by_id(facility_id)
            if facility:
                return facility
            return {"error": "Facility not found"}
        except Exception as e:
            logger.error(f"Error getting facility details: {e}")
            return {"error": str(e)}
