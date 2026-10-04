// @vitest-environment jsdom
import {mount, flushPromises, type VueWrapper} from '@vue/test-utils'
import {beforeEach, afterEach, describe, expect, it, vi} from 'vitest'
import PaymentReceiptPicker from './PaymentReceiptPicker.vue'
import type {Row} from './model'

const mocks = vi.hoisted(() => ({request:vi.fn(), confirm:vi.fn(), warning:vi.fn(), leave:[] as Function[], update:[] as Function[]}))
vi.mock('../../api', () => ({request:mocks.request, query:(values:Record<string,any>) => {
 const params = new URLSearchParams()
 for(const [key,value] of Object.entries(values)) if(value !== '' && value != null) params.set(key,String(value))
 return params.toString()
}}))
vi.mock('element-plus', () => ({ElMessageBox:{confirm:mocks.confirm}, ElMessage:{warning:mocks.warning}}))
vi.mock('vue-router', async importOriginal => ({...await importOriginal<typeof import('vue-router')>(),
 onBeforeRouteLeave:(guard:Function) => mocks.leave.push(guard), onBeforeRouteUpdate:(guard:Function) => mocks.update.push(guard)}))

const button = {props:['disabled','loading'],template:'<button :disabled="disabled || loading"><slot/></button>'}
const dialog = {props:['modelValue','title','beforeClose'],emits:['update:modelValue'],template:'<section v-if="modelValue" role="dialog" :aria-label="title"><button data-testid="dialog-close" @click="beforeClose(() => $emit(\'update:modelValue\',false))">关闭窗口</button><slot/><slot name="footer"/></section>'}
const global = {stubs:{'el-button':button,'el-dialog':dialog,RouterLink:{props:['to'],template:'<a :href="to"><slot/></a>'}}}
const payment = {id:2,pay_number:'FK-002',current_payment_amount:'200.00',payer_supplier_name:'付款甲公司',payee_supplier_name:'收款乙公司'}
const secondPayment = {id:3,pay_number:'FK-003',current_payment_amount:'300.00',payer_name:'付款丙公司',payee_supplier_name:'收款丁公司'}
const linked = {id:8,receipt_number:'OLD-008',amount:'50.00',payment_date:'2026-10-01',payer_name:'付款甲公司',payee_name:'收款乙公司',file_name:'old.pdf'}
const candidate = {id:9,receipt_number:'NEW-009',amount:'100.00',payment_date:'2026-10-02',payer_name:'付款甲公司',payee_name:'收款乙公司',file_name:'new.pdf',recommended:true}
const another = {...candidate,id:10,receipt_number:'NEW-010',amount:'100.00'}
const result = {code:0,data:{linked:[linked],candidates:[candidate,another],count:2}}
let wrappers:VueWrapper[] = []
function create() {const wrapper = mount(PaymentReceiptPicker,{global}); wrappers.push(wrapper); return wrapper}
async function open(payments:Row[] = [payment], selectedPaymentId?:number) {const wrapper = create(); (wrapper.vm as any).open(payments,selectedPaymentId); await flushPromises(); return wrapper}
const save = (wrapper:VueWrapper) => wrapper.get('[data-testid="save-payment-receipts"]')
const select = (wrapper:VueWrapper) => wrapper.get('select[aria-label="选择付款单"]')
const choose = (wrapper:VueWrapper,id=9) => wrapper.get(`input[type="checkbox"][value="${id}"]`).setValue(true)

describe('associate receipts from a payment', () => {
 beforeEach(() => {vi.resetAllMocks(); mocks.leave.length=0; mocks.update.length=0; mocks.confirm.mockResolvedValue(true); mocks.request.mockResolvedValue(result)})
 afterEach(() => {wrappers.forEach(wrapper => wrapper.unmount()); wrappers=[]})

 it('requires explicit checked receipt IDs and one batch save, while retaining existing links', async () => {
  const wrapper = await open()
  expect(wrapper.text()).toContain(payment.payee_supplier_name)
  expect(wrapper.text()).toContain('200.00')
  expect(wrapper.get(`a[href="/payment-receipts?receipt_id=8"]`).text()).toContain('OLD-008')
  expect(wrapper.findAll('input[type="checkbox"]').every(input => !(input.element as HTMLInputElement).checked)).toBe(true)
  expect(save(wrapper).attributes('disabled')).toBeDefined()
  await choose(wrapper); await choose(wrapper,10)
  expect(mocks.request.mock.calls.filter(([,options]) => options?.method === 'POST')).toHaveLength(0)
  mocks.request.mockResolvedValueOnce({code:0,data:{linked:[linked,candidate,another],candidates:[],count:0}})
  await save(wrapper).trigger('click'); await flushPromises()
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/for-payment/2',{method:'POST',body:JSON.stringify({receipt_ids:[9,10]})})
  expect(wrapper.text()).toContain('OLD-008')
  expect(wrapper.text()).toContain('NEW-009')
  expect(wrapper.emitted('changed')).toHaveLength(1)
 })

 it('shows empty orders and asks the user to choose among multiple payments', async () => {
  const empty = await open([])
  expect(empty.text()).toContain('订单尚无付款单，请先新增付款单')
  expect(mocks.request).not.toHaveBeenCalled()
  const multiple = await open([payment,secondPayment])
  expect((select(multiple).element as HTMLSelectElement).value).toBe('')
  expect(multiple.text()).toContain('请选择付款单')
  expect(mocks.request).not.toHaveBeenCalled()
  await select(multiple).setValue('3'); await flushPromises()
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/for-payment/3?page=1')
  expect(multiple.get('[aria-label="当前付款单"]').text()).toContain('付款丙公司')
  expect(multiple.get('[aria-label="当前付款单"]').text()).toContain('300.00')
 })

 it('uses an explicit payment identity when supplied', async () => {
  const wrapper = await open([payment,secondPayment],3)
  expect((select(wrapper).element as HTMLSelectElement).value).toBe('3')
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/for-payment/3?page=1')
 })

 it('shows saved server payment details instead of an unsaved editor amount or unit', async () => {
  mocks.request.mockResolvedValueOnce({...result,data:{...result.data,payment:{id:2,pay_number:'FK-002',current_payment_amount:'200.00',payer_name:'已保存付款公司',payee_supplier_name:'已保存收款公司'}}})
  const wrapper = await open([{...payment,current_payment_amount:'999.00',payer_supplier_name:'未保存付款公司',payee_supplier_name:'未保存收款公司'}])
  const summary = wrapper.get('[aria-label="当前付款单"]').text()
  expect(summary).toContain('200.00')
  expect(summary).toContain('已保存付款公司')
  expect(summary).toContain('已保存收款公司')
  expect(summary).not.toContain('999.00')
  expect(summary).not.toContain('未保存')
 })

 it('discards an older load when the user switches the payment', async () => {
  let resolve!:Function
  mocks.request.mockImplementationOnce(() => new Promise(done => {resolve=done}))
  const wrapper = create(); (wrapper.vm as any).open([payment,secondPayment],2)
  await flushPromises()
  await select(wrapper).setValue('3'); await flushPromises()
  resolve({code:0,data:{linked:[{...linked,receipt_number:'OLD PAYMENT RESULT'}],candidates:[],count:0}})
  await flushPromises()
  expect(wrapper.text()).not.toContain('OLD PAYMENT RESULT')
  expect(wrapper.text()).toContain('OLD-008')
  expect(wrapper.get('[aria-label="当前付款单"]').text()).toContain('FK-003')
 })

 it('retains checked choices on a failed save and allows a confirmed retry', async () => {
  const wrapper = await open(); await choose(wrapper)
  mocks.request.mockRejectedValueOnce(new Error('关联保存失败，请重试'))
  await save(wrapper).trigger('click'); await flushPromises()
  expect(wrapper.get('input[value="9"]').element).toHaveProperty('checked',true)
  expect(wrapper.get('[role="alert"]').text()).toContain('关联保存失败')
  expect(save(wrapper).attributes('disabled')).toBeUndefined()
  expect(wrapper.text()).toContain('OLD-008')
  expect(wrapper.emitted('changed')).toBeUndefined()
  await save(wrapper).trigger('click'); await flushPromises()
  expect(mocks.request.mock.calls.filter(([,options]) => options?.method === 'POST')).toHaveLength(2)
 })

 it('blocks a repeated uncertain write until a successful reload verifies the links', async () => {
  const wrapper = await open(); await choose(wrapper)
  mocks.request.mockRejectedValueOnce(Object.assign(new Error('连接中断，提交结果尚未确认。请先核对列表，勿重复提交。'),{uncertain:true}))
  await save(wrapper).trigger('click'); await flushPromises()
  expect(wrapper.get('input[value="9"]').element).toHaveProperty('checked',true)
  expect(save(wrapper).attributes('disabled')).toBeDefined()
  await wrapper.get('[data-testid="retry-payment-receipts"]').trigger('click'); await flushPromises()
  expect(wrapper.get('input[value="9"]').element).toHaveProperty('checked',false)
  await choose(wrapper)
  expect(save(wrapper).attributes('disabled')).toBeUndefined()
 })

 it('lets the user close an unsaved selection without writing any relation', async () => {
  const wrapper = await open(); await choose(wrapper)
  expect(await (wrapper.vm as any).close()).toBe(true)
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  expect(mocks.confirm).not.toHaveBeenCalled()
  expect(mocks.request.mock.calls.filter(([,options]) => options?.method === 'POST')).toHaveLength(0)
  ;(wrapper.vm as any).open([payment]); await flushPromises()
  expect(wrapper.get('input[value="9"]').element).toHaveProperty('checked',false)
 })

 it('clears unsaved choices when switching the target payment', async () => {
  const wrapper = await open([payment,secondPayment],2); await choose(wrapper)
  await select(wrapper).setValue('3'); await flushPromises()
  expect((select(wrapper).element as HTMLSelectElement).value).toBe('3')
  expect(wrapper.get('input[value="9"]').element).toHaveProperty('checked',false)
  expect(mocks.confirm).not.toHaveBeenCalled()
  expect(mocks.request).toHaveBeenCalledTimes(2)
 })

 it('prevents close, switch, and route changes while saving', async () => {
  const wrapper = await open([payment,secondPayment],2); await choose(wrapper)
  let finish!:Function
  mocks.request.mockImplementationOnce(() => new Promise(done => {finish=done}))
  await save(wrapper).trigger('click')
  expect(select(wrapper).attributes('disabled')).toBeDefined()
  expect(await (wrapper.vm as any).close()).toBe(false)
  expect(await mocks.leave[0]!()).toBe(false)
  expect(await mocks.update[0]!()).toBe(false)
  expect(wrapper.emitted('busy')).toEqual([[true]])
  finish(result); await flushPromises()
  expect(wrapper.emitted('busy')).toEqual([[true],[false]])
 })

 it('unlinks only the existing receipt-to-payment relationship after confirmation', async () => {
  const wrapper = await open()
  await wrapper.get('[aria-label="解除回单 OLD-008 的关联"]').trigger('click'); await flushPromises()
  expect(mocks.confirm).toHaveBeenCalled()
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/8/payments/2',{method:'DELETE'})
  expect(mocks.request).not.toHaveBeenCalledWith('/payment-receipts/8',{method:'DELETE'})
  expect(wrapper.emitted('changed')).toHaveLength(1)
 })

 it('does not unlink when confirmation is cancelled', async () => {
  const wrapper = await open(); mocks.confirm.mockRejectedValue('cancel')
  await wrapper.get('[aria-label="解除回单 OLD-008 的关联"]').trigger('click'); await flushPromises()
  expect(mocks.request.mock.calls.filter(([,options]) => options?.method === 'DELETE')).toHaveLength(0)
  expect(wrapper.text()).toContain('OLD-008')
 })

 it('searches and paginates candidates without auto-selecting any receipt', async () => {
  mocks.request.mockResolvedValue({...result,data:{...result.data,count:45}})
  const wrapper = await open()
  await wrapper.get('input[aria-label="搜索付款回单"]').setValue('乙公司')
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/for-payment/2?q=%E4%B9%99%E5%85%AC%E5%8F%B8&page=1')
  await wrapper.get('[data-testid="next-receipt-page"]').trigger('click'); await flushPromises()
  expect(mocks.request).toHaveBeenCalledWith('/payment-receipts/for-payment/2?q=%E4%B9%99%E5%85%AC%E5%8F%B8&page=2')
  expect(wrapper.findAll('input[type="checkbox"]').every(input => !(input.element as HTMLInputElement).checked)).toBe(true)
  expect(wrapper.get('a[href="/payment-receipts"]').text()).toContain('上传')
 })

 it('resets search and page after a saved batch returns the default first page', async () => {
  mocks.request.mockResolvedValue({...result,data:{...result.data,count:45}})
  const wrapper = await open()
  await wrapper.get('input[aria-label="搜索付款回单"]').setValue('乙公司')
  await wrapper.get('form').trigger('submit'); await flushPromises()
  await wrapper.get('[data-testid="next-receipt-page"]').trigger('click'); await flushPromises()
  await choose(wrapper)
  await save(wrapper).trigger('click'); await flushPromises()
  expect(wrapper.get('input[aria-label="搜索付款回单"]').element).toHaveProperty('value','')
  expect(wrapper.get('.receipt-pages').text()).toContain('1 / 3')
 })

 it('accepts an order-specific empty action without making a receipt request', async () => {
  const wrapper = mount(PaymentReceiptPicker,{global,slots:{empty:'<a href="/payments/new?order_id=5">新增此订单付款单</a>'}})
  wrappers.push(wrapper)
  ;(wrapper.vm as any).open([]); await flushPromises()
  expect(wrapper.get('a[href="/payments/new?order_id=5"]').text()).toContain('新增此订单付款单')
  expect(mocks.request).not.toHaveBeenCalled()
 })
})
