"""Pre-built workflow templates for common patterns"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel
from langchain.tools import BaseTool

from .engine import WorkflowEngine, WorkflowBuilder, WorkflowState


class WorkflowTemplate(ABC):
    """Abstract base class for workflow templates"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    def build(self, **kwargs) -> WorkflowEngine:
        """Build the workflow with provided configuration"""
        pass


class ResearchWorkflowTemplate(WorkflowTemplate):
    """
    Template for research workflows
    
    Steps:
    1. Parse research query
    2. Search for information
    3. Analyze results
    4. Generate summary
    """
    
    def __init__(self):
        super().__init__(
            "research_workflow",
            "Research and analysis workflow"
        )
    
    def build(
        self,
        llm: BaseChatModel,
        search_tool: BaseTool,
        summarize_tool: Optional[BaseTool] = None
    ) -> WorkflowEngine:
        """Build research workflow"""
        builder = WorkflowBuilder(self.name, self.description)
        
        # Step 1: Parse query
        builder.add_llm_node(
            "parse_query",
            llm,
            prompt_template="""
            Parse the following research query and extract:
            1. Main topic
            2. Key questions
            3. Search keywords
            
            Query: {query}
            
            Response format:
            Topic: ...
            Questions: ...
            Keywords: ...
            """
        )
        
        # Step 2: Search
        builder.add_tool_node(
            "search",
            search_tool,
            "search"
        )
        
        # Step 3: Analyze results
        builder.add_llm_node(
            "analyze",
            llm,
            prompt_template="""
            Analyze the search results and identify:
            1. Key findings
            2. Relevant sources
            3. Gaps in information
            
            Results: {search_results}
            
            Analysis:
            """
        )
        
        # Step 4: Generate summary
        if summarize_tool:
            builder.add_tool_node(
                "summarize",
                summarize_tool,
                "summarize"
            )
        else:
            builder.add_llm_node(
                "summarize",
                llm,
                prompt_template="""
                Create a comprehensive summary of the research findings:
                
                Topic: {topic}
                Analysis: {analysis}
                
                Summary:
                """
            )
        
        return builder.build()


class ConversationWorkflowTemplate(WorkflowTemplate):
    """
    Template for conversation workflows with memory
    
    Steps:
    1. Retrieve relevant memories
    2. Generate response
    3. Store important information
    """
    
    def __init__(self):
        super().__init__(
            "conversation_workflow",
            "Conversation workflow with memory integration"
        )
    
    def build(
        self,
        llm: BaseChatModel,
        memory_tool: BaseTool,
        store_memory_tool: BaseTool
    ) -> WorkflowEngine:
        """Build conversation workflow"""
        builder = WorkflowBuilder(self.name, self.description)
        
        # Step 1: Retrieve memories
        builder.add_tool_node(
            "retrieve_memories",
            memory_tool,
            "search_memories"
        )
        
        # Step 2: Generate response
        builder.add_llm_node(
            "generate_response",
            llm,
            prompt_template="""
            Context from memory: {memories}
            
            User message: {user_message}
            
            Generate a helpful response that takes into account the context and memories.
            
            Response:
            """
        )
        
        # Step 3: Conditional memory storage
        def should_store_memory(state: WorkflowState) -> str:
            # Simple heuristic - store if response is substantial
            response = state.results.get("generate_response", {}).get("response", "")
            if len(response) > 100:
                return "store_memory"
            return "end"
        
        builder.add_conditional(
            "check_storage",
            should_store_memory,
            {
                "store_memory": "store_memory",
                "end": None  # End workflow
            }
        )
        
        # Step 4: Store memory
        builder.add_tool_node(
            "store_memory",
            store_memory_tool,
            "store"
        )
        
        return builder.build()


class TaskExecutionWorkflowTemplate(WorkflowTemplate):
    """
    Template for task execution workflows
    
    Steps:
    1. Plan task execution
    2. Execute subtasks
    3. Verify results
    4. Report completion
    """
    
    def __init__(self):
        super().__init__(
            "task_execution_workflow",
            "Task planning and execution workflow"
        )
    
    def build(
        self,
        llm: BaseChatModel,
        task_tools: List[BaseTool],
        verification_tool: Optional[BaseTool] = None
    ) -> WorkflowEngine:
        """Build task execution workflow"""
        builder = WorkflowBuilder(self.name, self.description)
        
        # Step 1: Plan execution
        builder.add_llm_node(
            "plan_execution",
            llm,
            prompt_template="""
            Task: {task_description}
            Available tools: {available_tools}
            
            Create a step-by-step execution plan:
            1. Break down the task into subtasks
            2. Identify which tools to use for each subtask
            3. Define success criteria
            
            Plan:
            """
        )
        
        # Step 2: Execute subtasks (simplified - in practice would be dynamic)
        for i, tool in enumerate(task_tools[:3]):  # Limit to 3 tools for example
            builder.add_tool_node(
                f"execute_subtask_{i}",
                tool,
                tool.name
            )
        
        # Step 3: Verify results
        if verification_tool:
            builder.add_tool_node(
                "verify_results",
                verification_tool,
                "verify"
            )
        else:
            builder.add_llm_node(
                "verify_results",
                llm,
                prompt_template="""
                Task: {task_description}
                Execution plan: {plan}
                Results: {execution_results}
                
                Verify that the task has been completed successfully:
                1. Check if all subtasks were completed
                2. Validate the results
                3. Identify any issues
                
                Verification:
                """
            )
        
        # Step 4: Generate report
        builder.add_llm_node(
            "generate_report",
            llm,
            prompt_template="""
            Generate a completion report for the task:
            
            Task: {task_description}
            Verification: {verification}
            
            Report should include:
            - Summary of what was accomplished
            - Any issues encountered
            - Recommendations for future
            
            Report:
            """
        )
        
        return builder.build()


class AnalysisWorkflowTemplate(WorkflowTemplate):
    """
    Template for data analysis workflows
    
    Steps:
    1. Load and validate data
    2. Perform analysis
    3. Generate insights
    4. Create visualizations
    """
    
    def __init__(self):
        super().__init__(
            "analysis_workflow",
            "Data analysis and insight generation workflow"
        )
    
    def build(
        self,
        llm: BaseChatModel,
        data_tool: BaseTool,
        analysis_tool: BaseTool,
        visualization_tool: Optional[BaseTool] = None
    ) -> WorkflowEngine:
        """Build analysis workflow"""
        builder = WorkflowBuilder(self.name, self.description)
        
        # Step 1: Load data
        builder.add_tool_node(
            "load_data",
            data_tool,
            "load"
        )
        
        # Step 2: Validate and preprocess
        builder.add_llm_node(
            "validate_data",
            llm,
            prompt_template="""
            Data summary: {data_summary}
            
            Validate the data and identify:
            1. Data quality issues
            2. Missing values
            3. Preprocessing needs
            
            Validation report:
            """
        )
        
        # Step 3: Perform analysis
        builder.add_tool_node(
            "analyze_data",
            analysis_tool,
            "analyze"
        )
        
        # Step 4: Generate insights
        builder.add_llm_node(
            "generate_insights",
            llm,
            prompt_template="""
            Analysis results: {analysis_results}
            
            Generate key insights:
            1. Main findings
            2. Patterns and trends
            3. Anomalies or outliers
            4. Recommendations
            
            Insights:
            """
        )
        
        # Step 5: Create visualizations (optional)
        if visualization_tool:
            builder.add_tool_node(
                "create_visualizations",
                visualization_tool,
                "visualize"
            )
        
        return builder.build()


# Registry of available templates
WORKFLOW_TEMPLATES = {
    "research": ResearchWorkflowTemplate,
    "conversation": ConversationWorkflowTemplate,
    "task_execution": TaskExecutionWorkflowTemplate,
    "analysis": AnalysisWorkflowTemplate
}


def get_workflow_template(template_name: str) -> Optional[WorkflowTemplate]:
    """Get a workflow template by name"""
    template_class = WORKFLOW_TEMPLATES.get(template_name)
    if template_class:
        return template_class()
    return None


def list_workflow_templates() -> List[Dict[str, str]]:
    """List all available workflow templates"""
    return [
        {
            "name": name,
            "description": template_class().description
        }
        for name, template_class in WORKFLOW_TEMPLATES.items()
    ]