// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import InvoicePaymentLinks from './InvoicePaymentLinks.vue'
const mocks = vi.hoisted(() => ({request: vi.fn()}))
vi.mock('../../api', () => ({request: mocks.request}))
const global = {stubs: {'el-button': {props: ['disabled', 'loading'], template: '<button :disabled="disabled || loading"><slot/></button>'}, RouterLink: {props: ['to'], template: '<a :href="to"><slot/></a>'}}}
const payments = [
  {id: 1, pay_number: 'SMART-60', current_payment_amount: '60.00', reasons: ['收款单位一致', '同一项目'], amount_difference: '-40.00', can_recommend: true},
  {id: 2, pay_number: 'SMART-40', current_payment_amount: '40.00', reasons: ['收款单位一致'], amount_difference: '-60.00', can_recommend: true},
  {id: 3, pay_number: 'USED-100', current_payment_amount: '100.00', reasons: ['已关联其他发票，请核对'], amount_difference: '0.00', can_recommend: false},
]
const response = () => ({code: 0, data: {seller_name: '测试材料公司', linked: [{id: 9, pay_number: 'OLD-20', current_payment_amount: '20.00'}], matched: payments, context: {target_amount: '120.00', selected_gross: '20.00', remaining: '100.00', amount_basis: 'invoice_gross'}, combinations: [{payment_ids: [1, 2], total_gross: '100.00', difference: '0.00', reasons: ['2 张付款单金额合计一致']}], combination_limit: 30, total_count: 3, truncated: false}})

describe('smart payment suggestions from an invoice', () => {
  beforeEach(() => {vi.resetAllMocks(); mocks.request.mockResolvedValue(response())})
  it('shows matching evidence and the exact gross amount without selecting or saving', async () => {
    const wrapper = mount(InvoicePaymentLinks, {props: {invoiceId: 12}, global})
    await flushPromises()
    expect(wrapper.text()).toContain('120.00')
    expect(wrapper.text()).toContain('同一项目')
    expect(wrapper.text()).toContain('已关联其他发票，请核对')
    expect(wrapper.get('[data-testid="payment-amount-check"]').text()).toContain('差额')
    expect(wrapper.findAll('input[type="checkbox"]').every(input => !(input.element as HTMLInputElement).checked)).toBe(true)
    expect(mocks.request.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(0)
    wrapper.unmount()
  })
  it('checks a matching combination only on request and preserves existing links through explicit save', async () => {
    const wrapper = mount(InvoicePaymentLinks, {props: {invoiceId: 12}, global})
    await flushPromises()
    await wrapper.get('[data-testid="choose-payment-combination"]').trigger('click')
    expect((wrapper.get('[aria-label="关联付款单 SMART-60"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.get('[aria-label="关联付款单 SMART-40"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.get('[aria-label="关联付款单 USED-100"]').element as HTMLInputElement).checked).toBe(false)
    expect(wrapper.get('[aria-label="已关联付款单"]').text()).toContain('OLD-20')
    expect(wrapper.get('[data-testid="payment-amount-check"]').text()).toContain('差额 ¥0.00')
    expect(mocks.request.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(0)
    await wrapper.get('[data-testid="save-payment-links"]').trigger('click')
    await flushPromises()
    const saved = mocks.request.mock.calls.find(([, options]) => options?.method === 'POST')
    expect(JSON.parse(saved![1].body)).toEqual({payment_ids: [1, 2]})
    wrapper.unmount()
  })
  it('prevents a stale combination from adding payments after manual selection and when disabled', async () => {
    const wrapper = mount(InvoicePaymentLinks, {props: {invoiceId: 12}, global})
    await flushPromises()
    await wrapper.get('[aria-label="关联付款单 USED-100"]').setValue(true)
    expect(wrapper.get('[data-testid="choose-payment-combination"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[aria-label="关联付款单 USED-100"]').setValue(false)
    await wrapper.setProps({disabled: true})
    expect(wrapper.get('[data-testid="choose-payment-combination"]').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
  it('keeps the correct difference when an existing linked payment is negative', async () => {
    const result = response()
    result.data.linked[0]!.current_payment_amount = '-20.00'
    mocks.request.mockResolvedValue(result)
    const wrapper = mount(InvoicePaymentLinks, {props: {invoiceId: 12}, global})
    await flushPromises()
    expect(wrapper.get('[data-testid="payment-amount-check"]').text()).toContain('差额 ¥140.00')
    wrapper.unmount()
  })
  it('keeps unknown invoice amounts unverified and allows explicit manual linking', async () => {
    const result: any = response()
    result.data.context.target_amount = null
    result.data.context.remaining = null
    mocks.request.mockResolvedValue(result)
    const wrapper = mount(InvoicePaymentLinks, {props: {invoiceId: 12}, global})
    await flushPromises()
    expect(wrapper.get('[data-testid="payment-amount-check"]').text()).toContain('发票价税合计 待核实')
    expect(wrapper.get('[data-testid="payment-amount-check"]').text()).toContain('差额 待核实')
    expect(wrapper.find('[data-testid="choose-payment-combination"]').exists()).toBe(false)
    await wrapper.get('[aria-label="关联付款单 SMART-60"]').setValue(true)
    await wrapper.get('[data-testid="save-payment-links"]').trigger('click')
    await flushPromises()
    expect(mocks.request.mock.calls.find(([, options]) => options?.method === 'POST')).toBeDefined()
    wrapper.unmount()
  })
})
