"""
Rate Limiting Middleware for RehabAI
Prevents brute force attacks on login endpoints

NOTE: This limiter is per-process in-memory. Limits are NOT shared across
workers or replicas -- a deployment behind multiple Uvicorn workers or
Docker replicas multiplies the effective limit. For single-worker dev/demo
this is acceptable; for multi-replica production, replace the store with a
shared backend (e.g. Redis) before relying on these limits.
"""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, max_requests: int = 5, window_seconds: int = 300):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.attempts: dict[str, list[datetime]] = defaultdict(list)

    def is_allowed(self, identifier: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.
        Returns (is_allowed, seconds_until_reset)
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Clean old attempts
        self.attempts[identifier] = [
            t for t in self.attempts[identifier]
            if t > cutoff
        ]

        current_count = len(self.attempts[identifier])

        if current_count >= self.max_requests:
            # Calculate seconds until oldest attempt expires
            oldest = min(self.attempts[identifier])
            reset_time = oldest + timedelta(seconds=self.window_seconds)
            seconds_left = int((reset_time - now).total_seconds())
            return False, max(1, seconds_left)

        self.attempts[identifier].append(now)
        return True, None

    def reset(self, identifier: str):
        """Reset rate limit for identifier"""
        if identifier in self.attempts:
            del self.attempts[identifier]

# Global rate limiter instance
login_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)
api_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
