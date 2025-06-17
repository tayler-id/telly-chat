"""Thread manager for handling multiple conversation contexts"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid
from enum import Enum
import asyncio
from collections import deque

from ..memory.short_term import ShortTermMemory, MemoryPriority
from ..memory.episodic import EpisodicMemory, Episode, EpisodeType


class ThreadStatus(Enum):
    """Thread status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ThreadPriority(Enum):
    """Thread priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ThreadContext:
    """Context information for a thread"""
    topic: str
    participants: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_thread_id: Optional[str] = None
    child_thread_ids: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    
    def add_tag(self, tag: str):
        """Add a tag to the thread"""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str):
        """Remove a tag from the thread"""
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if thread has a tag"""
        return tag in self.tags


@dataclass
class ConversationThread:
    """Represents a conversation thread with isolated context"""
    id: str
    title: str
    status: ThreadStatus
    priority: ThreadPriority
    context: ThreadContext
    created_at: datetime
    updated_at: datetime
    
    # Memory components
    short_term_memory: ShortTermMemory
    episode_id: Optional[str] = None
    
    # Message history
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Thread metrics
    message_count: int = 0
    last_active: datetime = field(default_factory=datetime.now)
    inactive_duration: Optional[timedelta] = None
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the thread"""
        message = {
            "id": f"msg_{uuid.uuid4().hex}",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        self.message_count += 1
        self.last_active = datetime.now()
        self.updated_at = datetime.now()
        
        # Add to short-term memory
        priority = MemoryPriority.HIGH if role == "user" else MemoryPriority.MEDIUM
        self.short_term_memory.add(
            content=content,
            priority=priority,
            metadata={
                "role": role,
                "thread_id": self.id,
                **message["metadata"]
            }
        )
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from the thread"""
        return self.messages[-limit:]
    
    def get_context_summary(self) -> str:
        """Generate a summary of the thread context"""
        summary_parts = [
            f"Thread: {self.title}",
            f"Topic: {self.context.topic}",
            f"Messages: {self.message_count}",
            f"Status: {self.status.value}",
            f"Tags: {', '.join(self.context.tags)}" if self.context.tags else "Tags: None"
        ]
        
        # Add recent context from memory
        recent_memories = self.short_term_memory.get_recent(3)
        if recent_memories:
            summary_parts.append("Recent context:")
            for memory in recent_memories:
                summary_parts.append(f"- {memory.content[:50]}...")
        
        return "\n".join(summary_parts)
    
    def pause(self):
        """Pause the thread"""
        self.status = ThreadStatus.PAUSED
        self.inactive_duration = timedelta(0)
        self.updated_at = datetime.now()
    
    def resume(self):
        """Resume the thread"""
        if self.status == ThreadStatus.PAUSED:
            self.status = ThreadStatus.ACTIVE
            self.inactive_duration = None
            self.updated_at = datetime.now()
    
    def complete(self):
        """Mark thread as completed"""
        self.status = ThreadStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def archive(self):
        """Archive the thread"""
        self.status = ThreadStatus.ARCHIVED
        self.updated_at = datetime.now()


class ThreadManager:
    """
    Manages multiple conversation threads
    
    Features:
    - Thread creation and lifecycle management
    - Context isolation between threads
    - Thread merging and splitting
    - Priority-based thread switching
    - Automatic archival of inactive threads
    """
    
    def __init__(
        self,
        max_active_threads: int = 10,
        episodic_memory: Optional[EpisodicMemory] = None,
        auto_archive_after: timedelta = timedelta(hours=24)
    ):
        self.max_active_threads = max_active_threads
        self.episodic_memory = episodic_memory
        self.auto_archive_after = auto_archive_after
        
        # Thread storage
        self.threads: Dict[str, ConversationThread] = {}
        self.active_thread_ids: deque = deque(maxlen=max_active_threads)
        self.current_thread_id: Optional[str] = None
        
        # Thread relationships
        self.thread_graph: Dict[str, Set[str]] = {}  # thread_id -> related_thread_ids
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    def create_thread(
        self,
        title: str,
        topic: str,
        participants: List[str],
        priority: ThreadPriority = ThreadPriority.NORMAL,
        parent_thread_id: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Create a new conversation thread"""
        # Check active thread limit
        if len(self.active_thread_ids) >= self.max_active_threads:
            # Archive least recently used thread
            lru_thread_id = self.active_thread_ids[0]
            self.archive_thread(lru_thread_id)
        
        # Create thread
        thread_id = f"thread_{uuid.uuid4().hex}"
        
        context = ThreadContext(
            topic=topic,
            participants=participants,
            parent_thread_id=parent_thread_id,
            tags=tags or set()
        )
        
        thread = ConversationThread(
            id=thread_id,
            title=title,
            status=ThreadStatus.ACTIVE,
            priority=priority,
            context=context,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            short_term_memory=ShortTermMemory(capacity=100)
        )
        
        # Store thread
        self.threads[thread_id] = thread
        self.active_thread_ids.append(thread_id)
        
        # Update parent-child relationships
        if parent_thread_id and parent_thread_id in self.threads:
            parent_thread = self.threads[parent_thread_id]
            parent_thread.context.child_thread_ids.append(thread_id)
        
        # Start episode if episodic memory available
        if self.episodic_memory:
            episode_id = self.episodic_memory.start_episode(
                title=f"Thread: {title}",
                episode_type=EpisodeType.CONVERSATION,
                participants=participants,
                context={
                    "thread_id": thread_id,
                    "topic": topic,
                    "parent_thread_id": parent_thread_id
                }
            )
            thread.episode_id = episode_id
        
        return thread_id
    
    def switch_thread(self, thread_id: str) -> bool:
        """Switch to a different thread"""
        if thread_id not in self.threads:
            return False
        
        thread = self.threads[thread_id]
        
        # Check if thread is active
        if thread.status != ThreadStatus.ACTIVE:
            # Resume if paused
            if thread.status == ThreadStatus.PAUSED:
                thread.resume()
            else:
                return False
        
        # Update current thread
        self.current_thread_id = thread_id
        
        # Update active thread order
        if thread_id in self.active_thread_ids:
            self.active_thread_ids.remove(thread_id)
        self.active_thread_ids.append(thread_id)
        
        return True
    
    def get_current_thread(self) -> Optional[ConversationThread]:
        """Get the current active thread"""
        if self.current_thread_id:
            return self.threads.get(self.current_thread_id)
        return None
    
    def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """Get a specific thread"""
        return self.threads.get(thread_id)
    
    def list_active_threads(self) -> List[ConversationThread]:
        """List all active threads"""
        return [
            self.threads[tid] for tid in self.active_thread_ids
            if tid in self.threads and self.threads[tid].status == ThreadStatus.ACTIVE
        ]
    
    def search_threads(
        self,
        query: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        status: Optional[ThreadStatus] = None,
        limit: int = 10
    ) -> List[ConversationThread]:
        """Search threads by criteria"""
        results = []
        
        for thread in self.threads.values():
            # Status filter
            if status and thread.status != status:
                continue
            
            # Tag filter
            if tags and not tags.intersection(thread.context.tags):
                continue
            
            # Query filter
            if query:
                query_lower = query.lower()
                # Search in title, topic, and recent messages
                if (query_lower not in thread.title.lower() and 
                    query_lower not in thread.context.topic.lower()):
                    
                    # Search in messages
                    found = False
                    for msg in thread.messages[-10:]:  # Check last 10 messages
                        if query_lower in msg["content"].lower():
                            found = True
                            break
                    
                    if not found:
                        continue
            
            results.append(thread)
        
        # Sort by last active
        results.sort(key=lambda t: t.last_active, reverse=True)
        
        return results[:limit]
    
    def merge_threads(
        self,
        thread_ids: List[str],
        new_title: str,
        new_topic: Optional[str] = None
    ) -> str:
        """Merge multiple threads into one"""
        if len(thread_ids) < 2:
            raise ValueError("Need at least 2 threads to merge")
        
        # Get threads
        threads_to_merge = []
        for tid in thread_ids:
            thread = self.threads.get(tid)
            if not thread:
                raise ValueError(f"Thread {tid} not found")
            threads_to_merge.append(thread)
        
        # Sort by creation time
        threads_to_merge.sort(key=lambda t: t.created_at)
        
        # Create merged thread
        all_participants = set()
        all_tags = set()
        for thread in threads_to_merge:
            all_participants.update(thread.context.participants)
            all_tags.update(thread.context.tags)
        
        merged_thread_id = self.create_thread(
            title=new_title,
            topic=new_topic or threads_to_merge[0].context.topic,
            participants=list(all_participants),
            priority=max(t.priority for t in threads_to_merge),
            tags=all_tags
        )
        
        merged_thread = self.threads[merged_thread_id]
        
        # Merge messages and memories
        all_messages = []
        for thread in threads_to_merge:
            for msg in thread.messages:
                msg_copy = msg.copy()
                msg_copy["original_thread_id"] = thread.id
                all_messages.append(msg_copy)
        
        # Sort by timestamp
        all_messages.sort(key=lambda m: m["timestamp"])
        
        # Add to merged thread
        for msg in all_messages:
            merged_thread.add_message(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata", {})
            )
        
        # Archive original threads
        for thread in threads_to_merge:
            thread.archive()
            thread.context.metadata["merged_into"] = merged_thread_id
        
        # Update thread relationships
        self.thread_graph[merged_thread_id] = set(thread_ids)
        
        return merged_thread_id
    
    def split_thread(
        self,
        thread_id: str,
        split_point: int,
        new_title: str,
        new_topic: str
    ) -> str:
        """Split a thread into two at a specific message index"""
        original_thread = self.threads.get(thread_id)
        if not original_thread:
            raise ValueError(f"Thread {thread_id} not found")
        
        if split_point >= len(original_thread.messages):
            raise ValueError("Split point beyond message count")
        
        # Create new thread
        new_thread_id = self.create_thread(
            title=new_title,
            topic=new_topic,
            participants=original_thread.context.participants,
            priority=original_thread.priority,
            parent_thread_id=thread_id,
            tags=original_thread.context.tags.copy()
        )
        
        new_thread = self.threads[new_thread_id]
        
        # Move messages after split point to new thread
        messages_to_move = original_thread.messages[split_point:]
        for msg in messages_to_move:
            new_thread.add_message(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata", {})
            )
        
        # Remove moved messages from original thread
        original_thread.messages = original_thread.messages[:split_point]
        original_thread.message_count = len(original_thread.messages)
        original_thread.updated_at = datetime.now()
        
        # Update relationships
        self.thread_graph[thread_id] = self.thread_graph.get(thread_id, set())
        self.thread_graph[thread_id].add(new_thread_id)
        self.thread_graph[new_thread_id] = {thread_id}
        
        return new_thread_id
    
    def archive_thread(self, thread_id: str) -> bool:
        """Archive a thread"""
        thread = self.threads.get(thread_id)
        if not thread:
            return False
        
        thread.archive()
        
        # Remove from active threads
        if thread_id in self.active_thread_ids:
            self.active_thread_ids.remove(thread_id)
        
        # End episode if exists
        if thread.episode_id and self.episodic_memory:
            self.episodic_memory.end_episode(
                thread.episode_id,
                outcome="archived",
                success_metrics={
                    "message_count": thread.message_count,
                    "duration_hours": (datetime.now() - thread.created_at).total_seconds() / 3600
                }
            )
        
        # Switch to another thread if this was current
        if self.current_thread_id == thread_id:
            self.current_thread_id = None
            # Switch to most recent active thread
            for tid in reversed(self.active_thread_ids):
                if self.threads[tid].status == ThreadStatus.ACTIVE:
                    self.current_thread_id = tid
                    break
        
        return True
    
    async def start_cleanup(self):
        """Start background cleanup task"""
        if not self.is_running:
            self.is_running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup(self):
        """Stop background cleanup task"""
        self.is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Background task to clean up inactive threads"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check for inactive threads
                for thread in list(self.threads.values()):
                    if thread.status == ThreadStatus.ACTIVE:
                        # Check inactivity
                        inactive_time = current_time - thread.last_active
                        
                        if inactive_time > self.auto_archive_after:
                            # Auto-archive inactive thread
                            self.archive_thread(thread.id)
                    
                    elif thread.status == ThreadStatus.PAUSED:
                        # Update inactive duration
                        if thread.inactive_duration is not None:
                            thread.inactive_duration = current_time - thread.last_active
                
                # Sleep for a while before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                # Log error but continue
                print(f"Error in cleanup loop: {e}")
    
    def get_thread_relationships(self, thread_id: str) -> Dict[str, List[str]]:
        """Get relationships for a thread"""
        thread = self.threads.get(thread_id)
        if not thread:
            return {}
        
        relationships = {
            "parent": [thread.context.parent_thread_id] if thread.context.parent_thread_id else [],
            "children": thread.context.child_thread_ids,
            "related": list(self.thread_graph.get(thread_id, set()))
        }
        
        return relationships
    
    def export_thread(self, thread_id: str) -> Dict[str, Any]:
        """Export a thread's data"""
        thread = self.threads.get(thread_id)
        if not thread:
            return {}
        
        return {
            "id": thread.id,
            "title": thread.title,
            "status": thread.status.value,
            "priority": thread.priority.value,
            "context": {
                "topic": thread.context.topic,
                "participants": thread.context.participants,
                "tags": list(thread.context.tags),
                "parent_thread_id": thread.context.parent_thread_id,
                "child_thread_ids": thread.context.child_thread_ids
            },
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
            "message_count": thread.message_count,
            "messages": thread.messages,
            "memory_stats": thread.short_term_memory.get_statistics()
        }