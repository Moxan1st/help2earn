"""
Blockchain Skill - Ethereum token distribution

Handles all blockchain operations including:
- Sending token rewards to users
- Checking token balances
- Recording verification hashes on-chain
"""

import os
import logging
from typing import Optional

from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

# Configuration from environment
SEPOLIA_RPC_URL = os.getenv(
    "SEPOLIA_RPC_URL",
    "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
)
PRIVATE_KEY = os.getenv("MINTER_PRIVATE_KEY", "")
TOKEN_CONTRACT_ADDRESS = os.getenv("TOKEN_CONTRACT_ADDRESS", "")
DISTRIBUTOR_CONTRACT_ADDRESS = os.getenv("DISTRIBUTOR_CONTRACT_ADDRESS", "")
MOCK_BLOCKCHAIN = os.getenv("MOCK_BLOCKCHAIN", "false").lower() == "true"

# ERC-20 Token ABI (minimal for minting)
TOKEN_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# RewardDistributor ABI
DISTRIBUTOR_ABI = [
    {
        "inputs": [
            {"name": "user", "type": "address"},
            {"name": "locationHash", "type": "bytes32"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "distributeReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "bytes32"}],
        "name": "verificationRecords",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class MockContractFunction:
    def __init__(self, name):
        self.name = name
    
    def call(self, *args, **kwargs):
        if self.name == "decimals":
            return 18
        if self.name == "balanceOf":
            return 100 * 10**18
        if self.name == "verificationRecords":
            return False
        return None

    def build_transaction(self, *args, **kwargs):
        return {"to": "0x00", "data": "0x"}

class MockContract:
    def __init__(self, functions):
        self.functions = functions

class MockFunctions:
    def __getattr__(self, name):
        return MockContractFunction(name)

class MockWeb3:
    def is_connected(self):
        return True
    
    class eth:
        gas_price = 1000000000
        
        @staticmethod
        def get_transaction_count(address):
            return 0
            
        class account:
            address = "0x0000000000000000000000000000000000000000"
            
            @staticmethod
            def sign_transaction(tx, private_key):
                class SignedTx:
                    raw_transaction = b"mock"
                return SignedTx()
                
        @staticmethod
        def send_raw_transaction(raw_tx):
            return b"0x" + b"0"*64
            
        @staticmethod
        def wait_for_transaction_receipt(tx_hash, timeout=120):
            class Receipt:
                status = 1
            return Receipt()


class BlockchainClient:
    """Web3 client for blockchain operations."""

    def __init__(self):
        if MOCK_BLOCKCHAIN:
            self.w3 = MockWeb3()
            self.account = MockWeb3.eth.account
            self.token = MockContract(MockFunctions())
            self.distributor = MockContract(MockFunctions())
            return

        self.w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

        if PRIVATE_KEY:
            self.account = Account.from_key(PRIVATE_KEY)
        else:
            self.account = None
            logger.warning("No private key configured - blockchain operations will fail")

        if TOKEN_CONTRACT_ADDRESS:
            self.token = self.w3.eth.contract(
                address=Web3.to_checksum_address(TOKEN_CONTRACT_ADDRESS),
                abi=TOKEN_ABI
            )
        else:
            self.token = None

        if DISTRIBUTOR_CONTRACT_ADDRESS:
            self.distributor = self.w3.eth.contract(
                address=Web3.to_checksum_address(DISTRIBUTOR_CONTRACT_ADDRESS),
                abi=DISTRIBUTOR_ABI
            )
        else:
            self.distributor = None

    def is_configured(self) -> bool:
        """Check if blockchain client is properly configured."""
        if MOCK_BLOCKCHAIN:
            return True
            
        return all([
            self.w3.is_connected(),
            self.account is not None,
            self.token is not None
        ])


# Global client instance
_client: Optional[BlockchainClient] = None


def get_client() -> BlockchainClient:
    """Get or create the blockchain client."""
    global _client
    if _client is None:
        _client = BlockchainClient()
    return _client


async def send_reward(wallet: str, amount: int) -> str:
    """
    Send token rewards to a user's wallet.

    This calls the token contract's mint function to create new tokens
    and send them to the specified wallet address.

    Args:
        wallet: Recipient's wallet address
        amount: Number of tokens to send (in whole tokens, not wei)

    Returns:
        str: Transaction hash
    """
    client = get_client()
    
    if MOCK_BLOCKCHAIN:
        import hashlib
        logger.info(f"[MOCK] Sending reward: {amount} tokens to {wallet}")
        # Generate a fake hash
        fake_hash = "0x" + hashlib.sha256(f"{wallet}{amount}".encode()).hexdigest()
        return fake_hash

    if not client.is_configured():
        logger.error("Blockchain client not configured")
        return "0x" + "0" * 64  # Return dummy hash for testing

    try:
        # Convert to checksum address
        recipient = Web3.to_checksum_address(wallet)

        # Get token decimals (usually 18)
        decimals = client.token.functions.decimals().call()
        token_amount = amount * (10 ** decimals)

        # Build transaction
        nonce = client.w3.eth.get_transaction_count(client.account.address)

        tx = client.token.functions.mint(
            recipient,
            token_amount
        ).build_transaction({
            'from': client.account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': client.w3.eth.gas_price
        })

        # Sign and send
        signed_tx = client.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for confirmation
        receipt = client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            logger.info(f"Reward sent: {amount} tokens to {wallet}, tx: {tx_hash.hex()}")
            return tx_hash.hex()
        else:
            logger.error(f"Transaction failed: {tx_hash.hex()}")
            raise Exception("Transaction failed")

    except Exception as e:
        logger.error(f"Error sending reward: {e}")
        raise


async def distribute_reward_with_hash(
    wallet: str,
    location_hash: bytes,
    amount: int
) -> str:
    """
    Distribute reward through the RewardDistributor contract.

    This records the verification hash on-chain to prevent double-claiming
    and distributes tokens to the user.

    Args:
        wallet: Recipient's wallet address
        location_hash: Hash of the facility location (for duplicate prevention)
        amount: Number of tokens to distribute

    Returns:
        str: Transaction hash
    """
    client = get_client()

    if not client.distributor:
        logger.warning("Distributor contract not configured, using direct mint")
        return await send_reward(wallet, amount)

    try:
        recipient = Web3.to_checksum_address(wallet)

        # Check if already verified
        is_verified = client.distributor.functions.verificationRecords(
            location_hash
        ).call()

        if is_verified:
            logger.warning(f"Location already verified: {location_hash.hex()}")
            raise Exception("Location already verified")

        # Get token decimals
        decimals = client.token.functions.decimals().call()
        token_amount = amount * (10 ** decimals)

        # Build transaction
        nonce = client.w3.eth.get_transaction_count(client.account.address)

        tx = client.distributor.functions.distributeReward(
            recipient,
            location_hash,
            token_amount
        ).build_transaction({
            'from': client.account.address,
            'nonce': nonce,
            'gas': 300000,  # Increased from 150000
            'gasPrice': client.w3.eth.gas_price
        })

        # Sign and send
        signed_tx = client.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for confirmation
        receipt = client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            logger.info(f"Reward distributed: {amount} tokens to {wallet}, tx: {tx_hash.hex()}")
            return tx_hash.hex()
        else:
            raise Exception("Transaction failed")

    except Exception as e:
        logger.error(f"Error distributing reward: {e}")
        raise


async def get_balance(wallet: str) -> int:
    """
    Get the token balance for a wallet.

    Args:
        wallet: Wallet address to check

    Returns:
        int: Token balance (in whole tokens)
    """
    client = get_client()

    if not client.token:
        logger.error("Token contract not configured")
        return 0

    try:
        address = Web3.to_checksum_address(wallet)

        # Get balance in wei
        balance_wei = client.token.functions.balanceOf(address).call()

        # Convert to whole tokens
        decimals = client.token.functions.decimals().call()
        balance = balance_wei // (10 ** decimals)

        return balance

    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return 0


async def check_verification(location_hash: bytes) -> bool:
    """
    Check if a location has already been verified.

    Args:
        location_hash: Hash of the facility location

    Returns:
        bool: True if already verified
    """
    client = get_client()

    if not client.distributor:
        return False

    try:
        return client.distributor.functions.verificationRecords(
            location_hash
        ).call()

    except Exception as e:
        logger.error(f"Error checking verification: {e}")
        return False


def generate_location_hash(lat: float, lng: float, facility_type: str) -> bytes:
    """
    Generate a unique hash for a facility location.

    This is used to prevent duplicate verifications on-chain.

    Args:
        lat: Latitude (rounded to 5 decimal places ~1m precision)
        lng: Longitude (rounded to 5 decimal places)
        facility_type: Type of facility

    Returns:
        bytes: 32-byte hash
    """
    # Round to ~1m precision
    lat_rounded = round(lat, 5)
    lng_rounded = round(lng, 5)

    # Create unique string
    location_str = f"{lat_rounded}:{lng_rounded}:{facility_type}"

    # Hash it
    return Web3.keccak(text=location_str)


# Skill registration for SpoonOS
def skill(name: str):
    """Decorator for registering skills with SpoonOS."""
    def decorator(func):
        func._skill_name = name
        return func
    return decorator


# Register skills
send_reward = skill("send_reward")(send_reward)
distribute_reward_with_hash = skill("distribute_reward_with_hash")(distribute_reward_with_hash)
get_balance = skill("get_balance")(get_balance)
check_verification = skill("check_verification")(check_verification)
