"""Tests for workflow system"""

import unittest
import asyncio
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from workflows.engine import (
        WorkflowEngine, WorkflowState, WorkflowStatus,
        WorkflowNode, ConditionalNode, WorkflowBuilder
    )
    from workflows.orchestrator import WorkflowOrchestrator, WorkflowInstance
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False


class MockNode(WorkflowNode):
    """Mock node for testing"""
    
    def __init__(self, name: str, result: Any = None, should_fail: bool = False):
        super().__init__(name)
        self.result = result
        self.should_fail = should_fail
        self.executed = False
    
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        self.executed = True
        if self.should_fail:
            raise Exception("Mock node failure")
        return {"result": self.result or f"Result from {self.name}"}


@unittest.skipIf(not WORKFLOW_AVAILABLE, "Workflow modules not available")
class TestWorkflowEngine(unittest.TestCase):
    """Test workflow engine functionality"""
    
    def test_workflow_creation(self):
        """Test creating a workflow"""
        engine = WorkflowEngine("test_workflow", "Test workflow")
        self.assertEqual(engine.name, "test_workflow")
        self.assertEqual(len(engine.nodes), 0)
    
    def test_add_nodes(self):
        """Test adding nodes to workflow"""
        engine = WorkflowEngine("test_workflow")
        
        node1 = MockNode("node1")
        node2 = MockNode("node2")
        
        engine.add_node(node1)
        engine.add_node(node2)
        
        self.assertEqual(len(engine.nodes), 2)
        self.assertIn("node1", engine.nodes)
        self.assertIn("node2", engine.nodes)
    
    def test_workflow_state(self):
        """Test workflow state management"""
        state = WorkflowState(
            workflow_id="test_123",
            status=WorkflowStatus.PENDING,
            current_node=None
        )
        
        # Test state updates
        state.update(status=WorkflowStatus.RUNNING, current_node="node1")
        self.assertEqual(state.status, WorkflowStatus.RUNNING)
        self.assertEqual(state.current_node, "node1")
        
        # Test adding results
        state.set_result("node1", {"data": "test"})
        self.assertEqual(state.results["node1"]["data"], "test")
        
        # Test error handling
        state.add_error("node1", "Test error", {"code": 500})
        self.assertEqual(len(state.errors), 1)
        self.assertEqual(state.errors[0]["error"], "Test error")
    
    @unittest.skipIf(not WORKFLOW_AVAILABLE, "Requires async support")
    def test_workflow_execution(self):
        """Test workflow execution"""
        async def run_test():
            # Create workflow
            engine = WorkflowEngine("test_workflow")
            
            # Add nodes
            node1 = MockNode("node1", result="Result 1")
            node2 = MockNode("node2", result="Result 2")
            
            engine.add_node(node1)
            engine.add_node(node2)
            
            # Build and compile
            engine.build()
            engine.set_entry_point("node1")
            engine.add_edge("node1", "node2")
            engine.compile()
            
            # Execute
            state = await engine.execute({"test": "data"})
            
            # Verify execution
            self.assertTrue(node1.executed)
            self.assertTrue(node2.executed)
            self.assertEqual(state.status, WorkflowStatus.COMPLETED)
            self.assertIn("node1", state.results)
            self.assertIn("node2", state.results)
        
        # Run async test
        asyncio.run(run_test())
    
    def test_workflow_builder(self):
        """Test workflow builder pattern"""
        # Note: Can't test fully without LLM, but can test structure
        builder = WorkflowBuilder("test_workflow", "Test workflow")
        
        # Verify builder creates engine
        self.assertIsInstance(builder.engine, WorkflowEngine)
        self.assertEqual(builder.engine.name, "test_workflow")


@unittest.skipIf(not WORKFLOW_AVAILABLE, "Workflow modules not available")
class TestWorkflowOrchestrator(unittest.TestCase):
    """Test workflow orchestrator functionality"""
    
    def setUp(self):
        self.orchestrator = WorkflowOrchestrator(max_concurrent_workflows=3)
    
    def test_workflow_registration(self):
        """Test registering workflows"""
        workflow = WorkflowEngine("test_workflow")
        self.orchestrator.register_workflow(workflow)
        
        self.assertIn("test_workflow", self.orchestrator.registered_workflows)
    
    def test_workflow_scheduling(self):
        """Test scheduling workflows"""
        # Register workflow
        workflow = WorkflowEngine("test_workflow")
        self.orchestrator.register_workflow(workflow)
        
        # Schedule workflow
        instance_id = self.orchestrator.schedule_workflow(
            workflow_name="test_workflow",
            initial_context={"data": "test"},
            priority=2
        )
        
        self.assertIsNotNone(instance_id)
        self.assertEqual(len(self.orchestrator.workflow_queue), 1)
        
        # Check scheduled workflow
        status = self.orchestrator.get_status(instance_id)
        self.assertEqual(status, WorkflowStatus.PENDING)
    
    def test_priority_scheduling(self):
        """Test priority-based scheduling"""
        workflow = WorkflowEngine("test_workflow")
        self.orchestrator.register_workflow(workflow)
        
        # Schedule workflows with different priorities
        low_id = self.orchestrator.schedule_workflow("test_workflow", priority=1)
        high_id = self.orchestrator.schedule_workflow("test_workflow", priority=3)
        medium_id = self.orchestrator.schedule_workflow("test_workflow", priority=2)
        
        # Check queue order (high priority first)
        queue = self.orchestrator.workflow_queue
        self.assertEqual(queue[0].priority, 3)
        self.assertEqual(queue[1].priority, 2)
        self.assertEqual(queue[2].priority, 1)
    
    def test_workflow_cancellation(self):
        """Test cancelling workflows"""
        workflow = WorkflowEngine("test_workflow")
        self.orchestrator.register_workflow(workflow)
        
        instance_id = self.orchestrator.schedule_workflow("test_workflow")
        
        # Cancel workflow
        success = self.orchestrator.cancel_workflow(instance_id)
        self.assertTrue(success)
        
        # Check it's removed from queue
        self.assertEqual(len(self.orchestrator.workflow_queue), 0)
    
    def test_metrics_tracking(self):
        """Test metrics collection"""
        metrics = self.orchestrator.get_metrics()
        
        self.assertIn("total_executed", metrics)
        self.assertIn("total_completed", metrics)
        self.assertIn("total_failed", metrics)
        self.assertIn("queue_status", metrics)
        
        queue_status = metrics["queue_status"]
        self.assertIn("queued", queue_status)
        self.assertIn("active", queue_status)
        self.assertIn("completed", queue_status)


@unittest.skipIf(not WORKFLOW_AVAILABLE, "Workflow modules not available")
class TestWorkflowIntegration(unittest.TestCase):
    """Test workflow system integration"""
    
    def test_conditional_workflow(self):
        """Test workflow with conditional branching"""
        engine = WorkflowEngine("conditional_workflow")
        
        # Add nodes
        start_node = MockNode("start", result={"value": 10})
        
        def condition_fn(state: WorkflowState) -> str:
            value = state.results.get("start", {}).get("result", {}).get("value", 0)
            return "high" if value > 5 else "low"
        
        condition_node = ConditionalNode("check_value", condition_fn)
        high_node = MockNode("high_path", result="High value")
        low_node = MockNode("low_path", result="Low value")
        
        engine.add_node(start_node)
        engine.add_node(condition_node)
        engine.add_node(high_node)
        engine.add_node(low_node)
        
        # Verify nodes added
        self.assertEqual(len(engine.nodes), 4)


if __name__ == '__main__':
    unittest.main()