import { useState, useEffect } from 'react'
import { Clock, MessageSquare, Brain, ChevronDown, ChevronRight, Search, Calendar, Tag } from 'lucide-react'

interface Episode {
  id: string
  title: string
  type: string
  start_time: string
  end_time: string | null
  participants: string[]
  events: any[]
  outcome: string | null
  metadata: any
}

interface ConversationEvent {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface ConversationHistoryProps {
  sessionId: string | null
  isMemoryEnabled: boolean
}

export default function ConversationHistory({ sessionId, isMemoryEnabled }: ConversationHistoryProps) {
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [activeEpisodes, setActiveEpisodes] = useState<Episode[]>([])
  const [selectedEpisode, setSelectedEpisode] = useState<string | null>(null)
  const [conversations, setConversations] = useState<ConversationEvent[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [expandedEpisodes, setExpandedEpisodes] = useState<Set<string>>(new Set())
  const [insights, setInsights] = useState<any>(null)

  // Fetch episodes when memory is enabled
  useEffect(() => {
    if (isMemoryEnabled && sessionId) {
      fetchSessionEpisodes()
      fetchActiveEpisodes()
      fetchInsights()
      
      // Set up periodic refresh for active episodes
      const interval = setInterval(() => {
        fetchActiveEpisodes()
        fetchSessionEpisodes()
      }, 5000) // Refresh every 5 seconds
      
      return () => clearInterval(interval)
    }
  }, [isMemoryEnabled, sessionId])

  const fetchSessionEpisodes = async () => {
    if (!sessionId) return
    
    try {
      console.log('Fetching episodes for session:', sessionId)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/episodes/session/${sessionId}`)
      console.log('Response status:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('Episodes data:', data)
        setEpisodes(data.episodes || [])
      } else {
        const errorText = await response.text()
        console.error('Failed to fetch episodes:', response.status, errorText)
      }
    } catch (error) {
      console.error('Failed to fetch episodes:', error)
    }
  }

  const fetchActiveEpisodes = async () => {
    try {
      console.log('Fetching active episodes...')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/episodes/active`)
      
      if (response.ok) {
        const data = await response.json()
        console.log('Active episodes data:', data)
        setActiveEpisodes(data.active_episodes || [])
      } else {
        const errorText = await response.text()
        console.error('Failed to fetch active episodes:', response.status, errorText)
      }
    } catch (error) {
      console.error('Failed to fetch active episodes:', error)
    }
  }

  const fetchInsights = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/episodes/insights`)
      if (response.ok) {
        const data = await response.json()
        setInsights(data)
      }
    } catch (error) {
      console.error('Failed to fetch insights:', error)
    }
  }

  const fetchEpisodeConversations = async (episodeId: string) => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/episodes/${episodeId}`)
      if (response.ok) {
        const episode = await response.json()
        
        // Extract conversations from events
        const convos: ConversationEvent[] = []
        episode.events.forEach((event: any) => {
          if (event.event_type === 'user_message') {
            convos.push({
              role: 'user',
              content: event.data.content,
              timestamp: event.timestamp
            })
          } else if (event.event_type === 'assistant_response') {
            convos.push({
              role: 'assistant',
              content: event.data.content,
              timestamp: event.timestamp
            })
          }
        })
        
        setConversations(convos)
      }
    } catch (error) {
      console.error('Failed to fetch episode:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const searchEpisodes = async () => {
    if (!searchQuery.trim()) {
      fetchSessionEpisodes()
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/episodes/search?query=${encodeURIComponent(searchQuery)}&limit=10`
      )
      if (response.ok) {
        const data = await response.json()
        setEpisodes(data.results || [])
      }
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleEpisode = (episodeId: string) => {
    const newExpanded = new Set(expandedEpisodes)
    if (newExpanded.has(episodeId)) {
      newExpanded.delete(episodeId)
      if (selectedEpisode === episodeId) {
        setSelectedEpisode(null)
        setConversations([])
      }
    } else {
      newExpanded.add(episodeId)
      setSelectedEpisode(episodeId)
      fetchEpisodeConversations(episodeId)
    }
    setExpandedEpisodes(newExpanded)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit'
    })
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === today.toDateString()) {
      return 'Today'
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday'
    } else {
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
      })
    }
  }

  // Format episode title to be prettier
  const formatTitle = (title: string) => {
    // Remove "Chat: " prefix if present
    let formatted = title.replace(/^Chat:\s*/i, '')
    
    // Handle YouTube URLs - extract video title or show domain
    formatted = formatted.replace(
      /https?:\/\/(www\.)?youtube\.com\/watch\?v=([\w-]+)/g,
      'YouTube Video'
    )
    
    // Handle other URLs - show just the domain
    formatted = formatted.replace(
      /https?:\/\/(www\.)?([^\/]+)(\/[^\s]*)?/g, 
      (match, www, domain) => domain
    )
    
    // Capitalize first letter
    formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1)
    
    // Clean up any trailing ellipsis from original truncation
    formatted = formatted.replace(/\.\.\.+$/, '')
    
    // Limit length and add ellipsis if needed
    if (formatted.length > 40) {
      formatted = formatted.substring(0, 37) + '...'
    }
    
    return formatted
  }

  const getEpisodeIcon = (type: string) => {
    switch (type) {
      case 'learning':
        return '📚'
      case 'problem_solving':
        return '🔧'
      case 'task_completion':
        return '✅'
      case 'creative':
        return '🎨'
      default:
        return '💬'
    }
  }

  const getEpisodeColor = (type: string) => {
    switch (type) {
      case 'learning':
        return 'bg-blue-50 border-blue-200 text-blue-700'
      case 'problem_solving':
        return 'bg-orange-50 border-orange-200 text-orange-700'
      case 'task_completion':
        return 'bg-green-50 border-green-200 text-green-700'
      case 'creative':
        return 'bg-purple-50 border-purple-200 text-purple-700'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700'
    }
  }

  if (!isMemoryEnabled) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-600" />
            Conversation History
          </h3>
          {insights && (
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <MessageSquare className="w-4 h-4" />
                {insights.total_episodes} sessions
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {Math.round(insights.average_episode_duration / 60)}m avg
              </span>
            </div>
          )}
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && searchEpisodes()}
            className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Episodes List */}
      <div className="max-h-96 overflow-y-auto">
        {/* Active Episodes */}
        {activeEpisodes.length > 0 && (
          <div className="p-2 bg-gray-50 border-b border-gray-200">
            <p className="text-xs font-medium text-gray-700 px-2 py-1">Active Now</p>
            {activeEpisodes.map(episode => (
              <div
                key={episode.id}
                className={`mx-2 my-1 rounded-lg border ${
                  expandedEpisodes.has(episode.id) ? 'border-gray-300 shadow-sm' : 'border-gray-200 shadow-sm'
                }`}
              >
                <button
                  onClick={() => toggleEpisode(episode.id)}
                  className={`w-full p-3 text-left rounded-lg transition-colors ${
                    expandedEpisodes.has(episode.id) ? 'bg-gray-50' : 'bg-white hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-2 flex-1">
                      <span className="text-lg">{getEpisodeIcon(episode.type)}</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{formatTitle(episode.title)}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs text-gray-600">
                            Started {formatTime(episode.start_time)}
                          </span>
                          <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            <span className="text-xs text-green-700 font-medium">Live</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center ml-2">
                      {expandedEpisodes.has(episode.id) ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </div>
                </button>

                {/* Expanded Conversation for Active Episode */}
                {expandedEpisodes.has(episode.id) && (
                  <div className="border-t border-gray-100 p-3 bg-gray-50">
                    {isLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
                      </div>
                    ) : conversations.length > 0 ? (
                      <div className="space-y-3 max-h-64 overflow-y-auto">
                        {conversations.map((conv, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg ${
                              conv.role === 'user' 
                                ? 'bg-blue-50 ml-8' 
                                : 'bg-white mr-8 border border-gray-200'
                            }`}
                          >
                            <div className="flex items-start justify-between mb-1">
                              <span className={`text-xs font-medium ${
                                conv.role === 'user' ? 'text-blue-700' : 'text-gray-700'
                              }`}>
                                {conv.role === 'user' ? 'You' : 'Assistant'}
                              </span>
                              <span className="text-xs text-gray-500">
                                {formatTime(conv.timestamp)}
                              </span>
                            </div>
                            <p className="text-sm text-gray-900 whitespace-pre-wrap line-clamp-3">
                              {conv.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-gray-500 py-4 text-sm">
                        No conversation content available
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Past Episodes */}
        <div className="p-2">
          {episodes.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              No conversation history yet
            </p>
          ) : (
            [...episodes].reverse().map(episode => (
              <div
                key={episode.id}
                className="mb-2 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <span className="text-lg mt-0.5">{getEpisodeIcon(episode.type)}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 line-clamp-1">
                      {formatTitle(episode.title)}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-gray-600 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(episode.start_time)}
                      </span>
                      <span className="text-xs text-gray-600 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatTime(episode.start_time)}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${getEpisodeColor(episode.type)}`}>
                        {episode.type.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Insights Footer */}
      {insights && insights.common_topics && Object.keys(insights.common_topics).length > 0 && (
        <div className="p-3 bg-gray-50 border-t border-gray-200">
          <p className="text-xs font-medium text-gray-700 mb-2">Common Topics</p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(insights.common_topics).slice(0, 5).map(([topic, count]) => (
              <span
                key={topic}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-white border border-gray-200 rounded-full"
              >
                <Tag className="w-3 h-3" />
                {topic}
                <span className="text-gray-500">({count})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}