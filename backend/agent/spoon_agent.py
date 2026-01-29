"""
Help2Earn SpoonOS Agent - ReAct Agent implementation using SpoonOS SCDF framework

This agent uses the SpoonOS ReAct pattern to process accessibility facility uploads
by orchestrating tools through an LLM-driven decision loop.

Uses Gemini as the LLM provider.
"""

import base64
import json
import logging
import os
from typing import Optional

from spoon_ai.llm import LLMManager, ConfigurationManager
from spoon_ai.agents import SpoonReactAgent
from spoon_ai.llm.gemini import GeminiProvider

# Import tools
from tools.vision_tool import analyze_image, validate_image_quality
from tools.anti_fraud_tool import check_fraud, check_user_submission_rate, check_location_validity
from tools.database_tool import (
    save_facility,
    update_facility,
    save_reward,
    query_facilities,
    get_user_rewards,
    get_facility_by_id,
    check_existing
)
from tools.blockchain_tool import distribute_reward, get_balance, check_verification

logger = logging.getLogger(__name__)

# System prompt for the ReAct agent
SYSTEM_PROMPT = """
You are the Help2Earn verification agent. Your job is to process accessibility facility uploads
and ensure they are valid, not fraudulent, and properly rewarded.

## Your Workflow

When processing an upload, follow these steps in order:

1. **Vision Analysis** - Use the `vision_analyze` tool to analyze the image
   - Check if the image shows a valid accessibility facility
   - Identify the facility type (ramp, toilet, elevator, wheelchair)
   - Assess the facility condition

2. **Fraud Detection** - Use the `anti_fraud_check` tool to check for duplicates
   - Check if this is a duplicate submission (same location within 15 days)
   - Determine the appropriate reward amount:
     - New facility: 50 tokens
     - Facility update (>15 days old): 25 tokens
     - Duplicate: 0 tokens (reject)

3. **Database Storage** - Use the appropriate database tool
   - For new facilities: Use `database_save_facility`
   - For updates: Use `database_update_facility`

4. **Reward Distribution** - Use the `blockchain_reward` tool
   - Send tokens to the user's wallet
   - Record the transaction

5. **Record Reward** - Use `database_save_reward` to save the reward record

## Important Rules

- Always analyze the image FIRST before any other checks
- If the image is not a valid accessibility facility, reject immediately
- If fraud check shows is_fraud=true, reject the submission
- Always save the facility before sending rewards
- Always record the reward in the database after sending

## Response Format

After completing all steps, summarize the result with:
- Whether the submission was successful
- The facility ID (if saved)
- The facility type
- The reward amount
- The transaction hash (if reward was sent)
- Any errors encountered
"""


class Help2EarnSpoonAgent:
    """
    SpoonOS-based Help2Earn Agent using ReAct pattern.

    This agent uses the SpoonOS framework to orchestrate tools through
    an LLM-driven reasoning loop. Uses Gemini as the LLM provider.
    """

    def __init__(self):
        """Initialize the SpoonOS-based Help2Earn Agent."""
        # Configure Gemini as LLM provider
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for SpoonOS agent")

        # Initialize Gemini provider
        gemini_model = os.getenv("SPOON_GEMINI_MODEL", "gemini-2.0-flash")
        self.llm_provider = GeminiProvider(
            api_key=gemini_api_key,
            model=gemini_model
        )

        # Register all tools
        self.tools = [
            # Vision tools
            analyze_image,
            validate_image_quality,
            # Anti-fraud tools
            check_fraud,
            check_user_submission_rate,
            check_location_validity,
            # Database tools
            save_facility,
            update_facility,
            save_reward,
            query_facilities,
            get_user_rewards,
            get_facility_by_id,
            check_existing,
            # Blockchain tools
            distribute_reward,
            get_balance,
            check_verification,
        ]

        # Create ReAct Agent with Gemini
        self.agent = SpoonReactAgent(
            llm=self.llm_provider,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT
        )

        logger.info(f"Help2EarnSpoonAgent initialized with Gemini model: {gemini_model}")

    async def process_upload(
        self,
        image: bytes,
        lat: float,
        lng: float,
        wallet: str,
        image_url: Optional[str] = None
    ) -> dict:
        """
        Process a facility upload through the SpoonOS ReAct agent.

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
            # Encode image to base64 for tool passing
            image_base64 = base64.b64encode(image).decode('utf-8')

            # Create the prompt for the agent
            prompt = f"""
Process this accessibility facility upload:

**Input Data:**
- Image: [base64 encoded, {len(image)} bytes]
- Location: latitude={lat}, longitude={lng}
- Wallet Address: {wallet}
- Image URL: {image_url or "pending"}

**Instructions:**
1. First, analyze the image using vision_analyze with the base64 image data
2. If valid, check for fraud using anti_fraud_check
3. If not fraud, save to database
4. Send blockchain reward
5. Save reward record

Execute the complete verification workflow and report the results.
"""

            # Run the agent with context containing the actual data
            context = {
                "image_base64": image_base64,
                "latitude": lat,
                "longitude": lng,
                "wallet": wallet,
                "image_url": image_url or "pending"
            }

            result = await self.agent.run(prompt, context=context)

            # Parse agent result into standardized response format
            return self._parse_agent_result(result)

        except Exception as e:
            logger.error(f"SpoonOS agent error: {e}")
            return {
                "success": False,
                "reason": f"Agent processing error: {str(e)}"
            }

    def _parse_agent_result(self, result) -> dict:
        """
        Parse the SpoonOS agent result into standardized response format.

        The agent returns a result object that needs to be converted
        to our expected response format.
        """
        try:
            # If result is a dict, use it directly
            if isinstance(result, dict):
                return result

            # If result has a 'result' attribute
            if hasattr(result, 'result'):
                agent_output = result.result
                if isinstance(agent_output, dict):
                    return agent_output

            # If result has specific attributes we need
            response = {
                "success": getattr(result, 'success', False),
                "facility_id": getattr(result, 'facility_id', None),
                "facility_type": getattr(result, 'facility_type', None),
                "condition": getattr(result, 'condition', None),
                "reward_amount": getattr(result, 'reward_amount', 0),
                "tx_hash": getattr(result, 'tx_hash', None),
            }

            # Add error info if present
            if hasattr(result, 'error'):
                response['blockchain_error'] = result.error
            if hasattr(result, 'reason'):
                response['reason'] = result.reason

            return response

        except Exception as e:
            logger.error(f"Error parsing agent result: {e}")
            return {
                "success": False,
                "reason": f"Error parsing result: {str(e)}"
            }

    async def query_facilities(
        self,
        lat: float,
        lng: float,
        radius: int = 200
    ) -> dict:
        """
        Query nearby accessibility facilities.

        This is a direct tool call without going through the ReAct loop
        since it's a simple query operation.

        Args:
            lat: Center latitude
            lng: Center longitude
            radius: Search radius in meters (default 200m)

        Returns:
            dict with list of facilities
        """
        try:
            from skills.database.skill import query_facilities_nearby
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

        This is a direct tool call without going through the ReAct loop.

        Args:
            wallet: User's wallet address

        Returns:
            dict with reward history and totals
        """
        try:
            from skills.database.skill import get_user_rewards as db_get_user_rewards
            return await db_get_user_rewards(wallet)
        except Exception as e:
            logger.error(f"Error getting rewards: {e}")
            return {"rewards": [], "total_earned": 0, "error": str(e)}

    async def get_facility_details(self, facility_id: str) -> dict:
        """
        Get detailed information about a specific facility.

        This is a direct tool call without going through the ReAct loop.

        Args:
            facility_id: UUID of the facility

        Returns:
            dict with facility details
        """
        try:
            from skills.database.skill import get_facility_by_id as db_get_facility_by_id
            facility = await db_get_facility_by_id(facility_id)
            if facility:
                return facility
            return {"error": "Facility not found"}
        except Exception as e:
            logger.error(f"Error getting facility details: {e}")
            return {"error": str(e)}
