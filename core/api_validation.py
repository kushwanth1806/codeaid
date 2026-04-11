"""
API Input Validation Module
Provides validators for all API endpoint inputs to ensure data integrity and security.
"""

import re
from typing import Tuple, Optional, Dict, Any
from flask import request


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
MAX_TOTAL_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB total
MAX_FILES_PER_UPLOAD = 50  # Maximum number of files in single upload

# Content type whitelist for file uploads
ALLOWED_CONTENT_TYPES = {
    'application/zip',
    'application/x-zip-compressed',
    'text/plain',
    'text/x-python',
    'text/x-java',
    'text/x-java-source',
    'text/javascript',
    'text/x-typescript',
    'application/json',
}

# File extension whitelist (redundant but defense-in-depth)
ALLOWED_EXTENSIONS = {
    'zip', 'py', 'js', 'ts', 'jsx', 'tsx', 'java',
    'go', 'rs', 'rb', 'php', 'cs', 'c', 'cpp', 'h',
    'txt', 'json', 'yml', 'yaml', 'xml', 'md'
}

# GitHub URL pattern
GITHUB_URL_PATTERN = re.compile(
    r'^https://github\.com/[\w\-]+/[\w\-\.]+(?:/)?$',
    re.IGNORECASE
)

# API key pattern (basic: should be at least 20 chars)
API_KEY_MIN_LENGTH = 20


# ─────────────────────────────────────────────────────────────────────────────
# Error Responses
# ─────────────────────────────────────────────────────────────────────────────

class ValidationError(Exception):
    """Custom exception for validation failures."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# ─────────────────────────────────────────────────────────────────────────────
# Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_github_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate GitHub repository URL format.
    
    Args:
        url: The GitHub URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "GitHub URL must be a non-empty string"
    
    url = url.strip()
    
    if len(url) > 500:
        return False, "GitHub URL exceeds maximum length (500 characters)"
    
    if not GITHUB_URL_PATTERN.match(url):
        return False, "Invalid GitHub URL format. Must be: https://github.com/owner/repo"
    
    # Additional safety: no query parameters or fragments
    if '?' in url or '#' in url:
        return False, "GitHub URL must not contain query parameters or fragments"
    
    return True, None


def validate_file_upload(
    file_object,
    max_size: int = MAX_FILE_SIZE,
    allowed_extensions: set = ALLOWED_EXTENSIONS,
    allow_content_type_check: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validate a single uploaded file.
    
    Args:
        file_object: Flask FileStorage object
        max_size: Maximum file size in bytes
        allowed_extensions: Set of allowed file extensions
        allow_content_type_check: Whether to validate content-type header
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_object or not file_object.filename:
        return False, "File must be provided with a filename"
    
    filename = file_object.filename.strip()
    
    # Check filename length
    if len(filename) > 255:
        return False, "Filename is too long (max 255 characters)"
    
    # Check file extension
    if '.' not in filename:
        return False, f"File must have an extension from: {', '.join(sorted(allowed_extensions))}"
    
    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        return False, f"File type '.{extension}' not allowed. Allowed: {', '.join(sorted(allowed_extensions))}"
    
    # Check content-type if header present (defense-in-depth, not foolproof)
    if allow_content_type_check and file_object.content_type:
        if file_object.content_type not in ALLOWED_CONTENT_TYPES:
            # Lenient check: allow if it starts with 'text/' or is zip-like
            if not (file_object.content_type.startswith('text/') or 'zip' in file_object.content_type.lower()):
                return False, f"File content-type '{file_object.content_type}' not allowed"
    
    # Check file size by seeking to end
    file_object.seek(0, 2)  # Seek to end
    file_size = file_object.tell()
    file_object.seek(0)  # Reset to beginning
    
    if file_size == 0:
        return False, "File is empty"
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File exceeds maximum size ({max_mb:.1f}MB)"
    
    return True, None


def validate_upload_request(
    files_list: list,
    total_size_limit: int = MAX_TOTAL_UPLOAD_SIZE,
    max_files: int = MAX_FILES_PER_UPLOAD
) -> Tuple[bool, Optional[str]]:
    """
    Validate entire upload request (multiple files).
    
    Args:
        files_list: List of Flask FileStorage objects
        total_size_limit: Maximum total upload size
        max_files: Maximum number of files allowed
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not files_list or len(files_list) == 0:
        return False, "At least one file must be provided"
    
    if len(files_list) > max_files:
        return False, f"Too many files. Maximum is {max_files}"
    
    total_size = 0
    for file_obj in files_list:
        if not file_obj:
            return False, "One or more files are invalid"
        
        # Get file size
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
        total_size += size
        
        # Validate individual file
        is_valid, error = validate_file_upload(file_obj)
        if not is_valid:
            return False, error
    
    if total_size > total_size_limit:
        max_mb = total_size_limit / (1024 * 1024)
        return False, f"Total upload size exceeds limit ({max_mb:.1f}MB)"
    
    return True, None


def validate_json_request(
    data: Optional[Dict[str, Any]],
    required_fields: list = None,
    field_types: Dict[str, type] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate JSON request body.
    
    Args:
        data: Parsed JSON data
        required_fields: List of required field names
        field_types: Dict mapping field names to expected types
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if data is None:
        return False, "Request must contain valid JSON"
    
    if not isinstance(data, dict):
        return False, "JSON must be an object/dict"
    
    # Check required fields
    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
    
    # Check field types
    if field_types:
        for field, expected_type in field_types.items():
            if field in data:
                if not isinstance(data[field], expected_type):
                    type_name = expected_type.__name__
                    return False, f"Field '{field}' must be of type {type_name}"
    
    return True, None


def validate_api_key_format(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate API key format (basic length and character check).
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not api_key or not isinstance(api_key, str):
        return False, "API key must be a non-empty string"
    
    api_key = api_key.strip()
    
    if len(api_key) < API_KEY_MIN_LENGTH:
        return False, f"API key is too short (minimum {API_KEY_MIN_LENGTH} characters)"
    
    if len(api_key) > 500:
        return False, "API key is too long"
    
    # Basic check: should be alphanumeric + common special chars (-, _)
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', api_key):
        return False, "API key contains invalid characters"
    
    return True, None


def validate_integer_param(
    value: Any,
    param_name: str,
    min_value: int = None,
    max_value: int = None
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate and coerce integer parameter.
    
    Args:
        value: The value to validate
        param_name: Name of the parameter (for error messages)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Tuple of (is_valid, error_message, coerced_value)
    """
    if value is None:
        return False, f"Parameter '{param_name}' is required", None
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        return False, f"Parameter '{param_name}' must be an integer", None
    
    if min_value is not None and int_value < min_value:
        return False, f"Parameter '{param_name}' must be >= {min_value}", None
    
    if max_value is not None and int_value > max_value:
        return False, f"Parameter '{param_name}' must be <= {max_value}", None
    
    return True, None, int_value


def validate_boolean_param(value: Any, param_name: str) -> Tuple[bool, Optional[str], Optional[bool]]:
    """
    Validate and coerce boolean parameter.
    
    Args:
        value: The value to validate
        param_name: Name of the parameter (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message, coerced_value)
    """
    if isinstance(value, bool):
        return True, None, value
    
    if isinstance(value, str):
        if value.lower() in ('true', '1', 'yes'):
            return True, None, True
        elif value.lower() in ('false', '0', 'no'):
            return True, None, False
        else:
            return False, f"Parameter '{param_name}' must be 'true' or 'false'", None
    
    return False, f"Parameter '{param_name}' must be a boolean", None


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def validate_request_size(max_size: int = 1024 * 1024) -> Tuple[bool, Optional[str]]:
    """
    Validate incoming request size to prevent slowloris attacks.
    
    Args:
        max_size: Maximum request size in bytes (default 1MB for JSON)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    content_length = request.content_length
    if content_length and content_length > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"Request body exceeds maximum size ({max_mb:.1f}MB)"
    
    return True, None


def sanitize_error_message(error: Exception, expose_details: bool = False) -> str:
    """
    Create a sanitized error message safe for API responses.
    
    Args:
        error: The exception that occurred
        expose_details: Whether to expose internal details (use False in production)
        
    Returns:
        Sanitized error message
    """
    if expose_details:
        return str(error)
    else:
        # Generic message safe for production
        error_type = type(error).__name__
        if 'validation' in error_type.lower() or 'value' in error_type.lower():
            return "Invalid input provided"
        else:
            return "An error occurred while processing your request"
