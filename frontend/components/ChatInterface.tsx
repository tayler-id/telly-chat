import { useState, useRef, useEffect } from 'react'
import MessageList from './MessageList'
import InputBox from './InputBox'
import ToolExecution from './ToolExecution'
import MemoryToggle from './MemoryToggle'
import ConversationHistory from './ConversationHistory'
import { api, Message, ToolCall, ToolResult } from '../services/api'

interface ChatInterfaceProps {
  sessionId: string | null
  onSessionChange: (sessionId: string) => void
}

export default function ChatInterface({ sessionId, onSessionChange }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [currentToolCall, setCurrentToolCall] = useState<ToolCall | null>(null)
  const [currentToolResult, setCurrentToolResult] = useState<ToolResult | null>(null)
  const [isMemoryEnabled, setIsMemoryEnabled] = useState(false)
  const [showHistory, setShowHistory] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])
  
  // Check memory status on mount
  useEffect(() => {
    const checkMemoryStatus = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/memory/stats`)
        if (response.ok) {
          const data = await response.json()
          setIsMemoryEnabled(data.enabled || false)
        }
      } catch (error) {
        console.error('Failed to check memory status:', error)
      }
    }
    
    checkMemoryStatus()
  }, [])

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return

    // Add user message to UI
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setCurrentToolCall(null)
    setCurrentToolResult(null)

    try {
      // Create a temporary assistant message for streaming
      const tempAssistantMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, tempAssistantMessage])

      // Use Server-Sent Events for streaming
      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/stream?message=${encodeURIComponent(content)}${sessionId ? `&session_id=${sessionId}` : ''}`
      )

      let assistantContent = ''
      let messageId = tempAssistantMessage.id
      let toolCalls: ToolCall[] = []
      let toolResults: ToolResult[] = []

      eventSource.addEventListener('session', (event) => {
        const data = JSON.parse(event.data)
        if (!sessionId && data.session_id) {
          onSessionChange(data.session_id)
        }
      })

      eventSource.addEventListener('features', (event) => {
        const data = JSON.parse(event.data)
        setIsMemoryEnabled(data.memory_enabled || false)
      })

      eventSource.addEventListener('message', (event) => {
        const data = JSON.parse(event.data)
        console.log('Message event:', data)  // Debug log
        if (data.type === 'text') {
          assistantContent += data.content
          setMessages(prev => 
            prev.map(msg => 
              msg.id === messageId 
                ? { ...msg, content: assistantContent, isStreaming: true }
                : msg
            )
          )
        }
      })

      eventSource.addEventListener('tool_call', (event) => {
        const data = JSON.parse(event.data)
        console.log('Tool call event:', data)  // Debug log
        const toolCall: ToolCall = {
          tool_name: data.tool,
          parameters: data.input,
          call_id: data.id
        }
        toolCalls.push(toolCall)
        setCurrentToolCall(toolCall)
      })

      eventSource.addEventListener('tool_result', (event) => {
        const data = JSON.parse(event.data)
        console.log('Tool result event:', data)  // Debug log
        const toolResult: ToolResult = {
          call_id: data.id,
          output: data.output
        }
        toolResults.push(toolResult)
        setCurrentToolResult(toolResult)
      })

      eventSource.addEventListener('done', (event) => {
        const data = JSON.parse(event.data)
        messageId = data.message_id
        
        // Update the message with final data
        setMessages(prev => 
          prev.map(msg => 
            msg.id === tempAssistantMessage.id 
              ? { 
                  ...msg, 
                  id: messageId,
                  content: assistantContent || data.content,  // Use accumulated content
                  tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
                  tool_results: toolResults.length > 0 ? toolResults : undefined,
                  isStreaming: false
                }
              : msg
          )
        )
        
        setCurrentToolCall(null)
        setCurrentToolResult(null)
        eventSource.close()
        setIsLoading(false)
      })

      eventSource.addEventListener('error', (event) => {
        console.error('SSE error:', event)
        eventSource.close()
        setIsLoading(false)
        
        // Remove temp message and show error
        setMessages(prev => prev.filter(msg => msg.id !== tempAssistantMessage.id))
        
        const errorMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Sorry, an error occurred while processing your message.',
          timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, errorMessage])
      })

    } catch (error) {
      console.error('Error sending message:', error)
      setIsLoading(false)
      
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  return (
    <div className="h-full flex bg-gray-100">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <div className="border-b bg-white shadow-sm px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-gray-800">Telly Chat</h1>
            {sessionId && (
              <span className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">
                Session: {sessionId.slice(0, 8)}...
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <MemoryToggle 
              isMemoryEnabled={isMemoryEnabled}
              onToggle={(enabled) => setIsMemoryEnabled(enabled)}
            />
            {isMemoryEnabled && (
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title={showHistory ? 'Hide conversation history' : 'Show conversation history'}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d={showHistory 
                      ? "M13 5l7 7-7 7M5 5l7 7-7 7" 
                      : "M11 19l-7-7 7-7m8 14l-7-7 7-7"} 
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
        
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          <MessageList messages={messages} />
          {(currentToolCall || currentToolResult) && (
            <ToolExecution 
              toolCall={currentToolCall}
              toolResult={currentToolResult}
            />
          )}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input Area */}
        <div className="border-t bg-white px-4 py-4">
          <InputBox 
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
          />
        </div>
      </div>
      
      {/* Conversation History Sidebar */}
      {isMemoryEnabled && showHistory && (
        <div className="w-96 border-l bg-white shadow-lg overflow-hidden flex flex-col animate-slide-in">
          <ConversationHistory 
            sessionId={sessionId} 
            isMemoryEnabled={isMemoryEnabled}
          />
        </div>
      )}
    </div>
  )
}