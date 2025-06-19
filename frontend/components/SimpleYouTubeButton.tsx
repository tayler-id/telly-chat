import { useState } from 'react'
import { Youtube, Loader2, CheckCircle, XCircle } from 'lucide-react'
import axios from 'axios'

interface SimpleYouTubeButtonProps {
  youtubeUrl?: string
  onComplete?: (result: any) => void
}

export default function SimpleYouTubeButton({ youtubeUrl, onComplete }: SimpleYouTubeButtonProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [status, setStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle')
  const [result, setResult] = useState<any>(null)

  const processVideo = async () => {
    // Find YouTube URL
    let url = youtubeUrl
    if (!url) {
      const urlMatch = document.body.innerText.match(
        /https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/
      )
      if (urlMatch) {
        url = urlMatch[0]
      }
    }

    if (!url) {
      setStatus('error')
      setResult({ error: 'No YouTube URL found' })
      return
    }

    setIsProcessing(true)
    setStatus('processing')

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/youtube/process`,
        null,
        { params: { url } }
      )

      setStatus('success')
      setResult(response.data)
      onComplete?.(response.data)
    } catch (err: any) {
      setStatus('error')
      setResult({ error: err.response?.data?.detail || err.message })
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="inline-flex flex-col gap-2">
      <button
        onClick={processVideo}
        disabled={isProcessing}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
          ${isProcessing ? 'bg-blue-500 text-white cursor-not-allowed' : 
            status === 'success' ? 'bg-green-500 text-white hover:bg-green-600' :
            status === 'error' ? 'bg-red-500 text-white hover:bg-red-600' :
            'bg-purple-500 text-white hover:bg-purple-600'}
        `}
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Processing...</span>
          </>
        ) : status === 'success' ? (
          <>
            <CheckCircle className="w-4 h-4" />
            <span>Saved!</span>
          </>
        ) : status === 'error' ? (
          <>
            <XCircle className="w-4 h-4" />
            <span>Failed</span>
          </>
        ) : (
          <>
            <Youtube className="w-4 h-4" />
            <span>Process Video</span>
          </>
        )}
      </button>
      
      {result && (
        <div className={`text-sm ${status === 'error' ? 'text-red-600' : 'text-gray-600'}`}>
          {status === 'error' ? result.error : 
           `✓ ${result.title} - ${result.summary?.substring(0, 100)}...`}
        </div>
      )}
    </div>
  )
}