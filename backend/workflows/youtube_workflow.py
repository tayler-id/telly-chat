"""YouTube Analysis Workflow - Automated video processing and action plan generation"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import BaseTool

from .engine import WorkflowEngine, WorkflowBuilder, WorkflowState, WorkflowStatus, NodeStatus
from .templates import WorkflowTemplate
from ..agents.tools.telly_tool import get_telly_tool
from ..memory.transcript_store import TranscriptStore


class YouTubeAnalysisNode:
    """Custom node for YouTube analysis"""
    
    def __init__(self, name: str, agent=None, transcript_store: Optional[TranscriptStore] = None):
        self.name = name
        self.agent = agent
        self.transcript_store = transcript_store
        self.status = NodeStatus.PENDING
    
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute YouTube analysis step"""
        try:
            self.status = NodeStatus.RUNNING
            
            if self.name == "extract_transcript":
                # Extract transcript using Telly tool
                url = state.context.get("youtube_url")
                if not url:
                    raise ValueError("No YouTube URL provided")
                
                # Use the agent's Telly tool
                tool = get_telly_tool()
                result = await tool.arun(url)
                
                # Parse the result to extract transcript and metadata
                lines = result.split('\n')
                video_id = None
                title = None
                transcript_text = []
                action_plan = []
                in_transcript = False
                in_action_plan = False
                
                for line in lines:
                    if "Video ID:" in line and "`" in line:
                        video_id = line.split("`")[1]
                    elif line.startswith("### 📹"):
                        title = lines[lines.index(line) + 1].strip("- **Title:** ")
                    elif "### 📝 Transcript" in line or "### 📝 Full Transcript" in line:
                        in_transcript = True
                        in_action_plan = False
                    elif "### 📋 Action Plan" in line:
                        in_transcript = False
                        in_action_plan = True
                    elif in_transcript and line.strip():
                        transcript_text.append(line)
                    elif in_action_plan and line.strip():
                        action_plan.append(line)
                
                self.status = NodeStatus.COMPLETED
                return {
                    "video_id": video_id,
                    "title": title or "YouTube Video",
                    "transcript": "\n".join(transcript_text),
                    "action_plan": "\n".join(action_plan),
                    "url": url,
                    "raw_output": result
                }
            
            elif self.name == "analyze_content":
                # Analyze the transcript for key themes and insights
                transcript = state.results.get("extract_transcript", {}).get("transcript", "")
                
                if not transcript:
                    raise ValueError("No transcript available for analysis")
                
                # Create analysis prompt
                analysis_prompt = f"""
                Analyze this YouTube video transcript and identify:
                1. Main topics and themes
                2. Key takeaways (3-5 bullet points)
                3. Target audience
                4. Content quality assessment
                5. Potential improvements or gaps
                
                Transcript:
                {transcript[:3000]}...
                
                Analysis:
                """
                
                # Use agent to analyze
                response = ""
                async for chunk in self.agent.chat(analysis_prompt, [], stream=True):
                    if chunk["type"] == "text":
                        response += chunk["content"]
                
                self.status = NodeStatus.COMPLETED
                return {
                    "analysis": response,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif self.name == "generate_summary":
                # Generate a concise summary
                transcript = state.results.get("extract_transcript", {}).get("transcript", "")
                analysis = state.results.get("analyze_content", {}).get("analysis", "")
                
                summary_prompt = f"""
                Create a concise summary (max 200 words) of this YouTube video based on the transcript and analysis.
                
                Analysis: {analysis}
                
                The summary should include:
                - What the video is about
                - Main points covered
                - Why it's valuable
                - Who should watch it
                
                Summary:
                """
                
                response = ""
                async for chunk in self.agent.chat(summary_prompt, [], stream=True):
                    if chunk["type"] == "text":
                        response += chunk["content"]
                
                self.status = NodeStatus.COMPLETED
                return {
                    "summary": response
                }
            
            elif self.name == "save_to_store":
                # Save to transcript store if available
                if not self.transcript_store:
                    self.status = NodeStatus.SKIPPED
                    return {"saved": False, "reason": "No transcript store available"}
                
                extract_result = state.results.get("extract_transcript", {})
                analysis_result = state.results.get("analyze_content", {})
                summary_result = state.results.get("generate_summary", {})
                
                # Save to store
                transcript_id = self.transcript_store.save_transcript(
                    url=extract_result.get("url", ""),
                    title=extract_result.get("title", "YouTube Video"),
                    transcript=extract_result.get("transcript", ""),
                    action_plan=extract_result.get("action_plan", ""),
                    summary=summary_result.get("summary", ""),
                    metadata={
                        "video_id": extract_result.get("video_id"),
                        "analysis": analysis_result.get("analysis", ""),
                        "workflow_id": state.workflow_id,
                        "processed_at": datetime.now().isoformat()
                    }
                )
                
                self.status = NodeStatus.COMPLETED
                return {
                    "saved": True,
                    "transcript_id": transcript_id
                }
            
            elif self.name == "generate_report":
                # Generate final report
                all_results = {
                    "extraction": state.results.get("extract_transcript", {}),
                    "analysis": state.results.get("analyze_content", {}),
                    "summary": state.results.get("generate_summary", {}),
                    "storage": state.results.get("save_to_store", {})
                }
                
                report = f"""
# YouTube Video Analysis Report

## Video Information
- **Title**: {all_results["extraction"].get("title", "N/A")}
- **URL**: {all_results["extraction"].get("url", "N/A")}
- **Video ID**: {all_results["extraction"].get("video_id", "N/A")}
- **Processed**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
{all_results["summary"].get("summary", "No summary available")}

## Detailed Analysis
{all_results["analysis"].get("analysis", "No analysis available")}

## Action Plan
{all_results["extraction"].get("action_plan", "No action plan generated")}

## Storage Status
- **Saved to Store**: {"Yes" if all_results["storage"].get("saved") else "No"}
- **Transcript ID**: {all_results["storage"].get("transcript_id", "N/A")}

---
*Generated by YouTube Analysis Workflow*
                """
                
                self.status = NodeStatus.COMPLETED
                return {
                    "report": report,
                    "success": True
                }
            
            else:
                raise ValueError(f"Unknown node: {self.name}")
                
        except Exception as e:
            self.status = NodeStatus.FAILED
            state.add_error(self.name, str(e))
            return {"error": str(e)}


class YouTubeAnalysisWorkflow(WorkflowTemplate):
    """
    Complete YouTube video analysis workflow
    
    Steps:
    1. Extract transcript and metadata
    2. Analyze content for insights
    3. Generate summary
    4. Save to transcript store
    5. Generate comprehensive report
    """
    
    def __init__(self):
        super().__init__(
            "youtube_analysis_workflow",
            "Automated YouTube video processing and analysis"
        )
    
    def build(
        self,
        agent: Any,
        transcript_store: Optional[TranscriptStore] = None,
        **kwargs
    ) -> WorkflowEngine:
        """Build YouTube analysis workflow"""
        
        # Create custom workflow engine
        class YouTubeWorkflowEngine(WorkflowEngine):
            def __init__(self):
                super().__init__("youtube_analysis", "YouTube Analysis Workflow")
                self.agent = agent
                self.transcript_store = transcript_store
                self.nodes = {}
                self._build_graph()
            
            def _build_graph(self):
                """Build the workflow graph"""
                # Create nodes
                node_names = [
                    "extract_transcript",
                    "analyze_content", 
                    "generate_summary",
                    "save_to_store",
                    "generate_report"
                ]
                
                for name in node_names:
                    self.nodes[name] = YouTubeAnalysisNode(
                        name, 
                        self.agent,
                        self.transcript_store
                    )
            
            async def _execute_node(self, node_name: str, state: WorkflowState) -> Dict[str, Any]:
                """Execute a specific node"""
                node = self.nodes.get(node_name)
                if not node:
                    raise ValueError(f"Node {node_name} not found")
                
                result = await node.execute(state)
                state.set_result(node_name, result)
                state.visited_nodes.append(node_name)
                return result
            
            async def execute(self, inputs: Dict[str, Any]) -> WorkflowState:
                """Execute the workflow"""
                # Initialize state
                state = WorkflowState(
                    workflow_id=f"youtube_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status=WorkflowStatus.RUNNING,
                    current_node=None,
                    context=inputs
                )
                
                try:
                    # Execute nodes in sequence
                    for node_name in [
                        "extract_transcript",
                        "analyze_content",
                        "generate_summary", 
                        "save_to_store",
                        "generate_report"
                    ]:
                        state.current_node = node_name
                        result = await self._execute_node(node_name, state)
                        
                        # Check for errors
                        if "error" in result:
                            state.status = WorkflowStatus.FAILED
                            break
                    
                    if state.status != WorkflowStatus.FAILED:
                        state.status = WorkflowStatus.COMPLETED
                    
                except Exception as e:
                    state.status = WorkflowStatus.FAILED
                    state.add_error("workflow", str(e))
                
                return state
        
        return YouTubeWorkflowEngine()


def create_youtube_workflow(agent: Any, transcript_store: Optional[TranscriptStore] = None) -> WorkflowEngine:
    """Helper function to create YouTube workflow"""
    template = YouTubeAnalysisWorkflow()
    return template.build(agent=agent, transcript_store=transcript_store)


# Example usage function
async def run_youtube_analysis(youtube_url: str, agent: Any, transcript_store: Optional[TranscriptStore] = None) -> Dict[str, Any]:
    """
    Run YouTube analysis workflow on a video
    
    Args:
        youtube_url: URL of the YouTube video
        agent: Chat agent instance
        transcript_store: Optional transcript store for saving
    
    Returns:
        Dict with workflow results
    """
    # Create workflow
    workflow = create_youtube_workflow(agent, transcript_store)
    
    # Execute workflow
    state = await workflow.execute({"youtube_url": youtube_url})
    
    # Return results
    return {
        "workflow_id": state.workflow_id,
        "status": state.status.value,
        "report": state.results.get("generate_report", {}).get("report", ""),
        "errors": state.errors,
        "all_results": state.results
    }