"""Workflow engine for executing complex, stateful workflows"""

from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio
from abc import ABC, abstractmethod

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(Enum):
    """Individual node execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowState:
    """State container for workflow execution"""
    workflow_id: str
    status: WorkflowStatus
    current_node: Optional[str]
    visited_nodes: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    messages: List[BaseMessage] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update(self, **kwargs):
        """Update state fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def add_message(self, message: BaseMessage):
        """Add a message to the conversation"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def set_result(self, node: str, result: Any):
        """Set result for a node"""
        self.results[node] = result
        self.updated_at = datetime.now()
    
    def add_error(self, node: str, error: str, details: Optional[Dict] = None):
        """Add an error"""
        self.errors.append({
            "node": node,
            "error": error,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()


class WorkflowNode(ABC):
    """Abstract base class for workflow nodes"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = NodeStatus.PENDING
        self.retry_count = 0
        self.max_retries = 3
    
    @abstractmethod
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute the node logic"""
        pass
    
    def can_execute(self, state: WorkflowState) -> bool:
        """Check if node can be executed given current state"""
        return True
    
    def should_retry(self) -> bool:
        """Check if node should be retried after failure"""
        return self.retry_count < self.max_retries


class ConditionalNode(WorkflowNode):
    """Node that makes conditional decisions"""
    
    def __init__(
        self,
        name: str,
        condition_fn: Callable[[WorkflowState], str],
        description: str = ""
    ):
        super().__init__(name, description)
        self.condition_fn = condition_fn
    
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute conditional logic and return next node"""
        next_node = self.condition_fn(state)
        return {"next_node": next_node}


class ToolNode(WorkflowNode):
    """Node that executes tools"""
    
    def __init__(
        self,
        name: str,
        tool_executor: ToolExecutor,
        tool_name: str,
        description: str = ""
    ):
        super().__init__(name, description)
        self.tool_executor = tool_executor
        self.tool_name = tool_name
    
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute tool and return result"""
        # Extract tool input from state
        tool_input = state.context.get(f"{self.name}_input", {})
        
        # Execute tool
        result = await self.tool_executor.ainvoke({
            "tool": self.tool_name,
            "tool_input": tool_input
        })
        
        return {"result": result}


class LLMNode(WorkflowNode):
    """Node that interacts with language models"""
    
    def __init__(
        self,
        name: str,
        llm: Any,  # LangChain LLM
        prompt_template: Optional[str] = None,
        description: str = ""
    ):
        super().__init__(name, description)
        self.llm = llm
        self.prompt_template = prompt_template
    
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute LLM call"""
        # Build prompt from template and state
        if self.prompt_template:
            prompt = self.prompt_template.format(**state.context)
        else:
            # Use last message as prompt
            prompt = state.messages[-1].content if state.messages else ""
        
        # Call LLM
        response = await self.llm.ainvoke(prompt)
        
        # Add to messages
        state.add_message(HumanMessage(content=prompt))
        state.add_message(AIMessage(content=response.content))
        
        return {"response": response.content}


class WorkflowEngine:
    """
    Engine for executing complex workflows using LangGraph
    
    Features:
    - State management
    - Conditional branching
    - Error handling and retries
    - Async execution
    - Checkpointing
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.nodes: Dict[str, WorkflowNode] = {}
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None
        
        # Execution tracking
        self.active_workflows: Dict[str, WorkflowState] = {}
        
    def add_node(self, node: WorkflowNode):
        """Add a node to the workflow"""
        self.nodes[node.name] = node
    
    def add_edge(self, from_node: str, to_node: Union[str, Callable]):
        """Add an edge between nodes"""
        if not self.graph:
            raise ValueError("Graph not initialized. Call build() first.")
        
        if callable(to_node):
            # Conditional edge
            self.graph.add_conditional_edges(from_node, to_node)
        else:
            # Direct edge
            self.graph.add_edge(from_node, to_node)
    
    def set_entry_point(self, node: str):
        """Set the entry point for the workflow"""
        if not self.graph:
            raise ValueError("Graph not initialized. Call build() first.")
        
        self.graph.set_entry_point(node)
    
    def build(self):
        """Build the workflow graph"""
        # Initialize graph with state schema
        self.graph = StateGraph(WorkflowState)
        
        # Add nodes to graph
        for node_name, node in self.nodes.items():
            self.graph.add_node(node_name, self._create_node_handler(node))
    
    def compile(self):
        """Compile the workflow graph"""
        if not self.graph:
            raise ValueError("Graph not built. Call build() first.")
        
        self.compiled_graph = self.graph.compile()
    
    async def execute(
        self,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> WorkflowState:
        """Execute the workflow"""
        if not self.compiled_graph:
            raise ValueError("Workflow not compiled. Call compile() first.")
        
        # Create initial state
        workflow_id = workflow_id or f"wf_{uuid.uuid4().hex}"
        state = WorkflowState(
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            current_node=None,
            context=initial_context or {}
        )
        
        # Track active workflow
        self.active_workflows[workflow_id] = state
        state.status = WorkflowStatus.RUNNING
        
        try:
            # Execute workflow
            final_state = await self.compiled_graph.ainvoke(state)
            
            # Update status
            final_state.status = WorkflowStatus.COMPLETED
            
            return final_state
            
        except Exception as e:
            # Handle execution error
            state.status = WorkflowStatus.FAILED
            state.add_error("workflow", str(e))
            raise
            
        finally:
            # Clean up
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    def pause(self, workflow_id: str):
        """Pause a running workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].status = WorkflowStatus.PAUSED
    
    def resume(self, workflow_id: str):
        """Resume a paused workflow"""
        if workflow_id in self.active_workflows:
            state = self.active_workflows[workflow_id]
            if state.status == WorkflowStatus.PAUSED:
                state.status = WorkflowStatus.RUNNING
    
    def cancel(self, workflow_id: str):
        """Cancel a running workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].status = WorkflowStatus.CANCELLED
    
    def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get current state of a workflow"""
        return self.active_workflows.get(workflow_id)
    
    def _create_node_handler(self, node: WorkflowNode) -> Callable:
        """Create async handler for a node"""
        async def handler(state: WorkflowState) -> WorkflowState:
            # Update current node
            state.current_node = node.name
            state.visited_nodes.append(node.name)
            
            # Check if node can execute
            if not node.can_execute(state):
                node.status = NodeStatus.SKIPPED
                return state
            
            # Execute node
            node.status = NodeStatus.RUNNING
            
            try:
                result = await node.execute(state)
                
                # Store result
                state.set_result(node.name, result)
                node.status = NodeStatus.COMPLETED
                
                # Handle special results
                if isinstance(result, dict):
                    # Update context with result
                    state.context.update(result)
                    
                    # Check for next node directive
                    if "next_node" in result:
                        state.metadata["next_node"] = result["next_node"]
                
            except Exception as e:
                # Handle node error
                node.status = NodeStatus.FAILED
                state.add_error(node.name, str(e))
                
                # Retry if applicable
                if node.should_retry():
                    node.retry_count += 1
                    node.status = NodeStatus.PENDING
                    # Re-execute (simplified retry logic)
                    return await handler(state)
                else:
                    raise
            
            return state
        
        return handler


class WorkflowBuilder:
    """Helper class for building workflows"""
    
    def __init__(self, name: str, description: str = ""):
        self.engine = WorkflowEngine(name, description)
        self.current_node = None
    
    def add_llm_node(
        self,
        name: str,
        llm: Any,
        prompt_template: Optional[str] = None
    ) -> 'WorkflowBuilder':
        """Add an LLM node"""
        node = LLMNode(name, llm, prompt_template)
        self.engine.add_node(node)
        
        if self.current_node:
            self.engine.add_edge(self.current_node, name)
        else:
            self.engine.set_entry_point(name)
        
        self.current_node = name
        return self
    
    def add_tool_node(
        self,
        name: str,
        tool_executor: ToolExecutor,
        tool_name: str
    ) -> 'WorkflowBuilder':
        """Add a tool node"""
        node = ToolNode(name, tool_executor, tool_name)
        self.engine.add_node(node)
        
        if self.current_node:
            self.engine.add_edge(self.current_node, name)
        else:
            self.engine.set_entry_point(name)
        
        self.current_node = name
        return self
    
    def add_conditional(
        self,
        name: str,
        condition_fn: Callable[[WorkflowState], str],
        branches: Dict[str, str]
    ) -> 'WorkflowBuilder':
        """Add a conditional branch"""
        node = ConditionalNode(name, condition_fn)
        self.engine.add_node(node)
        
        if self.current_node:
            self.engine.add_edge(self.current_node, name)
        else:
            self.engine.set_entry_point(name)
        
        # Add conditional edges for each branch
        def router(state: WorkflowState) -> str:
            next_node = condition_fn(state)
            return branches.get(next_node, END)
        
        self.engine.add_edge(name, router)
        
        self.current_node = name
        return self
    
    def build(self) -> WorkflowEngine:
        """Build and return the workflow engine"""
        self.engine.build()
        self.engine.compile()
        return self.engine