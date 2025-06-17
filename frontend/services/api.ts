import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ToolCall {
  tool_name: string
  parameters: any
  call_id: string
}

export interface ToolResult {
  call_id: string
  output: any
  error?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  tool_calls?: ToolCall[]
  tool_results?: ToolResult[]
  isStreaming?: boolean
  metadata?: {
    hasTranscript?: boolean
    hasActionPlan?: boolean
    videoId?: string
  }
}

export interface Session {
  id: string
  messages: Message[]
  created_at: string
  updated_at: string
}

export const api = {
  async checkHealth(): Promise<boolean> {
    try {
      const response = await axios.get(`${API_URL}/health`)
      return response.data.status === 'healthy'
    } catch {
      return false
    }
  },

  async sendMessage(message: string, sessionId?: string): Promise<{
    message: Message
    sessionId: string
  }> {
    const response = await axios.post(`${API_URL}/chat`, {
      message,
      session_id: sessionId,
      stream: false
    })
    return response.data
  },

  async getSession(sessionId: string): Promise<Session> {
    const response = await axios.get(`${API_URL}/sessions/${sessionId}`)
    return response.data
  },

  async listSessions(): Promise<Session[]> {
    const response = await axios.get(`${API_URL}/sessions`)
    return response.data.sessions
  },

  async deleteSession(sessionId: string): Promise<void> {
    await axios.delete(`${API_URL}/sessions/${sessionId}`)
  }
}