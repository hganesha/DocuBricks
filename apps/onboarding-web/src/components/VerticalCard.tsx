import { cn } from '../lib/utils'
import Badge from './Badge'

interface VerticalCardProps {
  title: string
  docTypes: string[]
  fieldCount?: string
  available?: string
  selected?: boolean
  onClick?: () => void
  className?: string
}

export default function VerticalCard({
  title,
  docTypes,
  fieldCount,
  available,
  selected = false,
  onClick,
  className,
}: VerticalCardProps) {
  const isSoon = Boolean(available)

  return (
    <div
      onClick={isSoon ? undefined : onClick}
      className={cn(
        'relative flex flex-col gap-3 p-5 border rounded-xl select-none transition-all duration-150',
        isSoon
          ? 'opacity-60 cursor-default pointer-events-none border-gray-200 bg-gray-50'
          : selected
          ? 'cursor-pointer border-2 border-accent-700 bg-accent-50'
          : 'cursor-pointer border-gray-200 bg-white hover:border-gray-300',
        className,
      )}
    >
      {/* Soon badge — top-right corner */}
      {isSoon && (
        <div className="absolute top-3 right-3">
          <Badge variant="soon">{available}</Badge>
        </div>
      )}

      {/* Title */}
      <h3 className="font-semibold text-base text-gray-900 tracking-tighter">
        {title}
      </h3>

      {/* Doc types */}
      <div className="flex flex-col gap-0.5">
        {docTypes.map((doc) => (
          <span key={doc} className="text-xs text-gray-500">
            {doc}
          </span>
        ))}
      </div>

      {/* Field count */}
      {fieldCount && (
        <span className="text-xs text-accent-700 font-medium mt-auto">
          {fieldCount}
        </span>
      )}
    </div>
  )
}
