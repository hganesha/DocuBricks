import { CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '../lib/utils'

interface StepItemProps {
  status: 'pending' | 'running' | 'complete' | 'failed'
  label: string
  elapsedMs?: number
  error?: string
}

export default function StepItem({ status, label, elapsedMs, error }: StepItemProps) {
  const showElapsed =
    (status === 'complete' || status === 'failed') && elapsedMs !== undefined

  return (
    <div className="flex items-start gap-3">
      {/* Left icon */}
      <div className="shrink-0 mt-0.5">
        {status === 'pending' && (
          <div className="w-5 h-5 rounded-full border-2 border-gray-200" />
        )}
        {status === 'running' && (
          <div className="w-5 h-5 rounded-full bg-accent-700 animate-pulse" />
        )}
        {status === 'complete' && (
          <CheckCircle2 className="w-5 h-5 text-green-500" />
        )}
        {status === 'failed' && (
          <XCircle className="w-5 h-5 text-red-500" />
        )}
      </div>

      {/* Middle: label + error */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-sm',
            status === 'complete'
              ? 'text-gray-900 font-medium'
              : status === 'failed'
              ? 'text-red-700'
              : 'text-gray-700',
          )}
        >
          {label}
        </p>
        {status === 'failed' && error && (
          <p className="text-xs text-red-500 mt-0.5">{error}</p>
        )}
      </div>

      {/* Right: elapsed time */}
      {showElapsed && (
        <span className="text-xs text-gray-400 tabular-nums shrink-0">
          {((elapsedMs ?? 0) / 1000).toFixed(1)}s
        </span>
      )}
    </div>
  )
}
