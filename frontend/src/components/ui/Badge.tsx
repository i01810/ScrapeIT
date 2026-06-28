import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type Tone = 'zinc' | 'green' | 'amber' | 'red' | 'blue' | 'purple'

export function Badge({ tone = 'zinc', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        tone === 'zinc' && 'bg-zinc-50 text-zinc-700 ring-zinc-200',
        tone === 'green' && 'bg-emerald-50 text-emerald-800 ring-emerald-200',
        tone === 'amber' && 'bg-amber-50 text-amber-900 ring-amber-200',
        tone === 'red' && 'bg-rose-50 text-rose-800 ring-rose-200',
        tone === 'blue' && 'bg-sky-50 text-sky-900 ring-sky-200',
        tone === 'purple' && 'bg-violet-50 text-violet-900 ring-violet-200',
        className,
      )}
    >
      {children}
    </span>
  )
}
