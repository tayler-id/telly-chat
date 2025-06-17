"""Chat agent with tool support"""
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import Document
from langchain.tools import BaseTool
import json
import asyncio
from datetime import datetime

from .tools.telly_tool import get_telly_tool
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.schemas import Message, MessageRole, ToolCall, ToolResult


SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools for extracting YouTube video transcripts and generating action plans.

IMPORTANT: When a user shares a YouTube URL, you MUST use the youtube_transcript tool to extract the content. Always call the tool when you detect a YouTube URL in the user's message.

Your capabilities include:
- Extracting transcripts from YouTube videos
- Generating actionable plans from video content
- Summarizing and analyzing video content
- Answering questions about the video content

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. When you use the youtube_transcript tool, ALWAYS include the EXACT tool output in your response
2. DO NOT modify, summarize, or expand the tool output - the tool already handles truncation
3. The tool automatically shows a preview for long transcripts - DO NOT try to show more
4. After showing the tool output, you can add a brief comment or analysis
5. The tool output is already properly formatted - preserve it exactly as returned

RESPONSE FORMAT:
1. When using tools, let the tool output speak for itself - DO NOT repeat or summarize it
2. The tool output will be automatically included in your response
3. You may add a VERY BRIEF closing comment if helpful (1-2 sentences max)
4. NEVER repeat the transcript or recreate the tool's output
5. ALWAYS respond in plain text with GitHub-flavored markdown formatting

FORMATTING GUIDELINES:
- Use **bold** for emphasis and important points
- Use *italics* for subtle emphasis
- Use bullet points (- or *) for unordered lists
- Use numbered lists (1. 2. 3.) for sequential steps
- Use `inline code` for technical terms, URLs, or commands
- Use ```language code blocks for multi-line code
- Use > for blockquotes from transcripts
- Use ### for section headers (not #)
- Use --- for horizontal rules
- Add line breaks between sections for readability

Be conversational and helpful. Remember: tool outputs are automatically included - never recreate or repeat them."""


class ChatAgent:
    """Agent that can chat and use tools"""
    
    def __init__(self, model_provider: str = "anthropic", model_name: Optional[str] = None):
        """Initialize the chat agent
        
        Args:
            model_provider: Either "anthropic" or "openai"
            model_name: Specific model to use (optional)
        """
        self.model_provider = model_provider
        
        # Initialize the LLM
        if model_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            
            self.llm = ChatAnthropic(
                model=model_name or "claude-3-5-sonnet-20241022",
                anthropic_api_key=api_key,
                temperature=0.7,
                max_tokens=4000
            )
        elif model_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            self.llm = ChatOpenAI(
                model=model_name or "gpt-4-turbo-preview",
                openai_api_key=api_key,
                temperature=0.7,
                max_tokens=4000
            )
        else:
            raise ValueError(f"Unknown model provider: {model_provider}")
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create the agent
        self.agent = self._create_agent()
        
        # Memory for conversation history
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize available tools"""
        tools = []
        
        # Add Telly tool
        telly_tool = get_telly_tool()
        tools.append(telly_tool)
        
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the agent with tools"""
        # Create the prompt with custom formatting
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        # Create the executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,  # Disable verbose to avoid interference
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=True,  # We handle this ourselves
            early_stopping_method="generate"
        )
        
        return agent_executor
    
    def _convert_messages_to_langchain(self, messages: List[Message]) -> List:
        """Convert our Message objects to LangChain message objects"""
        lc_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.USER:
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                lc_messages.append(SystemMessage(content=msg.content))
        
        return lc_messages
    
    async def chat(
        self, 
        message: str, 
        history: Optional[List[Message]] = None,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a chat message and yield responses
        
        Args:
            message: User's message
            history: Previous messages in the conversation
            stream: Whether to stream the response
            
        Yields:
            Response chunks with type and content
        """
        try:
            # Convert history to LangChain format if provided
            if history:
                lc_history = self._convert_messages_to_langchain(history)
                # Clear and repopulate memory
                self.memory.clear()
                for i in range(0, len(lc_history), 2):
                    if i + 1 < len(lc_history):
                        self.memory.save_context(
                            {"input": lc_history[i].content},
                            {"output": lc_history[i + 1].content}
                        )
            
            # Prepare the input
            inputs = {
                "input": message,
                "chat_history": []  # We'll handle history differently
            }
            
            # Invoke the agent
            if stream:
                # For streaming, we need to handle tool calls differently
                # This is a simplified version - in production you'd want more sophisticated streaming
                
                # First, check if we need to use tools
                response = await asyncio.to_thread(
                    self.agent.invoke,
                    inputs
                )
                
                # Extract the response
                output = response.get("output", "")
                
                # Remove debug logging in production
                
                # Ensure output is a string
                if isinstance(output, list) and len(output) > 0:
                    # Handle Anthropic's response format: [{'text': '...', 'type': 'text', 'index': 0}]
                    first_item = output[0]
                    if isinstance(first_item, dict) and 'text' in first_item:
                        output = first_item['text']
                    else:
                        output = " ".join(str(item) for item in output)
                elif isinstance(output, dict):
                    # If it's a dict, try to get the content or convert to string
                    output = output.get("content") or output.get("text") or str(output)
                    
                # Clean up any JSON artifacts or dict representations
                if output.startswith("{") and output.endswith("}"):
                    try:
                        import json
                        parsed = json.loads(output)
                        if isinstance(parsed, dict):
                            # Try various keys that might contain the actual text
                            output = parsed.get("content") or parsed.get("text") or parsed.get("output") or str(parsed)
                    except:
                        pass
                        
                # Also check for dict string representation
                if output.startswith("{'") and output.endswith("}"):
                    try:
                        # Convert Python dict string to JSON
                        import ast
                        parsed = ast.literal_eval(output)
                        if isinstance(parsed, dict):
                            output = parsed.get("text") or parsed.get("content") or str(parsed)
                    except:
                        pass
                
                # Check if tools were used
                tool_outputs = []
                if "intermediate_steps" in response and response["intermediate_steps"]:
                    # Yield tool usage information
                    for step in response["intermediate_steps"]:
                        if len(step) >= 2:
                            action = step[0]
                            result = step[1]
                            
                            # Store tool output
                            tool_outputs.append(result)
                            
                            yield {
                                "type": "tool_call",
                                "content": {
                                    "tool": action.tool,
                                    "input": action.tool_input,
                                    "id": f"call_{datetime.now().timestamp()}"
                                }
                            }
                            
                            yield {
                                "type": "tool_result",
                                "content": {
                                    "output": result,
                                    "id": f"call_{datetime.now().timestamp()}"
                                }
                            }
                
                # If tools were used, use ONLY the tool output (don't duplicate)
                if tool_outputs and len(tool_outputs) > 0:
                    # Use only the tool output, not the agent's summary
                    output = str(tool_outputs[0])
                    # Tool output is already clean - no hidden sections to remove
                
                # Stream the final response
                # Simulate more natural streaming with smaller chunks
                words = output.split(' ')
                current_chunk = ""
                
                for i, word in enumerate(words):
                    current_chunk += word + (' ' if i < len(words) - 1 else '')
                    
                    # Send chunks of 3-5 words or when we hit punctuation
                    if (len(current_chunk.split()) >= 3 or 
                        any(p in word for p in ['.', '!', '?', '\n']) or 
                        i == len(words) - 1):
                        yield {
                            "type": "text",
                            "content": current_chunk
                        }
                        current_chunk = ""
                        await asyncio.sleep(0.03)  # Small delay for natural streaming
                
                # Save to memory
                self.memory.save_context(inputs, {"output": output})
                
            else:
                # Non-streaming response
                response = await asyncio.to_thread(
                    self.agent.invoke,
                    inputs
                )
                
                output = response.get("output", "")
                
                # Ensure output is a string
                if isinstance(output, list) and len(output) > 0:
                    # Handle Anthropic's response format: [{'text': '...', 'type': 'text', 'index': 0}]
                    first_item = output[0]
                    if isinstance(first_item, dict) and 'text' in first_item:
                        output = first_item['text']
                    else:
                        output = " ".join(str(item) for item in output)
                elif isinstance(output, dict):
                    # If it's a dict, try to get the content or convert to string
                    output = output.get("content") or output.get("text") or str(output)
                    
                # Clean up any JSON artifacts or dict representations
                if output.startswith("{") and output.endswith("}"):
                    try:
                        import json
                        parsed = json.loads(output)
                        if isinstance(parsed, dict):
                            # Try various keys that might contain the actual text
                            output = parsed.get("content") or parsed.get("text") or parsed.get("output") or str(parsed)
                    except:
                        pass
                        
                # Also check for dict string representation
                if output.startswith("{'") and output.endswith("}"):
                    try:
                        # Convert Python dict string to JSON
                        import ast
                        parsed = ast.literal_eval(output)
                        if isinstance(parsed, dict):
                            output = parsed.get("text") or parsed.get("content") or str(parsed)
                    except:
                        pass
                yield {
                    "type": "text",
                    "content": output
                }
                
                # Save to memory
                self.memory.save_context(inputs, {"output": output})
                
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error processing message: {str(e)}"
            }
    
    def clear_memory(self):
        """Clear the conversation memory"""
        self.memory.clear()