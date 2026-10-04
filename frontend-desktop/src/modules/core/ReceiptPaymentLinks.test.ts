// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import ReceiptPaymentLinks from './ReceiptPaymentLinks.vue'
const mocks = vi.hoisted(() => ({request: vi.fn(), confirm: vi.fn()}))
vi.mock('../../api', () => ({request: mocks.request, query: (v:any) => new URLSearchParams(v).toString()}))
vi.mock('element-plus', () => ({ElMessageBox: {confirm: mocks.confirm}}))
const stub = {props: ['disabled','loading'], template: '<button :disabled="disabled || loading"><slot/></button>'}
const linked = {id: 1, pay_number: '已关联付款单', current_payment_amount: '10.00'}
const candidate = {id: 2, pay_number: '待关联付款单', current_payment_amount: '20.00'}
const response = {code: 0, data: {linked: [linked], candidates: [candidate], count: 1}}
function open() {return mount(ReceiptPaymentLinks, {props: {receiptId: 8}, global: {stubs: {'el-button': stub, RouterLink: {template: '<a><slot/></a>'}}}})}
describe('explicit receipt links', () => {
 beforeEach(() => {vi.resetAllMocks(); mocks.request.mockResolvedValue(response); mocks.confirm.mockResolvedValue(true)})
 it('only appends the checked payment after a save click', async () => {
  const wrapper = open(); await flushPromises()
  expect(wrapper.text()).toContain(linked.pay_number)
  expect(wrapper.find('input[type=checkbox]').element).toHaveProperty('checked', false)
  await wrapper.find('input[type=checkbox]').setValue(true)
  expect(mocks.request).toHaveBeenCalledTimes(1)
  await wrapper.find('[data-testid=save-receipt-links]').trigger('click'); await flushPromises()
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/8/payments', {method: 'POST', body: JSON.stringify({payment_ids: [2]})})
  wrapper.unmount()
 })
 it('retains checked choices when saving fails', async () => {
  const wrapper = open(); await flushPromises()
  await wrapper.find('input[type=checkbox]').setValue(true)
  mocks.request.mockRejectedValueOnce(new Error('保存失败，请重试'))
  await wrapper.find('[data-testid=save-receipt-links]').trigger('click'); await flushPromises()
  expect(wrapper.find('input[type=checkbox]').element).toHaveProperty('checked', true)
  expect(wrapper.find('[role=alert]').text()).toContain('保存失败')
  wrapper.unmount()
 })
 it('does not let an old request overwrite a newly selected receipt', async () => {
  let resolve:any
  mocks.request.mockImplementationOnce(() => new Promise(r => resolve = r))
  const wrapper = open()
  await wrapper.setProps({receiptId: 9}); await flushPromises()
  resolve({code: 0, data: {linked: [{id: 3, pay_number: '旧回单的关联'}], candidates: [], count: 0}})
  await flushPromises()
  expect(wrapper.text()).not.toContain('旧回单的关联')
  expect(wrapper.text()).toContain(linked.pay_number)
  wrapper.unmount()
 })
})
