import { ToolResult } from '../services/api'
import SaveButton from './SaveButton'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ToolResultDisplayProps {
  toolResults: ToolResult[]
  messageId: string
}

export default function ToolResultDisplay({ toolResults, messageId }: ToolResultDisplayProps) {
  if (!toolResults || toolResults.length === 0) return null
  
  // Find YouTube transcript results
  const transcriptResults = toolResults.filter(tr => 
    tr.output && (
      tr.output.includes('Video Information') || 
      tr.output.includes('Transcript') ||
      tr.output.includes('Action Plan')
    )
  )
  
  if (transcriptResults.length === 0) return null
  
  return (
    <div className="mt-4 space-y-4">
      {transcriptResults.map((result, idx) => (
        <div key={`${result.call_id}-${idx}`} className="border-t pt-4">
          <div className="prose prose-sm max-w-none prose-gray">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {result.output}
            </ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  )
}