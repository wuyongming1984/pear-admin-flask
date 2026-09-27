// @vitest-environment jsdom
import {describe,it,expect,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import AttachmentEditor from './AttachmentEditor.vue'
const mocks=vi.hoisted(()=>({request:vi.fn()}))
vi.mock('../api',()=>({request:mocks.request,safeUrl:(v:any)=>v||''}))
vi.mock('../feedback',()=>({ElMessageBox:{confirm:vi.fn().mockResolvedValue('confirm')}}))
const stubs={'m-button':{template:'<button><slot/></button>'},'m-empty':true,'m-tag':{template:'<span><slot/></span>'},'m-image':true}
function setup(kind='payments'){return mount(AttachmentEditor,{props:{modelValue:[{id:9,url:'/old.pdf',name:'原附件.pdf'}],kind},global:{stubs}})}
async function select(w:any){const input=w.find('input');Object.defineProperty(input.element,'files',{value:[new File(['pdf'],'中文票据.pdf',{type:'application/pdf'})],configurable:true});await input.trigger('change');await flushPromises()}
beforeEach(()=>vi.clearAllMocks())
describe('desktop attachments',()=>{
it.each([['payments','pay_attachments'],['orders','order_attachments'],['projects','project_attachments']])('preserves existing metadata and upload convention for %s',async(kind,path)=>{mocks.request.mockResolvedValue({data:{id:10,url:'/new.pdf',original_filename:'中文票据.pdf'}});const w=setup(kind);await select(w);expect(mocks.request.mock.calls[0][1].body.get('path')).toBe(path);expect(w.emitted('update:modelValue')![0][0]).toEqual([{id:9,url:'/old.pdf',name:'原附件.pdf'},{id:10,url:'/new.pdf',original_filename:'中文票据.pdf',name:'中文票据.pdf'}]);w.unmount()})
it('blocks saving after failure and retries only on explicit click',async()=>{mocks.request.mockRejectedValueOnce(Error('上传失败')).mockResolvedValue({data:{url:'/new.pdf'}});const w=setup();await select(w);expect(mocks.request).toHaveBeenCalledTimes(1);expect(w.emitted('update:modelValue')).toBeUndefined();expect(w.emitted('busy')!.slice(-1)[0]).toEqual([true]);expect(w.text()).toContain('上传失败');await w.findAll('button').find(b=>b.text()==='重试')!.trigger('click');await flushPromises();expect(mocks.request).toHaveBeenCalledTimes(2);expect(w.emitted('busy')!.slice(-1)[0]).toEqual([false]);w.unmount()})
it('ignores a late upload result after editor disposal',async()=>{let complete:any;mocks.request.mockImplementation(()=>new Promise(resolve=>complete=resolve));const w=setup();const pending=select(w);await flushPromises();w.unmount();complete({data:{url:'/late.pdf'}});await pending;await flushPromises();expect(w.emitted('update:modelValue')).toBeUndefined()})
})
