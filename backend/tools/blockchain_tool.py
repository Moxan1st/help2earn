"""
Blockchain Tool - Token reward distribution

SpoonOS tool wrapper for the blockchain skill.
"""

import logging
from typing import Optional

from spoon_ai.tools import tool

logger = logging.getLogger(__name__)


@tool(name="blockchain_reward", description="Distribute token reward to user")
async def distribute_reward(
    wallet: str,
    lat: float,
    lng: float,
    facility_type: str,
    amount: int = 50
) -> dict:
    """
    Distribute H2E token reward via RewardDistributor contract.

    This tool:
    1. Generates a location hash from coordinates and facility type
    2. Attempts to distribute via RewardDistributor contract
    3. Falls back to direct minting if distributor fails

    Args:
        wallet: User's wallet address (0x...)
        lat: Latitude coordinate
        lng: Longitude coordinate
        facility_type: Type of facility (ramp/toilet/elevator/wheelchair)
        amount: Reward amount in tokens (default 50)

    Returns:
        dict with:
        - success: Whether the reward was sent
        - tx_hash: Transaction hash on blockchain
        - amount: Amount of tokens sent
        - error: Error message if failed
    """
    from skills.blockchain.skill import (
        generate_location_hash,
        distribute_reward_with_hash,
        send_reward
    )

    try:
        # Generate location hash for on-chain verification
        location_hash = generate_location_hash(lat, lng, facility_type)

        # Try distributor first
        try:
            tx_hash = await distribute_reward_with_hash(wallet, location_hash, amount)
            logger.info(f"Reward distributed via distributor: {amount} tokens to {wallet}")
            return {
                "success": True,
                "tx_hash": tx_hash,
                "amount": amount,
                "method": "distributor"
            }
        except Exception as distributor_error:
            logger.warning(f"Distributor failed, falling back to direct mint: {distributor_error}")

            # Fallback to direct mint
            tx_hash = await send_reward(wallet, amount)
            logger.info(f"Reward sent via direct mint: {amount} tokens to {wallet}")
            return {
                "success": True,
                "tx_hash": tx_hash,
                "amount": amount,
                "method": "direct_mint",
                "distributor_error": str(distributor_error)
            }

    except Exception as e:
        logger.error(f"Blockchain reward error: {e}")
        return {
            "success": False,
            "tx_hash": None,
            "amount": amount,
            "error": str(e)
        }


@tool(name="blockchain_balance", description="Check token balance for a wallet")
async def get_balance(wallet: str) -> dict:
    """
    Get the H2E token balance for a wallet.

    Args:
        wallet: Wallet address to check (0x...)

    Returns:
        dict with:
        - balance: Token balance in whole tokens
        - wallet: The wallet address checked
    """
    from skills.blockchain.skill import get_balance as _get_balance

    try:
        balance = await _get_balance(wallet)
        return {
            "balance": balance,
            "wallet": wallet
        }
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return {
            "balance": 0,
            "wallet": wallet,
            "error": str(e)
        }


@tool(name="blockchain_check_verification", description="Check if a location has been verified on-chain")
async def check_verification(lat: float, lng: float, facility_type: str) -> dict:
    """
    Check if a location has already been verified on-chain.

    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        facility_type: Type of facility

    Returns:
        dict with:
        - is_verified: Whether the location is already verified
        - location_hash: The hash that was checked
    """
    from skills.blockchain.skill import (
        generate_location_hash,
        check_verification as _check_verification
    )

    try:
        location_hash = generate_location_hash(lat, lng, facility_type)
        is_verified = await _check_verification(location_hash)

        return {
            "is_verified": is_verified,
            "location_hash": location_hash.hex()
        }
    except Exception as e:
        logger.error(f"Error checking verification: {e}")
        return {
            "is_verified": False,
            "error": str(e)
        }
