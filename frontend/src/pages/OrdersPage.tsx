import { useMemo, useState } from 'react'
import { Filter, Search } from 'lucide-react'
import { MOCK_ORDERS, type OrderStatus, type PaymentMethod, type PaymentStatus } from '../domain/finance'
import { orderStatusTone, paymentMethodLabel, paymentStatusTone } from '../domain/statusPresentation'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { formatDateTime, formatInr } from '../lib/format'
import { cn } from '../lib/cn'

const ALL = 'All' as const

export default function OrdersPage() {
  const [query, setQuery] = useState('')
  const [orderStatus, setOrderStatus] = useState<OrderStatus | typeof ALL>(ALL)
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | typeof ALL>(ALL)
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | typeof ALL>(ALL)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return MOCK_ORDERS.filter((o) => {
      if (orderStatus !== ALL && o.orderStatus !== orderStatus) return false
      if (paymentStatus !== ALL && o.payment.status !== paymentStatus) return false
      if (paymentMethod !== ALL && o.payment.method !== paymentMethod) return false

      if (!q) return true
      const hay = [
        o.id,
        o.customer.name,
        o.customer.email,
        o.customer.phone,
        o.payment.txnId,
        o.delivery.city,
        o.delivery.pincode,
      ]
        .join(' ')
        .toLowerCase()
      return hay.includes(q)
    })
  }, [orderStatus, paymentMethod, paymentStatus, query])

  const kpis = useMemo(() => {
    const totalGmv = filtered.reduce((sum, o) => sum + o.payment.total.amount, 0)
    const captured = filtered.filter((o) => o.payment.status === 'Captured').length
    const pending = filtered.filter((o) => o.payment.status === 'Pending').length
    const failed = filtered.filter((o) => o.payment.status === 'Failed').length

    return { totalGmv, captured, pending, failed, count: filtered.length }
  }, [filtered])

  return (
    <div className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-4">
        <Kpi title="Orders" value={String(kpis.count)} hint="Filtered set" />
        <Kpi title="GMV" value={formatInr({ currency: 'INR', amount: kpis.totalGmv })} hint="Sum of order totals" />
        <Kpi title="Captured" value={String(kpis.captured)} hint="Successful payments" />
        <Kpi title="Risk" value={`${kpis.pending} pending / ${kpis.failed} failed`} hint="Needs attention" />
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <CardTitle title="Orders" subtitle="Track fulfillment + payment state (demo data)" />
            <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
              <span className="inline-flex items-center gap-1 rounded-full bg-zinc-50 px-2 py-1 ring-1 ring-zinc-200">
                <Filter className="size-3.5" aria-hidden="true" />
                Filters apply instantly
              </span>
            </div>
          </div>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="grid gap-3 lg:grid-cols-4">
            <div className="lg:col-span-2">
              <label className="mb-1 block text-xs font-medium text-zinc-600">Search</label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" aria-hidden="true" />
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Order id, customer, txn id…" className="pl-10" />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-600">Order status</label>
              <Select value={orderStatus} onChange={(e) => setOrderStatus(e.target.value as OrderStatus | typeof ALL)}>
                <option value={ALL}>All</option>
                <option>Placed</option>
                <option>Packed</option>
                <option>Shipped</option>
                <option>OutForDelivery</option>
                <option>Delivered</option>
                <option>Cancelled</option>
                <option>Returned</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-600">Payment status</label>
              <Select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value as PaymentStatus | typeof ALL)}>
                <option value={ALL}>All</option>
                <option>Authorized</option>
                <option>Captured</option>
                <option>Pending</option>
                <option>Failed</option>
                <option>Refunded</option>
                <option>PartialRefund</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-600">Payment method</label>
              <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod | typeof ALL)}>
                <option value={ALL}>All</option>
                <option>Card</option>
                <option>UPI</option>
                <option>NetBanking</option>
                <option>Wallet</option>
                <option>EMI</option>
                <option>COD</option>
                <option>BankTransfer</option>
              </Select>
            </div>

            <div className="flex items-end justify-end gap-2 lg:col-span-4">
              <Button
                variant="ghost"
                type="button"
                onClick={() => {
                  setQuery('')
                  setOrderStatus(ALL)
                  setPaymentStatus(ALL)
                  setPaymentMethod(ALL)
                }}
              >
                Reset
              </Button>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-zinc-200">
            <div className="overflow-x-auto">
              <table className="min-w-[980px] w-full border-collapse text-left text-sm">
                <thead className="bg-zinc-50 text-xs text-zinc-600">
                  <tr>
                    <Th>Order</Th>
                    <Th>Customer</Th>
                    <Th>Items</Th>
                    <Th>Total</Th>
                    <Th>Method</Th>
                    <Th>Payment</Th>
                    <Th>Fulfillment</Th>
                    <Th>Delivery</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 bg-white">
                  {filtered.map((o) => (
                    <tr key={o.id} className="hover:bg-zinc-50/60">
                      <Td>
                        <div className="font-medium text-zinc-900">{o.id}</div>
                        <div className="mt-0.5 text-xs text-zinc-500">{formatDateTime(o.placedAt)}</div>
                        <div className="mt-1 font-mono text-[11px] text-zinc-500">{o.payment.txnId}</div>
                      </Td>
                      <Td>
                        <div className="font-medium text-zinc-900">{o.customer.name}</div>
                        <div className="mt-0.5 text-xs text-zinc-500">{o.customer.email}</div>
                        <div className="mt-0.5 text-xs text-zinc-500">{o.customer.phone}</div>
                      </Td>
                      <Td>{o.items}</Td>
                      <Td className="font-medium">{formatInr(o.payment.total)}</Td>
                      <Td>
                        <Badge tone="zinc">{paymentMethodLabel(o.payment.method)}</Badge>
                      </Td>
                      <Td>
                        <Badge tone={paymentStatusTone(o.payment.status)}>{o.payment.status}</Badge>
                      </Td>
                      <Td>
                        <Badge tone={orderStatusTone(o.orderStatus)}>{o.orderStatus}</Badge>
                      </Td>
                      <Td>
                        <div className="text-zinc-900">
                          {o.delivery.city} <span className="text-zinc-400">•</span> {o.delivery.pincode}
                        </div>
                        {o.delivery.eta ? <div className="mt-1 text-xs text-zinc-500">ETA {o.delivery.eta}</div> : null}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {filtered.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-200 bg-zinc-50 px-4 py-10 text-center text-sm text-zinc-600">
              No orders match your filters.
            </div>
          ) : null}
        </CardBody>
      </Card>
    </div>
  )
}

function Kpi({ title, value, hint }: { title: string; value: string; hint: string }) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium text-zinc-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-900">{value}</div>
      <div className="mt-1 text-xs text-zinc-500">{hint}</div>
    </Card>
  )
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn('px-4 py-3 font-medium', className)}>{children}</th>
}

function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-4 py-3 align-top text-zinc-700', className)}>{children}</td>
}
