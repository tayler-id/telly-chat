"""Session management service"""
import json
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from typing import Optional as OptionalType
try:
    from redis.asyncio import Redis, from_url as redis_from_url
except ImportError:
    Redis = None
    redis_from_url = None

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.schemas import Session, Message


class SessionManager:
    """Manages chat sessions and message history"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize session manager
        
        Args:
            redis_url: Redis connection URL (optional, uses in-memory if not provided)
        """
        self.redis_url = redis_url
        self.redis: Optional[Redis] = None
        self.sessions: Dict[str, Session] = {}  # In-memory fallback
        self.use_redis = bool(redis_url)
    
    async def _get_redis(self) -> Optional[Redis]:
        """Get Redis connection"""
        if self.use_redis and not self.redis:
            try:
                self.redis = await redis_from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis.ping()
            except Exception as e:
                print(f"Failed to connect to Redis: {e}")
                self.use_redis = False
        return self.redis if self.use_redis else None
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        redis = await self._get_redis()
        
        if redis:
            # Try Redis first
            data = await redis.get(f"session:{session_id}")
            if data:
                session_dict = json.loads(data)
                return Session(**session_dict)
        else:
            # Fallback to in-memory
            return self.sessions.get(session_id)
        
        return None
    
    async def create_session(self, session_id: str) -> Session:
        """Create a new session"""
        session = Session(id=session_id)
        
        redis = await self._get_redis()
        if redis:
            await redis.set(
                f"session:{session_id}",
                json.dumps(session.model_dump(mode="json")),
                ex=86400  # Expire after 24 hours
            )
        else:
            self.sessions[session_id] = session
        
        return session
    
    async def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one"""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)
        return session
    
    async def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to a session"""
        session = await self.get_or_create_session(session_id)
        session.messages.append(message)
        session.updated_at = datetime.now()
        
        redis = await self._get_redis()
        if redis:
            await redis.set(
                f"session:{session_id}",
                json.dumps(session.model_dump(mode="json")),
                ex=86400
            )
        else:
            self.sessions[session_id] = session
    
    async def update_session(self, session: Session) -> None:
        """Update a session"""
        session.updated_at = datetime.now()
        
        redis = await self._get_redis()
        if redis:
            await redis.set(
                f"session:{session.id}",
                json.dumps(session.model_dump(mode="json")),
                ex=86400
            )
        else:
            self.sessions[session.id] = session
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        redis = await self._get_redis()
        
        if redis:
            result = await redis.delete(f"session:{session_id}")
            return result > 0
        else:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    async def list_sessions(self, limit: int = 100) -> List[Session]:
        """List all sessions (limited for performance)"""
        sessions = []
        
        redis = await self._get_redis()
        if redis:
            # Get all session keys
            keys = await redis.keys("session:*")
            
            # Get sessions (limited)
            for key in keys[:limit]:
                data = await redis.get(key)
                if data:
                    session_dict = json.loads(data)
                    sessions.append(Session(**session_dict))
        else:
            # In-memory sessions
            sessions = list(self.sessions.values())[:limit]
        
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        return sessions
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis:
            await self.redis.close()
            self.redis = None