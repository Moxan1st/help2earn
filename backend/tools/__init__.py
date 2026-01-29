"""
SpoonOS Tools for Help2Earn

This module contains tools converted from the original skills
for use with the SpoonOS ReAct Agent.
"""

from tools.vision_tool import analyze_image
from tools.blockchain_tool import distribute_reward
from tools.database_tool import save_facility, query_facilities, update_facility, save_reward, get_user_rewards
from tools.anti_fraud_tool import check_fraud

__all__ = [
    "analyze_image",
    "distribute_reward",
    "save_facility",
    "query_facilities",
    "update_facility",
    "save_reward",
    "get_user_rewards",
    "check_fraud",
]
