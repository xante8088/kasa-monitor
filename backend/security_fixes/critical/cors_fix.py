"""
CORS Security Fix
Critical Security Fix - Restricts Cross-Origin Resource Sharing

Copyright (C) 2025 Kasa Monitor Contributors
Licensed under GPL v3
"""

import os
import re
from typing import List, Optional
from urllib.parse import urlparse
import logging

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class SecureCORSConfig:
    """Secure CORS configuration manager."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "production")
        self.allowed_origins = self._load_allowed_origins()
        self.allowed_patterns = self._load_origin_patterns()
        
    def _load_allowed_origins(self) -> List[str]:
        """Load allowed origins from environment or defaults."""
        origins = []
        
        # Load from environment variable
        env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
        if env_origins:
            origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])
        
        # Add development origins if in development mode
        if self.environment == "development":
            origins.extend([
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001"
            ])
        
        # Add production origins
        if self.environment == "production":
            # Only add explicitly configured production origins
            prod_domain = os.getenv("PRODUCTION_DOMAIN")
            if prod_domain:
                origins.extend([
                    f"https://{prod_domain}",
                    f"https://www.{prod_domain}"
                ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_origins = []
        for origin in origins:
            if origin not in seen:
                seen.add(origin)
                unique_origins.append(origin)
        
        return unique_origins
    
    def _load_origin_patterns(self) -> List[re.Pattern]:
        """Load regex patterns for dynamic origin matching."""
        patterns = []
        
        # Allow subdomains of trusted domains
        trusted_domains = os.getenv("CORS_TRUSTED_DOMAINS", "")
        if trusted_domains:
            for domain in trusted_domains.split(","):
                domain = domain.strip()
                if domain:
                    # Pattern to match domain and all subdomains
                    pattern = re.compile(
                        rf"^https?://([a-zA-Z0-9-]+\.)*{re.escape(domain)}(:[0-9]+)?$"
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is allowed."""
        if not origin:
            return False
        
        # Check exact match
        if origin in self.allowed_origins:
            return True
        
        # Check pattern match
        for pattern in self.allowed_patterns:
            if pattern.match(origin):
                return True
        
        return False
    
    def get_cors_middleware_config(self) -> dict:
        """Get configuration for FastAPI CORSMiddleware."""
        return {
            "allow_origins": self.allowed_origins if self.allowed_origins else [],
            "allow_credentials": True if self.allowed_origins else False,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "X-CSRF-Token"
            ],
            "expose_headers": [
                "X-Total-Count",
                "X-Page-Count",
                "X-Current-Page",
                "X-Per-Page"
            ],
            "max_age": 3600  # 1 hour
        }


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    Dynamic CORS middleware with per-request origin validation.
    Use this for more complex CORS requirements.
    """
    
    def __init__(self, app, config: SecureCORSConfig):
        super().__init__(app)
        self.config = config
        
    async def dispatch(self, request: Request, call_next):
        # Get origin from request
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._handle_preflight(request, origin)
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers if origin is allowed
        if origin and self.config.is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        
        return response
    
    def _handle_preflight(self, request: Request, origin: Optional[str]) -> Response:
        """Handle CORS preflight requests."""
        headers = {}
        
        if origin and self.config.is_origin_allowed(origin):
            headers.update({
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": request.headers.get(
                    "Access-Control-Request-Headers",
                    "Authorization, Content-Type"
                ),
                "Access-Control-Max-Age": "3600",
                "Vary": "Origin"
            })
        
        return Response(status_code=200, headers=headers)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        })
        
        # Add HSTS for HTTPS connections
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Add CSP header
        csp = self._generate_csp(request)
        if csp:
            response.headers["Content-Security-Policy"] = csp
        
        return response
    
    def _generate_csp(self, request: Request) -> str:
        """Generate Content Security Policy based on request context."""
        # Base CSP directives
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Tighten in production
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        
        # Add WebSocket support if needed
        if os.getenv("ENABLE_WEBSOCKETS", "true").lower() == "true":
            ws_scheme = "wss:" if request.url.scheme == "https" else "ws:"
            directives.append(f"connect-src 'self' {ws_scheme}")
        
        # Add report URI if configured
        report_uri = os.getenv("CSP_REPORT_URI")
        if report_uri:
            directives.append(f"report-uri {report_uri}")
        
        return "; ".join(directives)


def setup_cors_security(app):
    """
    Setup secure CORS configuration for FastAPI app.
    
    Usage:
        from cors_fix import setup_cors_security
        app = FastAPI()
        setup_cors_security(app)
    """
    # Initialize CORS configuration
    cors_config = SecureCORSConfig()
    
    # Log configuration
    logger.info(f"CORS Configuration for environment: {cors_config.environment}")
    logger.info(f"Allowed origins: {cors_config.allowed_origins}")
    
    # Option 1: Use FastAPI's built-in CORS middleware (simpler)
    if cors_config.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            **cors_config.get_cors_middleware_config()
        )
    
    # Option 2: Use dynamic CORS middleware (more flexible)
    # Uncomment to use instead of Option 1
    # app.add_middleware(DynamicCORSMiddleware, config=cors_config)
    
    # Always add security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add CORS configuration endpoint for debugging (remove in production)
    if cors_config.environment == "development":
        @app.get("/api/cors-config")
        async def get_cors_config():
            return {
                "environment": cors_config.environment,
                "allowed_origins": cors_config.allowed_origins,
                "patterns_count": len(cors_config.allowed_patterns)
            }
    
    return cors_config


# Testing utilities
def test_cors_configuration():
    """Test CORS configuration."""
    import json
    
    # Test configuration loading
    config = SecureCORSConfig()
    
    print("CORS Configuration Test")
    print("=" * 50)
    print(f"Environment: {config.environment}")
    print(f"Allowed Origins: {json.dumps(config.allowed_origins, indent=2)}")
    
    # Test origin validation
    test_origins = [
        "http://localhost:3000",
        "https://example.com",
        "http://evil.com",
        "https://app.trusted-domain.com"
    ]
    
    print("\nOrigin Validation Tests:")
    for origin in test_origins:
        allowed = config.is_origin_allowed(origin)
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"  {origin}: {status}")
    
    # Test middleware configuration
    middleware_config = config.get_cors_middleware_config()
    print("\nMiddleware Configuration:")
    print(json.dumps(middleware_config, indent=2, default=str))
    
    print("\n✅ CORS configuration test complete!")


if __name__ == "__main__":
    # Run tests
    test_cors_configuration()