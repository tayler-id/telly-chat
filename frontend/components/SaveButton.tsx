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
      
      // More comprehensive check for truncated transcripts
      const hasTranscriptPreview = message.content.includes('📊 **Full transcript:') || 
                                   message.content.includes('**Full transcript:') || 
                                   message.content.includes('Full transcript:') || 
                                   message.content.includes('💾 **Click \'Save Transcript & Action Plan\'') ||
                                   message.content.includes('Click \'Save Transcript & Action Plan\'') ||
                                   (message.content.includes('### 📝 Transcript') && 
                                    message.content.includes('...')) ||
                                   (message.content.includes('*Showing first') && 
                                    message.content.includes('characters of transcript:*'))
      
      console.log('URL Match:', urlMatch ? urlMatch[0] : 'none')
      console.log('Has Transcript Preview:', hasTranscriptPreview)
      console.log('Looking for Full transcript indicator:', message.content.includes('Full transcript:'))
      console.log('Checking for ...:', message.content.includes('...'))
      console.log('Checking for emoji+text:', message.content.includes('📊 **Full transcript:'))
      console.log('Message content preview:', message.content.substring(0, 500))
      
      let finalContent = ''
      
      // Also check if the user's original message had a YouTube URL (for tool calls)
      let youtubeUrl = urlMatch ? urlMatch[0] : null
      
      // If we have a tool call for youtube_transcript, try to extract URL from parameters
      if (!youtubeUrl && message.tool_calls) {
        const youtubeTool = message.tool_calls.find(tc => tc.tool_name === 'youtube_transcript')
        if (youtubeTool && youtubeTool.parameters && youtubeTool.parameters.url) {
          youtubeUrl = youtubeTool.parameters.url
          console.log('Extracted URL from tool call:', youtubeUrl)
        }
      }
      
      // Always try to fetch full transcript if we have a YouTube URL, regardless of truncation detection
      if (youtubeUrl) {
        try {
          console.log('Fetching full transcript for URL:', youtubeUrl)
          console.log('Has transcript preview (truncation detected):', hasTranscriptPreview)
          
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/youtube/transcript?url=${encodeURIComponent(youtubeUrl)}`
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
            
            // Extract title, transcript, and action plan for storage
            let videoTitle = 'YouTube Video Analysis'
            let transcript = ''
            let actionPlan = ''
            
            // Extract title
            const titleMatch = response.data.content.match(/### 📹 Video Information[\s\S]*?- \*\*Title:\*\* (.+)/)
            if (titleMatch) {
              videoTitle = titleMatch[1]
            }
            
            // Extract full transcript
            const transcriptMatch = response.data.content.match(/### 📝 Full Transcript\s*\n\s*```\s*\n([\s\S]*?)\n```/)
            if (transcriptMatch) {
              transcript = transcriptMatch[1].trim()
            }
            
            // Extract action plan
            const actionPlanMatch = response.data.content.match(/### 📋 Action Plan\s*\n\s*([\s\S]*?)(?=\n\n###|$)/)
            if (actionPlanMatch) {
              actionPlan = actionPlanMatch[1].trim()
            }
            
            // Save to transcript store
            if (transcript && actionPlan && youtubeUrl) {
              try {
                const saveResponse = await axios.post(
                  `${process.env.NEXT_PUBLIC_API_URL}/transcripts/save`,
                  {
                    url: youtubeUrl,
                    title: videoTitle,
                    transcript: transcript,
                    action_plan: actionPlan,
                    summary: transcript.substring(0, 500) + '...',
                  }
                )
                
                if (saveResponse.data.success) {
                  console.log('Transcript saved to store:', saveResponse.data)
                }
              } catch (saveError) {
                console.error('Error saving to transcript store:', saveError)
                // Continue with file download even if store save fails
              }
            }
          } else {
            throw new Error(response.data.error || 'Failed to fetch transcript')
          }
        } catch (error) {
          console.error('Failed to fetch full transcript:', error)
          // Fall back to using the displayed content
          finalContent = `# YouTube Video Analysis\n\n`
          finalContent += `**Date:** ${new Date().toLocaleDateString()}\n\n`
          finalContent += message.content
          
          // Add metadata if available
          if (message.tool_calls && message.tool_calls.length > 0) {
            finalContent += `\n\n---\n\n## Analysis Details\n\n`
            finalContent += `**Tools Used:** ${message.tool_calls.map(tc => tc.tool_name).join(', ')}\n`
          }
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
          Fetching Complete Transcript...
        </>
      ) : (
        <>
          <Download className="w-4 h-4" />
          Save Full Transcript & Action Plan
        </>
      )}
    </button>
  )
}