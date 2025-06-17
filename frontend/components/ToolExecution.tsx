import { Youtube, Loader2, CheckCircle } from 'lucide-react'
import { ToolCall, ToolResult } from '../services/api'

interface ToolExecutionProps {
  toolCall: ToolCall | null
  toolResult: ToolResult | null
}

export default function ToolExecution({ toolCall, toolResult }: ToolExecutionProps) {
  if (!toolCall && !toolResult) return null

  return (
    <div className="px-4 pb-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-3xl mx-auto">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">
            {toolResult ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : (
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-blue-900">
              {toolCall?.tool_name === 'youtube_transcript' && 'Extracting YouTube Transcript'}
            </p>
            
            {toolCall && toolCall.parameters.url && (
              <p className="text-xs text-blue-700 mt-1 truncate">
                <Youtube className="w-3 h-3 inline mr-1" />
                {toolCall.parameters.url}
              </p>
            )}
            
            {toolResult && (
              <p className="text-xs text-green-700 mt-1">
                Transcript extracted successfully
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}