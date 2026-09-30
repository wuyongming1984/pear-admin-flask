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
    const matches = (!query.get('project_id') || query.get('project_id') === '10')
      && (!query.get('supplier_contact_person') || query.get('supplier_contact_person') === '张三')
    return {data: matches ? [{id: 1, order_number: 'D001', pay_number: 'F001'}] : [], count: matches ? 1 : 0,
      projects: [{id: 10, project_name: '项目甲'}, {id: 20, project_name: '项目乙'}],
      contacts: ['张三', '李四'], totals: {}}
  },
}))
vi.mock('element-plus', () => ({ElMessage: {error: vi.fn()}}))
afterEach(() => vi.useRealTimers())
async function settle() {await vi.advanceTimersByTimeAsync(250); await flushPromises()}

it.each([
  ['orders', OrdersWorkspace], ['payments', PaymentsWorkspace],
] as const)('%s keeps both filter selections and search text independent, including empty results', async (kind, component) => {
  vi.useFakeTimers()
  const router = createRouter({history: createMemoryHistory(), routes: [
    {path: '/' + kind, component}, {path: '/:pathMatch(.*)*', component: {template: '<div />'}},
  ]})
  await router.push('/' + kind); await router.isReady()
  const wrapper = mount({template: '<router-view />'}, {global: {plugins: [router], stubs: {TablePrint: true}, directives: {loading: () => {}}}})
  try {
    await settle()
    await wrapper.get('input[aria-label="筛选项目"]').setValue('项目')
    await wrapper.get('input[aria-label="筛选联系人"]').setValue('张')
    await wrapper.get('[data-contact="张三"]').trigger('click')
    await settle()
    await wrapper.get('[data-project="20"]').trigger('click')
    await settle()
    expect(wrapper.get('[data-contact="张三"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('input[aria-label="筛选联系人"]').element).toHaveProperty('value', '张')
    expect(wrapper.findAll('article')).toHaveLength(0)
    await wrapper.get('[data-project="10"]').trigger('click')
    await settle()
    expect(wrapper.get('[data-contact="张三"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.findAll('article')).toHaveLength(1)
    await wrapper.get('aside[aria-label="项目筛选"] button').trigger('click')
    await settle()
    expect(wrapper.get('[data-contact="张三"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('input[aria-label="筛选联系人"]').element).toHaveProperty('value', '张')
    await wrapper.get('[data-project="10"]').trigger('click')
    await wrapper.get('input[aria-label="筛选联系人"]').setValue('')
    await wrapper.get('[data-contact="李四"]').trigger('click')
    await settle()
    expect(wrapper.get('[data-project="10"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('input[aria-label="筛选项目"]').element).toHaveProperty('value', '项目')
    expect(wrapper.findAll('article')).toHaveLength(0)
    await wrapper.get('aside[aria-label="联系人筛选"] button').trigger('click')
    await settle()
    expect(wrapper.get('[data-project="10"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.findAll('article')).toHaveLength(1)
  } finally {wrapper.unmount()}
})
