import { useState, useEffect } from 'react'
import ChatInterface from '../components/ChatInterface'
import { api } from '../services/api'

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Check backend health
    api.checkHealth()
      .then(() => setIsConnected(true))
      .catch(() => setIsConnected(false))
  }, [])

  return (
    <div className="h-full flex flex-col">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold">Telly Chat</h1>
              <span className="ml-3 text-sm text-gray-500">
                YouTube Transcript AI Assistant
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
                <span className="text-sm text-gray-600">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>
      
      <main className="flex-1 overflow-hidden">
        <ChatInterface 
          sessionId={sessionId} 
          onSessionChange={setSessionId}
        />
      </main>
    </div>
  )
}