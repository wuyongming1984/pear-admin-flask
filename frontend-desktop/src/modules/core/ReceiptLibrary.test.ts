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
})
