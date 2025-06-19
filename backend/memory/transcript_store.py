"""Transcript storage and retrieval system for YouTube videos"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from .long_term import LongTermMemory
from .vector_store import VectorStoreConfig


@dataclass
class TranscriptRecord:
    """Record of a saved transcript"""
    id: str
    url: str
    title: str
    transcript: str
    action_plan: str
    summary: str
    duration: Optional[str] = None
    saved_at: datetime = None
    accessed_count: int = 0
    last_accessed: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.saved_at is None:
            self.saved_at = datetime.now()
        if self.last_accessed is None:
            self.last_accessed = self.saved_at
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "transcript": self.transcript,
            "action_plan": self.action_plan,
            "summary": self.summary,
            "duration": self.duration,
            "saved_at": self.saved_at.isoformat(),
            "accessed_count": self.accessed_count,
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptRecord':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            url=data["url"],
            title=data["title"],
            transcript=data["transcript"],
            action_plan=data["action_plan"],
            summary=data["summary"],
            duration=data.get("duration"),
            saved_at=datetime.fromisoformat(data["saved_at"]),
            accessed_count=data.get("accessed_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            metadata=data.get("metadata", {})
        )


class TranscriptStore:
    """
    Store and retrieve YouTube transcripts with semantic search
    
    Features:
    - Save full transcripts and action plans
    - Semantic search across all transcripts
    - Track access patterns
    - Integration with long-term memory
    """
    
    def __init__(
        self,
        storage_dir: str = "./transcripts",
        vector_config: Optional[VectorStoreConfig] = None
    ):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # Initialize vector store for semantic search
        if vector_config is None:
            vector_config = VectorStoreConfig(
                store_type="faiss",
                embedding_provider="openai",
                persist_directory=os.path.join(storage_dir, "vectors")
            )
        
        self.long_term_memory = LongTermMemory(vector_config)
        
        # Local index for fast lookup
        self.index_file = os.path.join(storage_dir, "index.json")
        self._load_index()
    
    def _load_index(self):
        """Load transcript index from disk"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}
    
    def _save_index(self):
        """Save transcript index to disk"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def _generate_id(self, url: str) -> str:
        """Generate unique ID for transcript"""
        return f"transcript_{hashlib.md5(url.encode()).hexdigest()[:12]}"
    
    def save_transcript(
        self,
        url: str,
        title: str,
        transcript: str,
        action_plan: str,
        summary: Optional[str] = None,
        duration: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save a transcript and index it for search"""
        
        # Generate ID
        transcript_id = self._generate_id(url)
        
        # Create summary if not provided
        if not summary:
            # Take first 500 chars of transcript as summary
            summary = transcript[:500] + "..." if len(transcript) > 500 else transcript
        
        # Create record
        record = TranscriptRecord(
            id=transcript_id,
            url=url,
            title=title,
            transcript=transcript,
            action_plan=action_plan,
            summary=summary,
            duration=duration,
            metadata=metadata or {}
        )
        
        # Save to disk
        record_file = os.path.join(self.storage_dir, f"{transcript_id}.json")
        with open(record_file, 'w') as f:
            json.dump(record.to_dict(), f, indent=2)
        
        # Update index
        self.index[transcript_id] = {
            "url": url,
            "title": title,
            "saved_at": record.saved_at.isoformat(),
            "file": record_file
        }
        self._save_index()
        
        # Index in vector store for semantic search
        # Create searchable content combining title, summary, and action plan
        searchable_content = f"""
Title: {title}
URL: {url}
Summary: {summary}

Action Plan:
{action_plan}

Transcript Preview:
{transcript[:1000]}
"""
        
        # Store in long-term memory
        try:
            self.long_term_memory.store(
                content=searchable_content,
                summary=f"{title} - {url}",
                category="youtube_transcript",
                importance_score=0.8,
                metadata={
                    "transcript_id": transcript_id,
                    "url": url,
                    "title": title,
                    "duration": duration,
                    "has_action_plan": bool(action_plan),
                    "transcript_length": len(transcript),
                    "saved_at": record.saved_at.isoformat()
                }
            )
            print(f"[TRANSCRIPT] Indexed transcript: {title}")
        except Exception as e:
            print(f"[TRANSCRIPT] Error indexing transcript: {e}")
        
        return transcript_id
    
    def get_transcript(self, transcript_id: str) -> Optional[TranscriptRecord]:
        """Retrieve a specific transcript"""
        if transcript_id not in self.index:
            return None
        
        # Load from disk
        record_file = self.index[transcript_id]["file"]
        if not os.path.exists(record_file):
            return None
        
        with open(record_file, 'r') as f:
            data = json.load(f)
        
        record = TranscriptRecord.from_dict(data)
        
        # Update access tracking
        record.accessed_count += 1
        record.last_accessed = datetime.now()
        
        # Save updated record
        with open(record_file, 'w') as f:
            json.dump(record.to_dict(), f, indent=2)
        
        return record
    
    def search_transcripts(
        self,
        query: str,
        limit: int = 5
    ) -> List[Tuple[TranscriptRecord, float]]:
        """Search transcripts semantically"""
        
        # Search in vector store
        try:
            results = self.long_term_memory.retrieve(
                query=query,
                k=limit,
                category="youtube_transcript"
            )
            
            # Load full transcript records
            transcript_results = []
            for memory, score in results:
                metadata = memory.metadata
                transcript_id = metadata.get("transcript_id")
                
                if transcript_id:
                    record = self.get_transcript(transcript_id)
                    if record:
                        transcript_results.append((record, score))
            
            return transcript_results
            
        except Exception as e:
            print(f"[TRANSCRIPT] Search error: {e}")
            return []
    
    def get_recent_transcripts(self, limit: int = 10) -> List[TranscriptRecord]:
        """Get most recently saved transcripts"""
        # Sort by saved_at
        sorted_ids = sorted(
            self.index.items(),
            key=lambda x: x[1]["saved_at"],
            reverse=True
        )[:limit]
        
        records = []
        for transcript_id, _ in sorted_ids:
            record = self.get_transcript(transcript_id)
            if record:
                records.append(record)
        
        return records
    
    def get_transcript_by_url(self, url: str) -> Optional[TranscriptRecord]:
        """Get transcript by YouTube URL"""
        transcript_id = self._generate_id(url)
        return self.get_transcript(transcript_id)
    
    def get_related_transcripts(
        self,
        transcript_id: str,
        limit: int = 3
    ) -> List[Tuple[TranscriptRecord, float]]:
        """Find transcripts related to a given one"""
        record = self.get_transcript(transcript_id)
        if not record:
            return []
        
        # Search using the transcript's title and summary
        query = f"{record.title} {record.summary[:200]}"
        results = self.search_transcripts(query, limit=limit+1)
        
        # Remove the original transcript from results
        return [(r, s) for r, s in results if r.id != transcript_id][:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transcript store statistics"""
        total_transcripts = len(self.index)
        
        if total_transcripts == 0:
            return {
                "total_transcripts": 0,
                "total_size_mb": 0,
                "most_accessed": None,
                "recent_saves": []
            }
        
        # Calculate total size
        total_size = 0
        most_accessed = None
        max_access = 0
        
        for transcript_id in self.index:
            record = self.get_transcript(transcript_id)
            if record:
                # Estimate size (rough calculation)
                size = len(record.transcript) + len(record.action_plan)
                total_size += size
                
                if record.accessed_count > max_access:
                    max_access = record.accessed_count
                    most_accessed = {
                        "id": record.id,
                        "title": record.title,
                        "url": record.url,
                        "accessed_count": record.accessed_count
                    }
        
        return {
            "total_transcripts": total_transcripts,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "most_accessed": most_accessed,
            "recent_saves": [
                {"id": tid, **info} 
                for tid, info in sorted(
                    self.index.items(),
                    key=lambda x: x[1]["saved_at"],
                    reverse=True
                )[:5]
            ]
        }
    
    def export_for_training(self) -> List[Dict[str, Any]]:
        """Export all transcripts in a format suitable for training/tuning"""
        training_data = []
        
        for transcript_id in self.index:
            record = self.get_transcript(transcript_id)
            if record:
                training_data.append({
                    "url": record.url,
                    "title": record.title,
                    "content": record.transcript,
                    "action_plan": record.action_plan,
                    "summary": record.summary,
                    "metadata": {
                        "duration": record.duration,
                        "accessed_count": record.accessed_count,
                        "saved_at": record.saved_at.isoformat()
                    }
                })
        
        return training_data