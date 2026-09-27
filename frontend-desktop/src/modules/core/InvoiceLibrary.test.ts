// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {describe, it, expect, vi, beforeEach} from 'vitest'
import {createRouter, createMemoryHistory} from 'vue-router'
import InvoiceLibrary from './InvoiceLibrary.vue'
const mocks=vi.hoisted(()=>({request:vi.fn()}))
vi.mock('../../api',async importOriginal=>({...await importOriginal<any>(),request:mocks.request}))
const stubs={
 'el-button':{props:['disabled','loading'],template:'<button :disabled="disabled || loading"><slot/></button>'},
 'el-checkbox':true,'el-empty':{props:['description'],template:'<p>{{description}}</p>'},
}
const pdf={id:1,invoice_number:'PDF-001',file_type:'pdf',file_name:'发票.pdf',file_path:'https://private.example/invoice.pdf',file_url:'https://private.example/invoice.pdf?Signature=authorized&Expires=123'}
async function open(rows:any[]){
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]})
 await router.push('/');await router.isReady()
 return mount(InvoiceLibrary,{props:{rows,count:rows.length,busy:false,selection:[]},global:{plugins:[router],stubs}})
}
describe('invoice original displayed below the ticket',()=>{
 beforeEach(()=>vi.clearAllMocks())
 it('embeds the authorized PDF below the data without linking the private raw address',async()=>{
  const wrapper=await open([pdf])
  const embed=wrapper.find('object[type="application/pdf"]')
  expect(embed.exists()).toBe(true)
  expect(embed.attributes('data')).toBe(pdf.file_url)
  expect(wrapper.find('.invoice-paper').element.compareDocumentPosition(embed.element)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(wrapper.find(`a[href="${pdf.file_path}"]`).exists()).toBe(false)
  wrapper.unmount()
 })
 it('switches from PDF to an inline image and clears the old original when a row has no file',async()=>{
  const wrapper=await open([pdf])
  await wrapper.setProps({rows:[{id:2,invoice_number:'IMG-002',file_type:'image/jpeg',file_name:'测试.jpg',file_path:'/uploads/test.jpg'}]})
  expect(wrapper.find('object').exists()).toBe(false)
  expect(wrapper.find('.invoice-source img').attributes('src')).toContain('/uploads/test.jpg')
  await wrapper.setProps({rows:[{id:3,invoice_number:'NO-FILE'}]})
  expect(wrapper.find('.invoice-source img').exists()).toBe(false)
  expect(wrapper.text()).toContain('此发票尚未上传原文件')
  wrapper.unmount()
 })
 it('refreshes the signed URL and ignores a refresh that returns after switching invoices',async()=>{
  const wrapper=await open([pdf])
  mocks.request.mockResolvedValueOnce({code:0,data:[{...pdf,file_url:'https://private.example/invoice.pdf?Signature=renewed'}]})
  await wrapper.findAll('button').find(b=>b.text()==='刷新预览')!.trigger('click');await flushPromises()
  expect(wrapper.find('object').attributes('data')).toContain('Signature=renewed')
  let resolve:any
  mocks.request.mockImplementationOnce(()=>new Promise(r=>resolve=r))
  await wrapper.findAll('button').find(b=>b.text()==='刷新预览')!.trigger('click')
  await wrapper.setProps({rows:[{id:2,invoice_number:'NEXT',file_type:'png',file_path:'/uploads/next.png'}]})
  resolve({code:0,data:[pdf]});await flushPromises()
  expect(wrapper.find('object').exists()).toBe(false)
  expect(wrapper.find('.invoice-source img').attributes('src')).toContain('/uploads/next.png')
  wrapper.unmount()
 })
 it('does not embed unsafe URLs or unsupported file types as active documents',async()=>{
  const wrapper=await open([{id:1,file_url:'javascript:alert(1)',file_type:'pdf'}])
  expect(wrapper.find('object').exists()).toBe(false)
  await wrapper.setProps({rows:[{id:2,file_type:'html',file_path:'/uploads/file.html'}]})
  expect(wrapper.find('object').exists()).toBe(false)
  expect(wrapper.find('.invoice-source').text()).toContain('暂不支持直接预览')
  wrapper.unmount()
 })
})
