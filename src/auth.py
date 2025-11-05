import os
from fastapi import HTTPException, status
from dotenv import load_dotenv

from src.logging_config import get_logger

load_dotenv()

logger = get_logger(__name__)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


def verify_admin_credentials(username: str, password: str):
    """
    Verify admin credentials from environment variables.
    Raises HTTPException if credentials are invalid or not configured.
    """
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        logger.error("Admin credentials not configured. ADMIN_USERNAME and ADMIN_PASSWORD must be set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication not configured",
        )

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        logger.warning(f"Failed authentication attempt for username: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    logger.debug(f"Successful authentication for username: {username}")
    return username
