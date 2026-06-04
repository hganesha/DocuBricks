import { cn } from '../lib/utils'

interface ProgressBarProps {
  value: number
  className?: string
}

export default function ProgressBar({ value, className }: ProgressBarProps) {
  const clamped = Math.min(1, Math.max(0, value))

  return (
    <div
      className={cn('w-full h-[3px] bg-gray-100', className)}
      style={{ borderRadius: 0 }}
    >
      <div
        className="h-full bg-accent-700 transition-all duration-500 ease-out"
        style={{ width: `${clamped * 100}%`, borderRadius: 0 }}
      />
    </div>
  )
}
