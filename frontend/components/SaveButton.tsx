import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { Message } from '../services/api'
import axios from 'axios'

interface SaveButtonProps {
  message: Message
}

export default function SaveButton({ message }: SaveButtonProps) {
  const [isLoading, setIsLoading] = useState(false)
  
  const handleSave = async () => {
    setIsLoading(true)
    
    try {
      // Extract video ID from content if available
      const videoIdMatch = message.content.match(/Video ID:.*?`([^`]+)`/)
      const videoId = videoIdMatch ? videoIdMatch[1] : 'youtube-transcript'
      
      // Create filename with timestamp
      const timestamp = new Date().toISOString().split('T')[0]
      const filename = `${videoId}-${timestamp}.md`
      
      // Check if we have a YouTube video with a truncated transcript
      const urlMatch = message.content.match(/https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
      const hasTranscriptPreview = message.content.includes('📊 **Full transcript:') || 
                                   message.content.includes('**Full transcript:') || 
                                   message.content.includes('Full transcript:') || 
                                   (message.content.includes('### 📝 Transcript') && 
                                    message.content.includes('...'))
      
      console.log('URL Match:', urlMatch ? urlMatch[0] : 'none')
      console.log('Has Transcript Preview:', hasTranscriptPreview)
      console.log('Looking for Full transcript indicator:', message.content.includes('Full transcript:'))
      console.log('Checking for ...:', message.content.includes('...'))
      console.log('Checking for emoji+text:', message.content.includes('📊 **Full transcript:'))
      console.log('Message content preview:', message.content.substring(0, 500))
      
      let finalContent = ''
      
      if (urlMatch && hasTranscriptPreview) {
        // Fetch the full transcript from the backend
        try {
          console.log('Fetching full transcript for URL:', urlMatch[0])
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/youtube/transcript?url=${encodeURIComponent(urlMatch[0])}`
          )
          
          if (response.data.success) {
            // Use the full transcript from the backend
            finalContent = `# YouTube Video Analysis\n\n`
            finalContent += `**Date:** ${new Date().toLocaleDateString()}\n\n`
            finalContent += response.data.content
            
            // Add metadata if available
            if (message.tool_calls && message.tool_calls.length > 0) {
              finalContent += `\n\n---\n\n## Analysis Details\n\n`
              finalContent += `**Tools Used:** ${message.tool_calls.map(tc => tc.tool_name).join(', ')}\n`
            }
            
            console.log('Full content prepared, length:', finalContent.length)
          } else {
            throw new Error(response.data.error || 'Failed to fetch transcript')
          }
        } catch (error) {
          console.error('Failed to fetch full transcript:', error)
          // Fall back to using the truncated content
          finalContent = `# YouTube Video Analysis\n\n`
          finalContent += `**Date:** ${new Date().toLocaleDateString()}\n\n`
          finalContent += message.content
        }
      } else {
        // No truncated transcript, use the message content as is
        finalContent = `# YouTube Video Analysis\n\n`
        finalContent += `**Date:** ${new Date().toLocaleDateString()}\n\n`
        finalContent += message.content
        
        // Add metadata if available
        if (message.tool_calls && message.tool_calls.length > 0) {
          finalContent += `\n\n---\n\n## Analysis Details\n\n`
          finalContent += `**Tools Used:** ${message.tool_calls.map(tc => tc.tool_name).join(', ')}\n`
        }
      }
      
      // Create blob and download
      const blob = new Blob([finalContent], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error saving file:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  // Only show save button for assistant messages with substantial content
  const hasTranscript = message.content.includes('### 📹 Video Information') || 
                       message.content.includes('### 📝 Transcript') ||
                       message.content.includes('### 📋 Action Plan') ||
                       message.content.includes('youtube.com') ||
                       message.content.includes('youtu.be')
  
  // Also check if message has tool calls
  const hasYouTubeTool = message.tool_calls?.some(tc => tc.tool_name === 'youtube_transcript')
  
  if (message.role !== 'assistant' || (!hasTranscript && !hasYouTubeTool)) {
    return null
  }
  
  return (
    <button
      onClick={handleSave}
      disabled={isLoading}
      className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg transition-colors mt-4 shadow-sm"
      title="Save transcript and action plan as markdown"
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          Fetching Full Transcript...
        </>
      ) : (
        <>
          <Download className="w-4 h-4" />
          Save Transcript & Action Plan
        </>
      )}
    </button>
  )
}