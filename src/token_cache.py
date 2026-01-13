"""
Token Cache Manager - SQLite-based caching for TrustyVault tokens

Provides efficient token caching to reduce TrustyVault API calls:
- Cache access_token and refresh_token
- Automatic expiration checking
- Thread-safe SQLite operations
- Cleanup of expired tokens
"""

import sqlite3
import logging
import time
import os
from typing import Optional, Dict
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("TOKEN_CACHE_DB", "/app/data/tokens.db")


class TokenCache:
    """SQLite-based token cache manager"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Create data directory if it doesn't exist"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_cache (
                    session_token TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    microsoft_upn TEXT,
                    provider TEXT NOT NULL DEFAULT 'microsoft_graph',
                    expires_at INTEGER NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    last_used_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Index for cleanup queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON token_cache(expires_at)
            """)
            
            conn.commit()
            logger.info(f"Token cache database initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for SQLite connections with proper cleanup"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def get(self, session_token: str, provider: str = "microsoft_graph") -> Optional[Dict[str, str]]:
        """
        Get cached token if exists and not expired
        
        Args:
            session_token: TrustyVault session token (UUID)
            provider: Provider name (default: microsoft_graph)
        
        Returns:
            Dict with access_token, refresh_token, microsoft_upn if valid cache exists
            None if no valid cache
        """
        now = int(time.time())
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT access_token, refresh_token, microsoft_upn, expires_at
                FROM token_cache
                WHERE session_token = ? AND provider = ? AND expires_at > ?
            """, (session_token, provider, now))
            
            row = cursor.fetchone()
            
            if row:
                # Update last_used_at
                conn.execute("""
                    UPDATE token_cache 
                    SET last_used_at = strftime('%s', 'now')
                    WHERE session_token = ? AND provider = ?
                """, (session_token, provider))
                conn.commit()
                
                result = {
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "microsoft_upn": row["microsoft_upn"]
                }
                
                logger.debug(
                    f"Cache HIT: session={session_token[:8]}..., "
                    f"expires_in={row['expires_at'] - now}s"
                )
                
                return result
            else:
                logger.debug(f"Cache MISS: session={session_token[:8]}...")
                return None
    
    def set(
        self,
        session_token: str,
        access_token: str,
        refresh_token: Optional[str],
        microsoft_upn: str,
        expires_in_seconds: int,
        provider: str = "microsoft_graph"
    ):
        """
        Store token in cache
        
        Args:
            session_token: TrustyVault session token (UUID)
            access_token: JWT access token
            refresh_token: Optional refresh token
            microsoft_upn: User Principal Name extracted from JWT
            expires_in_seconds: Token TTL in seconds
            provider: Provider name (default: microsoft_graph)
        """
        expires_at = int(time.time()) + expires_in_seconds
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO token_cache 
                (session_token, access_token, refresh_token, microsoft_upn, provider, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_token, access_token, refresh_token, microsoft_upn, provider, expires_at))
            
            conn.commit()
        
        logger.info(
            f"Token cached: session={session_token[:8]}..., "
            f"upn={microsoft_upn}, expires_in={expires_in_seconds}s"
        )
    
    def delete(self, session_token: str, provider: str = "microsoft_graph"):
        """
        Delete cached token
        
        Args:
            session_token: TrustyVault session token
            provider: Provider name (default: microsoft_graph)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM token_cache 
                WHERE session_token = ? AND provider = ?
            """, (session_token, provider))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Token deleted from cache: session={session_token[:8]}...")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired tokens from cache
        
        Returns:
            Number of tokens deleted
        """
        now = int(time.time())
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM token_cache 
                WHERE expires_at < ?
            """, (now,))
            
            conn.commit()
            deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired tokens")
        
        return deleted_count
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dict with total_tokens, expired_tokens, valid_tokens
        """
        now = int(time.time())
        
        with self._get_connection() as conn:
            # Total tokens
            cursor = conn.execute("SELECT COUNT(*) as count FROM token_cache")
            total = cursor.fetchone()["count"]
            
            # Expired tokens
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM token_cache WHERE expires_at <= ?",
                (now,)
            )
            expired = cursor.fetchone()["count"]
            
            # Valid tokens
            valid = total - expired
        
        return {
            "total_tokens": total,
            "expired_tokens": expired,
            "valid_tokens": valid
        }


# Global cache instance
_cache_instance: Optional[TokenCache] = None


def get_cache() -> TokenCache:
    """Get or create global TokenCache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = TokenCache()
    
    return _cache_instance
