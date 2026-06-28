import { useMemo } from 'react'
import { MOCK_ORDERS, type PaymentMethod, type PaymentStatus } from '../domain/finance'
import { paymentMethodLabel, paymentStatusTone } from '../domain/statusPresentation'
import { Badge } from '../components/ui/Badge'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card'
import { formatInr } from '../lib/format'

type Agg = { count: number; gmv: number }

export default function PaymentsPage() {
  const byMethod = useMemo(() => {
    const map = new Map<PaymentMethod, Agg>()
    for (const o of MOCK_ORDERS) {
      const cur = map.get(o.payment.method) ?? { count: 0, gmv: 0 }
      cur.count += 1
      cur.gmv += o.payment.total.amount
      map.set(o.payment.method, cur)
    }
    return map
  }, [])

  const byStatus = useMemo(() => {
    const map = new Map<PaymentStatus, Agg>()
    for (const o of MOCK_ORDERS) {
      const cur = map.get(o.payment.status) ?? { count: 0, gmv: 0 }
      cur.count += 1
      cur.gmv += o.payment.total.amount
      map.set(o.payment.status, cur)
    }
    return map
  }, [])

  const methodRows = useMemo(() => {
    const methods: PaymentMethod[] = ['Card', 'UPI', 'NetBanking', 'Wallet', 'EMI', 'COD', 'BankTransfer']
    return methods.map((m) => ({ method: m, ...(byMethod.get(m) ?? { count: 0, gmv: 0 }) }))
  }, [byMethod])

  const statusRows = useMemo(() => {
    const statuses: PaymentStatus[] = ['Authorized', 'Captured', 'Pending', 'Failed', 'Refunded', 'PartialRefund']
    return statuses.map((s) => ({ status: s, ...(byStatus.get(s) ?? { count: 0, gmv: 0 }) }))
  }, [byStatus])

  const maxMethodGmv = Math.max(1, ...methodRows.map((r) => r.gmv))

  return (
    <div className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-3">
        <Card className="p-4 lg:col-span-2">
          <div className="text-xs font-medium text-zinc-500">Payments mix</div>
          <div className="mt-2 text-lg font-semibold text-zinc-900">GMV by payment method</div>
          <div className="mt-1 text-sm text-zinc-600">A quick “finance cockpit” view before wiring FastAPI.</div>

          <div className="mt-5 space-y-3">
            {methodRows.map((r) => (
              <div key={r.method} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-zinc-900">{paymentMethodLabel(r.method)}</div>
                    <div className="text-xs text-zinc-500">{r.count} orders</div>
                  </div>
                  <div className="shrink-0 text-sm font-semibold text-zinc-900">{formatInr({ currency: 'INR', amount: r.gmv })}</div>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
                  <div
                    className="h-full rounded-full bg-zinc-900"
                    style={{ width: `${Math.round((r.gmv / maxMethodGmv) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-xs font-medium text-zinc-500">Health</div>
          <div className="mt-2 text-lg font-semibold text-zinc-900">Payment status</div>
          <div className="mt-4 space-y-2">
            {statusRows.map((r) => (
              <div key={r.status} className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2">
                <Badge tone={paymentStatusTone(r.status)}>{r.status}</Badge>
                <div className="text-right">
                  <div className="text-sm font-semibold text-zinc-900">{r.count}</div>
                  <div className="text-xs text-zinc-500">{formatInr({ currency: 'INR', amount: r.gmv })}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle title="Recent payment attempts" subtitle="Flattened from demo orders (last attempt shown per order)" />
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="overflow-hidden rounded-2xl border border-zinc-200">
            <div className="overflow-x-auto">
              <table className="min-w-[980px] w-full border-collapse text-left text-sm">
                <thead className="bg-zinc-50 text-xs text-zinc-600">
                  <tr>
                    <th className="px-4 py-3 font-medium">Order</th>
                    <th className="px-4 py-3 font-medium">Method</th>
                    <th className="px-4 py-3 font-medium">Overall</th>
                    <th className="px-4 py-3 font-medium">Last attempt</th>
                    <th className="px-4 py-3 font-medium">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 bg-white">
                  {MOCK_ORDERS.map((o) => {
                    const last = o.payment.attempts[o.payment.attempts.length - 1]
                    return (
                      <tr key={o.id} className="hover:bg-zinc-50/60">
                        <td className="px-4 py-3 align-top">
                          <div className="font-medium text-zinc-900">{o.id}</div>
                          <div className="mt-1 text-xs text-zinc-500">{formatInr(o.payment.total)}</div>
                        </td>
                        <td className="px-4 py-3 align-top">
                          <Badge tone="zinc">{paymentMethodLabel(o.payment.method)}</Badge>
                        </td>
                        <td className="px-4 py-3 align-top">
                          <Badge tone={paymentStatusTone(o.payment.status)}>{o.payment.status}</Badge>
                        </td>
                        <td className="px-4 py-3 align-top">
                          <div className="flex flex-col gap-2">
                            <Badge tone={paymentStatusTone(last.status)}>{last.status}</Badge>
                            <div className="text-xs text-zinc-500">{last.provider}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3 align-top text-xs text-zinc-600">
                          {last.paidAt ? <div>Paid at: {new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(last.paidAt))}</div> : null}
                          {last.failureReason ? <div className="mt-1 text-rose-700">Reason: {last.failureReason}</div> : null}
                          <div className="mt-2 font-mono text-[11px] text-zinc-500">{o.payment.txnId}</div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
