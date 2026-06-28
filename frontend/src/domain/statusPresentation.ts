import type { Tone } from '../components/ui/Badge'
import type { OrderStatus, PaymentMethod, PaymentStatus } from './finance'

export function paymentStatusTone(status: PaymentStatus): Tone {
  switch (status) {
    case 'Captured':
      return 'green'
    case 'Authorized':
      return 'blue'
    case 'Pending':
      return 'amber'
    case 'Failed':
      return 'red'
    case 'Refunded':
    case 'PartialRefund':
      return 'purple'
    default:
      return 'zinc'
  }
}

export function orderStatusTone(status: OrderStatus): Tone {
  switch (status) {
    case 'Delivered':
      return 'green'
    case 'Shipped':
    case 'OutForDelivery':
      return 'blue'
    case 'Packed':
    case 'Placed':
      return 'zinc'
    case 'Cancelled':
    case 'Returned':
      return 'red'
    default:
      return 'zinc'
  }
}

export function paymentMethodLabel(method: PaymentMethod) {
  switch (method) {
    case 'NetBanking':
      return 'Net banking'
    case 'BankTransfer':
      return 'Bank transfer'
    default:
      return method
  }
}
