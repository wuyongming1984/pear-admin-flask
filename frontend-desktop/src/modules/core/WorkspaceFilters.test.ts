// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'
import {afterEach, expect, it, vi} from 'vitest'
import OrdersWorkspace from './OrdersWorkspace.vue'
import PaymentsWorkspace from './PaymentsWorkspace.vue'

vi.mock('../../api', () => ({
  allRows: async () => [],
  safeUrl: (value: string) => value,
  query: (params: any) => new URLSearchParams(params).toString(),
  request: async (path: string) => {
    const query = new URL(path, 'http://test').searchParams
    const orders = [
      {id: 1, project_id: 10, contact: '张三'}, {id: 2, project_id: 10, contact: '李四'},
      {id: 3, project_id: 20, contact: '张三'}, {id: 4, project_id: 20, contact: '王五'},
      {id: 5, project_id: 30, contact: '王五'},
    ]
    const projectMatch = (row: typeof orders[number]) => !query.get('project_id') || String(row.project_id) === query.get('project_id')
    const contactMatch = (row: typeof orders[number]) => !query.get('supplier_contact_person') || row.contact === query.get('supplier_contact_person')
    const data = orders.filter(row => projectMatch(row) && contactMatch(row)).map(row => ({...row, order_number: 'D' + row.id, pay_number: 'F' + row.id}))
    return {data, count: data.length,
      projects: [{id: 10, project_name: '项目甲'}, {id: 20, project_name: '项目乙'}, {id: 30, project_name: '项目丙'}]
        .filter(project => orders.some(row => row.project_id === project.id && contactMatch(row))),
      contacts: [...new Set(orders.filter(projectMatch).map(row => row.contact))], totals: {}}
  },
}))
vi.mock('element-plus', () => ({ElMessage: {error: vi.fn()}}))
afterEach(() => vi.useRealTimers())
async function settle() {await vi.advanceTimersByTimeAsync(250); await flushPromises()}

it.each([
  ['orders', OrdersWorkspace], ['payments', PaymentsWorkspace],
] as const)('%s updates opposite sidebar choices while preserving selections and search text', async (kind, component) => {
  vi.useFakeTimers()
  const router = createRouter({history: createMemoryHistory(), routes: [
    {path: '/' + kind, component}, {path: '/:pathMatch(.*)*', component: {template: '<div />'}},
  ]})
  await router.push('/' + kind); await router.isReady()
  const wrapper = mount({template: '<router-view />'}, {global: {plugins: [router], stubs: {TablePrint: true, OrderAttachments: true, PaymentReceiptPicker: true}, directives: {loading: () => {}}}})
  try {
    await settle()
    await wrapper.get('input[aria-label="筛选项目"]').setValue('项目')
    await wrapper.get('[data-project="10"]').trigger('click')
    await settle()
    expect(wrapper.find('[data-contact="王五"]').exists()).toBe(false)
    expect(wrapper.find('[data-contact="李四"]').exists()).toBe(true)
    await wrapper.get('input[aria-label="筛选联系人"]').setValue('张')
    await wrapper.get('[data-contact="张三"]').trigger('click')
    await settle()
    expect(wrapper.find('[data-project="30"]').exists()).toBe(false)
    expect(wrapper.get('[data-project="10"]').attributes('aria-pressed')).toBe('true')
    await wrapper.get('[data-project="20"]').trigger('click')
    await settle()
    expect(wrapper.get('[data-contact="张三"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('input[aria-label="筛选联系人"]').element).toHaveProperty('value', '张')
    expect(wrapper.findAll('article')).toHaveLength(1)
    expect(wrapper.find('article').text()).toContain(kind === 'orders' ? 'D3' : 'F3')
    await wrapper.get('input[aria-label="筛选联系人"]').setValue('')
    expect(wrapper.find('[data-contact="李四"]').exists()).toBe(false)
    expect(wrapper.find('[data-contact="王五"]').exists()).toBe(true)
    await wrapper.get('input[aria-label="筛选联系人"]').setValue('张')
    await wrapper.get('aside[aria-label="项目筛选"] button').trigger('click')
    await settle()
    expect(wrapper.get('[data-contact="张三"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('input[aria-label="筛选联系人"]').element).toHaveProperty('value', '张')
    expect(wrapper.find('[data-project="30"]').exists()).toBe(false)
    expect(wrapper.findAll('article')).toHaveLength(2)
    await wrapper.get('input[aria-label="筛选联系人"]').setValue('')
    await wrapper.get('[data-contact="王五"]').trigger('click')
    await settle()
    expect(wrapper.find('[data-project="10"]').exists()).toBe(false)
    expect(wrapper.find('[data-project="30"]').exists()).toBe(true)
    expect(wrapper.get('input[aria-label="筛选项目"]').element).toHaveProperty('value', '项目')
    await wrapper.get('[data-project="30"]').trigger('click')
    await settle()
    expect(wrapper.get('[data-contact="王五"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.findAll('[data-contact]')).toHaveLength(1)
    await wrapper.get('aside[aria-label="联系人筛选"] button').trigger('click')
    await settle()
    expect(wrapper.get('[data-project="30"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.findAll('[data-project]')).toHaveLength(3)
    expect(wrapper.findAll('article')).toHaveLength(1)
  } finally {wrapper.unmount()}
})
