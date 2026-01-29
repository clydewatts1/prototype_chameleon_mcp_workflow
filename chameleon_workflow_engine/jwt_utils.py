"""
JWT Authentication Utilities (Phase 2)

Provides JWT token parsing, validation, and Pilot identity extraction.
Upgrades from Phase 1's simple X-Pilot-ID header to secure JWT tokens.

Features:
- Token parsing and signature verification
- Expiration validation
- Claim extraction (sub, role, exp)
- Graceful error handling
- Phase 2 RBAC foundation

Constitutional Reference: Article XV (Pilot Sovereignty)
"""

import jwt
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from functools import lru_cache

from loguru import logger


class JWTConfig:
    """JWT configuration with sensible defaults."""
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        expiration_minutes: int = 60,
    ):
        """
        Initialize JWT configuration.
        
        Args:
            secret_key: JWT signing secret (defaults to JWT_SECRET_KEY env var)
            algorithm: JWT algorithm (HS256, RS256, etc.)
            expiration_minutes: Token lifetime in minutes
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "dev-secret-key")
        self.algorithm = algorithm
        self.expiration_minutes = expiration_minutes
    
    def validate(self):
        """Validate configuration for production use."""
        if self.secret_key == "dev-secret-key":
            logger.warning("⚠️ Using default JWT secret key - NOT SAFE FOR PRODUCTION")
        if len(self.secret_key) < 32:
            logger.warning("⚠️ JWT secret key is too short (< 32 chars) - WEAK SECURITY")


class JWTError(Exception):
    """Base JWT error."""
    pass


class InvalidTokenError(JWTError):
    """Token is invalid (malformed, expired, bad signature)."""
    pass


class MissingTokenError(JWTError):
    """Token is missing from request."""
    pass


class MissingClaimError(JWTError):
    """Required claim missing from token."""
    pass


class PilotToken:
    """
    Parsed JWT token representing a Pilot identity.
    
    Expected claims:
    - sub (str): Pilot ID/username
    - role (str): Pilot role (ADMIN, OPERATOR, VIEWER)
    - exp (int): Expiration timestamp
    - iat (int): Issued at timestamp
    """
    
    def __init__(
        self,
        pilot_id: str,
        role: str,
        issued_at: datetime,
        expires_at: datetime,
        raw_claims: Dict[str, Any],
    ):
        """
        Initialize PilotToken.
        
        Args:
            pilot_id: Extracted from 'sub' claim
            role: Extracted from 'role' claim
            issued_at: Extracted from 'iat' claim
            expires_at: Extracted from 'exp' claim
            raw_claims: Full JWT claims dict
        """
        self.pilot_id = pilot_id
        self.role = role
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.raw_claims = raw_claims
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def __repr__(self):
        return f"PilotToken(pilot_id={self.pilot_id}, role={self.role}, expires_at={self.expires_at})"


class JWTValidator:
    """JWT token parsing and validation."""
    
    def __init__(self, config: JWTConfig):
        """Initialize with JWT configuration."""
        self.config = config
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string (without 'Bearer ' prefix)
            
        Returns:
            Dict of decoded claims
            
        Raises:
            InvalidTokenError: If token is invalid, expired, or has bad signature
        """
        try:
            claims = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
            )
            return claims
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"JWT token expired: {e}")
            raise InvalidTokenError("Token has expired") from e
        except jwt.InvalidSignatureError as e:
            logger.warning(f"JWT signature invalid: {e}")
            raise InvalidTokenError("Invalid token signature") from e
        except jwt.DecodeError as e:
            logger.warning(f"JWT decode error: {e}")
            raise InvalidTokenError("Malformed token") from e
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            raise InvalidTokenError(f"Token validation failed: {str(e)}") from e
    
    def parse_pilot_token(self, token: str) -> PilotToken:
        """
        Parse JWT and extract Pilot identity.
        
        Args:
            token: JWT token string
            
        Returns:
            PilotToken with extracted identity
            
        Raises:
            InvalidTokenError: If token is invalid/expired
            MissingClaimError: If required claims missing
        """
        claims = self.decode_token(token)
        
        # Extract required claims
        pilot_id = claims.get("sub")
        if not pilot_id:
            raise MissingClaimError("Missing 'sub' (subject/pilot_id) claim")
        
        role = claims.get("role", "OPERATOR")  # Default role if not specified
        
        # Parse timestamps
        try:
            iat = claims.get("iat", datetime.now(timezone.utc).timestamp())
            exp = claims.get("exp")
            if not exp:
                raise MissingClaimError("Missing 'exp' (expiration) claim")
            
            issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        except (ValueError, TypeError) as e:
            raise InvalidTokenError(f"Invalid timestamp claims: {e}") from e
        
        logger.debug(f"Parsed Pilot token for {pilot_id} with role {role}")
        
        return PilotToken(
            pilot_id=pilot_id,
            role=role,
            issued_at=issued_at,
            expires_at=expires_at,
            raw_claims=claims,
        )
    
    def extract_bearer_token(self, auth_header: Optional[str]) -> str:
        """
        Extract token from 'Authorization: Bearer <token>' header.
        
        Args:
            auth_header: Authorization header value
            
        Returns:
            Token string (without 'Bearer ' prefix)
            
        Raises:
            MissingTokenError: If header missing or invalid format
        """
        if not auth_header:
            raise MissingTokenError("Missing Authorization header")
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise MissingTokenError(
                "Invalid Authorization header format. "
                "Expected: 'Authorization: Bearer <token>'"
            )
        
        return parts[1]


# Global JWT config (singleton)
_jwt_config = None


def get_jwt_config() -> JWTConfig:
    """Get or initialize global JWT config."""
    global _jwt_config
    if _jwt_config is None:
        _jwt_config = JWTConfig()
    return _jwt_config


def set_jwt_config(config: JWTConfig):
    """Set global JWT config (useful for testing)."""
    global _jwt_config
    _jwt_config = config


def create_token(
    pilot_id: str,
    role: str = "OPERATOR",
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Create a JWT token for a Pilot.
    
    Args:
        pilot_id: Pilot identifier (username, email, etc.)
        role: Pilot role (ADMIN, OPERATOR, VIEWER)
        expires_minutes: Token expiration (uses config default if None)
        
    Returns:
        JWT token string
    """
    config = get_jwt_config()
    
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes or config.expiration_minutes
    
    claims = {
        "sub": pilot_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now.timestamp())) + (exp_minutes * 60),
    }
    
    token = jwt.encode(
        claims,
        config.secret_key,
        algorithm=config.algorithm,
    )
    
    logger.debug(f"Created JWT token for pilot {pilot_id} with role {role}")
    return token
