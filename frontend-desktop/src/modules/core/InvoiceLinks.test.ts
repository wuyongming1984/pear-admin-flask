// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {describe, it, expect, vi, beforeEach} from 'vitest'
import PaymentInvoicePicker from './PaymentInvoicePicker.vue'
import InvoicePaymentLinks from './InvoicePaymentLinks.vue'
const mocks=vi.hoisted(()=>({request:vi.fn()}))
vi.mock('../../api',()=>({request:mocks.request}))
const global={stubs:{'el-button':{props:['disabled','loading'],template:'<button :disabled="disabled||loading"><slot/></button>'},RouterLink:{props:['to'],template:'<a :href="to"><slot/></a>'}}}

describe('seller matched invoice/payment selections',()=>{
 beforeEach(()=>vi.resetAllMocks())
 it('offers full-name seller matches, retains selected legacy invoices and never silently clears them when the payee changes',async()=>{
  const wrapper=mount(PaymentInvoicePicker,{props:{modelValue:[3],supplierName:'上海（甲）公司',invoices:[
   {id:1,seller_name:' 上海(甲) 公司 ',invoice_number:'MATCH',total_amount:'100',tax_amount:'13'},
   {id:2,seller_name:'上海（甲）公司分公司',invoice_number:'OTHER'},
   {id:3,seller_name:'旧单位',invoice_number:'EXISTING'},
  ]},global})
  expect(wrapper.text()).toContain('MATCH');expect(wrapper.text()).toContain('EXISTING');expect(wrapper.text()).not.toContain('OTHER')
  expect(wrapper.text()).toContain('113.00')
  await wrapper.get('[aria-label="关联发票 MATCH"]').setValue(true)
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([[3,1]])
  await wrapper.setProps({supplierName:'无关单位'})
  expect(wrapper.text()).not.toContain('MATCH');expect(wrapper.text()).toContain('EXISTING')
  expect(wrapper.emitted('update:modelValue')).toHaveLength(1)
  wrapper.unmount()
 })
 it('has no candidates for a blank payee and allows explicitly removing an old association',async()=>{
  const wrapper=mount(PaymentInvoicePicker,{props:{modelValue:[1],supplierName:'',invoices:[{id:1,invoice_number:'OLD',seller_name:''},{id:2,invoice_number:'UNSELECTED',seller_name:''}]},global})
  expect(wrapper.text()).not.toContain('UNSELECTED')
  await wrapper.get('[aria-label="关联发票 OLD"]').setValue(false)
  expect(wrapper.emitted('update:modelValue')).toEqual([[[]]])
  wrapper.unmount()
 })
 it('loads matching payments, posts selected IDs once, and displays the saved reverse links',async()=>{
  const pay={id:9,pay_number:'PAY-009',payee_supplier_name:'甲公司',current_payment_amount:'30.20',project_name:'公园'}
  mocks.request.mockResolvedValue({code:0,data:{seller_name:'甲公司',matched:[pay],linked:[]}})
  const wrapper=mount(InvoicePaymentLinks,{props:{invoiceId:12},global});await flushPromises()
  expect(wrapper.text()).toContain('PAY-009')
  await wrapper.get('[aria-label="关联付款单 PAY-009"]').setValue(true)
  let resolve:any;mocks.request.mockImplementationOnce(()=>new Promise(r=>resolve=r))
  await wrapper.get('[data-testid="save-payment-links"]').trigger('click')
  await wrapper.get('[data-testid="save-payment-links"]').trigger('click')
  const posts=mocks.request.mock.calls.filter(([,o])=>o?.method==='POST')
  expect(posts).toHaveLength(1);expect(posts[0]?.[0]).toBe('/invoice-links/invoices/12/payments')
  expect(JSON.parse(posts[0]?.[1].body)).toEqual({payment_ids:[9]})
  resolve({code:0,data:{seller_name:'甲公司',matched:[pay],linked:[pay]}});await flushPromises()
  expect(wrapper.get('[aria-label="已关联付款单"]').text()).toContain('PAY-009')
  expect(wrapper.get('a').attributes('href')).toBe('/payments/9')
  expect(wrapper.emitted('changed')).toHaveLength(1)
  wrapper.unmount()
 })
 it('discards a late response after switching invoices and preserves a selection on save failure',async()=>{
  let old:any;mocks.request.mockImplementationOnce(()=>new Promise(r=>old=r))
  const wrapper=mount(InvoicePaymentLinks,{props:{invoiceId:1},global})
  mocks.request.mockResolvedValueOnce({code:0,data:{seller_name:'乙公司',linked:[],matched:[{id:2,pay_number:'NEW'}]}})
  await wrapper.setProps({invoiceId:2});await flushPromises()
  old({code:0,data:{seller_name:'甲公司',linked:[],matched:[{id:1,pay_number:'STALE'}]}});await flushPromises()
  expect(wrapper.text()).toContain('NEW');expect(wrapper.text()).not.toContain('STALE')
  await wrapper.get('[aria-label="关联付款单 NEW"]').setValue(true)
  mocks.request.mockRejectedValueOnce(new Error('保存失败，请重试'))
  await wrapper.get('[data-testid="save-payment-links"]').trigger('click');await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('保存失败')
  expect((wrapper.get('input').element as HTMLInputElement).checked).toBe(true)
  expect(wrapper.emitted('changed')).toBeUndefined()
  wrapper.unmount()
 })
 it('refreshes associations when returning to a cached invoice after editing a payment',async()=>{
  mocks.request.mockResolvedValueOnce({code:0,data:{seller_name:'甲公司',linked:[],matched:[]}})
  const wrapper=mount({components:{InvoicePaymentLinks},data:()=>({shown:true}),template:'<keep-alive><InvoicePaymentLinks v-if="shown" :invoice-id="12"/></keep-alive>'},{global})
  await flushPromises();await wrapper.setData({shown:false})
  mocks.request.mockResolvedValueOnce({code:0,data:{seller_name:'甲公司',linked:[{id:9,pay_number:'SAVED-ELSEWHERE'}],matched:[]}})
  await wrapper.setData({shown:true});await flushPromises()
  expect(wrapper.text()).toContain('SAVED-ELSEWHERE')
  wrapper.unmount()
 })
})
