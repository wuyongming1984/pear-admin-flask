// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {createRouter, createMemoryHistory} from 'vue-router'
import {describe, it, beforeEach, expect, vi} from 'vitest'
import ReceiptLibrary from './ReceiptLibrary.vue'
const mocks = vi.hoisted(() => ({request:vi.fn(), confirm:vi.fn(), message: {success:vi.fn(),error:vi.fn(),warning:vi.fn()}}))
vi.mock('../../api', async original => ({...await original<any>(), request:mocks.request}))
vi.mock('element-plus', () => ({ElMessage:mocks.message, ElMessageBox:{confirm:mocks.confirm}}))
const stubs = {
 PageHeader: {props:['title'],template:'<header>{{title}}<slot/></header>'}, ReceiptPaymentLinks:true, InvoicePdfPreview:true,
 'el-button': {props:['disabled','loading'],template:'<button :disabled="disabled || loading"><slot/></button>'},
 'el-empty': {props:['description'],template:'<p>{{description}}</p>'},
 'el-pagination':true, 'el-upload':true,
 'el-dialog': {props:['modelValue'],template:'<div v-if="modelValue"><slot/><slot name="footer"/></div>'},
}
const row = {id:1,file_name:'回单.png',file_path:'/uploads/receipt.png',file_type:'png',payments:[],amount:'120.50',payee_name:'收款公司',remarks:'旧备注'}
async function open() {
 const router = createRouter({history:createMemoryHistory(),routes:[{path:'/',component:ReceiptLibrary}]})
 await router.push('/'); await router.isReady()
 const host = mount({template:'<router-view/>'}, {global:{plugins:[router], stubs}})
 await flushPromises();return host
}
describe('receipt library details', () => {
 beforeEach(() => {vi.resetAllMocks();mocks.request.mockResolvedValue({code:0,data:[row],count:1});mocks.confirm.mockResolvedValue(true)})
 it('shows the original receipt and its association section', async () => {
  const wrapper = await open()
  expect(wrapper.find('img.receipt-image').attributes('src')).toContain('/uploads/receipt.png')
  expect(wrapper.text()).toContain('付款回单库')
  expect(wrapper.findComponent({name:'ReceiptPaymentLinks'}).exists()).toBe(true)
  wrapper.unmount()
 })
 it('keeps edited information when a save fails', async () => {
  const wrapper = await open()
  await wrapper.findAll('button').find(b => b.text()==='编辑回单信息')!.trigger('click')
  await wrapper.find('textarea[aria-label="回单备注"]').setValue('新备注')
  mocks.request.mockRejectedValueOnce(new Error('保存失败'))
  await wrapper.findAll('button').find(b => b.text()==='保存回单信息')!.trigger('click');await flushPromises()
  expect((wrapper.find('textarea').element as HTMLTextAreaElement).value).toBe('新备注')
  expect(wrapper.text()).toContain('保存失败')
  wrapper.unmount()
 })
 it('fills only empty fields from recognition and waits for confirmation before saving', async () => {
  const wrapper = await open()
  mocks.request.mockResolvedValueOnce({code:0,data:{fields:{payer_name:'识别的付款公司',payee_name:'识别的另一公司',amount:'999.00',payment_date:'2026-10-04',receipt_number:'BANK-A'},source:'pdf_text',warnings:['请核对原件']}})
  await wrapper.find('[data-testid=recognize-receipt]').trigger('click'); await flushPromises()
  expect(mocks.request).toHaveBeenLastCalledWith('/payment-receipts/1/recognize')
  expect((wrapper.find('input[aria-label="回单付款单位"]').element as HTMLInputElement).value).toBe('识别的付款公司')
  expect((wrapper.find('input[aria-label="回单收款单位"]').element as HTMLInputElement).value).toBe('收款公司')
  expect((wrapper.find('input[aria-label="回单金额"]').element as HTMLInputElement).value).toBe('120.50')
  expect(wrapper.text()).toContain('请核对原件')
  expect(mocks.request.mock.calls.some((call:any[]) => call[1]?.method === 'PUT')).toBe(false)
  mocks.request.mockResolvedValueOnce({code:0,data:{...row,payer_name:'识别的付款公司'}})
  await wrapper.findAll('button').find(b => b.text()==='保存回单信息')!.trigger('click'); await flushPromises()
  expect(mocks.request).toHaveBeenLastCalledWith('/payment-receipts/1',{method:'PUT',body:JSON.stringify({receipt_number:'BANK-A',payment_date:'2026-10-04',payer_name:'识别的付款公司',payee_name:'收款公司',amount:'120.50',bank_name:'',remarks:'旧备注'})})
  wrapper.unmount()
 })
 it('keeps the editable form and original information when recognition fails', async () => {
  const wrapper = await open()
  mocks.request.mockRejectedValueOnce(new Error('扫描回单需要配置回单 OCR，可手工填写'))
  await wrapper.find('[data-testid=recognize-receipt]').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('扫描回单需要配置回单 OCR')
  expect((wrapper.find('input[aria-label="回单金额"]').element as HTMLInputElement).value).toBe('120.50')
  expect(wrapper.findAll('button').find(b => b.text()==='保存回单信息')!.attributes('disabled')).toBeUndefined()
  wrapper.unmount()
 })
 it('cancels a pending search when recognition opens so a draft cannot switch receipts', async () => {
  vi.useFakeTimers()
  const wrapper = await open()
  try {
   let finish:any
   mocks.request.mockImplementationOnce(() => new Promise(resolve => finish=resolve))
   await wrapper.find('input[aria-label="搜索付款回单"]').setValue('另一张回单')
   await wrapper.find('[data-testid=recognize-receipt]').trigger('click')
   mocks.request.mockResolvedValueOnce({code:0,data:[{...row,id:2,payee_name:'另一公司'}],count:1})
   await vi.advanceTimersByTimeAsync(350); await flushPromises()
   expect(mocks.request).toHaveBeenCalledTimes(2)
   finish({code:0,data:{fields:{payer_name:'识别付款方'},warnings:[]}}); await flushPromises()
   expect((wrapper.find('input[aria-label="回单收款单位"]').element as HTMLInputElement).value).toBe('收款公司')
  } finally {wrapper.unmount(); vi.useRealTimers()}
 })
 it('blocks saving a draft if the active receipt changes during editing', async () => {
  const wrapper = await open()
  await wrapper.findAll('button').find(b => b.text()==='编辑回单信息')!.trigger('click')
  mocks.request.mockResolvedValueOnce({code:0,data:[{...row,id:2,payee_name:'另一公司'}],count:1})
  wrapper.findComponent({name:'ReceiptPaymentLinks'}).vm.$emit('changed'); await flushPromises()
  await wrapper.findAll('button').find(b => b.text()==='保存回单信息')!.trigger('click'); await flushPromises()
  expect(mocks.request.mock.calls.some((call:any[]) => call[1]?.method === 'PUT')).toBe(false)
  wrapper.unmount()
 })
})
