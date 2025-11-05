import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database import DatabaseManager
from src.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_REQUESTS_PER_MINUTE = 100
DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    _instance = None
    _db_manager = None

    def __new__(
        cls,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        db_manager: DatabaseManager = None,
    ):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        db_manager: DatabaseManager = None,
    ):
        if not hasattr(self, "_initialized") or not self._initialized:
            self.requests_per_minute = requests_per_minute
            self.window_seconds = window_seconds
            self._db_manager = db_manager

            # Dictionary: token -> list of request timestamps
            self.token_requests: Dict[str, list] = defaultdict(list)
            logger.info(f"RateLimiter initialized: {requests_per_minute} requests per {window_seconds} seconds")
            self._initialized = True
        else:
            # Allow updating db_manager and limits even after initialization
            if db_manager is not None:
                self._db_manager = db_manager
            if requests_per_minute != DEFAULT_REQUESTS_PER_MINUTE:
                self.requests_per_minute = requests_per_minute
                self.token_requests.clear()  # Clear rate limit tracking when limit changes
            if window_seconds != DEFAULT_WINDOW_SECONDS:
                self.window_seconds = window_seconds

    def _cleanup_old_requests(self, token: str):
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        self.token_requests[token] = [ts for ts in self.token_requests[token] if ts > cutoff_time]

    def check_rate_limit(self, token: str) -> Tuple[bool, int, int]:
        """
        Returns True if the token is allowed to make a request, False otherwise.
        Return remaining tokens and time to reset.
        """
        if not token:
            logger.warning("Rate limit check called without token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is required")

        self._cleanup_old_requests(token)

        current_count = len(self.token_requests[token])

        if current_count >= self.requests_per_minute:
            oldest_request = self.token_requests[token][0]
            remaining_time = self.window_seconds - (time.time() - oldest_request)
            remaining_time = max(0, int(remaining_time))

            logger.warning(
                f"Rate limit exceeded for token {token[:8]}...: {current_count}/{self.requests_per_minute} requests"
            )
            return False, 0, remaining_time

        self.token_requests[token].append(time.time())

        oldest_request = self.token_requests[token][0] if self.token_requests[token] else time.time()
        remaining_time = self.window_seconds - (time.time() - oldest_request)
        remaining_time = max(0, int(remaining_time))

        remaining = self.requests_per_minute - current_count - 1
        logger.debug(f"Rate limit check passed for token {token[:8]}...: {remaining} requests remaining")

        return True, remaining, remaining_time

    def reset_token_limit(self, token: str):
        logger.info(f"Resetting rate limit for token {token[:8]}...")
        self.token_requests[token] = []

    def check_rate_limit_dependency(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())) -> str:
        token = credentials.credentials

        # Get the singleton instance
        instance = RateLimiter()

        if instance._db_manager and not instance._db_manager.validate_api_token(token):
            logger.warning(f"Invalid or expired token: {token[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        is_allowed, remaining_tokens, remaining_time = instance.check_rate_limit(token)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for token {token[:8]}...: "
                f"{instance.requests_per_minute} req/min, retry after {remaining_time}s"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Limit: {instance.requests_per_minute} "
                    f"requests per minute. Retry after {remaining_time} seconds."
                ),
                headers={
                    "X-RateLimit-Limit": str(instance.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining_tokens),
                    "X-RateLimit-Reset": str(int(time.time()) + remaining_time),
                    "Retry-After": str(remaining_time),
                },
            )

        return token
