"""Episodic memory for storing complete interaction sessions"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import uuid
from enum import Enum

from .short_term import MemoryItem
from .long_term import LongTermMemory


class EpisodeType(Enum):
    """Types of episodes"""
    CONVERSATION = "conversation"
    TASK_COMPLETION = "task_completion"
    LEARNING = "learning"
    PROBLEM_SOLVING = "problem_solving"
    CREATIVE = "creative"


@dataclass
class Episode:
    """Represents a complete interaction episode"""
    id: str
    type: EpisodeType
    title: str
    start_time: datetime
    end_time: Optional[datetime]
    participants: List[str]
    context: Dict[str, Any]
    events: List[Dict[str, Any]] = field(default_factory=list)
    outcome: Optional[str] = None
    success_metrics: Dict[str, float] = field(default_factory=dict)
    memories_created: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate episode duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if episode is still active"""
        return self.end_time is None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "participants": self.participants,
            "context": self.context,
            "events": self.events,
            "outcome": self.outcome,
            "success_metrics": self.success_metrics,
            "memories_created": self.memories_created,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        return cls(
            id=data["id"],
            type=EpisodeType(data["type"]),
            title=data["title"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data["end_time"] else None,
            participants=data["participants"],
            context=data["context"],
            events=data.get("events", []),
            outcome=data.get("outcome"),
            success_metrics=data.get("success_metrics", {}),
            memories_created=data.get("memories_created", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class EpisodeEvent:
    """Individual event within an episode"""
    timestamp: datetime
    event_type: str
    actor: str
    action: str
    data: Dict[str, Any]
    impact_score: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "data": self.data,
            "impact_score": self.impact_score
        }


class EpisodicMemory:
    """
    Episodic memory for storing and retrieving complete interaction episodes
    
    Features:
    - Session recording and playback
    - Pattern recognition across episodes
    - Success/failure analysis
    - Temporal organization
    """
    
    def __init__(
        self,
        long_term_memory: Optional[LongTermMemory] = None,
        max_active_episodes: int = 5,
        episode_timeout: timedelta = timedelta(hours=2)
    ):
        self.long_term_memory = long_term_memory
        self.max_active_episodes = max_active_episodes
        self.episode_timeout = episode_timeout
        
        # Episode storage
        self._episodes: Dict[str, Episode] = {}
        self._active_episodes: List[str] = []
        
        # Pattern tracking
        self._episode_patterns: Dict[str, List[str]] = {
            "successful_tasks": [],
            "failed_tasks": [],
            "learning_sequences": [],
            "repeated_questions": []
        }
    
    def start_episode(
        self,
        title: str,
        episode_type: EpisodeType,
        participants: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new episode"""
        # Check active episode limit
        if len(self._active_episodes) >= self.max_active_episodes:
            # Close oldest episode
            oldest_id = self._active_episodes[0]
            self.end_episode(oldest_id, outcome="auto_closed")
        
        # Create new episode
        episode_id = f"episode_{uuid.uuid4().hex}"
        episode = Episode(
            id=episode_id,
            type=episode_type,
            title=title,
            start_time=datetime.now(),
            end_time=None,
            participants=participants,
            context=context or {},
            events=[],
            metadata={"auto_close_timeout": self.episode_timeout.total_seconds()}
        )
        
        # Store episode
        self._episodes[episode_id] = episode
        self._active_episodes.append(episode_id)
        
        # Record start event
        self.add_event(
            episode_id,
            event_type="episode_start",
            actor="system",
            action="started_episode",
            data={"title": title, "type": episode_type.value}
        )
        
        return episode_id
    
    def add_event(
        self,
        episode_id: str,
        event_type: str,
        actor: str,
        action: str,
        data: Dict[str, Any],
        impact_score: float = 0.5
    ) -> bool:
        """Add an event to an active episode"""
        if episode_id not in self._episodes:
            return False
        
        episode = self._episodes[episode_id]
        if not episode.is_active:
            return False
        
        # Create event
        event = EpisodeEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            actor=actor,
            action=action,
            data=data,
            impact_score=impact_score
        )
        
        # Add to episode
        episode.events.append(event.to_dict())
        
        # Update patterns if significant
        if impact_score > 0.7:
            self._update_patterns(episode, event)
        
        return True
    
    def end_episode(
        self,
        episode_id: str,
        outcome: Optional[str] = None,
        success_metrics: Optional[Dict[str, float]] = None
    ) -> bool:
        """End an active episode"""
        if episode_id not in self._episodes:
            return False
        
        episode = self._episodes[episode_id]
        if not episode.is_active:
            return False
        
        # Set end time and outcome
        episode.end_time = datetime.now()
        episode.outcome = outcome
        if success_metrics:
            episode.success_metrics.update(success_metrics)
        
        # Remove from active episodes
        if episode_id in self._active_episodes:
            self._active_episodes.remove(episode_id)
        
        # Record end event
        self.add_event(
            episode_id,
            event_type="episode_end",
            actor="system",
            action="ended_episode",
            data={
                "outcome": outcome,
                "duration": episode.duration.total_seconds() if episode.duration else 0,
                "event_count": len(episode.events)
            }
        )
        
        # Consolidate to long-term memory if available
        if self.long_term_memory:
            self._consolidate_episode(episode)
        
        # Analyze patterns
        self._analyze_episode_patterns(episode)
        
        return True
    
    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Retrieve a specific episode"""
        return self._episodes.get(episode_id)
    
    def get_active_episodes(self) -> List[Episode]:
        """Get all active episodes"""
        return [
            self._episodes[eid] for eid in self._active_episodes
            if eid in self._episodes
        ]
    
    def search_episodes(
        self,
        query: Optional[str] = None,
        episode_type: Optional[EpisodeType] = None,
        participant: Optional[str] = None,
        min_success: Optional[float] = None,
        limit: int = 10
    ) -> List[Episode]:
        """Search episodes by criteria"""
        results = []
        
        for episode in self._episodes.values():
            # Type filter
            if episode_type and episode.type != episode_type:
                continue
            
            # Participant filter
            if participant and participant not in episode.participants:
                continue
            
            # Success filter
            if min_success:
                avg_success = sum(episode.success_metrics.values()) / len(episode.success_metrics) if episode.success_metrics else 0
                if avg_success < min_success:
                    continue
            
            # Query filter (search in title and events)
            if query:
                query_lower = query.lower()
                match = False
                
                if query_lower in episode.title.lower():
                    match = True
                else:
                    # Search in events
                    for event in episode.events:
                        if query_lower in json.dumps(event).lower():
                            match = True
                            break
                
                if not match:
                    continue
            
            results.append(episode)
        
        # Sort by recency
        results.sort(key=lambda e: e.start_time, reverse=True)
        
        return results[:limit]
    
    def get_similar_episodes(self, episode_id: str, limit: int = 5) -> List[Episode]:
        """Find episodes similar to a given episode"""
        if episode_id not in self._episodes:
            return []
        
        target_episode = self._episodes[episode_id]
        similar = []
        
        for eid, episode in self._episodes.items():
            if eid == episode_id:
                continue
            
            # Calculate similarity score
            similarity = 0.0
            
            # Same type
            if episode.type == target_episode.type:
                similarity += 0.3
            
            # Similar duration
            if episode.duration and target_episode.duration:
                duration_diff = abs(episode.duration.total_seconds() - target_episode.duration.total_seconds())
                if duration_diff < 300:  # Within 5 minutes
                    similarity += 0.2
            
            # Common participants
            common_participants = set(episode.participants) & set(target_episode.participants)
            if common_participants:
                similarity += 0.2 * (len(common_participants) / len(set(episode.participants + target_episode.participants)))
            
            # Similar outcomes
            if episode.outcome == target_episode.outcome:
                similarity += 0.3
            
            if similarity > 0.3:
                similar.append((episode, similarity))
        
        # Sort by similarity
        similar.sort(key=lambda x: x[1], reverse=True)
        
        return [ep for ep, _ in similar[:limit]]
    
    def cleanup_stale_episodes(self):
        """Clean up stale active episodes"""
        current_time = datetime.now()
        to_close = []
        
        for episode_id in self._active_episodes:
            if episode_id in self._episodes:
                episode = self._episodes[episode_id]
                age = current_time - episode.start_time
                
                if age > self.episode_timeout:
                    to_close.append(episode_id)
        
        # Close stale episodes
        for episode_id in to_close:
            self.end_episode(episode_id, outcome="timeout")
    
    def _consolidate_episode(self, episode: Episode):
        """Consolidate episode to long-term memory"""
        # Create episode summary
        summary = self._generate_episode_summary(episode)
        
        # Store in long-term memory
        memory_id = self.long_term_memory.store(
            content=json.dumps(episode.to_dict(), indent=2),
            summary=summary,
            category="experience",
            importance_score=self._calculate_episode_importance(episode),
            metadata={
                "episode_id": episode.id,
                "episode_type": episode.type.value,
                "duration": episode.duration.total_seconds() if episode.duration else 0
            }
        )
        
        episode.memories_created.append(memory_id)
    
    def _generate_episode_summary(self, episode: Episode) -> str:
        """Generate a summary of an episode"""
        summary_parts = [
            f"Episode: {episode.title}",
            f"Type: {episode.type.value}",
            f"Duration: {episode.duration}" if episode.duration else "Ongoing",
            f"Participants: {', '.join(episode.participants)}",
            f"Events: {len(episode.events)}",
            f"Outcome: {episode.outcome or 'Unknown'}"
        ]
        
        return " | ".join(summary_parts)
    
    def _calculate_episode_importance(self, episode: Episode) -> float:
        """Calculate importance score for an episode"""
        importance = 0.5
        
        # Success metrics
        if episode.success_metrics:
            avg_success = sum(episode.success_metrics.values()) / len(episode.success_metrics)
            importance = 0.3 + (0.4 * avg_success)
        
        # Event count and impact
        if episode.events:
            high_impact_events = sum(1 for e in episode.events if e.get("impact_score", 0) > 0.7)
            impact_ratio = high_impact_events / len(episode.events)
            importance += 0.2 * impact_ratio
        
        # Episode type importance
        type_importance = {
            EpisodeType.TASK_COMPLETION: 0.1,
            EpisodeType.PROBLEM_SOLVING: 0.15,
            EpisodeType.LEARNING: 0.2,
            EpisodeType.CREATIVE: 0.1,
            EpisodeType.CONVERSATION: 0.05
        }
        
        importance += type_importance.get(episode.type, 0.05)
        
        return min(importance, 1.0)
    
    def _update_patterns(self, episode: Episode, event: EpisodeEvent):
        """Update pattern tracking based on events"""
        # Task success/failure patterns
        if event.event_type == "task_complete":
            if event.data.get("success", False):
                self._episode_patterns["successful_tasks"].append(episode.id)
            else:
                self._episode_patterns["failed_tasks"].append(episode.id)
        
        # Learning patterns
        elif event.event_type == "concept_learned":
            self._episode_patterns["learning_sequences"].append(episode.id)
        
        # Question patterns
        elif event.event_type == "question_asked":
            question = event.data.get("question", "")
            # Check for similar questions in recent episodes
            for pattern_episode_id in self._episode_patterns["repeated_questions"][-10:]:
                if pattern_episode_id in self._episodes:
                    pattern_episode = self._episodes[pattern_episode_id]
                    for pattern_event in pattern_episode.events:
                        if pattern_event.get("event_type") == "question_asked":
                            if self._similar_questions(question, pattern_event.get("data", {}).get("question", "")):
                                self._episode_patterns["repeated_questions"].append(episode.id)
                                break
    
    def _similar_questions(self, q1: str, q2: str) -> bool:
        """Check if two questions are similar (simple implementation)"""
        # Simple word overlap check
        words1 = set(q1.lower().split())
        words2 = set(q2.lower().split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        
        return (overlap / total) > 0.6
    
    def _analyze_episode_patterns(self, episode: Episode):
        """Analyze patterns after episode completion"""
        # Find repeated patterns
        if episode.id in self._episode_patterns["failed_tasks"]:
            # Check for repeated failures
            similar_failures = [
                eid for eid in self._episode_patterns["failed_tasks"]
                if eid != episode.id and eid in self._episodes
                and self._episodes[eid].type == episode.type
            ]
            
            if len(similar_failures) >= 2:
                # Pattern detected: repeated failures in same type
                episode.metadata["pattern"] = "repeated_failure"
                episode.metadata["similar_episodes"] = similar_failures[-2:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get episodic memory statistics"""
        total_episodes = len(self._episodes)
        active_episodes = len(self._active_episodes)
        
        type_distribution = {}
        for episode_type in EpisodeType:
            type_distribution[episode_type.value] = sum(
                1 for e in self._episodes.values()
                if e.type == episode_type
            )
        
        avg_duration = 0
        completed_episodes = [e for e in self._episodes.values() if not e.is_active]
        if completed_episodes:
            total_duration = sum(
                e.duration.total_seconds() for e in completed_episodes
                if e.duration
            )
            avg_duration = total_duration / len(completed_episodes)
        
        return {
            "total_episodes": total_episodes,
            "active_episodes": active_episodes,
            "type_distribution": type_distribution,
            "average_duration_seconds": avg_duration,
            "patterns": {
                k: len(v) for k, v in self._episode_patterns.items()
            }
        }