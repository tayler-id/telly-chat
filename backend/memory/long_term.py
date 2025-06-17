"""Long-term memory implementation with semantic storage and retrieval"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
from dataclasses import dataclass
import json

from .vector_store import VectorStore, VectorStoreConfig, HybridMemorySearch
from .short_term import MemoryItem, MemoryPriority


@dataclass
class LongTermMemoryItem:
    """Enhanced memory item for long-term storage"""
    id: str
    content: str
    summary: str
    timestamp: datetime
    category: str
    importance_score: float
    consolidation_count: int
    related_memories: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "importance_score": self.importance_score,
            "consolidation_count": self.consolidation_count,
            "related_memories": self.related_memories,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LongTermMemoryItem':
        return cls(
            id=data["id"],
            content=data["content"],
            summary=data["summary"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            category=data["category"],
            importance_score=data["importance_score"],
            consolidation_count=data["consolidation_count"],
            related_memories=data["related_memories"],
            metadata=data["metadata"]
        )


class LongTermMemory:
    """
    Long-term memory with semantic storage and intelligent retrieval
    
    Features:
    - Vector-based semantic storage
    - Memory consolidation from short-term
    - Importance-based retention
    - Category organization
    - Relationship tracking
    """
    
    def __init__(
        self,
        vector_config: Optional[VectorStoreConfig] = None,
        importance_threshold: float = 0.5,
        consolidation_threshold: int = 3
    ):
        # Initialize vector store
        if vector_config is None:
            vector_config = VectorStoreConfig(
                store_type="faiss",
                embedding_provider="openai",
                persist_directory="./memory/long_term"
            )
        
        self.vector_store = VectorStore(vector_config)
        self.hybrid_search = HybridMemorySearch(self.vector_store)
        
        self.importance_threshold = importance_threshold
        self.consolidation_threshold = consolidation_threshold
        
        # Category management
        self.categories = {
            "conversation": "General conversation and dialogue",
            "fact": "Factual information and knowledge",
            "preference": "User preferences and settings",
            "task": "Tasks and action items",
            "relationship": "Information about people and relationships",
            "experience": "Past experiences and events"
        }
        
        # Memory index for quick lookups
        self._memory_index: Dict[str, LongTermMemoryItem] = {}
    
    def consolidate_from_short_term(
        self,
        short_term_memories: List[MemoryItem],
        summarizer_fn: Optional[callable] = None
    ) -> List[str]:
        """Consolidate important memories from short-term to long-term"""
        consolidated_ids = []
        
        for memory in short_term_memories:
            # Check importance criteria
            if self._should_consolidate(memory):
                # Generate summary if summarizer provided
                summary = memory.content
                if summarizer_fn:
                    summary = summarizer_fn(memory.content)
                
                # Determine category
                category = self._categorize_memory(memory.content)
                
                # Calculate importance score
                importance = self._calculate_importance(memory)
                
                # Store in long-term memory
                memory_id = self.store(
                    content=memory.content,
                    summary=summary,
                    category=category,
                    importance_score=importance,
                    metadata={
                        **memory.metadata,
                        "source": "short_term_consolidation",
                        "original_id": memory.id,
                        "access_count": memory.access_count
                    }
                )
                
                consolidated_ids.append(memory_id)
        
        return consolidated_ids
    
    def store(
        self,
        content: str,
        summary: Optional[str] = None,
        category: str = "conversation",
        importance_score: float = 0.5,
        related_memories: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a memory in long-term storage"""
        # Generate ID
        memory_id = f"ltm_{uuid.uuid4().hex}"
        
        # Create memory item
        memory = LongTermMemoryItem(
            id=memory_id,
            content=content,
            summary=summary or content[:200],
            timestamp=datetime.now(),
            category=category,
            importance_score=importance_score,
            consolidation_count=1,
            related_memories=related_memories or [],
            metadata=metadata or {}
        )
        
        # Store in vector store
        vector_metadata = {
            **memory.to_dict(),
            "memory_id": memory_id
        }
        
        self.vector_store.add_memory(
            content=f"{memory.summary}\n\n{memory.content}",
            metadata=vector_metadata,
            memory_type="long_term"
        )
        
        # Update index
        self._memory_index[memory_id] = memory
        
        # Find and link related memories
        if not related_memories:
            self._find_related_memories(memory)
        
        return memory_id
    
    def retrieve(
        self,
        query: str,
        k: int = 5,
        category: Optional[str] = None,
        min_importance: Optional[float] = None
    ) -> List[Tuple[LongTermMemoryItem, float]]:
        """Retrieve relevant memories"""
        # Build filter
        filter_dict = {}
        if category:
            filter_dict["category"] = category
        if min_importance:
            filter_dict["importance_score"] = {"$gte": min_importance}
        
        # Search using hybrid search
        results = self.hybrid_search.search(
            query=query,
            k=k,
            filter_dict=filter_dict
        )
        
        # Convert to memory items
        memory_results = []
        for doc, score in results:
            memory_data = doc.metadata
            if "memory_id" in memory_data:
                memory = self._memory_index.get(memory_data["memory_id"])
                if memory:
                    memory_results.append((memory, score))
        
        return memory_results
    
    def get_by_category(self, category: str, limit: int = 10) -> List[LongTermMemoryItem]:
        """Get memories by category"""
        memories = [
            m for m in self._memory_index.values()
            if m.category == category
        ]
        
        # Sort by importance and recency
        memories.sort(
            key=lambda m: (m.importance_score, m.timestamp),
            reverse=True
        )
        
        return memories[:limit]
    
    def get_related(self, memory_id: str, depth: int = 1) -> List[LongTermMemoryItem]:
        """Get related memories up to specified depth"""
        if memory_id not in self._memory_index:
            return []
        
        visited = set()
        to_visit = [(memory_id, 0)]
        related = []
        
        while to_visit:
            current_id, current_depth = to_visit.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
                
            visited.add(current_id)
            
            if current_id in self._memory_index:
                memory = self._memory_index[current_id]
                if current_id != memory_id:
                    related.append(memory)
                
                # Add related memories to visit
                for related_id in memory.related_memories:
                    if related_id not in visited:
                        to_visit.append((related_id, current_depth + 1))
        
        return related
    
    def update_importance(self, memory_id: str, new_importance: float):
        """Update memory importance score"""
        if memory_id in self._memory_index:
            memory = self._memory_index[memory_id]
            memory.importance_score = new_importance
            
            # Update in vector store metadata
            self.vector_store.update_memory(
                memory_id,
                content=f"{memory.summary}\n\n{memory.content}",
                metadata=memory.to_dict()
            )
    
    def forget(self, memory_id: str) -> bool:
        """Remove a memory from long-term storage"""
        if memory_id in self._memory_index:
            del self._memory_index[memory_id]
            # Note: Vector store deletion is limited
            return True
        return False
    
    def _should_consolidate(self, memory: MemoryItem) -> bool:
        """Determine if a short-term memory should be consolidated"""
        # High priority memories always consolidated
        if memory.priority.value >= MemoryPriority.HIGH.value:
            return True
        
        # Frequently accessed memories
        if memory.access_count >= self.consolidation_threshold:
            return True
        
        # Recent important interactions
        age = datetime.now() - memory.timestamp
        if age.total_seconds() < 3600 and memory.priority == MemoryPriority.MEDIUM:
            return True
        
        return False
    
    def _calculate_importance(self, memory: MemoryItem) -> float:
        """Calculate importance score for a memory"""
        # Base score from priority
        priority_scores = {
            MemoryPriority.LOW: 0.25,
            MemoryPriority.MEDIUM: 0.5,
            MemoryPriority.HIGH: 0.75,
            MemoryPriority.CRITICAL: 1.0
        }
        
        base_score = priority_scores.get(memory.priority, 0.5)
        
        # Boost for access patterns
        access_boost = min(memory.access_count * 0.1, 0.3)
        
        # Recency factor
        age_hours = (datetime.now() - memory.timestamp).total_seconds() / 3600
        recency_factor = 1.0 / (1.0 + age_hours / 24)  # Decay over days
        
        # Combine factors
        importance = base_score + access_boost
        importance *= (0.7 + 0.3 * recency_factor)  # Weighted by recency
        
        return min(importance, 1.0)
    
    def _categorize_memory(self, content: str) -> str:
        """Categorize memory based on content"""
        content_lower = content.lower()
        
        # Simple keyword-based categorization
        # In production, use NLP/classification
        if any(word in content_lower for word in ["prefer", "like", "want", "wish"]):
            return "preference"
        elif any(word in content_lower for word in ["task", "todo", "remind", "schedule"]):
            return "task"
        elif any(word in content_lower for word in ["fact", "know", "learn", "information"]):
            return "fact"
        elif any(word in content_lower for word in ["person", "people", "friend", "family"]):
            return "relationship"
        elif any(word in content_lower for word in ["did", "was", "went", "happened"]):
            return "experience"
        else:
            return "conversation"
    
    def _find_related_memories(self, memory: LongTermMemoryItem):
        """Find and link related memories"""
        # Search for similar memories
        results = self.vector_store.search_memories(
            query=memory.summary,
            k=5,
            memory_type="long_term"
        )
        
        # Link related memories (excluding self)
        for doc, score in results:
            if "memory_id" in doc.metadata:
                related_id = doc.metadata["memory_id"]
                if related_id != memory.id and score > 0.7:
                    memory.related_memories.append(related_id)
                    
                    # Bidirectional linking
                    if related_id in self._memory_index:
                        related_memory = self._memory_index[related_id]
                        if memory.id not in related_memory.related_memories:
                            related_memory.related_memories.append(memory.id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get long-term memory statistics"""
        if not self._memory_index:
            return {
                "total_memories": 0,
                "categories": {},
                "average_importance": 0.0
            }
        
        category_counts = {}
        for category in self.categories:
            category_counts[category] = sum(
                1 for m in self._memory_index.values()
                if m.category == category
            )
        
        total_importance = sum(m.importance_score for m in self._memory_index.values())
        
        return {
            "total_memories": len(self._memory_index),
            "categories": category_counts,
            "average_importance": total_importance / len(self._memory_index),
            "vector_store_stats": self.vector_store.get_statistics(),
            "total_relationships": sum(
                len(m.related_memories) for m in self._memory_index.values()
            ) // 2  # Bidirectional links counted once
        }