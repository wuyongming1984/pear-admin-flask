// @vitest-environment jsdom
import {describe,it,expect,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import AttachmentEditor from './AttachmentEditor.vue'
const mocks=vi.hoisted(()=>({request:vi.fn()}))
vi.mock('../api',()=>({request:mocks.request,safeUrl:(v:any)=>v||''}))
vi.mock('element-plus',()=>({ElMessageBox:{confirm:vi.fn().mockResolvedValue('confirm')}}))
const stubs={'el-button':{template:'<button><slot/></button>'},'el-empty':true,'el-tag':{template:'<span><slot/></span>'},'el-image':true}
function setup(kind='payments'){return mount(AttachmentEditor,{props:{modelValue:[{id:9,url:'/old.pdf',name:'原附件.pdf'}],kind},global:{stubs}})}
async function select(w:any){const input=w.find('input');Object.defineProperty(input.element,'files',{value:[new File(['pdf'],'中文票据.pdf',{type:'application/pdf'})],configurable:true});await input.trigger('change');await flushPromises()}
beforeEach(()=>vi.clearAllMocks())
describe('desktop attachments',()=>{
it.each([['orders','order_attachments'],['payments','pay_attachments']])('uploads dropped files for %s without losing existing attachments',async(kind,path)=>{
 const w=setup(kind);await w.setProps({drag:true} as any)
 w.setProps({'onUpdate:modelValue':(value:any[])=>w.setProps({modelValue:value})})
 mocks.request.mockImplementation(async(_url,options)=>({data:{url:`/${options.body.get('file').name}`}}))
 const files=[new File(['a'],'甲.pdf'),new File(['b'],'乙.png')]
 await w.trigger('drop',{dataTransfer:{types:['Files'],files}});await flushPromises()
 expect(mocks.request).toHaveBeenCalledTimes(2)
 expect(mocks.request.mock.calls.map(([,options])=>options.body.get('path'))).toEqual([path,path])
 expect(w.props('modelValue').map((file:any)=>file.name)).toEqual(['原附件.pdf','甲.pdf','乙.png'])
 w.unmount()
})
it('keeps the drop highlight across child elements and clears it on exit',async()=>{
 const w=setup();await w.setProps({drag:true} as any)
 const dataTransfer={types:['Files'],dropEffect:'none'}
 await w.trigger('dragenter',{dataTransfer});await w.find('.toolbar').trigger('dragenter',{dataTransfer})
 await w.find('.toolbar').trigger('dragleave',{dataTransfer})
 expect(w.classes()).toContain('is-dragging')
 await w.trigger('dragover',{dataTransfer});expect(dataTransfer.dropEffect).toBe('copy')
 await w.trigger('dragleave',{dataTransfer});expect(w.classes()).not.toContain('is-dragging')
 await w.trigger('dragenter',{dataTransfer:{types:['text/plain']}});expect(w.classes()).not.toContain('is-dragging')
 w.unmount()
})
it('rejects oversized dropped files but uploads the other files',async()=>{
 const w=setup();await w.setProps({drag:true} as any)
 const large=new File(['x'],'过大.pdf');Object.defineProperty(large,'size',{value:10*1024*1024+1})
 mocks.request.mockResolvedValue({data:{url:'/ok.pdf'}})
 await w.trigger('drop',{dataTransfer:{types:['Files'],files:[large,new File(['ok'],'正常.pdf')]}});await flushPromises()
 expect(mocks.request).toHaveBeenCalledTimes(1);expect(w.text()).toContain('文件不能超过 10 MB')
 expect(w.emitted('busy')!.at(-1)).toEqual([true]);w.unmount()
})
it('prevents drops from navigating or uploading while readonly or busy',async()=>{
 const w=setup();await w.setProps({drag:true,readonly:true} as any)
 const dataTransfer={types:['Files'],files:[new File(['pdf'],'票据.pdf')]}
 const event=new Event('drop',{bubbles:true,cancelable:true});Object.defineProperty(event,'dataTransfer',{value:dataTransfer})
 w.element.dispatchEvent(event);expect(event.defaultPrevented).toBe(true);expect(mocks.request).not.toHaveBeenCalled()
 await w.setProps({readonly:false});let complete:any
 mocks.request.mockImplementation(()=>new Promise(resolve=>complete=resolve))
 await w.trigger('drop',{dataTransfer});await w.trigger('drop',{dataTransfer})
 expect(mocks.request).toHaveBeenCalledTimes(1)
 complete({data:{url:'/ok.pdf'}});await flushPromises();w.unmount()
})
it('does not enable dragging for other attachment editors by default',async()=>{
 const w=setup('projects');await w.trigger('drop',{dataTransfer:{types:['Files'],files:[new File(['x'],'项目.pdf')]}})
 expect(mocks.request).not.toHaveBeenCalled();w.unmount()
})
it.each([['payments','pay_attachments'],['orders','order_attachments'],['projects','project_attachments']])('preserves existing metadata and upload convention for %s',async(kind,path)=>{mocks.request.mockResolvedValue({data:{id:10,url:'/new.pdf',original_filename:'中文票据.pdf'}});const w=setup(kind);await select(w);expect(mocks.request.mock.calls[0][1].body.get('path')).toBe(path);expect(w.emitted('update:modelValue')![0][0]).toEqual([{id:9,url:'/old.pdf',name:'原附件.pdf'},{id:10,url:'/new.pdf',original_filename:'中文票据.pdf',name:'中文票据.pdf'}]);w.unmount()})
it('blocks saving after failure and retries only on explicit click',async()=>{mocks.request.mockRejectedValueOnce(Error('上传失败')).mockResolvedValue({data:{url:'/new.pdf'}});const w=setup();await select(w);expect(mocks.request).toHaveBeenCalledTimes(1);expect(w.emitted('update:modelValue')).toBeUndefined();expect(w.emitted('busy')!.slice(-1)[0]).toEqual([true]);expect(w.text()).toContain('上传失败');await w.findAll('button').find(b=>b.text()==='重试')!.trigger('click');await flushPromises();expect(mocks.request).toHaveBeenCalledTimes(2);expect(w.emitted('busy')!.slice(-1)[0]).toEqual([false]);w.unmount()})
it('ignores a late upload result after editor disposal',async()=>{let complete:any;mocks.request.mockImplementation(()=>new Promise(resolve=>complete=resolve));const w=setup();const pending=select(w);await flushPromises();w.unmount();complete({data:{url:'/late.pdf'}});await pending;await flushPromises();expect(w.emitted('update:modelValue')).toBeUndefined()})
})
