"""
Session Token Security.

Provides cryptographically secure session token generation, validation,
rotation, and TTL-based expiration.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Token length in bytes (32 bytes = 256 bits of entropy)
TOKEN_BYTES = 32


@dataclass
class SessionToken:
    """Represents a validated session with metadata."""

    token_hash: str
    session_id: str
    created_at: float
    last_accessed: float
    expires_at: float


class SessionTokenManager:
    """
    Manages cryptographically secure session tokens.

    Tokens are stored as SHA-256 hashes — raw tokens are never persisted.
    Supports TTL-based expiration and token rotation.
    """

    def __init__(self, ttl: Optional[int] = None):
        settings = get_settings()
        self._ttl = ttl or settings.session.ttl
        # In-memory store: token_hash -> SessionToken
        self._sessions: dict[str, SessionToken] = {}

    def create_token(self, session_id: str) -> str:
        """
        Generate a new cryptographically random session token.

        Returns the raw token string (only returned once — caller must store it).
        The manager stores only the SHA-256 hash.
        """
        raw_token = secrets.token_urlsafe(TOKEN_BYTES)
        token_hash = self._hash(raw_token)
        now = time.time()

        self._sessions[token_hash] = SessionToken(
            token_hash=token_hash,
            session_id=session_id,
            created_at=now,
            last_accessed=now,
            expires_at=now + self._ttl,
        )

        self._cleanup_expired()
        return raw_token

    def validate_token(self, raw_token: str) -> Optional[SessionToken]:
        """
        Validate a raw token and return its session data.

        Returns None if the token is invalid or expired.
        Updates last_accessed on successful validation.
        """
        token_hash = self._hash(raw_token)
        session = self._sessions.get(token_hash)

        if session is None:
            return None

        if time.time() > session.expires_at:
            del self._sessions[token_hash]
            return None

        # Update last accessed
        session.last_accessed = time.time()
        return session

    def rotate_token(self, raw_token: str) -> Optional[str]:
        """
        Rotate a session token — invalidate the old one, issue a new one
        bound to the same session_id.

        Returns the new raw token, or None if the old token was invalid.
        """
        session = self.validate_token(raw_token)
        if session is None:
            return None

        # Invalidate old
        self.invalidate_token(raw_token)

        # Issue new with same session_id
        return self.create_token(session.session_id)

    def invalidate_token(self, raw_token: str) -> bool:
        """Invalidate a token. Returns True if it existed."""
        token_hash = self._hash(raw_token)
        return self._sessions.pop(token_hash, None) is not None

    def invalidate_session(self, session_id: str) -> int:
        """Invalidate all tokens for a given session_id. Returns count removed."""
        to_remove = [
            h for h, s in self._sessions.items() if s.session_id == session_id
        ]
        for h in to_remove:
            del self._sessions[h]
        return len(to_remove)

    def _cleanup_expired(self) -> None:
        """Remove expired sessions (called lazily)."""
        now = time.time()
        expired = [h for h, s in self._sessions.items() if now > s.expires_at]
        for h in expired:
            del self._sessions[h]

    @staticmethod
    def _hash(raw_token: str) -> str:
        """SHA-256 hash of a raw token."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# Module-level singleton
_manager: Optional[SessionTokenManager] = None


def get_session_manager() -> SessionTokenManager:
    """Get (or create) the global session token manager."""
    global _manager
    if _manager is None:
        _manager = SessionTokenManager()
    return _manager
