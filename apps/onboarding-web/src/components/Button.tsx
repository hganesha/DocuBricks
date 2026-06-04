import React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '../lib/utils'

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md'
  loading?: boolean
  disabled?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
  className?: string
  children: React.ReactNode
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  onClick,
  type = 'button',
  className,
  children,
}: ButtonProps) {
  const isDisabled = disabled || loading

  const base =
    'inline-flex items-center justify-center font-medium text-sm rounded-lg transition-colors duration-150 select-none focus:outline-none'

  const variants = {
    primary:
      'bg-accent-700 text-white hover:bg-accent-800 disabled:opacity-50 disabled:cursor-not-allowed',
    secondary:
      'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed',
    ghost:
      'bg-transparent text-gray-500 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed',
  }

  const sizes = {
    md: variant === 'ghost' ? 'h-11 px-4' : 'h-11 px-6',
    sm: variant === 'ghost' ? 'h-9 px-3' : 'h-9 px-4',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={cn(base, variants[variant], sizes[size], className)}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        children
      )}
    </button>
  )
}
