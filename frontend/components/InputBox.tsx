import { useState, KeyboardEvent } from 'react'
import { Send, Loader2 } from 'lucide-react'

interface InputBoxProps {
  onSendMessage: (message: string) => void
  isLoading: boolean
}

export default function InputBox({ onSendMessage, isLoading }: InputBoxProps) {
  const [input, setInput] = useState('')

  const handleSubmit = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input)
      setInput('')
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex gap-3 items-end max-w-4xl mx-auto w-full">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder="Share a YouTube URL or ask a question..."
        className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        rows={1}
        disabled={isLoading}
        style={{
          minHeight: '48px',
          maxHeight: '200px'
        }}
      />
      
      <button
        onClick={handleSubmit}
        disabled={!input.trim() || isLoading}
        className="flex-shrink-0 rounded-lg bg-blue-600 px-4 py-3 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Send className="w-5 h-5" />
        )}
      </button>
    </div>
  )
}