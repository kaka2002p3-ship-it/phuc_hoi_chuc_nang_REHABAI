"""
Authentication Module for RehabAI.
Provides JWT-based authentication with role-based access control.
Note: This module provides basic auth functions. For full user management,
use the existing security.py module which integrates with the User model.
"""
from datetime import datetime, timedelta
from typing import Optional

# Re-export from security module for convenience
from backend.core.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
    user_id_from_token,
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(
    user_id: str,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token with user info.

    Args:
        user_id: The user's ID
        role: Optional role (therapist/patient)
        expires_delta: Optional custom expiration time

    Returns:
        JWT token string
    """
    from backend.core.security import create_token
    return create_token(user_id)


def get_token_payload(token: str) -> Optional[dict]:
    """
    Get payload from JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload dict or None if invalid
    """
    try:
        return decode_token(token)
    except Exception:
        return None


def verify_token(token: str) -> bool:
    """
    Verify if token is valid.

    Args:
        token: JWT token string

    Returns:
        True if valid, False otherwise
    """
    try:
        decode_token(token)
        return True
    except Exception:
        return False
