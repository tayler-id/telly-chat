"""Short-term memory implementation for immediate context"""

from typing import List, Dict, Any, Optional, Deque
from collections import deque
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from enum import Enum


class MemoryPriority(Enum):
    """Priority levels for memories"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryItem:
    """Individual memory item"""
    id: str
    content: str
    timestamp: datetime
    priority: MemoryPriority = MemoryPriority.MEDIUM
    metadata: Dict[str, Any] = None
    access_count: int = 0
    last_accessed: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_accessed is None:
            self.last_accessed = self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "metadata": self.metadata,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=MemoryPriority(data["priority"]),
            metadata=data.get("metadata", {}),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
        )


class ShortTermMemory:
    """
    Short-term memory with sliding window and priority-based retention
    
    Features:
    - Fixed capacity with FIFO eviction
    - Priority-based retention
    - Time-based decay
    - Access pattern tracking
    """
    
    def __init__(
        self,
        capacity: int = 50,
        decay_time: timedelta = timedelta(minutes=30),
        priority_threshold: MemoryPriority = MemoryPriority.MEDIUM
    ):
        self.capacity = capacity
        self.decay_time = decay_time
        self.priority_threshold = priority_threshold
        
        # Memory storage
        self._memories: Deque[MemoryItem] = deque(maxlen=capacity)
        self._memory_index: Dict[str, MemoryItem] = {}
        
        # Context window for current conversation
        self._context_window: List[str] = []
        self._max_context_size = 10
        
    def add(
        self,
        content: str,
        memory_id: Optional[str] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a memory to short-term storage"""
        # Generate ID if not provided
        if memory_id is None:
            memory_id = f"stm_{datetime.now().timestamp()}"
        
        # Create memory item
        memory = MemoryItem(
            id=memory_id,
            content=content,
            timestamp=datetime.now(),
            priority=priority,
            metadata=metadata or {}
        )
        
        # Check if we need to evict
        if len(self._memories) >= self.capacity:
            self._evict_memory()
        
        # Add to storage
        self._memories.append(memory)
        self._memory_index[memory_id] = memory
        
        # Update context window
        self._update_context_window(content)
        
        return memory_id
    
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory"""
        memory = self._memory_index.get(memory_id)
        if memory:
            # Update access tracking
            memory.access_count += 1
            memory.last_accessed = datetime.now()
        return memory
    
    def search(
        self,
        query: str,
        limit: int = 5,
        min_priority: Optional[MemoryPriority] = None
    ) -> List[MemoryItem]:
        """Search memories by content"""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Keywords to look for when asking about names
        name_keywords = {'name', 'called', 'who', 'i am', 'my name', 'know me'}
        is_name_query = any(keyword in query_lower for keyword in name_keywords)
        
        for memory in self._memories:
            # Check priority filter
            if min_priority and memory.priority.value < min_priority.value:
                continue
            
            memory_lower = memory.content.lower()
            memory_words = set(memory_lower.split())
            
            # Check various matching strategies
            match_score = 0
            
            # 1. Direct substring match
            if query_lower in memory_lower:
                match_score += 3
            
            # 2. Word overlap
            common_words = query_words & memory_words
            if common_words:
                match_score += len(common_words)
            
            # 3. Special handling for name queries
            if is_name_query:
                # Look for "i am" or "my name is" patterns
                if 'i am' in memory_lower or 'my name' in memory_lower:
                    match_score += 5
                # Look for user messages (they contain personal info)
                if memory_lower.startswith('user:'):
                    match_score += 2
            
            # 4. Any word from query in memory
            if any(word in memory_lower for word in query_words if len(word) > 2):
                match_score += 1
                
            if match_score > 0:
                # Update access count when memory is found
                memory.access_count += 1
                memory.last_accessed = datetime.now()
                results.append((memory, match_score))
                
        # Sort by score, then by relevance (access count and recency)
        results.sort(
            key=lambda x: (x[1], x[0].access_count, x[0].last_accessed or datetime.min),
            reverse=True
        )
        
        return [memory for memory, score in results[:limit]]
    
    def get_context_window(self) -> List[str]:
        """Get current context window"""
        return self._context_window.copy()
    
    def get_all(self) -> List[MemoryItem]:
        """Get all memories (for consolidation checks)"""
        return list(self._memories)
    
    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """Get most recent memories"""
        # Return newest first
        recent = list(self._memories)
        recent.reverse()
        return recent[:limit]
    
    def get_high_priority(self) -> List[MemoryItem]:
        """Get high priority memories"""
        return [
            m for m in self._memories 
            if m.priority.value >= MemoryPriority.HIGH.value
        ]
    
    def decay(self):
        """Apply time-based decay to memories"""
        current_time = datetime.now()
        to_remove = []
        
        for memory in self._memories:
            # Skip high priority memories
            if memory.priority.value >= MemoryPriority.HIGH.value:
                continue
                
            # Check if memory has decayed
            age = current_time - memory.timestamp
            if age > self.decay_time:
                # Consider access patterns
                if memory.access_count < 2:
                    to_remove.append(memory.id)
        
        # Remove decayed memories
        for memory_id in to_remove:
            self.remove(memory_id)
    
    def remove(self, memory_id: str) -> bool:
        """Remove a specific memory"""
        if memory_id in self._memory_index:
            memory = self._memory_index[memory_id]
            self._memories.remove(memory)
            del self._memory_index[memory_id]
            return True
        return False
    
    def clear(self):
        """Clear all memories"""
        self._memories.clear()
        self._memory_index.clear()
        self._context_window.clear()
    
    def _evict_memory(self):
        """Evict least important memory when at capacity"""
        if not self._memories:
            return
            
        # Find lowest priority, least accessed, oldest memory
        eviction_candidate = min(
            self._memories,
            key=lambda m: (
                m.priority.value,
                m.access_count,
                -m.timestamp.timestamp()
            )
        )
        
        # Don't evict critical memories
        if eviction_candidate.priority != MemoryPriority.CRITICAL:
            self.remove(eviction_candidate.id)
    
    def _update_context_window(self, content: str):
        """Update the context window with new content"""
        self._context_window.append(content)
        
        # Maintain window size
        if len(self._context_window) > self._max_context_size:
            self._context_window.pop(0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if not self._memories:
            return {
                "total_memories": 0,
                "capacity": self.capacity,
                "utilization": 0.0
            }
            
        priorities = {}
        for priority in MemoryPriority:
            priorities[priority.name] = sum(
                1 for m in self._memories if m.priority == priority
            )
        
        total_access = sum(m.access_count for m in self._memories)
        avg_access = total_access / len(self._memories) if self._memories else 0
        
        return {
            "total_memories": len(self._memories),
            "capacity": self.capacity,
            "utilization": len(self._memories) / self.capacity,
            "priorities": priorities,
            "total_access_count": total_access,
            "average_access_count": avg_access,
            "context_window_size": len(self._context_window),
            "oldest_memory": min(self._memories, key=lambda m: m.timestamp).timestamp.isoformat() if self._memories else None,
            "newest_memory": max(self._memories, key=lambda m: m.timestamp).timestamp.isoformat() if self._memories else None
        }
    
    def export(self) -> Dict[str, Any]:
        """Export memory state"""
        return {
            "memories": [m.to_dict() for m in self._memories],
            "context_window": self._context_window,
            "statistics": self.get_statistics()
        }
    
    def import_state(self, state: Dict[str, Any]):
        """Import memory state"""
        self.clear()
        
        # Import memories
        for memory_data in state.get("memories", []):
            memory = MemoryItem.from_dict(memory_data)
            self._memories.append(memory)
            self._memory_index[memory.id] = memory
        
        # Import context window
        self._context_window = state.get("context_window", [])