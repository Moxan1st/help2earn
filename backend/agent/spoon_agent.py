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


class Help2EarnReactAgent(SpoonReactAI):
    """Custom ReAct Agent that handles Gemini's lack of tool_choice support."""

    # Track completed tools and their results
    _completed_tools: list = []
    _tool_results: dict = {}

    def _get_next_tool_call(self) -> Optional[dict]:
        """Determine the next tool to call based on workflow state."""
        completed_names = [t['name'] for t in self._completed_tools]
        ctx = _current_upload_context

        logger.info(f"[WORKFLOW] Completed tools: {completed_names}")
        logger.info(f"[WORKFLOW] Context keys: {list(ctx.keys())}")

        # Workflow sequence
        if 'vision_analyze' not in completed_names:
            return {
                'name': 'vision_analyze',
                'arguments': {'image_base64': 'USE_CONTEXT'}
            }

        # Get vision result
        vision_result = self._tool_results.get('vision_analyze', {})
        if not vision_result.get('is_valid', False):
            logger.info("[WORKFLOW] Vision invalid, stopping")
            return None

        if 'anti_fraud_check' not in completed_names:
            return {
                'name': 'anti_fraud_check',
                'arguments': {
                    'latitude': ctx.get('lat'),
                    'longitude': ctx.get('lng'),
                    'facility_type': vision_result.get('facility_type', 'unknown')
                }
            }

        # Get fraud check result
        fraud_result = self._tool_results.get('anti_fraud_check', {})
        if fraud_result.get('is_fraud', False):
            logger.info("[WORKFLOW] Fraud detected, stopping")
            return None

        if 'database_save_facility' not in completed_names:
            return {
                'name': 'database_save_facility',
                'arguments': {
                    'latitude': ctx.get('lat'),
                    'longitude': ctx.get('lng'),
                    'facility_type': vision_result.get('facility_type'),
                    'condition': vision_result.get('condition', ''),
                    'image_url': ctx.get('image_url', ''),
                    'wallet_address': ctx.get('wallet')
                }
            }

        # Get database result
        db_result = self._tool_results.get('database_save_facility', {})
        facility_id = db_result.get('facility_id')

        if 'blockchain_reward' not in completed_names:
            reward_amount = fraud_result.get('reward_amount', 50)
            return {
                'name': 'blockchain_reward',
                'arguments': {
                    'wallet_address': ctx.get('wallet'),
                    'amount': reward_amount,
                    'facility_type': vision_result.get('facility_type'),
                    'latitude': ctx.get('lat'),
                    'longitude': ctx.get('lng')
                }
            }

        # Get blockchain result
        blockchain_result = self._tool_results.get('blockchain_reward', {})
        tx_hash = blockchain_result.get('tx_hash')

        if 'database_save_reward' not in completed_names:
            return {
                'name': 'database_save_reward',
                'arguments': {
                    'wallet_address': ctx.get('wallet'),
                    'amount': fraud_result.get('reward_amount', 50),
                    'facility_id': facility_id,
                    'tx_hash': tx_hash
                }
            }

        logger.info("[WORKFLOW] All tools completed!")
        return None

    async def step(self) -> str:
        """Override step to manually control workflow when Gemini returns empty."""
        from spoon_ai.schema import AgentState, ToolCall

        # First, try normal LLM-driven step
        should_act = await self.think()

        # If LLM returned tools, execute them normally
        if self.tool_calls:
            return await self.act()

        # LLM returned empty - manually determine next tool
        next_tool = self._get_next_tool_call()
        if next_tool is None:
            self.state = AgentState.FINISHED
            return "Workflow complete or stopped due to validation failure."

        # Create manual tool call
        logger.info(f"[WORKFLOW] Manually injecting tool call: {next_tool['name']}")

        # Create a ToolCall object
        class ManualToolCall:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments
                self.id = f"manual_{name}"

        self.tool_calls = [ManualToolCall(next_tool['name'], next_tool['arguments'])]

        # Execute the tool
        return await self.act()

    async def execute_tool(self, tool_call) -> str:
        """Override to track tool results."""
        result = await super().execute_tool(tool_call)

        # Track completed tool
        tool_name = getattr(tool_call, 'name', None)
        if tool_name:
            self._completed_tools.append({'name': tool_name})

            # Parse and store result
            try:
                import json
                # Result might be a string representation of dict
                if isinstance(result, str) and result.startswith('{'):
                    self._tool_results[tool_name] = json.loads(result)
                elif isinstance(result, str) and 'Observed output' in result:
                    # Extract dict from SpoonOS format
                    import re
                    match = re.search(r'\{.*\}', result, re.DOTALL)
                    if match:
                        self._tool_results[tool_name] = eval(match.group())
            except Exception as e:
                logger.warning(f"Could not parse tool result: {e}")

            logger.info(f"[WORKFLOW] Tool {tool_name} completed, result stored")

        return result

    def clear(self):
        """Clear state including completed tools."""
        super().clear()
        self._completed_tools = []
        self._tool_results = {}

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
You are the Help2Earn verification agent. You MUST call tools to process facility uploads.

CRITICAL RULES:
1. You MUST call a tool in EVERY response until workflow is complete
2. NEVER respond with text only - always call a tool
3. Follow this EXACT sequence of tool calls:

WORKFLOW SEQUENCE:
Step 1: vision_analyze (image_base64="USE_CONTEXT")
  → If is_valid=false: STOP
  → If is_valid=true: Go to Step 2

Step 2: anti_fraud_check (latitude, longitude, facility_type from Step 1)
  → If is_fraud=true: STOP
  → If is_fraud=false: Go to Step 3

Step 3: database_save_facility (latitude, longitude, facility_type, condition, image_url, wallet_address)
  → Save facility_id, Go to Step 4

Step 4: blockchain_reward (wallet_address, amount=50, facility_type, latitude, longitude)
  → Save tx_hash, Go to Step 5

Step 5: database_save_reward (wallet_address, amount, facility_id, tx_hash)
  → Workflow COMPLETE

After each tool result, IMMEDIATELY call the next tool. Do NOT summarize or explain - just call the next tool.
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

        # Next step prompt to guide agent to continue workflow
        # Must be very explicit because Gemini doesn't support tool_choice="required"
        next_step_prompt = """
IMPORTANT: You MUST call a tool now. Do NOT respond with text only.

Based on the last tool result, call the NEXT tool in this sequence:
1. vision_analyze → call anti_fraud_check
2. anti_fraud_check → call database_save_facility
3. database_save_facility → call blockchain_reward
4. blockchain_reward → call database_save_reward
5. database_save_reward → workflow complete

Call the next tool NOW with the appropriate parameters.
"""

        # Create custom ReAct Agent with required tool_choice to force tool execution
        self.agent = Help2EarnReactAgent(
            llm=self.llm,
            available_tools=self.tool_manager,
            system_prompt=SYSTEM_PROMPT,
            next_step_prompt=next_step_prompt,
            tool_choice="required",
            max_steps=15  # Allow more steps for complete workflow
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
