import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost'

export function Button({
  className,
  variant = 'secondary',
  leftIcon,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; leftIcon?: ReactNode }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition',
        variant === 'primary' && 'bg-zinc-900 text-white shadow-sm hover:bg-zinc-800',
        variant === 'secondary' && 'border border-zinc-200 bg-white text-zinc-900 hover:bg-zinc-50',
        variant === 'ghost' && 'text-zinc-700 hover:bg-zinc-100',
        props.disabled && 'cursor-not-allowed opacity-50 hover:bg-inherit',
        className,
      )}
      {...props}
    >
      {leftIcon}
      {children}
    </button>
  )
}
