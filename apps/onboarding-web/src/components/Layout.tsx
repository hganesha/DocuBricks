import React from 'react'
import ProgressBar from './ProgressBar'

interface LayoutProps {
  children: React.ReactNode
  step?: number
  totalSteps?: number
}

const STEP_LABELS = ['Project', 'Vertical', 'Workspace', 'Resources', 'Review']

export default function Layout({ children, step, totalSteps = 5 }: LayoutProps) {
  return (
    <div className="min-h-screen bg-white">
      {/* Progress bar — only when step is provided */}
      {step !== undefined && (
        <ProgressBar value={step / totalSteps} />
      )}

      {/* Step labels — only when step is provided */}
      {step !== undefined && (
        <div className="max-w-xl mx-auto px-6 pt-6 pb-0 flex gap-6 text-xs text-gray-400">
          {STEP_LABELS.map((s, i) => (
            <span
              key={s}
              className={i + 1 === step ? 'text-accent-700 font-medium' : ''}
            >
              {i + 1 < step ? '✓ ' : ''}
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Main content */}
      <main className="max-w-xl mx-auto px-6 py-12">
        {children}
      </main>
    </div>
  )
}
