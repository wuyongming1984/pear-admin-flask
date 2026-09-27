// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'
import {afterEach, beforeEach, expect, it, vi} from 'vitest'
import routes from './routes'

const mocks = vi.hoisted(() => ({allRows: vi.fn(), request: vi.fn()}))
vi.mock('../../api', () => ({...mocks, query: (p: any) => new URLSearchParams(p).toString(), safeUrl: (s: string) => s || ''}))
vi.mock('element-plus', () => ({ElMessage: {error: vi.fn(), success: vi.fn()}, ElMessageBox: {confirm: vi.fn()}}))
const orders = [
  {id: 1, project_id: 10, project_name: '项目甲', supplier_contact_person: '张三', order_number: 'D001', order_amount: '100.00', paid_amount: '100.00', order_balance: '0.00'},
  {id: 2, project_id: 10, project_name: '项目甲', supplier_contact_person: '李四', order_number: 'D002', order_amount: '200.00', paid_amount: '60.00', order_balance: '140.00'},
]
const payments = [
  {id: 7, pay_number: 'F007', order_id: 1, project_name: '项目甲', supplier_contact_person: '张三', current_payment_amount: '100.00', invoice_amount: '0.00', payment_status: 'paid', invoices_list: [{id: 9, invoice_number: 'INV009', total_amount: '100.00'}]},
  {id: 8, pay_number: 'F008', order_id: 2, project_name: '项目甲', supplier_contact_person: '李四', current_payment_amount: '60.00', invoice_amount: '0.00', payment_status: 'pending', invoices_list: []},
  {id: 9, pay_number: 'F009', order_id: null, current_payment_amount: '0.00', payment_status: 'pending', invoices_list: []},
]
beforeEach(() => {
  vi.clearAllMocks(); vi.useFakeTimers()
  mocks.allRows.mockImplementation(async (path: string, params: any) => path === '/pay/' ? payments : path === '/order/' ? orders : path === '/project/' ? [{id: 10, project_name: '项目甲'}] : params?.dic_id === 28 ? [{code: 'paid', value: '已付款'}, {code: 'pending', value: '待付款'}] : [])
  mocks.request.mockImplementation(async (path: string) => {
    if (!path.startsWith('/workspace/payments?')) return {code: 0, data: {}}
    const q = new URL(path, 'http://test').searchParams
    const data = payments.map(p => ({...p, order_summary: orders.find(o => o.id === p.order_id) || {}})).filter(p => (!q.get('project_id') || String((p.order_summary as any).project_id) === q.get('project_id')) && (!q.get('supplier_contact_person') || p.supplier_contact_person === q.get('supplier_contact_person')) && p.pay_number.includes(q.get('pay_number') || '') && (!q.get('payment_status') || p.payment_status === q.get('payment_status')))
    return {code: 0, data, count: data.length, projects: [{id: 10, project_name: '项目甲'}], contacts: ['张三', '李四'], totals: {paid: '160', invoiced: '0'}}
  })
})
afterEach(() => vi.useRealTimers())
async function settle() {await vi.advanceTimersByTimeAsync(250); await flushPromises()}
async function setup(url = '/payments') {
  const router = createRouter({history: createMemoryHistory(), routes})
  await router.push(url); await router.isReady()
  const wrapper = mount({template: '<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.path" /></keep-alive></router-view>'}, {global: {plugins: [router], stubs: {TablePrint: true, 'el-table': true, 'el-table-column': true}, directives: {loading: () => {}}, config: {warnHandler: () => {}}}})
  await flushPromises()
  await settle()
  expect(mocks.allRows.mock.calls.every(([path]) => path === '/dictionary/detail/list')).toBe(true)
  return {wrapper, router}
}
it('restores three columns at /payments and retains combined filters after viewing an edit page', async () => {
  const {wrapper, router} = await setup()
  expect(wrapper.find('aside[aria-label="项目筛选"]').exists()).toBe(true)
  expect(wrapper.findAll('article')).toHaveLength(3)
  await wrapper.get('button[data-project="10"]').trigger('click')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(2)
  await wrapper.get('button[data-contact="张三"]').trigger('click')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(1)
  await wrapper.get('input[aria-label="付款单号搜索"]').setValue('no-match')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(0)
  await wrapper.get('input[aria-label="付款单号搜索"]').setValue('F007')
  await settle()
  await wrapper.get('select[aria-label="付款状态筛选"]').setValue('pending')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(0)
  await wrapper.get('select[aria-label="付款状态筛选"]').setValue('paid')
  await settle()
  await router.push('/payments/7/edit'); await flushPromises()
  await router.push('/payments'); await flushPromises()
  expect(wrapper.get('input[aria-label="付款单号搜索"]').element).toHaveProperty('value', 'F007')
  expect(wrapper.findAll('article')).toHaveLength(1)
  wrapper.unmount()
})
it('keeps related order/invoice links below the paper and handles an unlinked payment without fake order amounts', async () => {
  const {wrapper} = await setup()
  const card = wrapper.findAll('article').find(c => c.text().includes('F007'))!
  expect(card.get('a[aria-label="打印付款单 F007"]').attributes('href')).toBe('/payments/7/print')
  expect(card.get('a[aria-label="查看关联订单 D001"]').attributes('href')).toBe('/orders/1/edit')
  expect(card.get('a[aria-label="查看发票 INV009"]').attributes('href')).toBe('/invoices/9')
  expect(card.get('.order-sheet-grid').element.compareDocumentPosition(card.get('[aria-label="关联发票"]').element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  const unlinked = wrapper.findAll('article').find(c => c.text().includes('F009'))!
  expect(unlinked.text()).toContain('未关联订单')
  expect(unlinked.find('a[aria-label^="查看关联订单"]').exists()).toBe(false)
  wrapper.unmount()
})
