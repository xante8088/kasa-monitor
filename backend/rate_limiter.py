"""Rate limiting implementation for API endpoints.

Copyright (C) 2025 Kasa Monitor Contributors

This file is part of Kasa Monitor.

Kasa Monitor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Kasa Monitor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
from typing import Optional, Dict, Any, Callable
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import redis
from functools import wraps


class RateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize rate limiter.
        
        Args:
            redis_client: Optional Redis client for distributed rate limiting
        """
        self.redis_client = redis_client
        self.local_storage = defaultdict(dict)
        
        # Create limiter with custom key function
        self.limiter = Limiter(
            key_func=self.get_rate_limit_key,
            default_limits=["100 per minute"],
            storage_uri="memory://" if not redis_client else f"redis://{redis_client}"
        )
        
        # Define rate limit tiers
        self.rate_limit_tiers = {
            'guest': {
                'default': '10 per minute',
                'auth': '3 per minute',
                'api': '20 per hour'
            },
            'user': {
                'default': '60 per minute',
                'auth': '10 per minute',
                'api': '1000 per hour'
            },
            'premium': {
                'default': '200 per minute',
                'auth': '20 per minute',
                'api': '5000 per hour'
            },
            'admin': {
                'default': '1000 per minute',
                'auth': '50 per minute',
                'api': '10000 per hour'
            }
        }
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/auth/login': '5 per minute',
            '/api/auth/register': '3 per hour',
            '/api/auth/reset-password': '3 per hour',
            '/api/devices/discover': '1 per minute',
            '/api/export': '10 per hour',
            '/api/backup': '5 per day',
            '/api/system/config': '20 per minute'
        }
        
    def get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key based on user and IP.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Rate limit key
        """
        # Try to get user ID from request
        user_id = getattr(request.state, 'user_id', None)
        
        if user_id:
            return f"user:{user_id}"
        else:
            # Fall back to IP address
            return get_remote_address(request)
    
    def get_user_tier(self, request: Request) -> str:
        """Determine user's rate limit tier.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User tier (guest, user, premium, admin)
        """
        user = getattr(request.state, 'user', None)
        
        if not user:
            return 'guest'
        
        if user.get('is_admin'):
            return 'admin'
        elif user.get('is_premium'):
            return 'premium'
        else:
            return 'user'
    
    def get_limit_for_endpoint(self, request: Request) -> str:
        """Get rate limit for specific endpoint.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Rate limit string
        """
        # Check for endpoint-specific limit
        path = request.url.path
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Get user tier and category
        tier = self.get_user_tier(request)
        
        # Determine category based on path
        if 'auth' in path:
            category = 'auth'
        elif 'api' in path:
            category = 'api'
        else:
            category = 'default'
        
        return self.rate_limit_tiers[tier].get(category, '60 per minute')
    
    def create_limiter_decorator(self, limit: Optional[str] = None):
        """Create a rate limiter decorator for endpoints.
        
        Args:
            limit: Optional custom limit string
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                # Get limit for this endpoint
                endpoint_limit = limit or self.get_limit_for_endpoint(request)
                
                # Apply rate limiting
                @self.limiter.limit(endpoint_limit)
                async def limited_func():
                    return await func(request, *args, **kwargs)
                
                return await limited_func()
            
            return wrapper
        return decorator
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if rate limit is exceeded.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        if self.redis_client:
            return self._check_redis_rate_limit(key, limit, window)
        else:
            return self._check_local_rate_limit(key, limit, window)
    
    def _check_local_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check rate limit using local storage.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        
        # Get or create bucket for this key
        bucket = self.local_storage[key]
        
        # Clean old entries
        cutoff = now - window
        bucket = {k: v for k, v in bucket.items() if k > cutoff}
        self.local_storage[key] = bucket
        
        # Check if limit exceeded
        if len(bucket) >= limit:
            return False
        
        # Add new entry
        bucket[now] = 1
        return True
    
    def _check_redis_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check rate limit using Redis.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        try:
            pipe = self.redis_client.pipeline()
            now = time.time()
            
            # Use sliding window algorithm
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcount(key, now - window, now)
            pipe.expire(key, window + 1)
            
            results = pipe.execute()
            request_count = results[2]
            
            return request_count <= limit
        except Exception:
            # Fall back to allowing request on Redis error
            return True
    
    def get_rate_limit_headers(self, key: str, limit: int, window: int) -> Dict[str, str]:
        """Generate rate limit headers for response.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Dictionary of headers
        """
        if self.redis_client:
            remaining = self._get_redis_remaining(key, limit, window)
        else:
            remaining = self._get_local_remaining(key, limit, window)
        
        reset_time = int(time.time()) + window
        
        return {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(max(0, remaining)),
            'X-RateLimit-Reset': str(reset_time),
            'X-RateLimit-Window': str(window)
        }
    
    def _get_local_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests for local storage.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Number of remaining requests
        """
        now = time.time()
        bucket = self.local_storage.get(key, {})
        cutoff = now - window
        current_count = sum(1 for k in bucket if k > cutoff)
        return limit - current_count
    
    def _get_redis_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests for Redis storage.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Number of remaining requests
        """
        try:
            now = time.time()
            count = self.redis_client.zcount(key, now - window, now)
            return limit - count
        except Exception:
            return limit


class IPBasedRateLimiter:
    """IP-based rate limiting with blacklist/whitelist support."""
    
    def __init__(self):
        """Initialize IP-based rate limiter."""
        self.whitelist = set()
        self.blacklist = set()
        self.temporary_blocks = {}
        self.request_history = defaultdict(list)
        
    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist.
        
        Args:
            ip: IP address to whitelist
        """
        self.whitelist.add(ip)
        if ip in self.blacklist:
            self.blacklist.remove(ip)
    
    def add_to_blacklist(self, ip: str, duration: Optional[int] = None):
        """Add IP to blacklist.
        
        Args:
            ip: IP address to blacklist
            duration: Optional duration in seconds for temporary block
        """
        if duration:
            self.temporary_blocks[ip] = datetime.now() + timedelta(seconds=duration)
        else:
            self.blacklist.add(ip)
            if ip in self.whitelist:
                self.whitelist.remove(ip)
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if blocked, False otherwise
        """
        # Check whitelist first
        if ip in self.whitelist:
            return False
        
        # Check permanent blacklist
        if ip in self.blacklist:
            return True
        
        # Check temporary blocks
        if ip in self.temporary_blocks:
            if datetime.now() < self.temporary_blocks[ip]:
                return True
            else:
                # Block expired, remove it
                del self.temporary_blocks[ip]
        
        return False
    
    def track_request(self, ip: str, endpoint: str):
        """Track request for pattern analysis.
        
        Args:
            ip: IP address
            endpoint: Requested endpoint
        """
        self.request_history[ip].append({
            'endpoint': endpoint,
            'timestamp': datetime.now()
        })
        
        # Keep only last hour of history
        cutoff = datetime.now() - timedelta(hours=1)
        self.request_history[ip] = [
            r for r in self.request_history[ip]
            if r['timestamp'] > cutoff
        ]
    
    def detect_suspicious_activity(self, ip: str) -> bool:
        """Detect suspicious request patterns.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if suspicious activity detected
        """
        history = self.request_history.get(ip, [])
        
        if not history:
            return False
        
        # Check for rapid requests (more than 100 in last minute)
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        recent_requests = [r for r in history if r['timestamp'] > one_minute_ago]
        if len(recent_requests) > 100:
            return True
        
        # Check for auth endpoint abuse
        auth_endpoints = ['/api/auth/login', '/api/auth/register', '/api/auth/reset-password']
        auth_requests = [
            r for r in recent_requests
            if any(endpoint in r['endpoint'] for endpoint in auth_endpoints)
        ]
        if len(auth_requests) > 10:
            return True
        
        return False


class UserBasedRateLimiter:
    """User-based rate limiting with custom limits."""
    
    def __init__(self):
        """Initialize user-based rate limiter."""
        self.custom_limits = {}
        self.user_request_counts = defaultdict(lambda: defaultdict(int))
        
    def set_custom_limit(self, user_id: str, limit: Dict[str, Any]):
        """Set custom rate limit for a user.
        
        Args:
            user_id: User identifier
            limit: Custom limit configuration
        """
        self.custom_limits[user_id] = limit
    
    def get_user_limit(self, user_id: str, endpoint: str) -> Dict[str, Any]:
        """Get rate limit for a user.
        
        Args:
            user_id: User identifier
            endpoint: Requested endpoint
            
        Returns:
            Rate limit configuration
        """
        # Check for custom limit
        if user_id in self.custom_limits:
            custom = self.custom_limits[user_id]
            if endpoint in custom.get('endpoints', {}):
                return custom['endpoints'][endpoint]
            elif 'default' in custom:
                return custom['default']
        
        # Return default limits based on user type
        return {
            'requests': 60,
            'window': 60
        }
    
    def track_user_request(self, user_id: str, endpoint: str):
        """Track user request for analytics.
        
        Args:
            user_id: User identifier
            endpoint: Requested endpoint
        """
        window_key = int(time.time() // 60)  # 1-minute windows
        self.user_request_counts[user_id][window_key] += 1
        
        # Clean old windows (keep last hour)
        current_window = int(time.time() // 60)
        old_windows = [
            w for w in self.user_request_counts[user_id]
            if w < current_window - 60
        ]
        for window in old_windows:
            del self.user_request_counts[user_id][window]