"""Service for transcript operations"""

from typing import List, Dict, Any, Optional
from agents.enhanced_chat_agent import EnhancedChatAgent


async def save_transcript(
    agent: EnhancedChatAgent,
    url: str,
    title: str,
    transcript: str,
    action_plan: str,
    summary: Optional[str] = None,
    duration: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Save a transcript using the agent's transcript store"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    try:
        transcript_id = agent.transcript_store.save_transcript(
            url=url,
            title=title,
            transcript=transcript,
            action_plan=action_plan,
            summary=summary,
            duration=duration,
            metadata=metadata
        )
        
        return {
            "success": True,
            "transcript_id": transcript_id,
            "message": f"Transcript saved: {title}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_transcript(
    agent: EnhancedChatAgent,
    transcript_id: str
) -> Dict[str, Any]:
    """Get a specific transcript"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    record = agent.transcript_store.get_transcript(transcript_id)
    if not record:
        return {"error": "Transcript not found"}
    
    return {
        "success": True,
        "transcript": record.to_dict()
    }


async def search_transcripts(
    agent: EnhancedChatAgent,
    query: str,
    limit: int = 5
) -> Dict[str, Any]:
    """Search transcripts semantically"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    try:
        results = agent.transcript_store.search_transcripts(query, limit)
        
        return {
            "success": True,
            "results": [
                {
                    "transcript": record.to_dict(),
                    "score": score
                }
                for record, score in results
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_recent_transcripts(
    agent: EnhancedChatAgent,
    limit: int = 10
) -> Dict[str, Any]:
    """Get recent transcripts"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    records = agent.transcript_store.get_recent_transcripts(limit)
    
    return {
        "success": True,
        "transcripts": [record.to_dict() for record in records]
    }


async def get_transcript_by_url(
    agent: EnhancedChatAgent,
    url: str
) -> Dict[str, Any]:
    """Get transcript by YouTube URL"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    record = agent.transcript_store.get_transcript_by_url(url)
    if not record:
        return {"error": "Transcript not found for this URL"}
    
    return {
        "success": True,
        "transcript": record.to_dict()
    }


async def get_related_transcripts(
    agent: EnhancedChatAgent,
    transcript_id: str,
    limit: int = 3
) -> Dict[str, Any]:
    """Get transcripts related to a given one"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    try:
        results = agent.transcript_store.get_related_transcripts(transcript_id, limit)
        
        return {
            "success": True,
            "related": [
                {
                    "transcript": record.to_dict(),
                    "score": score
                }
                for record, score in results
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_transcript_stats(
    agent: EnhancedChatAgent
) -> Dict[str, Any]:
    """Get transcript store statistics"""
    
    if not agent.transcript_store:
        return {"error": "Transcript store not available"}
    
    stats = agent.transcript_store.get_statistics()
    
    return {
        "success": True,
        "stats": stats
    }