"""Workflow orchestrator for managing multiple workflow executions"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
import json

from .engine import WorkflowEngine, WorkflowState, WorkflowStatus


@dataclass
class WorkflowInstance:
    """Represents a workflow instance"""
    id: str
    workflow_name: str
    state: WorkflowState
    priority: int = 1
    scheduled_time: Optional[datetime] = None
    timeout: Optional[timedelta] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_ready(self) -> bool:
        """Check if workflow is ready to execute"""
        # Check scheduled time
        if self.scheduled_time and datetime.now() < self.scheduled_time:
            return False
        
        # Check dependencies (simplified - would need dependency tracking)
        if self.dependencies:
            return False
        
        return True
    
    @property
    def is_timeout(self) -> bool:
        """Check if workflow has timed out"""
        if not self.timeout:
            return False
        
        age = datetime.now() - self.state.created_at
        return age > self.timeout


class WorkflowOrchestrator:
    """
    Orchestrates multiple workflow executions
    
    Features:
    - Concurrent workflow execution
    - Priority-based scheduling
    - Resource management
    - Dependency handling
    - Monitoring and metrics
    """
    
    def __init__(
        self,
        max_concurrent_workflows: int = 10,
        max_queue_size: int = 100
    ):
        self.max_concurrent_workflows = max_concurrent_workflows
        self.max_queue_size = max_queue_size
        
        # Workflow registry
        self.registered_workflows: Dict[str, WorkflowEngine] = {}
        
        # Execution management
        self.workflow_queue: List[WorkflowInstance] = []
        self.active_workflows: Dict[str, WorkflowInstance] = {}
        self.completed_workflows: Dict[str, WorkflowInstance] = {}
        
        # Metrics
        self.metrics = {
            "total_executed": 0,
            "total_completed": 0,
            "total_failed": 0,
            "average_duration": 0.0,
            "by_workflow": defaultdict(lambda: {
                "executed": 0,
                "completed": 0,
                "failed": 0,
                "average_duration": 0.0
            })
        }
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Orchestrator state
        self.is_running = False
        self._executor_task = None
    
    def register_workflow(self, workflow: WorkflowEngine):
        """Register a workflow for execution"""
        self.registered_workflows[workflow.name] = workflow
    
    def schedule_workflow(
        self,
        workflow_name: str,
        initial_context: Optional[Dict[str, Any]] = None,
        priority: int = 1,
        scheduled_time: Optional[datetime] = None,
        timeout: Optional[timedelta] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule a workflow for execution"""
        if workflow_name not in self.registered_workflows:
            raise ValueError(f"Workflow '{workflow_name}' not registered")
        
        # Check queue size
        if len(self.workflow_queue) >= self.max_queue_size:
            raise RuntimeError("Workflow queue is full")
        
        # Create workflow instance
        instance_id = f"instance_{uuid.uuid4().hex}"
        state = WorkflowState(
            workflow_id=instance_id,
            status=WorkflowStatus.PENDING,
            current_node=None,
            context=initial_context or {}
        )
        
        instance = WorkflowInstance(
            id=instance_id,
            workflow_name=workflow_name,
            state=state,
            priority=priority,
            scheduled_time=scheduled_time,
            timeout=timeout,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        # Add to queue
        self.workflow_queue.append(instance)
        self._sort_queue()
        
        # Emit event
        self._emit_event("workflow_scheduled", instance)
        
        return instance_id
    
    async def start(self):
        """Start the orchestrator"""
        if self.is_running:
            return
        
        self.is_running = True
        self._executor_task = asyncio.create_task(self._executor_loop())
        self._emit_event("orchestrator_started", {})
    
    async def stop(self):
        """Stop the orchestrator"""
        self.is_running = False
        
        if self._executor_task:
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass
        
        self._emit_event("orchestrator_stopped", {})
    
    def cancel_workflow(self, instance_id: str) -> bool:
        """Cancel a workflow"""
        # Check if in queue
        for i, instance in enumerate(self.workflow_queue):
            if instance.id == instance_id:
                self.workflow_queue.pop(i)
                instance.state.status = WorkflowStatus.CANCELLED
                self._emit_event("workflow_cancelled", instance)
                return True
        
        # Check if active
        if instance_id in self.active_workflows:
            instance = self.active_workflows[instance_id]
            workflow = self.registered_workflows[instance.workflow_name]
            workflow.cancel(instance_id)
            instance.state.status = WorkflowStatus.CANCELLED
            self._emit_event("workflow_cancelled", instance)
            return True
        
        return False
    
    def get_status(self, instance_id: str) -> Optional[WorkflowStatus]:
        """Get workflow status"""
        # Check queue
        for instance in self.workflow_queue:
            if instance.id == instance_id:
                return instance.state.status
        
        # Check active
        if instance_id in self.active_workflows:
            return self.active_workflows[instance_id].state.status
        
        # Check completed
        if instance_id in self.completed_workflows:
            return self.completed_workflows[instance_id].state.status
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queued": len(self.workflow_queue),
            "active": len(self.active_workflows),
            "completed": len(self.completed_workflows),
            "max_concurrent": self.max_concurrent_workflows,
            "is_running": self.is_running
        }
    
    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.event_handlers[event_type].append(handler)
    
    async def _executor_loop(self):
        """Main executor loop"""
        while self.is_running:
            try:
                # Check for workflows to execute
                await self._process_queue()
                
                # Check for timeouts
                await self._check_timeouts()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self._emit_event("orchestrator_error", {"error": str(e)})
    
    async def _process_queue(self):
        """Process workflow queue"""
        # Check if we can execute more workflows
        if len(self.active_workflows) >= self.max_concurrent_workflows:
            return
        
        # Find next ready workflow
        next_instance = None
        for i, instance in enumerate(self.workflow_queue):
            if instance.is_ready:
                next_instance = self.workflow_queue.pop(i)
                break
        
        if not next_instance:
            return
        
        # Execute workflow
        await self._execute_workflow(next_instance)
    
    async def _execute_workflow(self, instance: WorkflowInstance):
        """Execute a workflow instance"""
        workflow = self.registered_workflows.get(instance.workflow_name)
        if not workflow:
            instance.state.status = WorkflowStatus.FAILED
            instance.state.add_error("orchestrator", f"Workflow '{instance.workflow_name}' not found")
            self.completed_workflows[instance.id] = instance
            return
        
        # Add to active workflows
        self.active_workflows[instance.id] = instance
        instance.state.status = WorkflowStatus.RUNNING
        
        # Update metrics
        self.metrics["total_executed"] += 1
        self.metrics["by_workflow"][instance.workflow_name]["executed"] += 1
        
        # Emit event
        self._emit_event("workflow_started", instance)
        
        # Create execution task
        asyncio.create_task(self._run_workflow(workflow, instance))
    
    async def _run_workflow(self, workflow: WorkflowEngine, instance: WorkflowInstance):
        """Run workflow in background"""
        start_time = datetime.now()
        
        try:
            # Execute workflow
            final_state = await workflow.execute(
                initial_context=instance.state.context,
                workflow_id=instance.id
            )
            
            # Update instance state
            instance.state = final_state
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self._update_metrics(instance.workflow_name, "completed", duration)
            
            # Emit event
            self._emit_event("workflow_completed", instance)
            
        except Exception as e:
            # Handle failure
            instance.state.status = WorkflowStatus.FAILED
            instance.state.add_error("execution", str(e))
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self._update_metrics(instance.workflow_name, "failed", duration)
            
            # Emit event
            self._emit_event("workflow_failed", instance)
        
        finally:
            # Move to completed
            if instance.id in self.active_workflows:
                del self.active_workflows[instance.id]
            self.completed_workflows[instance.id] = instance
    
    async def _check_timeouts(self):
        """Check for workflow timeouts"""
        for instance_id, instance in list(self.active_workflows.items()):
            if instance.is_timeout:
                # Cancel workflow
                workflow = self.registered_workflows[instance.workflow_name]
                workflow.cancel(instance_id)
                
                # Update state
                instance.state.status = WorkflowStatus.FAILED
                instance.state.add_error("orchestrator", "Workflow timeout")
                
                # Move to completed
                del self.active_workflows[instance_id]
                self.completed_workflows[instance_id] = instance
                
                # Emit event
                self._emit_event("workflow_timeout", instance)
    
    def _sort_queue(self):
        """Sort workflow queue by priority and scheduled time"""
        self.workflow_queue.sort(
            key=lambda x: (
                -x.priority,  # Higher priority first
                x.scheduled_time or datetime.min  # Earlier scheduled time first
            )
        )
    
    def _update_metrics(self, workflow_name: str, status: str, duration: float):
        """Update execution metrics"""
        if status == "completed":
            self.metrics["total_completed"] += 1
            self.metrics["by_workflow"][workflow_name]["completed"] += 1
        elif status == "failed":
            self.metrics["total_failed"] += 1
            self.metrics["by_workflow"][workflow_name]["failed"] += 1
        
        # Update average duration
        workflow_metrics = self.metrics["by_workflow"][workflow_name]
        current_avg = workflow_metrics["average_duration"]
        count = workflow_metrics["completed"] + workflow_metrics["failed"]
        
        if count > 0:
            workflow_metrics["average_duration"] = (
                (current_avg * (count - 1) + duration) / count
            )
        
        # Update global average
        total_count = self.metrics["total_completed"] + self.metrics["total_failed"]
        if total_count > 0:
            current_global_avg = self.metrics["average_duration"]
            self.metrics["average_duration"] = (
                (current_global_avg * (total_count - 1) + duration) / total_count
            )
    
    def _emit_event(self, event_type: str, data: Any):
        """Emit an event to registered handlers"""
        for handler in self.event_handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event_type, data))
                else:
                    handler(event_type, data)
            except Exception as e:
                # Log error but don't fail
                print(f"Error in event handler: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics"""
        return {
            **self.metrics,
            "queue_status": self.get_queue_status()
        }
    
    def export_state(self) -> Dict[str, Any]:
        """Export orchestrator state"""
        return {
            "registered_workflows": list(self.registered_workflows.keys()),
            "queue": [
                {
                    "id": inst.id,
                    "workflow": inst.workflow_name,
                    "status": inst.state.status.value,
                    "priority": inst.priority
                }
                for inst in self.workflow_queue
            ],
            "active": [
                {
                    "id": inst.id,
                    "workflow": inst.workflow_name,
                    "status": inst.state.status.value,
                    "started": inst.state.created_at.isoformat()
                }
                for inst in self.active_workflows.values()
            ],
            "metrics": self.get_metrics()
        }