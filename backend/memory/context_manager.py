"""
Context Manager for Enhanced Memory Retrieval

This module manages the context window for the LLM, allowing it to access
full transcripts and past conversations naturally.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
from memory.transcript_store import TranscriptStore
from memory.episodic_store import EpisodicStore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class ContextManager:
    """Manages context window for LLM with full transcript access"""
    
    def __init__(
        self,
        transcript_store: Optional[TranscriptStore] = None,
        episodic_store: Optional[EpisodicStore] = None,
        max_context_tokens: int = 100000,  # Claude 3 supports 200k, leaving room
        prioritize_recent: bool = True
    ):
        self.transcript_store = transcript_store
        self.episodic_store = episodic_store
        self.max_context_tokens = max_context_tokens
        self.prioritize_recent = prioritize_recent
        
        # Token estimation (rough)
        self.avg_chars_per_token = 4
        
    def build_context(
        self,
        query: str,
        session_id: Optional[str] = None,
        include_transcripts: bool = True,
        include_episodes: bool = True,
        max_transcripts: int = 5,
        max_episodes: int = 10
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for the LLM
        
        Returns:
            Dict containing:
            - relevant_transcripts: Full transcript records
            - recent_episodes: Recent conversation episodes
            - semantic_matches: Semantically similar content
            - context_summary: Summary of available context
        """
        context = {
            "relevant_transcripts": [],
            "recent_episodes": [],
            "semantic_matches": [],
            "context_summary": "",
            "total_tokens": 0
        }
        
        token_budget = self.max_context_tokens
        
        # 1. Get current session's episode if available
        if session_id and self.episodic_store:
            current_episodes = self._get_session_episodes(session_id, limit=3)
            for episode in current_episodes:
                tokens = self._estimate_tokens(json.dumps(episode))
                if token_budget - tokens > 0:
                    context["recent_episodes"].append(episode)
                    token_budget -= tokens
        
        # 2. Search for semantically relevant transcripts
        if include_transcripts and self.transcript_store:
            # Search for relevant transcripts
            transcript_results = self.transcript_store.search_transcripts(
                query, 
                limit=max_transcripts * 2  # Get more, then filter
            )
            
            for transcript, score in transcript_results:
                if len(context["relevant_transcripts"]) >= max_transcripts:
                    break
                    
                # Include full transcript if within token budget
                transcript_dict = transcript.to_dict()
                tokens = self._estimate_tokens(transcript_dict["transcript"])
                
                if token_budget - tokens > 10000:  # Keep 10k buffer
                    context["relevant_transcripts"].append({
                        "id": transcript_dict["id"],
                        "title": transcript_dict["title"],
                        "url": transcript_dict["url"],
                        "relevance_score": score,
                        "full_transcript": transcript_dict["transcript"],
                        "action_plan": transcript_dict["action_plan"],
                        "created_at": transcript_dict["created_at"]
                    })
                    token_budget -= tokens
        
        # 3. Get recent conversation episodes
        if include_episodes and self.episodic_store:
            recent_episodes = self._get_recent_episodes(
                limit=max_episodes,
                days_back=7
            )
            
            for episode in recent_episodes:
                if episode["id"] not in [e.get("id") for e in context["recent_episodes"]]:
                    tokens = self._estimate_tokens(json.dumps(episode))
                    if token_budget - tokens > 5000:  # Keep 5k buffer
                        context["recent_episodes"].append(episode)
                        token_budget -= tokens
        
        # 4. Add semantic matches from both sources
        semantic_results = self._search_semantic_matches(query, limit=10)
        for match in semantic_results:
            tokens = self._estimate_tokens(match["content"])
            if token_budget - tokens > 2000:
                context["semantic_matches"].append(match)
                token_budget -= tokens
        
        # 5. Generate context summary
        context["context_summary"] = self._generate_context_summary(context)
        context["total_tokens"] = self.max_context_tokens - token_budget
        
        return context
    
    def _get_session_episodes(self, session_id: str, limit: int = 3) -> List[Dict]:
        """Get episodes from current session"""
        episodes = []
        try:
            session_dir = Path(f"data/memory/episodes/session_{session_id}")
            if session_dir.exists():
                episode_files = sorted(
                    session_dir.glob("episode_*.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )[:limit]
                
                for file in episode_files:
                    with open(file, 'r') as f:
                        episodes.append(json.load(f))
        except Exception as e:
            print(f"Error loading session episodes: {e}")
        
        return episodes
    
    def _get_recent_episodes(self, limit: int = 10, days_back: int = 7) -> List[Dict]:
        """Get recent episodes across all sessions"""
        episodes = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            episodes_dir = Path("data/memory/episodes")
            if episodes_dir.exists():
                all_episodes = []
                
                # Collect all episode files
                for session_dir in episodes_dir.iterdir():
                    if session_dir.is_dir() and session_dir.name.startswith("session_"):
                        for episode_file in session_dir.glob("episode_*.json"):
                            if episode_file.stat().st_mtime > cutoff_date.timestamp():
                                with open(episode_file, 'r') as f:
                                    episode = json.load(f)
                                    all_episodes.append(episode)
                
                # Sort by start time and limit
                all_episodes.sort(
                    key=lambda e: e.get("start_time", ""),
                    reverse=True
                )
                episodes = all_episodes[:limit]
                
        except Exception as e:
            print(f"Error loading recent episodes: {e}")
        
        return episodes
    
    def _search_semantic_matches(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for semantic matches across all memory stores"""
        matches = []
        
        # Search in transcript store's vector DB
        if self.transcript_store and hasattr(self.transcript_store, 'long_term_memory'):
            try:
                results = self.transcript_store.long_term_memory.retrieve(query, k=limit)
                for doc, score in results:
                    matches.append({
                        "source": "transcript",
                        "content": doc,
                        "score": score,
                        "type": "semantic_match"
                    })
            except Exception as e:
                print(f"Error searching transcripts: {e}")
        
        return matches
    
    def _estimate_tokens(self, content: Any) -> int:
        """Estimate token count for content"""
        if isinstance(content, dict):
            content = json.dumps(content)
        elif not isinstance(content, str):
            content = str(content)
        
        return len(content) // self.avg_chars_per_token
    
    def _generate_context_summary(self, context: Dict) -> str:
        """Generate a summary of available context"""
        summary_parts = []
        
        if context["relevant_transcripts"]:
            summary_parts.append(
                f"Found {len(context['relevant_transcripts'])} relevant video transcripts: " +
                ", ".join([t["title"] for t in context["relevant_transcripts"]])
            )
        
        if context["recent_episodes"]:
            summary_parts.append(
                f"Loaded {len(context['recent_episodes'])} recent conversation episodes"
            )
        
        if context["semantic_matches"]:
            summary_parts.append(
                f"Found {len(context['semantic_matches'])} semantic matches"
            )
        
        return " | ".join(summary_parts) if summary_parts else "No relevant context found"
    
    def format_for_prompt(self, context: Dict) -> str:
        """Format context for inclusion in LLM prompt"""
        formatted_parts = []
        
        # Add context summary
        if context["context_summary"]:
            formatted_parts.append(f"Available Context: {context['context_summary']}\n")
        
        # Add relevant transcripts
        if context["relevant_transcripts"]:
            formatted_parts.append("=== RELEVANT VIDEO TRANSCRIPTS ===")
            for transcript in context["relevant_transcripts"]:
                formatted_parts.append(f"\n📹 {transcript['title']}")
                formatted_parts.append(f"URL: {transcript['url']}")
                formatted_parts.append(f"Relevance: {transcript['relevance_score']:.2f}")
                formatted_parts.append(f"\nTranscript:\n{transcript['full_transcript'][:500]}...")
                if transcript.get('action_plan'):
                    formatted_parts.append(f"\nAction Plan:\n{transcript['action_plan']}")
                formatted_parts.append("-" * 80)
        
        # Add recent episodes
        if context["recent_episodes"]:
            formatted_parts.append("\n=== RECENT CONVERSATIONS ===")
            for episode in context["recent_episodes"][:3]:  # Limit to most recent
                formatted_parts.append(f"\n💬 {episode['title']}")
                formatted_parts.append(f"Type: {episode['type']}")
                
                # Extract key exchanges
                for event in episode.get('events', [])[:5]:
                    if event['event_type'] in ['user_message', 'assistant_response']:
                        role = "User" if event['event_type'] == 'user_message' else "Assistant"
                        content = event['data'].get('content', '')[:200]
                        formatted_parts.append(f"{role}: {content}...")
                
                formatted_parts.append("-" * 80)
        
        return "\n".join(formatted_parts)