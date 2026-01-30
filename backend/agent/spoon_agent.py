"""
Help2Earn SpoonOS Agent - ReAct Agent implementation using SpoonOS SCDF framework

This agent uses the SpoonOS ReAct pattern to process accessibility facility uploads
by orchestrating tools through an LLM-driven decision loop.

Uses Gemini as the LLM provider via ChatBot.
"""

import base64
import json
import logging
import os
from typing import Optional

from spoon_ai import ChatBot
from spoon_ai.agents import SpoonReactAI
from spoon_ai.tools import ToolManager

# Global context for current upload (to avoid passing large data through LLM)
_current_upload_context = {}

# Import tool classes
from tools.vision_tool import VisionAnalyzeTool, VisionValidateQualityTool
from tools.anti_fraud_tool import (
    AntiFraudCheckTool,
    AntiFraudRateCheckTool,
    AntiFraudLocationCheckTool,
)
from tools.database_tool import (
    DatabaseSaveFacilityTool,
    DatabaseUpdateFacilityTool,
    DatabaseSaveRewardTool,
    DatabaseQueryFacilitiesTool,
    DatabaseGetUserRewardsTool,
    DatabaseGetFacilityTool,
    DatabaseCheckExistingTool,
)
from tools.blockchain_tool import (
    BlockchainRewardTool,
    BlockchainBalanceTool,
    BlockchainCheckVerificationTool,
)

logger = logging.getLogger(__name__)

# System prompt for the ReAct agent
SYSTEM_PROMPT = """
You are the Help2Earn verification agent. Your job is to process accessibility facility uploads
and ensure they are valid, not fraudulent, and properly rewarded.

CRITICAL: You MUST complete ALL 5 steps below. Do NOT stop after vision analysis.

## Your Workflow (MUST complete all steps)

1. **Vision Analysis** - Use `vision_analyze` tool with image_base64="USE_CONTEXT"
   - If is_valid=false, stop and report rejection
   - If is_valid=true, CONTINUE to step 2

2. **Fraud Detection** - Use `anti_fraud_check` tool
   - Pass: latitude, longitude, facility_type (from step 1)
   - If is_fraud=true, stop and report rejection
   - If is_fraud=false, CONTINUE to step 3

3. **Database Storage** - Use `database_save_facility` tool
   - Pass: latitude, longitude, facility_type, condition, image_url, wallet_address
   - Save the returned facility_id for step 5
   - CONTINUE to step 4

4. **Reward Distribution** - Use `blockchain_reward` tool
   - Pass: wallet_address, amount (50 for new, 25 for update), facility_type, latitude, longitude
   - Save the tx_hash for step 5
   - CONTINUE to step 5

5. **Record Reward** - Use `database_save_reward` tool
   - Pass: wallet_address, amount, facility_id (from step 3), tx_hash (from step 4)
   - This completes the workflow

## Important

- You MUST call tools in sequence: vision_analyze → anti_fraud_check → database_save_facility → blockchain_reward → database_save_reward
- Do NOT stop until all 5 steps are complete or a rejection occurs
- Always use image_base64="USE_CONTEXT" for vision tools
"""


class Help2EarnSpoonAgent:
    """
    SpoonOS-based Help2Earn Agent using ReAct pattern.

    This agent uses the SpoonOS framework to orchestrate tools through
    an LLM-driven reasoning loop. Uses Gemini as the LLM provider.
    """

    def __init__(self):
        """Initialize the SpoonOS-based Help2Earn Agent."""
        # Verify API key is available
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for SpoonOS agent")

        # Initialize ChatBot with Gemini provider
        gemini_model = os.getenv("SPOON_GEMINI_MODEL", "gemini-2.0-flash")
        self.llm = ChatBot(
            llm_provider="gemini",
            model_name=gemini_model,
            api_key=gemini_api_key
        )

        # Create tool instances
        tool_instances = [
            # Vision tools
            VisionAnalyzeTool(),
            VisionValidateQualityTool(),
            # Anti-fraud tools
            AntiFraudCheckTool(),
            AntiFraudRateCheckTool(),
            AntiFraudLocationCheckTool(),
            # Database tools
            DatabaseSaveFacilityTool(),
            DatabaseUpdateFacilityTool(),
            DatabaseSaveRewardTool(),
            DatabaseQueryFacilitiesTool(),
            DatabaseGetUserRewardsTool(),
            DatabaseGetFacilityTool(),
            DatabaseCheckExistingTool(),
            # Blockchain tools
            BlockchainRewardTool(),
            BlockchainBalanceTool(),
            BlockchainCheckVerificationTool(),
        ]

        # Create ToolManager with tool instances
        self.tool_manager = ToolManager(tool_instances)

        # Create SpoonReactAI Agent
        self.agent = SpoonReactAI(
            llm=self.llm,
            available_tools=self.tool_manager,
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
        global _current_upload_context

        try:
            # Store image in context for tools to access directly
            # This avoids passing large base64 data through the LLM which causes truncation
            image_base64 = base64.b64encode(image).decode('utf-8')
            _current_upload_context = {
                "image_base64": image_base64,
                "image_bytes": image,
                "lat": lat,
                "lng": lng,
                "wallet": wallet,
                "image_url": image_url
            }

            # Create the prompt for the agent (without full image data)
            prompt = f"""
Process this accessibility facility upload. You MUST complete ALL steps.

**Input Data:**
- latitude: {lat}
- longitude: {lng}
- wallet_address: {wallet}
- image_url: {image_url or "pending"}

**Execute these steps in order:**

Step 1: Call vision_analyze with image_base64="USE_CONTEXT"
Step 2: If is_valid=true, call anti_fraud_check with latitude={lat}, longitude={lng}, facility_type=<from step 1>
Step 3: If is_fraud=false, call database_save_facility with all required params
Step 4: Call blockchain_reward with wallet_address={wallet}, amount=50, facility_type=<from step 1>, latitude={lat}, longitude={lng}
Step 5: Call database_save_reward with the facility_id and tx_hash from previous steps

START NOW with step 1.
"""

            # Run the agent
            result = await self.agent.run(prompt)

            # Clear context after processing
            _current_upload_context = {}

            # Parse agent result into standardized response format
            return self._parse_agent_result(result)

        except Exception as e:
            logger.error(f"SpoonOS agent error: {e}")
            _current_upload_context = {}  # Clear context on error
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
            # If result is a string, try to parse JSON from it
            if isinstance(result, str):
                # Try to extract structured data from the text response
                response = {
                    "success": True,
                    "agent_response": result
                }

                # Look for common patterns in the response
                result_lower = result.lower()
                if "error" in result_lower or "failed" in result_lower or "rejected" in result_lower:
                    response["success"] = False

                return response

            # If result is a dict, use it directly
            if isinstance(result, dict):
                return result

            # If result has a 'result' attribute
            if hasattr(result, 'result'):
                agent_output = result.result
                if isinstance(agent_output, dict):
                    return agent_output
                if isinstance(agent_output, str):
                    return {
                        "success": True,
                        "agent_response": agent_output
                    }

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
