from collections import defaultdict
from typing import Dict, Tuple
from fastapi import HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.database import DatabaseManager
import time

DEFAULT_REQUESTS_PER_MINUTE = 100
DEFAULT_WINDOW_SECONDS = 60

class RateLimiter:
    _instance = None
    _db_manager = None

    def __new__(cls, requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE, 
                 window_seconds: int = DEFAULT_WINDOW_SECONDS, db_manager: DatabaseManager = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE, 
                 window_seconds: int = DEFAULT_WINDOW_SECONDS, db_manager: DatabaseManager = None):
        if not self._initialized:
            self.requests_per_minute = requests_per_minute
            self.window_seconds = window_seconds
            self._db_manager = db_manager

            # Dictionary: token -> list of request timestamps
            self.token_requests: Dict[str, list] = defaultdict(list)
            self._initialized = True
    
    def _cleanup_old_requests(self, token: str):
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        self.token_requests[token] = [
            ts for ts in self.token_requests[token] 
            if ts > cutoff_time
        ]
    
    def check_rate_limit(self, token: str) -> Tuple[bool, int, int]:
        """
        Returns True if the token is allowed to make a request, False otherwise.
        Return remaining tokens and time to reset.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is required"
            )
        
        self._cleanup_old_requests(token)
        
        current_count = len(self.token_requests[token])
        
        if current_count >= self.requests_per_minute:
            oldest_request = self.token_requests[token][0]
            remaining_time = self.window_seconds - (time.time() - oldest_request)
            remaining_time = max(0, int(remaining_time))
            
            return False, 0, remaining_time
        
        self.token_requests[token].append(time.time())
        
        oldest_request = self.token_requests[token][0] if self.token_requests[token] else time.time()
        remaining_time = self.window_seconds - (time.time() - oldest_request)
        remaining_time = max(0, int(remaining_time))
        
        return True, self.requests_per_minute - current_count - 1, remaining_time
    
    def reset_token_limit(self, token: str):
        self.token_requests[token] = []

    def check_rate_limit_dependency(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())) -> str:
        token = credentials.credentials
        
        if self._db_manager and not self._db_manager.validate_api_token(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        is_allowed, remaining_tokens, remaining_time = self.check_rate_limit(token)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Limit: {self.requests_per_minute} requests per minute. Retry after {remaining_time} seconds.",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining_tokens),
                    "X-RateLimit-Reset": str(int(time.time()) + remaining_time),
                    "Retry-After": str(remaining_time)
                }
            )
        
        return token

