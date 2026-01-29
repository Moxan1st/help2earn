"""
Help2Earn FastAPI Backend

Main entry point for the Help2Earn API server.
All core business logic is driven by the SpoonOS React Agent.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
load_dotenv()

from agent.help2earn_agent import Help2EarnAgent
from models.schemas import (
    UploadResponse,
    FacilityListResponse,
    FacilityResponse,
    UserRewardsResponse,
    HealthCheck,
    ErrorResponse
)
from skills.database.skill import DatabasePool
from skills.storage.skill import upload_image
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global agent instance
agent: Optional[Help2EarnAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent

    # Startup
    logger.info("Starting Help2Earn API server...")
    agent = Help2EarnAgent()
    logger.info("SpoonOS React Agent initialized")

    yield

    # Shutdown
    logger.info("Shutting down Help2Earn API server...")
    await DatabasePool.close()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Help2Earn API",
    description="DePIN-based accessibility facility data collection platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "https://help2earn.vercel.app",  # Production frontend
        "*"  # Allow all for hackathon demo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for mock storage
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ============ Health Check ============

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Check API health status."""
    return HealthCheck(
        status="ok",
        version="1.0.0",
        services={
            "agent": agent is not None,
            "database": True  # Could add actual DB check
        }
    )


# ============ Upload Endpoint ============

@app.post("/upload", response_model=UploadResponse)
async def upload_facility(
    image: UploadFile = File(..., description="Facility image"),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    wallet_address: str = Form(..., min_length=42, max_length=42)
):
    """
    Upload a new accessibility facility.

    The SpoonOS React Agent handles the complete verification workflow:
    1. Image analysis using Vision Skill
    2. Fraud/duplicate detection using Anti-Fraud Skill
    3. Data storage using Database Skill
    4. Token distribution using Blockchain Skill

    Args:
        image: Photo of the accessibility facility
        latitude: GPS latitude coordinate
        longitude: GPS longitude coordinate
        wallet_address: User's Ethereum wallet for rewards

    Returns:
        UploadResponse with verification result and reward info
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        # Read image data
        image_data = await image.read()

        # Validate image size (max 10MB)
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

        # Validate image type
        content_type = image.content_type
        if content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type: {content_type}. Use JPEG, PNG, or WebP."
            )

        logger.info(
            f"Processing upload: lat={latitude}, lng={longitude}, "
            f"wallet={wallet_address[:10]}..., size={len(image_data)}"
        )

        # Upload image to Google Cloud Storage first
        storage_result = await upload_image(
            image_data=image_data,
            facility_type="pending",  # Will be updated after AI analysis
            content_type=content_type
        )

        image_url = storage_result.get("url") if storage_result.get("success") else None
        logger.info(f"Image uploaded to GCS: {image_url}")

        # Process through SpoonOS Agent
        result = await agent.process_upload(
            image=image_data,
            lat=latitude,
            lng=longitude,
            wallet=wallet_address,
            image_url=image_url
        )

        # Build response
        return UploadResponse(
            success=result.get("success", False),
            message="Facility verified and reward sent" if result.get("success") else "Verification failed",
            facility_id=result.get("facility_id"),
            facility_type=result.get("facility_type"),
            condition=result.get("condition"),
            reward_amount=result.get("reward_amount"),
            tx_hash=result.get("tx_hash"),
            reason=result.get("reason"),
            blockchain_error=result.get("blockchain_error")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Facility Queries ============

@app.get("/facilities", response_model=FacilityListResponse)
async def get_facilities(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: int = Query(default=200, ge=10, le=5000, description="Radius in meters"),
    facility_type: Optional[str] = Query(default=None, description="Filter by type")
):
    """
    Query nearby accessibility facilities.

    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius: Search radius in meters (default 200m, max 5000m)
        facility_type: Optional filter (ramp/toilet/elevator/wheelchair)

    Returns:
        List of facilities within the specified radius
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = await agent.query_facilities(
            lat=latitude,
            lng=longitude,
            radius=radius
        )

        facilities = result.get("facilities", [])

        # Filter by type if specified
        if facility_type:
            facilities = [f for f in facilities if f.get("type") == facility_type]

        return FacilityListResponse(
            facilities=facilities,
            count=len(facilities)
        )

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/facilities/{facility_id}", response_model=FacilityResponse)
async def get_facility(facility_id: str):
    """
    Get details of a specific facility.

    Args:
        facility_id: UUID of the facility

    Returns:
        Facility details including AI analysis
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = await agent.get_facility_details(facility_id)

        if not result or "error" in result:
            raise HTTPException(status_code=404, detail="Facility not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get facility error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Rewards Queries ============

@app.get("/rewards/{wallet}", response_model=UserRewardsResponse)
async def get_rewards(wallet: str):
    """
    Get reward history for a wallet address.

    Args:
        wallet: Ethereum wallet address

    Returns:
        Reward history and totals
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # Validate wallet address format
    if not wallet.startswith("0x") or len(wallet) != 42:
        raise HTTPException(status_code=400, detail="Invalid wallet address format")

    try:
        result = await agent.get_user_rewards(wallet)

        return UserRewardsResponse(
            wallet_address=wallet,
            rewards=result.get("rewards", []),
            total_earned=result.get("total_earned", 0),
            contribution_count=result.get("contribution_count", 0)
        )

    except Exception as e:
        logger.error(f"Get rewards error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Debug ============

@app.get("/debug/blockchain")
async def debug_blockchain():
    """Debug endpoint to check blockchain configuration."""
    import os
    from skills.blockchain.skill import get_client, MOCK_BLOCKCHAIN
    from web3 import Web3

    client = get_client()

    # Check configuration (mask sensitive data)
    private_key = os.getenv("MINTER_PRIVATE_KEY", "")
    has_private_key = len(private_key) > 10

    result = {
        "mock_mode": MOCK_BLOCKCHAIN,
        "has_private_key": has_private_key,
        "private_key_length": len(private_key),
        "rpc_url": os.getenv("SEPOLIA_RPC_URL", "not set")[:50] + "...",
        "token_contract": os.getenv("TOKEN_CONTRACT_ADDRESS", "not set"),
        "distributor_contract": os.getenv("DISTRIBUTOR_CONTRACT_ADDRESS", "not set"),
        "client_configured": client.is_configured() if client else False,
    }

    # Try to get account address if configured
    if not MOCK_BLOCKCHAIN and client and client.account:
        result["minter_address"] = client.account.address

    # Test RPC connection
    if not MOCK_BLOCKCHAIN and client:
        try:
            connected = client.w3.is_connected()
            result["rpc_connected"] = connected
            if connected:
                result["chain_id"] = client.w3.eth.chain_id

                # Check if minter wallet is authorized caller on distributor
                if client.distributor and client.account:
                    auth_abi = [{
                        "inputs": [{"name": "", "type": "address"}],
                        "name": "authorizedCallers",
                        "outputs": [{"name": "", "type": "bool"}],
                        "stateMutability": "view",
                        "type": "function"
                    }]
                    dist_addr = os.getenv("DISTRIBUTOR_CONTRACT_ADDRESS")
                    dist = client.w3.eth.contract(
                        address=Web3.to_checksum_address(dist_addr),
                        abi=auth_abi
                    )
                    is_authorized = dist.functions.authorizedCallers(client.account.address).call()
                    result["is_authorized_caller"] = is_authorized

                # Check who is the current minter on token
                if client.token:
                    minter_abi = [{
                        "inputs": [],
                        "name": "minter",
                        "outputs": [{"name": "", "type": "address"}],
                        "stateMutability": "view",
                        "type": "function"
                    }]
                    token_addr = os.getenv("TOKEN_CONTRACT_ADDRESS")
                    token = client.w3.eth.contract(
                        address=Web3.to_checksum_address(token_addr),
                        abi=minter_abi
                    )
                    current_minter = token.functions.minter().call()
                    result["token_minter"] = current_minter
                    result["distributor_is_minter"] = current_minter.lower() == dist_addr.lower()
        except Exception as e:
            result["rpc_error"] = str(e)

    return result


# ============ Statistics ============

@app.get("/stats")
async def get_statistics():
    """
    Get platform statistics.

    Returns:
        Overall platform statistics
    """
    # This could be expanded to use the agent for more complex queries
    return {
        "total_facilities": 0,  # TODO: Query from database
        "total_rewards_distributed": 0,
        "unique_contributors": 0,
        "facilities_by_type": {
            "ramp": 0,
            "toilet": 0,
            "elevator": 0,
            "wheelchair": 0
        }
    }


# ============ Error Handlers ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code=str(exc.status_code)
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump()
    )


# ============ Main Entry Point ============

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
