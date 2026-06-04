import React from 'react'
import { cn } from '../lib/utils'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'soon' | 'live' | 'coming'
}

export default function Badge({ children, variant = 'soon' }: BadgeProps) {
  const styles = {
    soon: 'bg-gray-100 text-gray-500',
    coming: 'bg-gray-100 text-gray-500',
    live: 'bg-green-50 text-green-700',
  }

  return (
    <span
      className={cn(
        'text-xs px-2 py-0.5 rounded-full font-medium',
        styles[variant],
      )}
    >
      {children}
    </span>
  )
}
