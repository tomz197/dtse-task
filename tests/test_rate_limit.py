import time

import pytest
from fastapi import HTTPException

from src.database import DatabaseManager
from src.rate_limit import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter class"""

    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization"""
        assert rate_limiter.requests_per_minute == 10
        assert rate_limiter.window_seconds == 60
        assert rate_limiter.token_requests == {}

    def test_rate_limit_allows_requests(self, rate_limiter):
        """Test that requests within limit are allowed"""
        token = "test_token"

        # Make requests up to the limit
        for i in range(10):
            is_allowed, remaining, remaining_time = rate_limiter.check_rate_limit(token)
            assert is_allowed is True
            assert remaining == 10 - i - 1

    def test_rate_limit_blocks_excess_requests(self, rate_limiter):
        """Test that requests exceeding limit are blocked"""
        token = "test_token"

        # Exhaust the limit
        for _ in range(10):
            rate_limiter.check_rate_limit(token)

        # Next request should be blocked
        is_allowed, remaining, remaining_time = rate_limiter.check_rate_limit(token)
        assert is_allowed is False
        assert remaining == 0
        assert remaining_time >= 0

    def test_rate_limit_requires_token(self, rate_limiter):
        """Test that rate limit check requires a token"""
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit("")

        assert exc_info.value.status_code == 401
        assert "Token is required" in str(exc_info.value.detail)

    def test_rate_limit_window_reset(self, rate_limiter):
        """Test that rate limit window resets after time passes"""
        token = "test_token"

        # Set a very short window for testing
        rate_limiter.window_seconds = 1

        # Exhaust the limit
        for _ in range(10):
            rate_limiter.check_rate_limit(token)

        # Should be blocked
        is_allowed, _, _ = rate_limiter.check_rate_limit(token)
        assert is_allowed is False

        # Wait for window to reset
        time.sleep(1.1)

        # Should be allowed again
        is_allowed, remaining, _ = rate_limiter.check_rate_limit(token)
        assert is_allowed is True

    def test_rate_limit_cleanup_old_requests(self, rate_limiter):
        """Test that old requests are cleaned up"""
        token = "test_token"

        # Set a very short window
        rate_limiter.window_seconds = 1

        # Make some requests
        for _ in range(5):
            rate_limiter.check_rate_limit(token)

        # Wait for requests to expire
        time.sleep(1.1)

        # Make more requests - should still be within limit
        for _ in range(5):
            is_allowed, _, _ = rate_limiter.check_rate_limit(token)
            assert is_allowed is True

    def test_rate_limit_different_tokens(self, rate_limiter):
        """Test that rate limits are per-token"""
        token1 = "token1"
        token2 = "token2"

        # Exhaust limit for token1
        for _ in range(10):
            rate_limiter.check_rate_limit(token1)

        # Token2 should still have full limit
        is_allowed, remaining, _ = rate_limiter.check_rate_limit(token2)
        assert is_allowed is True
        assert remaining == 9

    def test_reset_token_limit(self, rate_limiter):
        """Test resetting rate limit for a token"""
        token = "test_token"

        # Exhaust the limit
        for _ in range(10):
            rate_limiter.check_rate_limit(token)

        # Reset the limit
        rate_limiter.reset_token_limit(token)

        # Should be able to make requests again
        is_allowed, remaining, _ = rate_limiter.check_rate_limit(token)
        assert is_allowed is True
        assert remaining == 9

    def test_check_rate_limit_dependency_invalid_token(self, rate_limiter, temp_db):
        """Test dependency function with invalid token"""
        from fastapi.security import HTTPAuthorizationCredentials

        db_manager, _ = temp_db
        rate_limiter._db_manager = db_manager

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit_dependency(credentials)

        assert exc_info.value.status_code == 401

    def test_check_rate_limit_dependency_valid_token(
        self, rate_limiter, db_manager_with_token
    ):
        """Test dependency function with valid token"""
        from fastapi.security import HTTPAuthorizationCredentials

        db_manager, _, token = db_manager_with_token
        rate_limiter._db_manager = db_manager

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Should return the token
        result = rate_limiter.check_rate_limit_dependency(credentials)
        assert result == token

    def test_check_rate_limit_dependency_rate_limit_exceeded(
        self, rate_limiter, db_manager_with_token
    ):
        """Test dependency function when rate limit is exceeded"""
        from fastapi.security import HTTPAuthorizationCredentials

        db_manager, _, token = db_manager_with_token
        rate_limiter._db_manager = db_manager

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Exhaust the rate limit
        for _ in range(10):
            rate_limiter.check_rate_limit(token)

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit_dependency(credentials)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)
