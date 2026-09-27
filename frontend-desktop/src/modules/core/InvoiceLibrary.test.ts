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
const preview={code:0,data:{image:'data:image/png;base64,cGFnZTE=',page:1,page_count:2}}
async function open(rows:any[]){
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]})
 await router.push('/');await router.isReady()
 return mount(InvoiceLibrary,{props:{rows,count:rows.length,busy:false,selection:[]},global:{plugins:[router],stubs}})
}
describe('invoice original displayed below the ticket',()=>{
 beforeEach(()=>{vi.resetAllMocks();mocks.request.mockResolvedValue(preview)})
 it('renders PDF pixels below the data without a browser PDF object or automatic download',async()=>{
  const wrapper=await open([pdf])
  await flushPromises()
  const embed=wrapper.find('img.pdf-page')
  expect(embed.exists()).toBe(true)
  expect(embed.attributes('src')).toBe(preview.data.image)
  expect(wrapper.find('object,iframe,embed').exists()).toBe(false)
  expect(mocks.request).toHaveBeenCalledWith('/material/invoice/1/preview-page?page=1',expect.anything())
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
  expect(wrapper.find('.source-actions a').attributes('href')).toContain('Signature=renewed')
  let resolve:any
  mocks.request.mockImplementationOnce(()=>new Promise(r=>resolve=r))
  await wrapper.findAll('button').find(b=>b.text()==='刷新预览')!.trigger('click')
  await wrapper.setProps({rows:[{id:2,invoice_number:'NEXT',file_type:'png',file_path:'/uploads/next.png'}]})
  resolve({code:0,data:[pdf]});await flushPromises()
  expect(wrapper.find('object').exists()).toBe(false)
  expect(wrapper.find('.invoice-source img').attributes('src')).toContain('/uploads/next.png')
  wrapper.unmount()
 })
 it('loads subsequent PDF pages only on demand and reuses already loaded pages',async()=>{
  const wrapper=await open([pdf]);await flushPromises()
  expect(mocks.request).toHaveBeenCalledTimes(1)
  mocks.request.mockResolvedValueOnce({code:0,data:{image:'data:image/png;base64,cGFnZTI=',page:2,page_count:2}})
  await wrapper.findAll('button').find(b=>b.text()==='下一页原文件')!.trigger('click');await flushPromises()
  expect(wrapper.find('img.pdf-page').attributes('src')).toContain('cGFnZTI=')
  expect(wrapper.text()).toContain('第 2 / 2 页')
  await wrapper.findAll('button').find(b=>b.text()==='上一页原文件')!.trigger('click');await flushPromises()
  expect(mocks.request).toHaveBeenCalledTimes(2)
  expect(wrapper.find('img.pdf-page').attributes('src')).toBe(preview.data.image)
  wrapper.unmount()
 })
 it('shows a retryable error instead of opening a download and ignores late PDF responses',async()=>{
  mocks.request.mockRejectedValueOnce(new Error('原文件读取失败'))
  const wrapper=await open([pdf]);await flushPromises()
  expect(wrapper.find('[role="alert"]').text()).toContain('原文件读取失败')
  let resolve:any
  mocks.request.mockImplementationOnce(()=>new Promise(r=>resolve=r))
  await wrapper.findAll('button').find(b=>b.text()==='重试加载')!.trigger('click')
  await wrapper.setProps({rows:[{id:2,file_type:'png',file_path:'/uploads/next.png'}]})
  resolve(preview);await flushPromises()
  expect(wrapper.find('.pdf-page').exists()).toBe(false)
  expect(wrapper.find('.source-image').attributes('src')).toContain('/uploads/next.png')
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
