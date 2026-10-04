// @vitest-environment jsdom
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {computed, defineComponent, inject, provide} from 'vue'
import {mount, flushPromises} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'
import CorePage from './CorePage.vue'

const mocks = vi.hoisted(() => ({request: vi.fn(), allRows: vi.fn()}))
vi.mock('../../api', () => ({request: mocks.request, allRows: mocks.allRows, query: (p: any) => new URLSearchParams(p).toString(), safeUrl: (p: any) => p || ''}))
vi.mock('../../feedback', () => ({ElMessage: {error: vi.fn(), success: vi.fn(), warning: vi.fn()}, ElMessageBox: {confirm: vi.fn()}}))
vi.mock('../../components/AttachmentEditor.vue', () => ({default: {template: '<div />'}}))

const table = defineComponent({props: ['data'], setup(props) {provide('rows', computed(() => props.data || []))}, template: '<div class="test-table"><slot /></div>'})
const column = defineComponent({props: ['label', 'prop'], setup() {return {rows: inject<any>('rows')}}, template: '<section class="test-column" :data-label="label"><b>{{label}}</b><span v-for="row in rows" :key="row.id"><slot :row="row">{{row[prop]}}</slot></span></section>'})
const stubs: any = {
  'm-table': table, 'm-table-column': column,
  'm-descriptions': {template: '<div><slot /></div>'},
  'm-descriptions-item': {props: ['label'], template: '<p :data-label="label">{{label}}：<slot /></p>'},
  'm-form': {template: '<form><slot /></form>'}, 'm-form-item': {props: ['label'], template: '<label>{{label}}<slot /></label>'},
  'm-select': {template: '<div class="test-select"><slot /></div>'}, 'm-option': {props: ['label'], template: '<p class="test-option">{{label}}</p>'},
  'm-button': {template: '<button><slot /></button>'}, 'm-input': true, 'm-date-picker': true,
  'm-alert': true, 'm-dialog': true, 'm-pagination': true, 'm-popover': true, 'm-checkbox-group': true, 'm-checkbox': true, 'van-search': true,
  'm-empty': {props: ['description'], template: '<p>{{description}}</p>'}, TablePrint: true,
}

async function render(path: string, kind: string, mode: string, invoice: Record<string, any>) {
  const payment = {id: 9, pay_number: 'LOCAL-FK9', current_payment_amount: '88.00', invoice_amount: '35.00', invoices_list: [invoice]}
  mocks.request.mockImplementation(async (url: string) => {
    if (url.startsWith('/material/invoice?')) return {data: [invoice], count: 1}
    if (url === '/pay/9') return {data: payment}
    return {data: {}}
  })
  mocks.allRows.mockImplementation(async (url: string) => url === '/material/invoice' ? [invoice] : url === '/pay/' ? [payment] : [])
  const routePath = path.replace(/\/\d+(?=\/|$)/, '/:id')
  const router = createRouter({history: createMemoryHistory(), routes: [{path: '/apps', component: {template: '<div />'}}, {path: routePath, component: CorePage, meta: {coreKind: kind, coreMode: mode}}]})
  await router.push(path)
  await router.isReady()
  const wrapper = mount({template: '<router-view />'}, {global: {plugins: [router], stubs, directives: {loading: () => {}}}})
  await flushPromises()
  return wrapper
}

describe('mobile invoice amount display', () => {
  beforeEach(() => vi.clearAllMocks())
  it.each([
    ['standard', '100', '13', '113.00', '100.00', '13.00'],
    ['zero tax', '100', 0, '100.00', '100.00', '0.00'],
    ['credit invoice', '-100', '-13', '-113.00', '-100.00', '-13.00'],
    ['precise addition', '1.005', '0.005', '1.01', '1.01', '0.01'],
    ['missing tax', '100', null, '待核实', '100.00', '待核实'],
    ['invalid untaxed amount', 'NaN', '13', '待核实', '待核实', '13.00'],
  ])('shows the same labeled amounts for %s in library, detail, payment and picker', async (_name, untaxed, tax, totalText, untaxedText, taxText) => {
    const invoice = {id: 1, invoice_number: 'LOCAL-INV1', seller_name: '本地测试单位', total_amount: untaxed, tax_amount: tax, ocr_status: 'pending'}
    for (const [path, kind, mode] of [['/invoices', 'invoices', 'list'], ['/invoices/1', 'invoices', 'detail'], ['/payments/9', 'payments', 'detail']]) {
      const wrapper = await render(path!, kind!, mode!, invoice)
      for (const [label, value] of [['价税合计', totalText], ['不含税金额', untaxedText], ['税额', taxText]]) {
        expect(wrapper.findAll(`[data-label="${label}"]`).some(part => part.text().includes(value!)), `${path}: ${label} ${value}; rendered ${wrapper.text()}`).toBe(true)
      }
      if (kind === 'payments') {
        expect(wrapper.find('[data-label="本次实付金额"]').text()).toContain('88.00')
        expect(wrapper.find('[data-label="开票金额"]').text()).toContain('35.00')
      }
      expect(wrapper.text()).not.toContain('NaN')
      expect(mocks.request.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true)
      wrapper.unmount()
    }
    const picker = await render('/payments/9/edit', 'payments', 'edit', invoice)
    const option = picker.findAll('.test-option').find(part => part.text().includes('LOCAL-INV1'))!
    const currency = (value: string) => value === '待核实' ? value : `¥${value}`
    expect(option.text()).toContain(`价税合计 ${currency(totalText!)}`)
    expect(option.text()).toContain(`不含税金额 ${currency(untaxedText!)}`)
    expect(option.text()).toContain(`税额 ${currency(taxText!)}`)
    picker.unmount()
  })
})
