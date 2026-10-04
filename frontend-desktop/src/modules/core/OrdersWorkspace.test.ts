// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'
import {afterEach, beforeEach, expect, it, vi} from 'vitest'
import routes from './routes'

const mocks = vi.hoisted(() => ({allRows: vi.fn(), request: vi.fn(), openReceipts: vi.fn()}))
vi.mock('../../api', () => ({...mocks, query: (p: any) => new URLSearchParams(p).toString(), safeUrl: (s: string) => s || ''}))
vi.mock('element-plus', () => ({ElMessage: {error: vi.fn(), success: vi.fn()}, ElMessageBox: {confirm: vi.fn()}}))
const orders = [
  {id: 1, order_number: 'D001', project_id: 10, project_name: '项目甲', supplier_contact_person: '张三', order_amount: '100.00', paid_amount: '100.00', order_balance: '0.00', pays_list: [{id: 7, pay_number: 'F007', current_payment_amount: '100.00', payer_supplier_name: '付款单位', payee_supplier_name: '收款单位'}]},
  {id: 2, order_number: 'D002', project_id: 10, project_name: '项目甲', supplier_contact_person: '李四', order_amount: '200.00', paid_amount: '0.00', order_balance: '200.00', pays_list: []},
  {id: 3, order_number: 'D003', project_id: 20, project_name: '项目乙', supplier_contact_person: '张三', order_amount: '50.00', paid_amount: '0.00', order_balance: '50.00', pays_list: []},
]
beforeEach(() => {
  vi.clearAllMocks(); vi.useFakeTimers()
  mocks.allRows.mockImplementation(async (path: string) => path === '/order/' ? orders : path === '/project/' ? [{id: 10, project_name: '项目甲'}, {id: 20, project_name: '项目乙'}] : [])
  mocks.request.mockImplementation(async (path: string) => {
    if (!path.startsWith('/workspace/orders?')) return {code: 0, data: {}}
    const q = new URL(path, 'http://test').searchParams
    const data = orders.filter(o => (!q.get('project_id') || String(o.project_id) === q.get('project_id')) && (!q.get('supplier_contact_person') || o.supplier_contact_person === q.get('supplier_contact_person')) && o.order_number.includes(q.get('order_number') || '') && (q.get('hide_settled') !== '1' || Number(o.order_balance) !== 0))
    return {code: 0, data, count: data.length, projects: [{id: 10, project_name: '项目甲'}, {id: 20, project_name: '项目乙'}], contacts: ['张三', '李四'], totals: {orders: '350', paid: '100', balance: '250'}}
  })
})
afterEach(() => vi.useRealTimers())
async function settle() {await vi.advanceTimersByTimeAsync(250); await flushPromises()}
async function setup(url = '/orders') {
  const router = createRouter({history: createMemoryHistory(), routes})
  await router.push(url); await router.isReady()
  const wrapper = mount({template: '<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.path" /></keep-alive></router-view>'}, {global: {plugins: [router], stubs: {PaymentReceiptPicker: {setup(_, {expose}) {expose({open:mocks.openReceipts});return {}},template:'<div/>'}, TablePrint: true, 'el-table': true, 'el-table-column': true}, directives: {loading: () => {}}, config: {warnHandler: () => {}}}})
  await flushPromises()
  await settle()
  expect(mocks.allRows.mock.calls.every(([path]) => path === '/dictionary/detail/list')).toBe(true)
  return {wrapper, router}
}
it('serves the three-column workspace at the real /orders route and combines project/contact/number filters', async () => {
  const {wrapper, router} = await setup()
  expect(wrapper.find('aside[aria-label="项目筛选"]').exists()).toBe(true)
  expect(wrapper.find('aside[aria-label="联系人筛选"]').exists()).toBe(true)
  await wrapper.find('aside[aria-label="项目筛选"] button[data-project="10"]').trigger('click')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(2)
  await wrapper.find('aside[aria-label="联系人筛选"] button[data-contact="张三"]').trigger('click')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(1)
  expect(wrapper.find('article').text()).toContain('D001')
  await wrapper.get('input[aria-label="订单号搜索"]').setValue('not-found')
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(0)
  await wrapper.get('input[aria-label="订单号搜索"]').setValue('D001')
  await settle()
  await wrapper.get('input[aria-label="隐藏已结清"]').setValue(true)
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(0)
  await wrapper.get('input[aria-label="隐藏已结清"]').setValue(false)
  await settle()
  expect(wrapper.findAll('article')).toHaveLength(1)
  await router.push('/payments/7/edit'); await flushPromises()
  await router.push('/orders'); await flushPromises()
  expect(wrapper.get('input[aria-label="订单号搜索"]').element).toHaveProperty('value', 'D001')
  expect(wrapper.findAll('article')).toHaveLength(1)
  wrapper.unmount()
})
it('opens receipt association for only the payments belonging to the clicked order', async () => {
  const {wrapper, router} = await setup('/orders?project_id=10')
  await wrapper.get('button[aria-label="关联付款回单 D001"]').trigger('click')
  expect(mocks.openReceipts).toHaveBeenCalledWith(orders[0]!.pays_list)
  expect(router.currentRoute.value.fullPath).toBe('/orders?project_id=10')
  await wrapper.get('button[aria-label="关联付款回单 F007"]').trigger('click')
  expect(mocks.openReceipts).toHaveBeenLastCalledWith(orders[0]!.pays_list, 7)
  wrapper.unmount()
})
it('opens the empty-order guidance without making up a payment', async () => {
  const {wrapper} = await setup()
  await wrapper.get('button[aria-label="关联付款回单 D002"]').trigger('click')
  expect(mocks.openReceipts).toHaveBeenCalledWith([])
  expect(mocks.request.mock.calls.every(([,options]) => !options?.method)).toBe(true)
  wrapper.unmount()
})
it('places related payment actions below the order sheet and preserves project deep links', async () => {
  const {wrapper, router} = await setup('/orders?project_id=10')
  expect(wrapper.findAll('article')).toHaveLength(2)
  const article = wrapper.findAll('article').find(x => x.text().includes('D001'))!
  const sheet = article.get('.order-sheet-grid').element
  const newPayment = new URL(article.get('.new-payment-button').attributes('href')!, 'http://test')
  expect(newPayment.pathname).toBe('/payments/new')
  expect(newPayment.searchParams.get('order_id')).toBe('1')
  expect(newPayment.searchParams.get('returnTo')).toBe('/orders?project_id=10')
  const payments = article.get('[aria-label="关联付款单"]').element
  const attachments = article.get('[aria-label="订单附件"]').element
  expect(sheet.compareDocumentPosition(attachments) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(attachments.compareDocumentPosition(payments) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(article.get('input[type="file"]').attributes('multiple')).toBeDefined()
  expect(sheet.compareDocumentPosition(payments) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(article.get('a[aria-label="打印付款单 F007"]').attributes('href')).toBe('/payments/7/print')
  await article.get('a[aria-label="编辑付款单 F007"]').trigger('click')
  await settle()
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/payments/7/edit'))
  wrapper.unmount()
})
