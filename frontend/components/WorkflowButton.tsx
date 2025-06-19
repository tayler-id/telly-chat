import { useState } from 'react'
import { PlayCircle, Loader2, CheckCircle, XCircle } from 'lucide-react'
import axios from 'axios'

interface WorkflowButtonProps {
  youtubeUrl?: string
  onComplete?: (result: any) => void
}

export default function WorkflowButton({ youtubeUrl, onComplete }: WorkflowButtonProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [status, setStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle')
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string>('')

  const runWorkflow = async () => {
    // Extract YouTube URL from the message if not provided
    let url = youtubeUrl
    if (!url) {
      // Try to find YouTube URL in the page
      const urlMatch = document.body.innerText.match(
        /https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/
      )
      if (urlMatch) {
        url = urlMatch[0]
      }
    }

    if (!url) {
      setError('No YouTube URL found')
      setStatus('error')
      return
    }

    setIsRunning(true)
    setStatus('running')
    setError('')

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/workflows/youtube-analysis`,
        null,
        { params: { url } }
      )

      if (response.data.success) {
        setStatus('success')
        setResult(response.data)
        onComplete?.(response.data)
      } else {
        setStatus('error')
        setError(response.data.errors?.[0]?.error || 'Workflow failed')
      }
    } catch (err: any) {
      setStatus('error')
      setError(err.response?.data?.detail || err.message || 'Failed to run workflow')
    } finally {
      setIsRunning(false)
    }
  }

  const getButtonContent = () => {
    switch (status) {
      case 'running':
        return (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Running Analysis...</span>
          </>
        )
      case 'success':
        return (
          <>
            <CheckCircle className="w-4 h-4" />
            <span>Analysis Complete</span>
          </>
        )
      case 'error':
        return (
          <>
            <XCircle className="w-4 h-4" />
            <span>Analysis Failed</span>
          </>
        )
      default:
        return (
          <>
            <PlayCircle className="w-4 h-4" />
            <span>Run Full Analysis</span>
          </>
        )
    }
  }

  const getButtonClass = () => {
    const base = "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
    switch (status) {
      case 'running':
        return `${base} bg-blue-500 text-white cursor-not-allowed`
      case 'success':
        return `${base} bg-green-500 text-white hover:bg-green-600`
      case 'error':
        return `${base} bg-red-500 text-white hover:bg-red-600`
      default:
        return `${base} bg-purple-500 text-white hover:bg-purple-600`
    }
  }

  return (
    <div className="space-y-2">
      <button
        onClick={runWorkflow}
        disabled={isRunning}
        className={getButtonClass()}
        title="Run complete YouTube analysis workflow"
      >
        {getButtonContent()}
      </button>
      
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
      
      {result && status === 'success' && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-semibold mb-2">Workflow Complete</h4>
          <p className="text-sm text-gray-600">
            Workflow ID: <code className="bg-gray-200 px-1 rounded">{result.workflow_id}</code>
          </p>
          {result.report && (
            <details className="mt-2">
              <summary className="cursor-pointer text-sm text-blue-600 hover:text-blue-800">
                View Report
              </summary>
              <pre className="mt-2 p-2 bg-white rounded text-xs overflow-auto max-h-96">
                {result.report}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}