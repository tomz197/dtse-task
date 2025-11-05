import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.auth import verify_admin_credentials
from src.jsend import success_response
from src.logging_config import get_logger
from src.schemas import (
    CreateTokenRequest,
    GetTokensRequest,
    RevokeTokenRequest,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/create-token")
def create_token(request: CreateTokenRequest):
    verify_admin_credentials(request.username, request.password)
    logger.info("Creating new API token")
    expires_at = None
    try:
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at)
            logger.info(f"Token expiration set to: {expires_at}")
    except ValueError:
        logger.warning(f"Invalid expires_at format: {request.expires_at}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"expires_at": "Invalid expires_at format. Expected ISO format (YYYY-MM-DDTHH:MM:SS)"},
        )

    import src.config as config

    if config.db_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )

    token = uuid.uuid4().hex
    try:
        config.db_manager.create_api_token(token, expires_at)
        logger.info(f"API token created successfully: {token[:8]}...")
        return success_response({"token": token, "expires_at": request.expires_at})
    except Exception as e:
        logger.error(f"Error creating API token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token",
        )


@router.post("/revoke-token")
def revoke_token(request: RevokeTokenRequest):
    verify_admin_credentials(request.username, request.password)
    logger.info(f"Revoking API token: {request.token[:8]}...")

    import src.config as config

    if config.db_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )

    if not config.db_manager.deactivate_api_token(request.token):
        logger.warning(f"Token not found for revocation: {request.token[:8]}...")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"token": "Token not found"})
    logger.info(f"Token revoked successfully: {request.token[:8]}...")
    return success_response({"message": "Token revoked successfully"})


@router.post("/get-tokens")
def get_tokens(request: GetTokensRequest):
    verify_admin_credentials(request.username, request.password)
    logger.info("Retrieving all active API tokens")

    import src.config as config

    if config.db_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )

    try:
        tokens = config.db_manager.get_api_tokens()
        logger.info(f"Retrieved {len(tokens)} active tokens")
        return success_response({"tokens": tokens})
    except Exception as e:
        logger.error(f"Error retrieving tokens: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens",
        )
