import type { ComponentType, ReactNode } from 'react'
import { Link, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { Building2, CreditCard, LayoutDashboard, ReceiptText, ShoppingBag, Sparkles } from 'lucide-react'
import AskAIPage from './pages/AskAIPage'
import OrdersPage from './pages/OrdersPage'
import PaymentsPage from './pages/PaymentsPage'
import { cn } from './lib/cn'

const PAGE_META: Record<string, { title: string; subtitle?: string }> = {
  '/orders': { title: 'Order tracking & payment status', subtitle: 'Finance system' },
  '/payments': { title: 'Payments overview', subtitle: 'Finance system' },
  '/ask-ai': { title: 'AskAI assistant' },
}

function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const pageMeta = PAGE_META[location.pathname] ?? PAGE_META['/orders']
  const isAskAi = location.pathname === '/ask-ai'
  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-zinc-50 text-zinc-900">
      <div className="mx-auto flex min-h-0 w-full max-w-[1400px] flex-1 gap-4 p-4 lg:gap-6 lg:p-6">
        <aside className="hidden w-64 shrink-0 rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm lg:block">
          <div className="flex items-center gap-2 rounded-xl px-3 py-2">
            <div className="grid size-9 place-items-center rounded-xl bg-zinc-900 text-white">
              <Building2 className="size-5" aria-hidden="true" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">GoodSaaS Finance</div>
              <div className="text-xs text-zinc-500">Orders & payments</div>
            </div>
          </div>

          <nav className="mt-3 space-y-1">
            <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" />
            <NavItem to="/orders" icon={ShoppingBag} label="Orders" />
            <NavItem to="/payments" icon={CreditCard} label="Payments" />
            <NavItem to="/ask-ai" icon={Sparkles} label="AskAI" />
            <NavItem to="/invoices" icon={ReceiptText} label="Invoices" disabled />
          </nav>
        </aside>

        <div className={cn('flex min-h-0 min-w-0 flex-1 flex-col', isAskAi ? 'gap-2 lg:gap-3' : 'gap-4 lg:gap-6')}>
          <header
            className={cn(
              'flex rounded-2xl border border-zinc-200 bg-white shadow-sm lg:items-center lg:justify-between',
              isAskAi ? 'flex-row items-center gap-3 px-4 py-2.5' : 'flex-col gap-3 p-4 lg:flex-row',
            )}
          >
            <div className="min-w-0">
              {pageMeta.subtitle ? <div className="text-sm text-zinc-500">{pageMeta.subtitle}</div> : null}
              <div className={cn('truncate font-semibold', isAskAi ? 'text-base' : 'text-lg')}>{pageMeta.title}</div>
            </div>

            {!isAskAi ? (
              <div className="flex flex-wrap items-center gap-2">
                <div className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
                  <span className="text-zinc-500">Store</span>
                  <span className="font-medium">Flipkart-like</span>
                </div>
                <Link
                  className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
                  to="/orders"
                >
                  View orders
                </Link>
              </div>
            ) : (
              <Link
                className="shrink-0 rounded-xl border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
                to="/orders"
              >
                Back to orders
              </Link>
            )}
          </header>

          <main
            className={cn(
              'flex min-h-0 min-w-0 flex-1 flex-col pb-20 lg:pb-0',
              isAskAi ? 'overflow-hidden' : 'overflow-auto',
            )}
          >
            {children}
          </main>
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-zinc-200 bg-white/90 backdrop-blur lg:hidden">
        <div className="mx-auto grid max-w-[1400px] grid-cols-3 px-2 py-2">
          <MobileTab to="/orders" label="Orders" icon={ShoppingBag} />
          <MobileTab to="/payments" label="Payments" icon={CreditCard} />
          <MobileTab to="/ask-ai" label="AskAI" icon={Sparkles} />
        </div>
      </nav>
    </div>
  )
}

function NavItem({
  to,
  icon: Icon,
  label,
  disabled,
}: {
  to: string
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
  label: string
  disabled?: boolean
}) {
  if (disabled) {
    return (
      <div className="flex cursor-not-allowed items-center gap-2 rounded-xl px-3 py-2 text-sm text-zinc-400">
        <span className="grid size-9 place-items-center rounded-xl bg-zinc-100">
          <Icon className="size-4" aria-hidden="true" />
        </span>
        <span className="font-medium">{label}</span>
        <span className="ml-auto rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">Soon</span>
      </div>
    )
  }

  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 hover:text-zinc-900',
          isActive && 'bg-zinc-900 text-white hover:bg-zinc-900 hover:text-white',
        )
      }
    >
      {({ isActive }) => (
        <>
          <span className={cn('grid size-9 place-items-center rounded-xl', isActive ? 'bg-white/15' : 'bg-zinc-100')}>
            <Icon className={cn('size-4', isActive ? 'text-white' : 'text-zinc-700')} aria-hidden="true" />
          </span>
          <span className="font-medium">{label}</span>
        </>
      )}
    </NavLink>
  )
}

function MobileTab({
  to,
  label,
  icon: Icon,
}: {
  to: string
  label: string
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex flex-col items-center justify-center gap-1 rounded-xl px-3 py-2 text-xs font-medium text-zinc-600',
          isActive && 'bg-zinc-900 text-white',
        )
      }
    >
      <Icon className="size-5" aria-hidden="true" />
      {label}
    </NavLink>
  )
}

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/orders" replace />} />
        <Route path="/dashboard" element={<Navigate to="/orders" replace />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/ask-ai" element={<AskAIPage />} />
        <Route path="*" element={<Navigate to="/orders" replace />} />
      </Routes>
    </AppShell>
  )
}

