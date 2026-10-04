// @vitest-environment jsdom
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {mount, flushPromises} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'
import Detail from './Detail.vue'

const api = vi.hoisted(() => ({request: vi.fn()}))
vi.mock('../api', () => api)
vi.mock('../store', () => ({can: () => true, label: (_dict: string, value: any) => value}))
vi.mock('../components/AttachmentPanel.vue', () => ({default: {template: '<div />'}}))
const stubs = {
  'van-nav-bar': {props: ['title'], template: '<header>{{title}}</header>'},
  'van-cell-group': {template: '<section><slot /></section>'},
  'van-cell': {props: ['title', 'label', 'value'], template: '<p class="test-cell"><b>{{title}}</b><span>{{label}}</span><strong>{{value}}</strong></p>'},
  'van-icon': true, 'van-empty': true, 'van-loading': true, 'van-button': true,
}

describe('native mobile payment invoice amounts', () => {
  beforeEach(() => vi.clearAllMocks())
  it.each([
    ['100', '13', '¥113.00', '¥100.00', '¥13.00'],
    ['100', 0, '¥100.00', '¥100.00', '¥0.00'],
    ['-100', '-13', '¥-113.00', '¥-100.00', '¥-13.00'],
    ['1.005', '0.005', '¥1.01', '¥1.01', '¥0.01'],
    [undefined, '13', '待核实', '待核实', '¥13.00'],
    ['100', 'NaN', '待核实', '¥100.00', '待核实'],
  ])('shows inclusive, untaxed and tax while preserving payment amount (%s, %s)', async (untaxed, tax, totalText, untaxedText, taxText) => {
    api.request.mockResolvedValue({data: {id: 9, pay_number: 'LOCAL-FK9', current_payment_amount: '88.00', invoices_list: [{id: 1, invoice_number: 'LOCAL-INV1', seller_name: '本地测试单位', total_amount: untaxed, tax_amount: tax}]}})
    const router = createRouter({history: createMemoryHistory(), routes: [{path: '/:kind/:id', component: Detail}, {path: '/:kind/:id/edit', component: {template: '<div />'}}]})
    await router.push('/pay/9')
    await router.isReady()
    const wrapper = mount({template: '<router-view />'}, {global: {plugins: [router], stubs}})
    await flushPromises()
    const invoiceCell = wrapper.findAll('.test-cell').find(cell => cell.text().includes('LOCAL-INV1'))!
    expect(invoiceCell.text()).toContain(`价税合计 ${totalText}`)
    expect(invoiceCell.text()).toContain(`不含税金额 ${untaxedText}`)
    expect(invoiceCell.text()).toContain(`税额 ${taxText}`)
    expect(invoiceCell.text()).not.toContain('NaN')
    expect(wrapper.find('.hero-money').text()).toBe('¥ 88.00')
    expect(api.request).toHaveBeenCalledTimes(1)
    expect(api.request).toHaveBeenCalledWith('/pay/9')
    wrapper.unmount()
  })
})
