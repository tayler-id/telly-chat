"""Enhanced chat agent with memory and workflow support (backward compatible)"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
from datetime import datetime

# Keep original imports
from .chat_agent import ChatAgent

# New feature imports with graceful fallback
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from memory.short_term import ShortTermMemory, MemoryPriority
    from memory.long_term import LongTermMemory
    from memory.episodic import EpisodicMemory, EpisodeType
    from memory.episodic_store import EpisodicStore
    from memory.vector_store import VectorStoreConfig
    from memory.transcript_store import TranscriptStore
    from memory.context_manager import ContextManager
    from prompts.memory_aware_prompt import get_memory_prompt
    MEMORY_AVAILABLE = True
except ImportError as e:
    MEMORY_AVAILABLE = False
    print(f"Warning: Memory modules not available. {e}")

try:
    from ..workflows import WorkflowEngine, WorkflowOrchestrator
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
    print("Warning: Workflow modules not available. Install required dependencies.")

try:
    from ..threads import ThreadManager
    THREADS_AVAILABLE = True
except ImportError:
    THREADS_AVAILABLE = False
    print("Warning: Threading modules not available. Install required dependencies.")


class EnhancedChatAgent(ChatAgent):
    """
    Enhanced chat agent with optional memory, workflow, and threading support
    Maintains backward compatibility with original ChatAgent
    """
    
    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: Optional[str] = None,
        enable_memory: bool = False,
        enable_workflows: bool = False,
        enable_threads: bool = False,
        memory_config: Optional[Dict[str, Any]] = None
    ):
        # Initialize base agent
        super().__init__(model_provider, model_name)
        
        # Initialize enhanced features if available and enabled
        self.memory_capability = enable_memory and MEMORY_AVAILABLE
        self.workflows_enabled = enable_workflows and WORKFLOW_AVAILABLE
        self.threads_enabled = enable_threads and THREADS_AVAILABLE
        
        # Memory components - always initialize if capability exists
        if self.memory_capability:
            self._init_memory(memory_config or {})
            self.memory_enabled = False  # Start with memory disabled (can be toggled at runtime)
            # Initialize transcript store
            self.transcript_store = TranscriptStore(
                storage_dir=(memory_config or {}).get("transcript_dir", "./data/memory/transcripts")
            )
            
            # Initialize context manager
            self.context_manager = ContextManager(
                transcript_store=self.transcript_store,
                episodic_store=self.episodic_memory if isinstance(self.episodic_memory, EpisodicStore) else None,
                max_context_tokens=100000  # Conservative for Claude
            )
        else:
            self.memory_enabled = False
            self.short_term_memory = None
            self.long_term_memory = None
            self.episodic_memory = None
            self.transcript_store = None
            self.context_manager = None
        
        # Workflow components
        if self.workflows_enabled:
            self.workflow_orchestrator = WorkflowOrchestrator()
            self.registered_workflows = {}
        else:
            self.workflow_orchestrator = None
            self.registered_workflows = None
        
        # Threading components
        if self.threads_enabled:
            self.thread_manager = ThreadManager(
                episodic_memory=self.episodic_memory if self.memory_enabled else None
            )
        else:
            self.thread_manager = None
    
    def _init_memory(self, config: Dict[str, Any]):
        """Initialize memory components"""
        # Short-term memory
        self.short_term_memory = ShortTermMemory(
            capacity=config.get("short_term_capacity", 100)
        )
        
        # Long-term memory with vector store
        vector_config = VectorStoreConfig(
            store_type=config.get("vector_store_type", "faiss"),
            embedding_provider=config.get("embedding_provider", "openai"),
            persist_directory=config.get("persist_directory", "./memory/vectors")
        )
        
        self.long_term_memory = LongTermMemory(vector_config)
        
        # Episodic memory with persistent storage
        self.episodic_memory = EpisodicStore(
            storage_dir=config.get("episode_dir", "./memory/episodes"),
            long_term_memory=self.long_term_memory
        )
        
        # Current episode tracking
        self.current_episode_id = None
    
    async def chat(
        self,
        message: str,
        history: Optional[List] = None,
        stream: bool = True,
        thread_id: Optional[str] = None,
        use_memory: bool = True,
        use_workflow: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Enhanced chat with optional memory and workflow support
        Falls back to original behavior if features are disabled
        """
        # Handle episodic memory
        if self.memory_enabled and use_memory and self.episodic_memory:
            # Start or continue episode
            if not self.current_episode_id or session_id:
                # Determine episode type from message
                episode_type = self._determine_episode_type(message)
                
                # Start new episode
                self.current_episode_id = self.episodic_memory.start_episode(
                    title=f"Chat: {message[:50]}...",
                    episode_type=episode_type,
                    participants=["user", "assistant"],
                    context={
                        "session_id": session_id,
                        "thread_id": thread_id,
                        "initial_message": message
                    },
                    session_id=session_id
                )
            
            # Record user message event
            self.episodic_memory.add_event(
                self.current_episode_id,
                event_type="user_message",
                actor="user",
                action="sent_message",
                data={"content": message},
                impact_score=0.5
            )
        
        # Handle threading
        if self.threads_enabled and thread_id:
            thread = self.thread_manager.get_thread(thread_id)
            if not thread:
                # Create new thread
                thread_id = self.thread_manager.create_thread(
                    title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    topic=message[:50],
                    participants=["user", "assistant"]
                )
            
            # Add message to thread
            thread = self.thread_manager.get_thread(thread_id)
            thread.add_message("user", message)
        
        # Handle memory retrieval
        context_additions = []
        if self.memory_enabled and use_memory:
            if self.context_manager:
                # Use context manager for comprehensive retrieval
                context = self.context_manager.build_context(
                    query=message,
                    session_id=session_id,
                    include_transcripts=True,
                    include_episodes=True
                )
                
                # Format context for prompt
                formatted_context = self.context_manager.format_for_prompt(context)
                if formatted_context:
                    context_additions.append(formatted_context)
                    
                print(f"[CONTEXT] Loaded {context['total_tokens']} tokens of context")
                print(f"[CONTEXT] {context['context_summary']}")
            else:
                # Fallback to simple memory search
                relevant_memories = await self._search_memories(message)
                if relevant_memories:
                    context_additions.append(
                        f"Relevant context from memory:\n{self._format_memories(relevant_memories)}"
                    )
        
        # Handle workflow execution
        if self.workflows_enabled and use_workflow and use_workflow in self.registered_workflows:
            # Execute via workflow
            async for chunk in self._execute_workflow_chat(
                workflow_name=use_workflow,
                message=message,
                context_additions=context_additions
            ):
                yield chunk
        else:
            # Use original chat method with memory-aware system prompt if needed
            # Add context to message if available
            enhanced_message = message
            
            # If we have context, prepend it with clear separation
            if context_additions:
                enhanced_message = "\n".join(context_additions) + "\n\n---\n\nUser Query: " + message
            
            # Accumulate response for memory storage
            full_response = ""
            
            # Override system prompt if memory is enabled
            original_prompt = None
            if self.memory_enabled and context_additions and MEMORY_AVAILABLE:
                # Temporarily update the agent's system prompt
                original_prompt = self.agent.agent.prompt.messages[0].content
                memory_prompt = get_memory_prompt(has_context=True)
                self.agent.agent.prompt.messages[0] = ("system", memory_prompt)
            
            async for chunk in super().chat(enhanced_message, history, stream):
                # Accumulate text chunks
                if chunk.get("type") == "text":
                    full_response += chunk.get("content", "")
                
                yield chunk
            
            # Restore original prompt if it was changed
            if original_prompt is not None:
                self.agent.agent.prompt.messages[0] = ("system", original_prompt)
            
            # Store complete conversation in memory after streaming is done
            if self.memory_enabled and use_memory and full_response:
                self._update_memory(message, full_response)
                
                # Record assistant response in episode
                if self.episodic_memory and self.current_episode_id:
                    self.episodic_memory.add_event(
                        self.current_episode_id,
                        event_type="assistant_response",
                        actor="assistant",
                        action="sent_response",
                        data={
                            "content": full_response,
                            "memories_used": len(context_additions) if context_additions else 0,
                            "context_tokens": context.get("total_tokens", 0) if 'context' in locals() else 0
                        },
                        impact_score=0.6
                    )
    
    async def _search_memories(self, query: str) -> List[Any]:
        """Search relevant memories"""
        print(f"[MEMORY] Searching for: {query[:100]}...")
        memories = []
        
        # Search short-term memory
        st_memories = self.short_term_memory.search(query, limit=3)
        memories.extend([("short_term", m) for m in st_memories])
        print(f"[MEMORY] Found {len(st_memories)} short-term memories")
        
        # Search long-term memory
        try:
            lt_results = self.long_term_memory.retrieve(query, k=3)
            memories.extend([("long_term", m) for m, score in lt_results])
            print(f"[MEMORY] Found {len(lt_results)} long-term memories")
        except Exception as e:
            print(f"[MEMORY] Long-term search error: {e}")
        
        # Search transcript store if available
        if self.transcript_store:
            try:
                transcript_results = self.transcript_store.search_transcripts(query, limit=2)
                for transcript, score in transcript_results:
                    memories.append(("transcript", transcript))
                print(f"[MEMORY] Found {len(transcript_results)} related transcripts")
            except Exception as e:
                print(f"[MEMORY] Transcript search error: {e}")
        
        # Log what was found
        if memories:
            print("[MEMORY] Retrieved memories:")
            for mem_type, mem in memories[:2]:  # Show first 2
                if mem_type == "short_term":
                    content = mem.content
                elif mem_type == "long_term":
                    content = mem.summary
                else:  # transcript
                    content = f"{mem.title} - {mem.summary[:50]}"
                print(f"  [{mem_type}] {content[:80]}...")
        
        return memories
    
    def _format_memories(self, memories: List[Any]) -> str:
        """Format memories for context"""
        formatted = []
        
        for memory_type, memory in memories:
            if memory_type == "short_term":
                formatted.append(f"- {memory.content[:100]}...")
            elif memory_type == "long_term":
                formatted.append(f"- {memory.summary}")
            else:  # transcript
                formatted.append(f"- Transcript: {memory.title} ({memory.url})\n  Action Plan: {memory.action_plan[:200]}...")
        
        return "\n".join(formatted)
    
    def _update_memory(self, user_message: str, assistant_response: str):
        """Update memory with conversation"""
        if not self.memory_enabled:
            return
        
        print(f"[MEMORY] Storing conversation:")
        print(f"  User: {user_message[:100]}...")
        print(f"  Assistant: {assistant_response[:100]}...")
        
        # Add to short-term memory
        self.short_term_memory.add(
            content=f"User: {user_message}",
            priority=MemoryPriority.HIGH
        )
        
        self.short_term_memory.add(
            content=f"Assistant: {assistant_response}",
            priority=MemoryPriority.MEDIUM
        )
        
        # Log memory stats
        stats = self.short_term_memory.get_statistics()
        print(f"[MEMORY] Stats: {stats['total_memories']} memories, {stats['utilization']:.1%} capacity")
        
        # Check for consolidation to long-term
        self._check_memory_consolidation()
    
    def _check_memory_consolidation(self):
        """Check if any memories should be consolidated to long-term storage"""
        if not self.long_term_memory:
            return
        
        print("[MEMORY] Checking for consolidation...")
        
        # Get all memories from short-term
        all_memories = self.short_term_memory.get_all()
        
        for memory in all_memories:
            # Skip if already consolidated
            if memory.metadata.get("consolidated", False):
                continue
                
            # Consolidate if accessed 3+ times or high priority
            if (memory.access_count >= 3 or 
                memory.priority == MemoryPriority.HIGH or
                memory.priority == MemoryPriority.CRITICAL):
                
                # Extract key information for long-term storage
                content = memory.content
                
                # Determine category
                category = "conversation"
                if "name" in content.lower() or "i am" in content.lower():
                    category = "personal_info"
                elif "prefer" in content.lower() or "like" in content.lower():
                    category = "preferences"
                
                # Create summary
                summary = content[:100] + "..." if len(content) > 100 else content
                
                # Store in long-term memory
                try:
                    memory_id = self.long_term_memory.store(
                        content=content,
                        summary=summary,
                        category=category,
                        importance_score=0.8 if memory.priority.value >= 3 else 0.5,
                        metadata={
                            "source": "short_term_consolidation",
                            "original_id": memory.id,
                            "access_count": memory.access_count,
                            "timestamp": memory.timestamp.isoformat()
                        }
                    )
                    print(f"[MEMORY] Consolidated to long-term: {summary[:50]}... (ID: {memory_id})")
                    
                    # Update access count to prevent re-consolidation
                    memory.metadata["consolidated"] = True
                    
                except Exception as e:
                    print(f"[MEMORY] Consolidation error: {e}")
    
    async def _execute_workflow_chat(
        self,
        workflow_name: str,
        message: str,
        context_additions: List[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute chat via workflow"""
        # This is a simplified implementation
        # In practice, you'd integrate workflow execution properly
        
        workflow_id = self.workflow_orchestrator.schedule_workflow(
            workflow_name=workflow_name,
            initial_context={
                "user_message": message,
                "context": "\n".join(context_additions)
            }
        )
        
        # Wait for workflow completion
        # (In practice, this would stream results)
        yield {
            "type": "text",
            "content": f"Executing workflow '{workflow_name}'..."
        }
    
    def register_workflow(self, workflow: 'WorkflowEngine'):
        """Register a workflow for use in chat"""
        if self.workflows_enabled:
            self.workflow_orchestrator.register_workflow(workflow)
            self.registered_workflows[workflow.name] = workflow
    
    def get_features_status(self) -> Dict[str, bool]:
        """Get status of enhanced features"""
        return {
            "memory": self.memory_enabled,
            "workflows": self.workflows_enabled,
            "threads": self.threads_enabled,
            "base_functional": True,
            "transcript_store": self.transcript_store is not None
        }
    
    async def export_memory(self) -> Dict[str, Any]:
        """Export memory state"""
        if not self.memory_enabled:
            return {"error": "Memory not enabled"}
        
        return {
            "short_term": self.short_term_memory.export(),
            "long_term": self.long_term_memory.get_statistics(),
            "episodic": self.episodic_memory.get_statistics(),
            "current_episode": self.current_episode_id
        }
    
    def _determine_episode_type(self, message: str) -> EpisodeType:
        """Determine episode type from message content"""
        message_lower = message.lower()
        
        # Check for task-related keywords
        if any(word in message_lower for word in ["do", "create", "build", "fix", "implement"]):
            return EpisodeType.TASK_COMPLETION
        
        # Check for problem-solving keywords
        elif any(word in message_lower for word in ["error", "issue", "problem", "debug", "solve"]):
            return EpisodeType.PROBLEM_SOLVING
        
        # Check for learning keywords
        elif any(word in message_lower for word in ["learn", "teach", "explain", "understand", "how"]):
            return EpisodeType.LEARNING
        
        # Check for creative keywords
        elif any(word in message_lower for word in ["design", "imagine", "create", "idea"]):
            return EpisodeType.CREATIVE
        
        # Default to conversation
        return EpisodeType.CONVERSATION
    
    def end_current_episode(self, outcome: str = "completed", success_metrics: Optional[Dict[str, float]] = None):
        """End the current episode"""
        if self.episodic_memory and self.current_episode_id:
            self.episodic_memory.end_episode(
                self.current_episode_id,
                outcome=outcome,
                success_metrics=success_metrics
            )
            self.current_episode_id = None
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if not self.episodic_memory:
            return []
        
        episodes = self.episodic_memory.get_session_episodes(session_id)
        history = []
        
        for episode in episodes:
            conversation = self.episodic_memory.get_conversation_history(episode.id)
            history.extend(conversation)
        
        return history
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.threads_enabled and self.thread_manager:
            await self.thread_manager.stop_cleanup()
        
        if self.workflows_enabled and self.workflow_orchestrator:
            await self.workflow_orchestrator.stop()