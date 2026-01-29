"""
SpoonOS Tools for Help2Earn

This module contains tools using BaseTool class pattern
for use with the SpoonOS ReAct Agent.
"""

from tools.vision_tool import VisionAnalyzeTool, VisionValidateQualityTool
from tools.anti_fraud_tool import (
    AntiFraudCheckTool,
    AntiFraudRateCheckTool,
    AntiFraudLocationCheckTool,
    AntiFraudStatisticsTool,
)
from tools.database_tool import (
    DatabaseSaveFacilityTool,
    DatabaseUpdateFacilityTool,
    DatabaseQueryFacilitiesTool,
    DatabaseSaveRewardTool,
    DatabaseGetUserRewardsTool,
    DatabaseGetFacilityTool,
    DatabaseCheckExistingTool,
)
from tools.blockchain_tool import (
    BlockchainRewardTool,
    BlockchainBalanceTool,
    BlockchainCheckVerificationTool,
)

__all__ = [
    # Vision tools
    "VisionAnalyzeTool",
    "VisionValidateQualityTool",
    # Anti-fraud tools
    "AntiFraudCheckTool",
    "AntiFraudRateCheckTool",
    "AntiFraudLocationCheckTool",
    "AntiFraudStatisticsTool",
    # Database tools
    "DatabaseSaveFacilityTool",
    "DatabaseUpdateFacilityTool",
    "DatabaseQueryFacilitiesTool",
    "DatabaseSaveRewardTool",
    "DatabaseGetUserRewardsTool",
    "DatabaseGetFacilityTool",
    "DatabaseCheckExistingTool",
    # Blockchain tools
    "BlockchainRewardTool",
    "BlockchainBalanceTool",
    "BlockchainCheckVerificationTool",
]
