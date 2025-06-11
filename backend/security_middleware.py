"""
Security middleware for Alberta Perspectives RAG API
Provides comprehensive security features including API key validation, input sanitization,
rate limiting, and request monitoring.
"""

import re
import time
import hashlib
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config import settings

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for API protection."""
    
    def __init__(self, app, rate_limit_requests: int = 100, rate_limit_window: int = 3600):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests  # requests per window
        self.rate_limit_window = rate_limit_window      # window in seconds
        self.request_history: Dict[str, deque] = defaultdict(deque)
        
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks."""
        try:
            # Apply rate limiting
            if not self._check_rate_limit(request):
                logger.warning(f"Rate limit exceeded for {self._get_client_ip(request)}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            # Log request for monitoring
            self._log_request(request)
            
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal security error"
            )
    
    def _check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limits."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests outside the window
        while (self.request_history[client_ip] and 
               self.request_history[client_ip][0] < current_time - self.rate_limit_window):
            self.request_history[client_ip].popleft()
        
        # Check if under limit
        if len(self.request_history[client_ip]) >= self.rate_limit_requests:
            return False
        
        # Add current request
        self.request_history[client_ip].append(current_time)
        return True
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (Railway, Vercel, etc.)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _log_request(self, request: Request):
        """Log request details for monitoring."""
        logger.info(f"Request: {request.method} {request.url.path} from {self._get_client_ip(request)}")

class InputValidator:
    """Input validation and sanitization utilities."""
    
    # Dangerous patterns to detect
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',               # JavaScript URLs
        r'on\w+\s*=',                # Event handlers
        r'data:text/html',           # Data URLs
        r'eval\s*\(',                # eval() calls
        r'exec\s*\(',                # exec() calls
        r'import\s+os',              # Python imports
        r'__import__',               # Python imports
        r'file://',                  # File URLs
        r'ftp://',                   # FTP URLs
    ]
    
    @classmethod
    def validate_api_key(cls, api_key: Optional[str]) -> bool:
        """Validate API key format and authenticity."""
        if not api_key:
            return False
        
        # Check basic format (Google AI API keys start with specific patterns)
        if not api_key.startswith(('AIzaSy', 'sk-')):
            logger.warning("Invalid API key format detected")
            return False
        
        # Check length (Google API keys are typically 39 characters)
        if len(api_key) < 20 or len(api_key) > 100:
            logger.warning("API key length validation failed")
            return False
        
        return True
    
    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """Sanitize user query input."""
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        # Check length limits
        if len(query) > 5000:  # Reasonable limit for queries
            raise ValueError("Query too long (max 5000 characters)")
        
        if len(query.strip()) < 3:
            raise ValueError("Query too short (minimum 3 characters)")
        
        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected in query: {pattern}")
                raise ValueError("Query contains potentially unsafe content")
        
        # Basic sanitization
        sanitized = query.strip()
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        return sanitized
    
    @classmethod
    def validate_file_upload(cls, filename: str, file_size: int) -> Dict[str, Any]:
        """Validate uploaded file."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check filename
        if not filename:
            validation_result["valid"] = False
            validation_result["errors"].append("Filename is required")
            return validation_result
        
        # Check file extension
        allowed_extensions = {'.pdf', '.pptx', '.docx', '.txt'}
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            validation_result["valid"] = False
            validation_result["errors"].append(f"File type {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}")
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            validation_result["valid"] = False
            validation_result["errors"].append(f"File too large. Max size: {max_size // (1024*1024)}MB")
        
        # Check filename for suspicious patterns
        if re.search(r'[<>:"/\\|?*]', filename):
            validation_result["warnings"].append("Filename contains special characters")
        
        return validation_result

class DatabaseConnectionManager:
    """Enhanced database connection management with health checks."""
    
    def __init__(self):
        self.connection_failures = 0
        self.last_failure_time = None
        self.max_failures = 5
        self.failure_window = 300  # 5 minutes
    
    def record_connection_failure(self):
        """Record a database connection failure."""
        current_time = time.time()
        
        # Reset counter if outside failure window
        if (self.last_failure_time and 
            current_time - self.last_failure_time > self.failure_window):
            self.connection_failures = 0
        
        self.connection_failures += 1
        self.last_failure_time = current_time
        
        logger.error(f"Database connection failure #{self.connection_failures}")
    
    def should_circuit_break(self) -> bool:
        """Check if circuit breaker should be triggered."""
        return self.connection_failures >= self.max_failures
    
    def reset_failures(self):
        """Reset failure counter after successful connection."""
        if self.connection_failures > 0:
            logger.info("Database connection restored, resetting failure counter")
            self.connection_failures = 0
            self.last_failure_time = None

# Global instances
security_middleware = SecurityMiddleware
input_validator = InputValidator()
db_connection_manager = DatabaseConnectionManager()

def validate_environment_security() -> Dict[str, Any]:
    """Validate security configuration of environment variables."""
    security_status = {
        "secure": True,
        "issues": [],
        "recommendations": []
    }
    
    # Check API key security
    if settings.environment == "production":
        if not input_validator.validate_api_key(settings.gemini_api_key):
            security_status["secure"] = False
            security_status["issues"].append("Invalid or insecure Gemini API key")
        
        # Check for debug endpoints in production
        if settings.environment == "production":
            security_status["recommendations"].append("Ensure debug endpoints are disabled in production")
    
    # Check CORS configuration
    cors_origins = getattr(settings, 'cors_origins', [])
    if '*' in cors_origins and settings.environment == "production":
        security_status["secure"] = False
        security_status["issues"].append("Wildcard CORS origins not allowed in production")
    
    return security_status 