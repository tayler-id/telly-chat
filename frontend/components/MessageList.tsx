import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { format } from 'date-fns'
import { User, Bot, Youtube } from 'lucide-react'
import { Message } from '../services/api'
import SaveButton from './SaveButton'
import ToolResultDisplay from './ToolResultDisplay'

interface MessageListProps {
  messages: Message[]
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="px-4 py-6 space-y-6">
      {messages.length === 0 && (
        <div className="text-center py-12">
          <Youtube className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Welcome to Telly Chat
          </h3>
          <p className="text-gray-500 max-w-md mx-auto">
            Share a YouTube URL and I'll extract the transcript and help you create actionable plans from the video content.
          </p>
        </div>
      )}
      
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-4 ${
            message.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          {message.role === 'assistant' && (
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          )}
          
          <div
            className={`max-w-3xl ${
              message.role === 'user'
                ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm'
                : 'bg-gray-100 text-gray-900 rounded-2xl rounded-tl-sm'
            } px-4 py-3 shadow-sm`}
          >
            {message.role === 'user' ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="prose prose-sm max-w-none prose-gray prose-pre:max-w-full prose-pre:overflow-x-auto">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    pre: ({ node, ...props }) => (
                      <pre className="bg-gray-50 text-gray-800 p-4 rounded-lg overflow-x-auto max-h-96 overflow-y-auto border border-gray-200" {...props} />
                    ),
                    code: ({ node, inline, ...props }) => 
                      inline ? (
                        <code className="bg-gray-200 text-gray-800 px-1 py-0.5 rounded" {...props} />
                      ) : (
                        <code {...props} />
                      ),
                    blockquote: ({ node, ...props }) => (
                      <blockquote className="border-l-4 border-blue-400 pl-4 my-3 text-gray-700 bg-blue-50 py-3 pr-4 rounded-r text-sm leading-relaxed max-h-96 overflow-y-auto" {...props} />
                    ),
                    ul: ({ node, ...props }) => (
                      <ul className="list-disc list-inside space-y-1" {...props} />
                    ),
                    ol: ({ node, ...props }) => (
                      <ol className="list-decimal list-inside space-y-1" {...props} />
                    ),
                    h3: ({ node, ...props }) => (
                      <h3 className="text-lg font-semibold mt-4 mb-2" {...props} />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
                {message.isStreaming && (
                  <span className="inline-block w-2 h-4 bg-gray-600 animate-pulse ml-1" />
                )}
              </div>
            )}
            
            {/* Show tool results if available */}
            {message.tool_results && message.tool_results.length > 0 && (
              <ToolResultDisplay 
                toolResults={message.tool_results} 
                messageId={message.id}
              />
            )}
            
            {message.tool_calls && message.tool_calls.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Used tools:</p>
                {message.tool_calls.map((tool) => (
                  <div key={tool.call_id} className="text-xs text-gray-600">
                    <Youtube className="w-3 h-3 inline mr-1" />
                    {tool.tool_name}
                  </div>
                ))}
              </div>
            )}
            
            <div className="mt-2 text-xs opacity-70">
              {format(new Date(message.timestamp), 'HH:mm')}
            </div>
            
            {message.role === 'assistant' && <SaveButton message={message} />}
          </div>
          
          {message.role === 'user' && (
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                <User className="w-5 h-5 text-gray-600" />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}