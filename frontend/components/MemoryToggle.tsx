import { useState, useEffect } from 'react'

interface MemoryToggleProps {
  isMemoryEnabled?: boolean
  onToggle?: (enabled: boolean) => void
}

export default function MemoryToggle({ isMemoryEnabled: propEnabled, onToggle }: MemoryToggleProps) {
  const [memoryEnabled, setMemoryEnabled] = useState(propEnabled || false)
  const [features, setFeatures] = useState<any>(null)
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [showInfo, setShowInfo] = useState(false)

  // Check feature availability on mount
  useEffect(() => {
    checkFeatures()
  }, [])
  
  // Sync with parent prop
  useEffect(() => {
    if (propEnabled !== undefined && propEnabled !== memoryEnabled) {
      setMemoryEnabled(propEnabled)
    }
  }, [propEnabled])

  // Poll memory stats when enabled
  useEffect(() => {
    if (memoryEnabled) {
      const interval = setInterval(fetchMemoryStats, 5000)
      fetchMemoryStats() // Initial fetch
      return () => clearInterval(interval)
    }
  }, [memoryEnabled])

  const checkFeatures = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/features`)
      const data = await response.json()
      setFeatures(data)
      setMemoryEnabled(data.features?.memory || false)
    } catch (error) {
      console.error('Error checking features:', error)
    }
  }

  const fetchMemoryStats = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/memory/stats`)
      const data = await response.json()
      if (data.enabled && data.stats) {
        setStats(data.stats)
      }
    } catch (error) {
      console.error('Error fetching memory stats:', error)
    }
  }

  const toggleMemory = async () => {
    setLoading(true)
    console.log('Toggling memory from', memoryEnabled, 'to', !memoryEnabled)
    console.log('API URL:', process.env.NEXT_PUBLIC_API_URL)
    
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL}/features/memory/toggle?enable=${!memoryEnabled}`
      console.log('Fetching:', url)
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      
      console.log('Response status:', response.status)
      console.log('Response ok:', response.ok)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Error response:', errorText)
        
        try {
          const error = JSON.parse(errorText)
          alert(error.detail || 'Failed to toggle memory')
        } catch {
          alert(`Failed to toggle memory: ${errorText}`)
        }
        return
      }

      const data = await response.json()
      console.log('Response data:', data)
      setMemoryEnabled(data.memory_enabled)
      
      // Notify parent component
      if (onToggle) {
        onToggle(data.memory_enabled)
      }
      
      if (data.memory_enabled) {
        fetchMemoryStats()
      } else {
        setStats(null)
      }
    } catch (error) {
      console.error('Error toggling memory:', error)
      console.error('Error details:', {
        message: error.message,
        stack: error.stack
      })
      alert(`Failed to toggle memory: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const clearMemory = async () => {
    if (!confirm('Are you sure you want to clear all memories?')) return
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/memory/clear`, {
        method: 'POST'
      })
      
      if (response.ok) {
        setStats(null)
        fetchMemoryStats()
      }
    } catch (error) {
      console.error('Error clearing memory:', error)
    }
  }

  // If features not available, don't show toggle
  if (!features?.available) {
    return null
  }

  return (
    <div className="relative">
      {/* Memory Toggle Button */}
      <button
        onClick={toggleMemory}
        disabled={loading}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
          memoryEnabled
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
        } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        title={memoryEnabled ? 'Memory is ON' : 'Memory is OFF'}
      >
        <span>{memoryEnabled ? '🧠' : '🧠'}</span>
        <span>{memoryEnabled ? 'Memory ON' : 'Memory OFF'}</span>
      </button>

      {/* Info Icon */}
      <button
        onClick={() => setShowInfo(!showInfo)}
        className="absolute -top-2 -right-2 w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center hover:bg-gray-200"
      >
        <span className="text-xs">ℹ️</span>
      </button>

      {/* Info Popup */}
      {showInfo && (
        <div className="absolute top-10 right-0 w-80 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50">
          <h3 className="font-semibold text-gray-900 mb-2">🧠 AI Memory System</h3>
          
          <div className="text-sm text-gray-600 space-y-2 mb-3">
            <p>When enabled, the AI will remember:</p>
            <ul className="list-disc list-inside ml-2">
              <li>Your name and preferences</li>
              <li>Previous conversations</li>
              <li>Important facts you share</li>
              <li>Context across messages</li>
            </ul>
          </div>

          {memoryEnabled && stats && (
            <div className="border-t pt-3">
              <h4 className="font-medium text-gray-800 mb-2">Memory Stats</h4>
              <div className="text-xs space-y-1">
                {stats.short_term && (
                  <div>
                    <span className="text-gray-500">Short-term:</span>{' '}
                    <span className="font-medium">{stats.short_term.total_memories || 0} memories</span>
                    {stats.short_term.utilization && (
                      <span className="text-gray-400"> ({Math.round(stats.short_term.utilization * 100)}% full)</span>
                    )}
                  </div>
                )}
                {stats.long_term && (
                  <div>
                    <span className="text-gray-500">Long-term:</span>{' '}
                    <span className="font-medium">{stats.long_term.total_memories || 0} memories</span>
                  </div>
                )}
                {stats.episodic && (
                  <div>
                    <span className="text-gray-500">Episodes:</span>{' '}
                    <span className="font-medium">{stats.episodic.total_episodes || 0} recorded</span>
                  </div>
                )}
              </div>

              {memoryEnabled && (
                <button
                  onClick={clearMemory}
                  className="mt-3 flex items-center gap-1 text-xs text-red-600 hover:text-red-700"
                >
                  <span>🗑️</span>
                  Clear Memory
                </button>
              )}
            </div>
          )}

          <div className="mt-3 pt-3 border-t">
            <p className="text-xs text-gray-500">
              Memory data is stored locally in <code className="bg-gray-100 px-1 rounded">./data/memory/</code>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}