export type OrderStatus =
  | 'Placed'
  | 'Packed'
  | 'Shipped'
  | 'OutForDelivery'
  | 'Delivered'
  | 'Cancelled'
  | 'Returned'

export type PaymentStatus = 'Authorized' | 'Captured' | 'Pending' | 'Failed' | 'Refunded' | 'PartialRefund'

export type PaymentMethod = 'Card' | 'UPI' | 'NetBanking' | 'Wallet' | 'EMI' | 'COD' | 'BankTransfer'

export type Money = {
  currency: 'INR'
  amount: number
}

export type PaymentAttempt = {
  id: string
  method: PaymentMethod
  status: PaymentStatus
  provider: string
  paidAt?: string
  failureReason?: string
}

export type Order = {
  id: string
  placedAt: string
  customer: { name: string; email: string; phone: string }
  items: number
  orderStatus: OrderStatus
  payment: {
    total: Money
    method: PaymentMethod
    status: PaymentStatus
    txnId: string
    attempts: PaymentAttempt[]
  }
  delivery: { city: string; pincode: string; eta?: string }
}

export const MOCK_ORDERS: Order[] = [
  {
    id: 'OD1001',
    placedAt: '2026-04-16T09:12:00+05:30',
    customer: { name: 'Aarav Mehta', email: 'aarav.mehta@example.com', phone: '+91-98765-43210' },
    items: 3,
    orderStatus: 'Shipped',
    payment: {
      total: { currency: 'INR', amount: 12499 },
      method: 'UPI',
      status: 'Captured',
      txnId: 'UPI-9F2C-77A1',
      attempts: [
        { id: 'PA-001', method: 'UPI', status: 'Captured', provider: 'NPCI', paidAt: '2026-04-16T09:13:12+05:30' },
      ],
    },
    delivery: { city: 'Bengaluru', pincode: '560001', eta: '2026-04-18' },
  },
  {
    id: 'OD1002',
    placedAt: '2026-04-15T18:40:00+05:30',
    customer: { name: 'Isha Kapoor', email: 'isha.kapoor@example.com', phone: '+91-91234-56789' },
    items: 1,
    orderStatus: 'Delivered',
    payment: {
      total: { currency: 'INR', amount: 45990 },
      method: 'Card',
      status: 'Captured',
      txnId: 'CC-4B91-2210',
      attempts: [
        { id: 'PA-010', method: 'Card', status: 'Authorized', provider: 'Visa', paidAt: '2026-04-15T18:40:18+05:30' },
        { id: 'PA-011', method: 'Card', status: 'Captured', provider: 'Visa', paidAt: '2026-04-15T18:40:21+05:30' },
      ],
    },
    delivery: { city: 'Mumbai', pincode: '400001' },
  },
  {
    id: 'OD1003',
    placedAt: '2026-04-15T11:05:00+05:30',
    customer: { name: 'Rohan Verma', email: 'rohan.verma@example.com', phone: '+91-99887-76655' },
    items: 2,
    orderStatus: 'Packed',
    payment: {
      total: { currency: 'INR', amount: 3299 },
      method: 'NetBanking',
      status: 'Pending',
      txnId: 'NB-PENDING-19C2',
      attempts: [
        { id: 'PA-020', method: 'NetBanking', status: 'Pending', provider: 'HDFC', paidAt: undefined },
      ],
    },
    delivery: { city: 'Delhi', pincode: '110001', eta: '2026-04-17' },
  },
  {
    id: 'OD1004',
    placedAt: '2026-04-14T21:22:00+05:30',
    customer: { name: 'Neha Joshi', email: 'neha.joshi@example.com', phone: '+91-90000-11122' },
    items: 5,
    orderStatus: 'OutForDelivery',
    payment: {
      total: { currency: 'INR', amount: 1899 },
      method: 'Wallet',
      status: 'Captured',
      txnId: 'WL-88AA-3301',
      attempts: [
        { id: 'PA-030', method: 'Wallet', status: 'Captured', provider: 'PhonePe', paidAt: '2026-04-14T21:22:44+05:30' },
      ],
    },
    delivery: { city: 'Pune', pincode: '411001', eta: '2026-04-16' },
  },
  {
    id: 'OD1005',
    placedAt: '2026-04-14T10:18:00+05:30',
    customer: { name: 'Kabir Singh', email: 'kabir.singh@example.com', phone: '+91-98111-22333' },
    items: 1,
    orderStatus: 'Cancelled',
    payment: {
      total: { currency: 'INR', amount: 9999 },
      method: 'EMI',
      status: 'Failed',
      txnId: 'EMI-FAIL-01',
      attempts: [
        {
          id: 'PA-040',
          method: 'EMI',
          status: 'Failed',
          provider: 'IssuerBank',
          failureReason: 'Insufficient credit limit',
        },
      ],
    },
    delivery: { city: 'Hyderabad', pincode: '500001' },
  },
  {
    id: 'OD1006',
    placedAt: '2026-04-13T16:02:00+05:30',
    customer: { name: 'Sana Qureshi', email: 'sana.qureshi@example.com', phone: '+91-93333-44455' },
    items: 4,
    orderStatus: 'Returned',
    payment: {
      total: { currency: 'INR', amount: 7499 },
      method: 'Card',
      status: 'Refunded',
      txnId: 'CC-REFUND-2211',
      attempts: [
        { id: 'PA-050', method: 'Card', status: 'Captured', provider: 'Mastercard', paidAt: '2026-04-13T16:02:10+05:30' },
        { id: 'PA-051', method: 'Card', status: 'Refunded', provider: 'Mastercard', paidAt: '2026-04-20T12:10:00+05:30' },
      ],
    },
    delivery: { city: 'Chennai', pincode: '600001' },
  },
  {
    id: 'OD1007',
    placedAt: '2026-04-12T08:55:00+05:30',
    customer: { name: 'Dev Patel', email: 'dev.patel@example.com', phone: '+91-95555-66677' },
    items: 2,
    orderStatus: 'Placed',
    payment: {
      total: { currency: 'INR', amount: 0 },
      method: 'COD',
      status: 'Pending',
      txnId: 'COD-PLACEHOLDER',
      attempts: [{ id: 'PA-060', method: 'COD', status: 'Pending', provider: 'CashOnDelivery' }],
    },
    delivery: { city: 'Ahmedabad', pincode: '380001', eta: '2026-04-15' },
  },
  {
    id: 'OD1008',
    placedAt: '2026-04-11T19:30:00+05:30',
    customer: { name: 'Priya Nair', email: 'priya.nair@example.com', phone: '+91-94444-33322' },
    items: 6,
    orderStatus: 'Delivered',
    payment: {
      total: { currency: 'INR', amount: 22150 },
      method: 'BankTransfer',
      status: 'Captured',
      txnId: 'NEFT-7788-2211',
      attempts: [
        { id: 'PA-070', method: 'BankTransfer', status: 'Captured', provider: 'IMPS/NEFT', paidAt: '2026-04-11T19:35:02+05:30' },
      ],
    },
    delivery: { city: 'Kochi', pincode: '682001' },
  },
  {
    id: 'OD1009',
    placedAt: '2026-04-10T13:44:00+05:30',
    customer: { name: 'Manish Gupta', email: 'manish.gupta@example.com', phone: '+91-92222-33444' },
    items: 2,
    orderStatus: 'Shipped',
    payment: {
      total: { currency: 'INR', amount: 5499 },
      method: 'UPI',
      status: 'PartialRefund',
      txnId: 'UPI-PREFUND-01',
      attempts: [
        { id: 'PA-080', method: 'UPI', status: 'Captured', provider: 'NPCI', paidAt: '2026-04-10T13:44:18+05:30' },
        { id: 'PA-081', method: 'UPI', status: 'PartialRefund', provider: 'NPCI', paidAt: '2026-04-12T10:00:00+05:30' },
      ],
    },
    delivery: { city: 'Jaipur', pincode: '302001', eta: '2026-04-14' },
  },
  {
    id: 'OD1010',
    placedAt: '2026-04-09T07:10:00+05:30',
    customer: { name: 'Ananya Bose', email: 'ananya.bose@example.com', phone: '+91-91111-00099' },
    items: 1,
    orderStatus: 'Delivered',
    payment: {
      total: { currency: 'INR', amount: 1299 },
      method: 'NetBanking',
      status: 'Captured',
      txnId: 'NB-SBI-9911',
      attempts: [{ id: 'PA-090', method: 'NetBanking', status: 'Captured', provider: 'SBI', paidAt: '2026-04-09T07:10:55+05:30' }],
    },
    delivery: { city: 'Kolkata', pincode: '700001' },
  },
]
