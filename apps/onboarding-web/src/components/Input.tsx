import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { cn } from '../lib/utils'

interface InputProps {
  label?: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
  error?: string
  hint?: string
  prefix?: string
  className?: string
  autoFocus?: boolean
}

export default function Input({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  error,
  hint,
  prefix,
  className,
  autoFocus = false,
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false)

  const isPassword = type === 'password'
  const resolvedType = isPassword ? (showPassword ? 'text' : 'password') : type
  const hasError = Boolean(error)

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label && (
        <label className="text-sm font-medium text-gray-700">{label}</label>
      )}

      <div className="relative flex items-center">
        {prefix && (
          <span className="absolute left-3 text-sm text-gray-400 pointer-events-none select-none">
            {prefix}
          </span>
        )}

        <input
          type={resolvedType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className={cn(
            'w-full h-11 px-3 border rounded-lg text-sm text-gray-900 bg-white',
            'focus:outline-none focus:ring-2 focus:border-transparent transition-all',
            'placeholder:text-gray-400',
            hasError
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-200 focus:ring-accent-500',
            prefix ? 'pl-8' : '',
            isPassword ? 'pr-10' : '',
          )}
        />

        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="absolute right-3 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none"
            tabIndex={-1}
          >
            {showPassword ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-600 mt-1">{error}</p>
      )}

      {hint && !error && (
        <p className="text-xs text-gray-400 mt-1">{hint}</p>
      )}
    </div>
  )
}
