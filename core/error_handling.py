"""
Error Handling & Logging Module
Provides centralized error handling with proper logging and user-friendly messages.
"""

import logging
import traceback
from functools import wraps
from typing import Callable, Dict, Any, Optional
from flask import jsonify, request

# Configure logger
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Error Classes
# ─────────────────────────────────────────────────────────────────────────────

class CodeAidError(Exception):
    """Base exception for CodeAid application."""
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "INVALID_REQUEST"
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(CodeAidError):
    """Invalid user input or request parameters."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")


class RepositoryError(CodeAidError):
    """Issue loading or accessing repository."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="REPOSITORY_ERROR")


class AnalysisError(CodeAidError):
    """Error during code analysis pipeline."""
    def __init__(self, message: str):
        super().__init__(message, status_code=500, error_code="ANALYSIS_ERROR")


class LLMError(CodeAidError):
    """Error with LLM integration."""
    def __init__(self, message: str):
        super().__init__(message, status_code=503, error_code="LLM_UNAVAILABLE")


class TimeoutError(CodeAidError):
    """Request timeout."""
    def __init__(self, message: str = "Request took too long"):
        super().__init__(message, status_code=408, error_code="TIMEOUT")


class RateLimitError(CodeAidError):
    """Rate limit exceeded."""
    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED")


# ─────────────────────────────────────────────────────────────────────────────
# Error Handler Decorator
# ─────────────────────────────────────────────────────────────────────────────

def handle_api_errors(f: Callable) -> Callable:
    """
    Decorator for Flask route handlers that catches and formats errors consistently.
    
    Usage:
        @app.route('/api/endpoint')
        @handle_api_errors
        def my_endpoint():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except CodeAidError as e:
            # Expected application errors
            log_error(
                error=e,
                level='warning',
                endpoint=request.endpoint,
                method=request.method,
                status_code=e.status_code
            )
            return jsonify({
                'error': e.message,
                'error_code': e.error_code,
                'status': 'error'
            }), e.status_code
        
        except TimeoutError as e:
            log_error(
                error=e,
                level='warning',
                endpoint=request.endpoint,
                message="Request timeout - analysis took too long"
            )
            return jsonify({
                'error': 'Analysis request took too long. Please try with a smaller repository.',
                'error_code': 'TIMEOUT',
                'status': 'error'
            }), 408
        
        except RateLimitError as e:
            log_error(
                error=e,
                level='warning',
                endpoint=request.endpoint,
                message="Rate limit exceeded"
            )
            return jsonify({
                'error': 'Too many requests. Please wait before trying again.',
                'error_code': 'RATE_LIMIT_EXCEEDED',
                'status': 'error',
                'retry_after': 60
            }), 429
        
        except ValueError as e:
            # Value/type errors in input
            log_error(
                error=e,
                level='warning',
                endpoint=request.endpoint,
                message="Invalid parameter value"
            )
            return jsonify({
                'error': 'Invalid parameter value provided',
                'error_code': 'INVALID_PARAMETER',
                'status': 'error'
            }), 400
        
        except KeyError as e:
            # Missing required keys
            log_error(
                error=e,
                level='warning',
                endpoint=request.endpoint,
                message=f"Missing required field: {str(e)}"
            )
            return jsonify({
                'error': f'Missing required field: {str(e).strip(chr(39))}',
                'error_code': 'MISSING_FIELD',
                'status': 'error'
            }), 400
        
        except Exception as e:
            # Unexpected errors - don't expose details to user
            log_error(
                error=e,
                level='error',
                endpoint=request.endpoint,
                method=request.method,
                include_traceback=True
            )
            return jsonify({
                'error': 'An unexpected error occurred. Please try again or contact support.',
                'error_code': 'INTERNAL_ERROR',
                'status': 'error'
            }), 500
    
    return decorated_function


# ─────────────────────────────────────────────────────────────────────────────
# Logging Functions
# ─────────────────────────────────────────────────────────────────────────────

def log_error(
    error: Exception,
    level: str = 'error',
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    message: Optional[str] = None,
    status_code: Optional[int] = None,
    include_traceback: bool = False
) -> None:
    """
    Log an error with context information.
    
    Args:
        error: The exception that occurred
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        endpoint: Flask endpoint name
        method: HTTP method
        message: Additional context message
        status_code: HTTP status code to be returned
        include_traceback: Whether to include full traceback
    """
    log_func = getattr(logger, level, logger.error)
    
    context = []
    if endpoint:
        context.append(f"endpoint={endpoint}")
    if method:
        context.append(f"method={method}")
    if status_code:
        context.append(f"status={status_code}")
    
    context_str = ' | '.join(context) if context else ''
    error_msg = message or str(error)
    
    if include_traceback:
        error_info = f"{error_msg} | {context_str}\n{traceback.format_exc()}"
    else:
        error_info = f"{error_msg} | {context_str}" if context_str else error_msg
    
    log_func(error_info)


def log_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: Optional[float] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log successful API request.
    
    Args:
        endpoint: Flask endpoint name
        method: HTTP method
        status_code: Response status code
        response_time_ms: Request duration in milliseconds
        user_id: Optional user identifier
    """
    parts = [f"endpoint={endpoint}", f"method={method}", f"status={status_code}"]
    
    if response_time_ms:
        parts.append(f"time={response_time_ms:.2f}ms")
    if user_id:
        parts.append(f"user={user_id}")
    
    logger.info(' | '.join(parts))


def log_security_event(
    event_type: str,
    severity: str = 'info',
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> None:
    """
    Log security-relevant events (failed auth, rate limit, suspicious input, etc.)
    
    Args:
        event_type: Type of security event
        severity: 'info', 'warning', or 'critical'
        details: Additional context
        user_id: Optional user identifier
        ip_address: Optional client IP
    """
    parts = [f"security_event={event_type}", f"severity={severity}"]
    
    if user_id:
        parts.append(f"user={user_id}")
    if ip_address:
        parts.append(f"ip={ip_address}")
    if details:
        details_str = ' '.join(f"{k}={v}" for k, v in details.items())
        parts.append(details_str)
    
    log_func = getattr(logger, severity, logger.info)
    log_func(' | '.join(parts))


# ─────────────────────────────────────────────────────────────────────────────
# Context Managers for Error Handling
# ─────────────────────────────────────────────────────────────────────────────

class catch_analysis_errors:
    """Context manager for catching and translating analysis pipeline errors."""
    
    def __init__(self, error_message: str = "Code analysis failed"):
        self.error_message = error_message
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        
        # Log the error
        log_error(
            exc_val,
            level='error',
            message=self.error_message,
            include_traceback=True
        )
        
        # Don't suppress exceptions (let them be caught by route handler)
        return False


class catch_repository_errors:
    """Context manager for catching and translating repository loading errors."""
    
    def __init__(self, repo_source: str = "repository"):
        self.repo_source = repo_source
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        
        error_msg = f"Failed to load {self.repo_source}"
        
        if 'not found' in str(exc_val).lower() or 'cannot find' in str(exc_val).lower():
            raise RepositoryError(f"{self.repo_source} not found or is not accessible")
        elif 'permission' in str(exc_val).lower():
            raise RepositoryError(f"Permission denied accessing {self.repo_source}")
        else:
            log_error(exc_val, level='error', message=error_msg, include_traceback=True)
            raise AnalysisError(error_msg)


# ─────────────────────────────────────────────────────────────────────────────
# Summary Statistics
# ─────────────────────────────────────────────────────────────────────────────

class ErrorStats:
    """Track error statistics for monitoring."""
    
    def __init__(self):
        self.total_errors = 0
        self.errors_by_type = {}
        self.errors_by_endpoint = {}
    
    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record an error occurrence."""
        self.total_errors += 1
        
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self.errors_by_endpoint[endpoint] = self.errors_by_endpoint.get(endpoint, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            'total_errors': self.total_errors,
            'errors_by_type': self.errors_by_type,
            'errors_by_endpoint': self.errors_by_endpoint,
        }
    
    def reset(self) -> None:
        """Reset statistics."""
        self.total_errors = 0
        self.errors_by_type = {}
        self.errors_by_endpoint = {}


# Global error stats instance
error_stats = ErrorStats()
