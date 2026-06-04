import { cn } from '../lib/utils'

interface RadioOption {
  value: string
  label: string
  description?: string
}

interface RadioGroupProps {
  options: RadioOption[]
  value: string
  onChange: (v: string) => void
  layout?: 'vertical' | 'horizontal'
  className?: string
}

export default function RadioGroup({
  options,
  value,
  onChange,
  layout = 'vertical',
  className,
}: RadioGroupProps) {
  const isVertical = layout === 'vertical'

  return (
    <div
      className={cn(
        isVertical ? 'flex flex-col gap-2' : 'flex flex-row gap-3',
        className,
      )}
    >
      {options.map((option) => {
        const selected = option.value === value

        return (
          <div
            key={option.value}
            onClick={() => onChange(option.value)}
            className={cn(
              'flex items-start gap-3 border rounded-lg cursor-pointer transition-all duration-150',
              isVertical ? 'w-full py-3 px-4' : 'py-3 px-4',
              selected
                ? 'border-accent-700 bg-accent-50 text-accent-700'
                : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300',
            )}
          >
            {/* Circle indicator */}
            <div className="mt-0.5 shrink-0">
              {selected ? (
                <div className="w-4 h-4 rounded-full bg-accent-700 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                </div>
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
              )}
            </div>

            {/* Label + description */}
            <div className="flex flex-col">
              <span className="text-sm font-medium leading-tight">
                {option.label}
              </span>
              {option.description && (
                <span
                  className={cn(
                    'text-xs mt-0.5',
                    selected ? 'text-accent-700 opacity-80' : 'text-gray-400',
                  )}
                >
                  {option.description}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
