"""Enhanced episodic memory with persistent storage"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .episodic import EpisodicMemory, Episode, EpisodeType
from .long_term import LongTermMemory


class EpisodicStore(EpisodicMemory):
    """
    Extended episodic memory with persistent storage
    Saves complete conversation sessions for later retrieval
    """
    
    def __init__(
        self,
        storage_dir: str = "./memory/episodes",
        long_term_memory: Optional[LongTermMemory] = None,
        **kwargs
    ):
        super().__init__(long_term_memory=long_term_memory, **kwargs)
        
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # Episode index file
        self.index_file = os.path.join(storage_dir, "episode_index.json")
        self._load_index()
        
        # Load existing episodes
        self._load_episodes()
    
    def _load_index(self):
        """Load episode index from disk"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.episode_index = json.load(f)
        else:
            self.episode_index = {
                "episodes": {},
                "sessions": {},
                "patterns": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
    
    def _save_index(self):
        """Save episode index to disk"""
        self.episode_index["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.episode_index, f, indent=2)
    
    def _load_episodes(self):
        """Load episodes from disk"""
        for episode_id, info in self.episode_index["episodes"].items():
            if "file" in info and os.path.exists(info["file"]):
                try:
                    with open(info["file"], 'r') as f:
                        episode_data = json.load(f)
                        episode = Episode.from_dict(episode_data)
                        self._episodes[episode_id] = episode
                        
                        # Re-add to active if still active
                        if episode.is_active:
                            self._active_episodes.append(episode_id)
                except Exception as e:
                    print(f"[EPISODIC] Error loading episode {episode_id}: {e}")
    
    def start_episode(
        self,
        title: str,
        episode_type: EpisodeType,
        participants: List[str],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Start a new episode with session tracking"""
        # Call parent method
        episode_id = super().start_episode(title, episode_type, participants, context)
        
        # Add session tracking
        if session_id:
            self._episodes[episode_id].metadata["session_id"] = session_id
            
            # Track in session index
            if session_id not in self.episode_index["sessions"]:
                self.episode_index["sessions"][session_id] = []
            self.episode_index["sessions"][session_id].append(episode_id)
        
        # Save to disk
        self._save_episode(episode_id)
        
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
        """Add event and persist"""
        result = super().add_event(
            episode_id, event_type, actor, action, data, impact_score
        )
        
        if result:
            # Save updated episode
            self._save_episode(episode_id)
        
        return result
    
    def end_episode(
        self,
        episode_id: str,
        outcome: Optional[str] = None,
        success_metrics: Optional[Dict[str, float]] = None
    ) -> bool:
        """End episode and persist"""
        result = super().end_episode(episode_id, outcome, success_metrics)
        
        if result:
            # Save final state
            self._save_episode(episode_id)
            
            # Update patterns in index
            episode = self._episodes[episode_id]
            if "pattern" in episode.metadata:
                pattern = episode.metadata["pattern"]
                if pattern not in self.episode_index["patterns"]:
                    self.episode_index["patterns"][pattern] = []
                self.episode_index["patterns"][pattern].append(episode_id)
            
            self._save_index()
        
        return result
    
    def _save_episode(self, episode_id: str):
        """Save episode to disk"""
        if episode_id not in self._episodes:
            return
        
        episode = self._episodes[episode_id]
        
        # Create filename
        filename = f"episode_{episode.start_time.strftime('%Y%m%d_%H%M%S')}_{episode_id}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        # Save episode data
        with open(filepath, 'w') as f:
            json.dump(episode.to_dict(), f, indent=2)
        
        # Update index
        self.episode_index["episodes"][episode_id] = {
            "file": filepath,
            "title": episode.title,
            "type": episode.type.value,
            "start_time": episode.start_time.isoformat(),
            "end_time": episode.end_time.isoformat() if episode.end_time else None,
            "is_active": episode.is_active,
            "participants": episode.participants,
            "event_count": len(episode.events)
        }
        
        self._save_index()
    
    def get_session_episodes(self, session_id: str) -> List[Episode]:
        """Get all episodes from a specific session"""
        episode_ids = self.episode_index["sessions"].get(session_id, [])
        episodes = []
        
        for episode_id in episode_ids:
            episode = self.get_episode(episode_id)
            if episode:
                episodes.append(episode)
        
        # Sort by start time
        episodes.sort(key=lambda e: e.start_time)
        
        return episodes
    
    def search_episodes_by_content(
        self,
        query: str,
        limit: int = 10
    ) -> List[Episode]:
        """Enhanced search that includes event content"""
        results = []
        query_lower = query.lower()
        
        for episode in self._episodes.values():
            score = 0.0
            
            # Title match
            if query_lower in episode.title.lower():
                score += 0.5
            
            # Event content match
            for event in episode.events:
                event_str = json.dumps(event).lower()
                if query_lower in event_str:
                    score += 0.1
                    
                    # Higher score for specific event types
                    if event.get("event_type") in ["user_message", "assistant_response"]:
                        if query_lower in event.get("data", {}).get("content", "").lower():
                            score += 0.3
            
            # Context match
            context_str = json.dumps(episode.context).lower()
            if query_lower in context_str:
                score += 0.2
            
            if score > 0:
                results.append((episode, score))
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return [ep for ep, _ in results[:limit]]
    
    def get_conversation_history(
        self,
        episode_id: str
    ) -> List[Dict[str, Any]]:
        """Extract conversation history from episode"""
        episode = self.get_episode(episode_id)
        if not episode:
            return []
        
        conversation = []
        
        for event in episode.events:
            if event.get("event_type") == "user_message":
                conversation.append({
                    "role": "user",
                    "content": event.get("data", {}).get("content", ""),
                    "timestamp": event.get("timestamp")
                })
            elif event.get("event_type") == "assistant_response":
                conversation.append({
                    "role": "assistant",
                    "content": event.get("data", {}).get("content", ""),
                    "timestamp": event.get("timestamp")
                })
        
        return conversation
    
    def export_session_for_training(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Export session data in format suitable for training"""
        episodes = self.get_session_episodes(session_id)
        
        session_data = {
            "session_id": session_id,
            "episodes": [],
            "total_duration": 0,
            "conversation_count": 0
        }
        
        for episode in episodes:
            conversation = self.get_conversation_history(episode.id)
            
            episode_data = {
                "episode_id": episode.id,
                "title": episode.title,
                "type": episode.type.value,
                "duration": episode.duration.total_seconds() if episode.duration else 0,
                "conversation": conversation,
                "outcome": episode.outcome,
                "success_metrics": episode.success_metrics
            }
            
            session_data["episodes"].append(episode_data)
            session_data["conversation_count"] += len(conversation)
            if episode.duration:
                session_data["total_duration"] += episode.duration.total_seconds()
        
        return session_data
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Analyze episodes for learning patterns"""
        insights = {
            "total_episodes": len(self._episodes),
            "active_episodes": len(self._active_episodes),
            "patterns_found": {},
            "common_topics": {},
            "success_rate": 0.0,
            "average_episode_duration": 0.0
        }
        
        # Analyze patterns
        for pattern_type, episode_ids in self.episode_index["patterns"].items():
            insights["patterns_found"][pattern_type] = len(episode_ids)
        
        # Calculate success rate
        completed = [e for e in self._episodes.values() if not e.is_active]
        if completed:
            successful = sum(
                1 for e in completed 
                if e.outcome in ["success", "completed", "resolved"]
            )
            insights["success_rate"] = successful / len(completed)
            
            # Average duration
            durations = [
                e.duration.total_seconds() for e in completed 
                if e.duration
            ]
            if durations:
                insights["average_episode_duration"] = sum(durations) / len(durations)
        
        # Extract common topics from titles
        words = {}
        for episode in self._episodes.values():
            for word in episode.title.lower().split():
                if len(word) > 3:  # Skip short words
                    words[word] = words.get(word, 0) + 1
        
        # Top 10 common words
        insights["common_topics"] = dict(
            sorted(words.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return insights