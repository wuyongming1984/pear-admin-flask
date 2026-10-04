// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {createMemoryHistory, createRouter} from 'vue-router'
import PaymentInvoicePicker from './PaymentInvoicePicker.vue'
import PaymentEntrySheet from './PaymentEntrySheet.vue'
import CorePage from './CorePage.vue'

const mocks = vi.hoisted(() => ({request: vi.fn(), allRows: vi.fn()}))
vi.mock('../../api', () => ({request: mocks.request, allRows: mocks.allRows, query: (data: any) => new URLSearchParams(data).toString(), safeUrl: (value: any) => value || ''}))
vi.mock('../../session', () => ({session: {nickname: '测试经办人', userName: 'test'}}))
vi.mock('element-plus', () => ({ElMessage: {error: vi.fn(), success: vi.fn(), warning: vi.fn()}, ElMessageBox: {confirm: vi.fn()}}))
vi.mock('../../components/AttachmentEditor.vue', () => ({default: {template: '<div />'}}))
vi.mock('./PaymentReceiptsForPayment.vue', () => ({default: {template: '<div />'}}))
const input = {props: ['modelValue'], emits: ['update:modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />'}
const stubs: any = {
  'el-dialog': {props: ['modelValue', 'title'], template: '<section v-if="modelValue" role="dialog" :aria-label="title"><slot/><slot name="footer"/></section>'},
  'el-button': {props: ['disabled', 'loading'], template: '<button type="button" :disabled="disabled || loading"><slot/></button>'},
  'el-form': {template: '<form><slot/></form>'}, 'el-form-item': {template: '<label><slot/></label>'},
  'el-input': input, 'el-select': input, 'el-select-v2': input, 'el-date-picker': input,
  'el-option': true, 'el-alert': true, 'el-descriptions': true, 'el-descriptions-item': true,
  'el-table': true, 'el-table-column': true, 'el-popover': true, 'el-checkbox': true, 'el-pagination': true, 'el-checkbox-group': true,
  RouterLink: {props: ['to'], template: '<a><slot/></a>'},
}
const old = {id: 8, invoice_number: 'OLD', seller_name: '原有单位', total_amount: '10.00', tax_amount: '1.30'}
const invoices = [
  {id: 1, invoice_number: 'FIRST', seller_name: '上海建材有限公司', total_amount: '40.00', tax_amount: '5.20', gross_amount: '45.20', score: 95, reasons: ['购买方与付款单位一致', '同一项目'], linked_payments: [], already_selected: false, can_recommend: true, amount_difference: '-43.50'},
  {id: 2, invoice_number: 'SECOND', seller_name: '上海建材有限公司分公司', total_amount: '38.50', tax_amount: '5.00', gross_amount: '43.50', score: 80, reasons: ['销售方名称相近'], linked_payments: [], already_selected: false, can_recommend: true, amount_difference: '-45.20'},
]
const recommendation = () => ({
  context: {target_amount: '100.00', amount_basis: 'invoice_amount', selected_gross: '11.30', remaining: '88.70'},
  candidates: invoices,
  combinations: [{invoice_ids: [1, 2], total_gross: '88.70', difference: '0.00', reasons: ['两张价税合计与剩余金额一致']}],
  total_count: 2, truncated: false, combination_limit: 30,
})
function picker(extra: Record<string, any> = {}) {
  return mount(PaymentInvoicePicker, {props: {modelValue: [8], invoices: [old, ...invoices], supplierName: '上海建材有限公司', recommendation: recommendation(), ...extra} as any, global: {stubs}})
}

describe('smart payment invoice recommendations', () => {
  beforeEach(() => vi.resetAllMocks())
  it('shows fuzzy candidates with reasons and other payment links without selecting recommendations', async () => {
    const occupied = {...invoices[1], can_recommend: false, linked_payments: [{id: 7, pay_number: 'OTHER-PAY'}]}
    const wrapper = picker({recommendation: {...recommendation(), candidates: [invoices[0], occupied], combinations: []}})
    await wrapper.get('[data-testid="smart-invoice-recommendations"]').trigger('click')
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.text()).toContain('FIRST')
    expect(dialog.text()).toContain('SECOND')
    expect(dialog.text()).toContain('购买方与付款单位一致')
    expect(dialog.text()).toContain('OTHER-PAY')
    expect(dialog.text()).toContain('43.50')
    expect(dialog.findAll('input[type="checkbox"]').every(item => !(item.element as HTMLInputElement).checked)).toBe(true)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    wrapper.unmount()
  })
  it('adds a chosen combination to the draft while preserving original links until explicit confirmation', async () => {
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    expect(wrapper.get('[aria-label="智能关联金额核对"]').text()).toContain('100.00')
    expect(wrapper.get('[aria-label="智能关联金额核对"]').text()).toContain('11.30')
    await wrapper.get('[data-testid="choose-invoice-combination"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.get('[aria-label="关联发票 FIRST"]').element).toHaveProperty('checked', true)
    expect(wrapper.get('[aria-label="关联发票 SECOND"]').element).toHaveProperty('checked', true)
    await wrapper.get('[data-testid="confirm-invoice-selection"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[[8, 1, 2]]])
    wrapper.unmount()
  })
  it('requires recalculation after manual draft changes and sends the draft to the reload event', async () => {
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.get('[aria-label="关联发票 FIRST"]').setValue(true)
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="choose-invoice-combination"]').trigger('click')
    expect(wrapper.get('[aria-label="关联发票 SECOND"]').element).toHaveProperty('checked', false)
    await wrapper.get('[data-testid="recalculate-invoice-recommendations"]').trigger('click')
    expect(wrapper.emitted('load')?.at(-1)).toEqual([[8, 1]])
    await wrapper.setProps({recommendation: {...recommendation(), combinations: [], context: {target_amount: '100.00', amount_basis: 'invoice_amount', selected_gross: '56.50', remaining: '43.50'}}} as any)
    expect(wrapper.get('[aria-label="智能关联金额核对"]').text()).toContain('56.50')
    expect(wrapper.get('[role="dialog"]').text()).toContain('可继续逐张核对')
    wrapper.unmount()
  })
  it('removes outdated combinations when payment fields invalidate the recommendation', async () => {
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.setProps({recommendation: undefined} as any)
    expect(wrapper.find('[data-testid="choose-invoice-combination"]').exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    wrapper.unmount()
  })
  it('rejects an invalid combination containing a candidate linked to another payment', async () => {
    const wrapper = picker({recommendation: {...recommendation(), candidates: [invoices[0], {...invoices[1], can_recommend: false}]}})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.get('[data-testid="choose-invoice-combination"]').trigger('click')
    expect(wrapper.get('[aria-label="关联发票 FIRST"]').element).toHaveProperty('checked', false)
    expect(wrapper.get('[aria-label="关联发票 SECOND"]').element).toHaveProperty('checked', false)
    wrapper.unmount()
  })
  it('keeps new combinations disabled when their request used an older selection than the current draft', async () => {
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.get('[aria-label="关联发票 FIRST"]').setValue(true)
    await wrapper.setProps({recommendation: {...recommendation(), selected_invoice_ids: [8]}} as any)
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="choose-invoice-combination"]').trigger('click')
    expect(wrapper.get('[aria-label="关联发票 SECOND"]').element).toHaveProperty('checked', false)
    wrapper.unmount()
  })
  it('subtracts a negative invoice total correctly when displaying the remaining amount', async () => {
    const credit = {...old, total_amount: '-10.00', tax_amount: '-1.30'}
    const wrapper = picker({invoices: [credit, ...invoices], recommendation: {...recommendation(), context: {target_amount: '100.00', amount_basis: 'invoice_amount', selected_gross: '-11.30', remaining: '111.30'}}})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    expect(wrapper.get('[aria-label="智能关联金额核对"]').text()).toContain('111.30')
    wrapper.unmount()
  })
  it('keeps the latest three monetary fields and totals original decimals before rounding', async () => {
    const first = {...old, total_amount: '.004', tax_amount: '1e-3'}
    const second = {id: 9, invoice_number: 'TINY', seller_name: '上海建材有限公司', total_amount: '.004', tax_amount: '.001'}
    const wrapper = picker({modelValue: [8, 9], invoices: [first, second, ...invoices]})
    expect(wrapper.get('[aria-label="已选择的发票"]').text()).toContain('不含税金额：¥0.00')
    expect(wrapper.get('[aria-label="已选择的发票"]').text()).toContain('税额：¥0.00')
    expect(wrapper.get('.payment-invoice-picker > header').text()).toContain('价税合计 ¥0.01')
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    const amounts = wrapper.get('[aria-label="智能关联金额核对"]').findAll('.recommendation-amounts > span')
    expect(amounts[1]!.text()).toBe('当前已选价税合计¥0.01')
    expect(amounts[2]!.text()).toBe('还差金额¥99.99')
    expect(wrapper.find('[data-testid="confirm-invoice-selection"]').exists()).toBe(true)
    wrapper.unmount()
  })
  it.each([undefined, null, '', '无法识别', true])('marks an unknown selected tax as unverified and stops amount combinations (%j)', async tax => {
    const wrapper = picker({invoices: [{...old, tax_amount: tax}, ...invoices]})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    const amounts = wrapper.get('[aria-label="智能关联金额核对"]').findAll('.recommendation-amounts > span')
    expect(amounts[1]!.text()).toBe('当前已选价税合计待核实')
    expect(amounts[2]!.text()).toBe('还差金额待核实')
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="choose-invoice-combination"]').trigger('click')
    expect(wrapper.get('[aria-label="关联发票 FIRST"]').element).toHaveProperty('checked', false)
    expect(wrapper.get('[data-testid="confirm-invoice-selection"]').attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })
  it('marks an uncached selected invoice as unverified instead of counting it as zero', async () => {
    const wrapper = picker({invoices})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    const amounts = wrapper.get('[aria-label="智能关联金额核对"]').findAll('.recommendation-amounts > span')
    expect(amounts[1]!.text()).toBe('当前已选价税合计待核实')
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
  it('rejects an amount combination whose candidate has an unknown tax field', async () => {
    const unknown = {...invoices[1], tax_amount: null}
    const wrapper = picker({invoices: [old, invoices[0], unknown], recommendation: {...recommendation(), candidates: [invoices[0], unknown]}})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="choose-invoice-combination"]').trigger('click')
    expect(wrapper.get('[aria-label="关联发票 FIRST"]').element).toHaveProperty('checked', false)
    wrapper.unmount()
  })
  it('keeps an unknown recommendation target unverified and stops amount combinations', async () => {
    const wrapper = picker({recommendation: {...recommendation(), context: {target_amount: null, amount_basis: 'invoice_amount', selected_gross: '11.30', remaining: null}}})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    const amounts = wrapper.get('[aria-label="智能关联金额核对"]').findAll('.recommendation-amounts > span')
    expect(amounts[0]!.text()).toBe('开票金额待核实')
    expect(amounts[2]!.text()).toBe('还差金额待核实')
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
  it('honors an unverified server context even when older cached selected amounts look complete', async () => {
    const wrapper = picker({recommendation: {...recommendation(), context: {target_amount: '100.00', amount_basis: 'invoice_amount', selected_gross: null, remaining: null, reasons: ['原关联发票金额尚待核实']}}})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    const panel = wrapper.get('[aria-label="智能关联金额核对"]')
    const amounts = panel.findAll('.recommendation-amounts > span')
    expect(amounts[1]!.text()).toBe('当前已选价税合计待核实')
    expect(amounts[2]!.text()).toBe('还差金额待核实')
    expect(panel.text()).toContain('原关联发票金额尚待核实')
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
  it('discards cancelled draft changes and asks for fresh data each time the dialog opens', async () => {
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.get('[aria-label="关联发票 FIRST"]').setValue(true)
    await wrapper.get('[data-testid="cancel-invoice-selection"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    await wrapper.get('[data-testid="smart-invoice-recommendations"]').trigger('click')
    expect(wrapper.get('[aria-label="关联发票 FIRST"]').element).toHaveProperty('checked', false)
    expect(wrapper.emitted('load')).toEqual([[[8]], [[8]]])
    wrapper.unmount()
  })
  it('shows bounded search scope when candidate results are truncated', async () => {
    const wrapper = picker({recommendation: {...recommendation(), truncated: true, total_count: 1001}})
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    expect(wrapper.get('[role="dialog"]').text()).toContain('1001')
    expect(wrapper.get('[role="dialog"]').text()).toContain('前 30 张')
    wrapper.unmount()
  })
  it.each([{disabled: true}, {loading: true}, {error: '加载失败'}])('prevents confirmation and combination changes while blocked: %j', async blocked => {
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.setProps(blocked)
    expect(wrapper.get('[data-testid="confirm-invoice-selection"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="confirm-invoice-selection"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    wrapper.unmount()
  })
  it('prevents draft changes and confirmation throughout a dropped invoice upload', async () => {
    let finish!: (value: any) => void
    mocks.request.mockImplementation(() => new Promise(resolve => {finish = resolve}))
    const wrapper = picker()
    await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
    await wrapper.get('.payment-invoice-picker').trigger('drop', {dataTransfer: {files: [new File(['pdf'], 'test.pdf')]}})
    expect(wrapper.get('[aria-label="关联发票 FIRST"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="choose-invoice-combination"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="confirm-invoice-selection"]').attributes('disabled')).toBeDefined()
    finish({code: 0, data: {invoices: [], errors: [{name: 'test.pdf', reason: '上传失败'}]}})
    await flushPromises()
    wrapper.unmount()
  })
})

describe('payment editor recommendation context', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.allRows.mockImplementation(async (path: string) => path === '/order/' ? [{id: 3, supplier_id: 5, supplier_contact_person: '张工'}] : path === '/supplier/' ? [{id: 5, name: '上海建材有限公司', contact_person: '张工'}] : [])
  })
  it('loads read-only recommendations from the current payment and ignores a response after its amount changes', async () => {
    let finishOld!: (value: any) => void
    const payment = {id: 2, pay_number: 'PAY', order_id: 3, payee_supplier_id: 5, payer_supplier_id: 4, current_payment_amount: '120.00', invoice_amount: '100.00', create_at: '2026-10-01', invoices_list: [old]}
    let calls = 0
    mocks.request.mockImplementation(async (url: string) => {
      if (url === '/invoice-links/payments/recommendations') {
        calls++
        if (calls === 1) return new Promise(resolve => {finishOld = resolve})
        return {code: 0, data: {...recommendation(), candidates: [{...invoices[0], invoice_number: 'LATEST'}], combinations: []}}
      }
      return {code: 0, data: payment}
    })
    const router = createRouter({history: createMemoryHistory(), routes: [{path: '/payments/:id/edit', component: CorePage, meta: {coreKind: 'payments', coreMode: 'edit'}}]})
    await router.push('/payments/2/edit'); await router.isReady()
    const wrapper = mount({template: '<router-view />'}, {global: {plugins: [router], stubs, directives: {loading: () => {}}}})
    try {
      await flushPromises()
      await wrapper.get('[data-testid="smart-invoice-recommendations"]').trigger('click')
      const first = mocks.request.mock.calls.find(([url]) => url === '/invoice-links/payments/recommendations')!
      expect(first[1].method).toBe('POST')
      expect(JSON.parse(first[1].body)).toEqual({pay_id: 2, payee_supplier_id: 5, payer_supplier_id: 4, order_id: 3, current_payment_amount: '120.00', invoice_amount: '100.00', create_at: '2026-10-01', selected_invoice_ids: [8]})
      wrapper.getComponent(PaymentEntrySheet).vm.$emit('field', 'invoice_amount', '200.00')
      await flushPromises()
      expect(wrapper.get('[role="dialog"]').text()).toContain('LATEST')
      finishOld({code: 0, data: {...recommendation(), candidates: [{...invoices[0], invoice_number: 'STALE'}]}})
      await flushPromises()
      expect(wrapper.get('[role="dialog"]').text()).not.toContain('STALE')
      expect(wrapper.get('[aria-label="已选择的发票"]').text()).toContain('OLD')
      expect(mocks.request.mock.calls.some(([url, options]) => url.startsWith('/pay/') && options?.method)).toBe(false)
    } finally {wrapper.unmount()}
  })
})
