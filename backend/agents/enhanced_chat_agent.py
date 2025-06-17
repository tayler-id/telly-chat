"""Enhanced chat agent with memory and workflow support (backward compatible)"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
from datetime import datetime

# Keep original imports
from .chat_agent import ChatAgent

# New feature imports with graceful fallback
try:
    from ..memory import ShortTermMemory, LongTermMemory, EpisodicMemory
    from ..memory.vector_store import VectorStoreConfig
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("Warning: Memory modules not available. Install required dependencies.")

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
        self.memory_enabled = enable_memory and MEMORY_AVAILABLE
        self.workflows_enabled = enable_workflows and WORKFLOW_AVAILABLE
        self.threads_enabled = enable_threads and THREADS_AVAILABLE
        
        # Memory components
        if self.memory_enabled:
            self._init_memory(memory_config or {})
        else:
            self.short_term_memory = None
            self.long_term_memory = None
            self.episodic_memory = None
        
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
        
        # Episodic memory
        self.episodic_memory = EpisodicMemory(
            long_term_memory=self.long_term_memory
        )
    
    async def chat(
        self,
        message: str,
        history: Optional[List] = None,
        stream: bool = True,
        thread_id: Optional[str] = None,
        use_memory: bool = True,
        use_workflow: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Enhanced chat with optional memory and workflow support
        Falls back to original behavior if features are disabled
        """
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
            # Search relevant memories
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
            # Use original chat method
            # Add context to message if available
            enhanced_message = message
            if context_additions:
                enhanced_message = "\n".join(context_additions) + "\n\n" + message
            
            async for chunk in super().chat(enhanced_message, history, stream):
                # Store in memory if enabled
                if self.memory_enabled and chunk.get("type") == "text":
                    self._update_memory(message, chunk.get("content", ""))
                
                yield chunk
    
    async def _search_memories(self, query: str) -> List[Any]:
        """Search relevant memories"""
        memories = []
        
        # Search short-term memory
        st_memories = self.short_term_memory.search(query, limit=3)
        memories.extend([("short_term", m) for m in st_memories])
        
        # Search long-term memory
        lt_results = self.long_term_memory.retrieve(query, k=3)
        memories.extend([("long_term", m) for m, score in lt_results])
        
        return memories
    
    def _format_memories(self, memories: List[Any]) -> str:
        """Format memories for context"""
        formatted = []
        
        for memory_type, memory in memories:
            if memory_type == "short_term":
                formatted.append(f"- {memory.content[:100]}...")
            else:  # long_term
                formatted.append(f"- {memory.summary}")
        
        return "\n".join(formatted)
    
    def _update_memory(self, user_message: str, assistant_response: str):
        """Update memory with conversation"""
        if not self.memory_enabled:
            return
        
        # Add to short-term memory
        self.short_term_memory.add(
            content=f"User: {user_message}",
            priority=self.short_term_memory.MemoryPriority.HIGH
        )
        
        self.short_term_memory.add(
            content=f"Assistant: {assistant_response}",
            priority=self.short_term_memory.MemoryPriority.MEDIUM
        )
        
        # Consider consolidation to long-term
        # (This would typically be done periodically)
    
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
            "base_functional": True
        }
    
    async def export_memory(self) -> Dict[str, Any]:
        """Export memory state"""
        if not self.memory_enabled:
            return {"error": "Memory not enabled"}
        
        return {
            "short_term": self.short_term_memory.export(),
            "long_term": self.long_term_memory.get_statistics(),
            "episodic": self.episodic_memory.get_statistics()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.threads_enabled and self.thread_manager:
            await self.thread_manager.stop_cleanup()
        
        if self.workflows_enabled and self.workflow_orchestrator:
            await self.workflow_orchestrator.stop()