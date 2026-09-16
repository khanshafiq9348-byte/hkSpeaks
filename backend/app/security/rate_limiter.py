import time
from typing import Dict, List
from fastapi import Request
from app.core.config import settings
from app.core.errors import AppException, ErrorCode

class RateLimiter:
    def __init__(self):
        self.memory_store: Dict[str, List[float]] = {}

    async def check_rate_limit(self, identifier: str, max_requests: int = 60, window_seconds: int = 60):
        """
        Sliding-window rate limiter.
        """
        now = time.time()
        # In-memory implementation
        requests = self.memory_store.get(identifier, [])
        # prune older than window
        valid_requests = [t for t in requests if now - t < window_seconds]
        if len(valid_requests) >= max_requests:
            retry_after = int(window_seconds - (now - valid_requests[0]))
            raise AppException(
                status_code=429,
                error_code=ErrorCode.RATE_LIMITED,
                message=f"Too many requests. Please retry in {retry_after} seconds.",
                details={"retry_after_seconds": retry_after}
            )
        valid_requests.append(now)
        self.memory_store[identifier] = valid_requests

rate_limiter = RateLimiter()

async def rate_limit_dependency(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    identifier = auth_header if auth_header else client_ip
    await rate_limiter.check_rate_limit(identifier, max_requests=120, window_seconds=60)
