// @vitest-environment jsdom
import {describe,it,expect,vi,beforeEach,afterEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {createRouter,createMemoryHistory} from 'vue-router'
import CorePage from './CorePage.vue'
import OrderEntrySheet from './OrderEntrySheet.vue'
import SupplierContactSelect from './SupplierContactSelect.vue'
const mocks=vi.hoisted(()=>({request:vi.fn(),allRows:vi.fn(),confirm:vi.fn()}))
vi.mock('../../session',()=>({session:{nickname:'当前用户昵称',userName:'login-account'}}))
vi.mock('../../api',()=>({request:mocks.request,allRows:mocks.allRows,query:(p:any)=>new URLSearchParams(p).toString(),safeUrl:(p:any)=>p||''}))
vi.mock('element-plus',()=>({ElMessage:{error:vi.fn(),success:vi.fn(),warning:vi.fn()},ElMessageBox:{confirm:mocks.confirm}}))
vi.mock('../../components/AttachmentEditor.vue',()=>({default:{props:['modelValue'],template:'<div />'}}))
const input={props:['modelValue'],emits:['update:modelValue'],template:'<input :value="modelValue" @input="$emit(\'update:modelValue\',$event.target.value)" />'}
const stubs:any={'el-form':{template:'<form><slot/></form>'},'el-form-item':{props:['label'],template:'<label>{{label}}<slot/></label>'},'el-input':input,'el-select':input,'el-option':true,'el-date-picker':input,'el-button':{props:['nativeType','disabled','loading'],template:'<button :type="nativeType||\'button\'" :disabled="disabled||loading"><slot/></button>'},'el-alert':{props:['title'],template:'<div role="alert">{{title}}</div>'},'el-dialog':true,'el-table':true,'el-table-column':true,'el-pagination':true,'el-descriptions':true,'el-descriptions-item':true,'el-popover':true,'el-checkbox-group':true,'el-checkbox':true,'el-empty':{props:['description'],template:'<p>{{description}}</p>'}}
describe('invoice live search',()=>{
 let wrapper:any
 const invoiceCalls=()=>mocks.request.mock.calls.filter(([url])=>url.startsWith('/material/invoice?'))
 const result=(number:string)=>({code:0,count:1,data:[{id:number,invoice_number:number,buyer_name:'测试购买方',seller_name:'测试销售方',total_amount:'10.00',tax_amount:'1.30',details:[]}]})
 async function open(){
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/invoices',component:CorePage,meta:{coreKind:'invoices',coreMode:'list'}},{path:'/other',component:{template:'<p>其他页面</p>'}}]})
  await router.push('/invoices');await router.isReady()
  wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  return router
 }
 beforeEach(()=>{vi.useFakeTimers();vi.clearAllMocks();mocks.allRows.mockResolvedValue([]);mocks.request.mockImplementation(async(url:string)=>url.startsWith('/material/invoice?')?result('INITIAL'):{code:0,data:{fpdl:[],kfdk:[]}})})
 afterEach(()=>{wrapper?.unmount();vi.useRealTimers()})
 it('debounces typing and shows matching rows without reloading options or downloading all invoices',async()=>{
  await open();const optionsCalls=mocks.allRows.mock.calls.length
  mocks.request.mockImplementation(async(url:string)=>url.startsWith('/material/invoice?')?result('MATCH-001'):{code:0,data:{}})
  await wrapper.get('[aria-label="发票号码"]').setValue('0')
  await vi.advanceTimersByTimeAsync(100)
  await wrapper.get('[aria-label="发票号码"]').setValue('001')
  expect(invoiceCalls()).toHaveLength(1)
  await vi.advanceTimersByTimeAsync(220);await flushPromises()
  expect(invoiceCalls()).toHaveLength(2)
  expect(wrapper.get('.invoice-cards').text()).toContain('MATCH-001')
  expect(wrapper.get('.invoice-cards').text()).not.toContain('INITIAL')
  expect(mocks.allRows.mock.calls).toHaveLength(optionsCalls)
  await wrapper.get('[aria-label="发票大类"]').setValue('material')
  await vi.advanceTimersByTimeAsync(220);await flushPromises()
  expect(invoiceCalls().at(-1)![0]).toContain('invoice_category=material')
  expect(mocks.allRows.mock.calls.some(([url])=>url==='/material/invoice')).toBe(false)
 })
 it('cancels the old query and never lets its late response replace the latest matches',async()=>{
  await open();let oldResolve:any,oldSignal:AbortSignal|undefined
  mocks.request.mockImplementation((url:string,options:any)=>{
   if(url.includes('invoice_number=old')){oldSignal=options?.signal;return new Promise(resolve=>oldResolve=resolve)}
   return Promise.resolve(result('LATEST'))
  })
  await wrapper.get('[aria-label="发票号码"]').setValue('old')
  await vi.advanceTimersByTimeAsync(220)
  expect(oldResolve).toBeTypeOf('function')
  await wrapper.get('[aria-label="发票号码"]').setValue('new')
  expect(oldSignal?.aborted).toBe(true)
  await vi.advanceTimersByTimeAsync(220);await flushPromises()
  expect(wrapper.get('.invoice-cards').text()).toContain('LATEST')
  oldResolve(result('OBSOLETE'));await flushPromises()
  expect(wrapper.get('.invoice-cards').text()).not.toContain('OBSOLETE')
 })
 it('resets immediately, avoids a second delayed query, and stops pending searches on leave',async()=>{
  const router=await open()
  await wrapper.get('[aria-label="购买方"]').setValue('待查')
  await wrapper.findAll('button').find((button:any)=>button.text()==='重置')!.trigger('click');await flushPromises()
  const calls=invoiceCalls().length
  await vi.advanceTimersByTimeAsync(500);await flushPromises()
  expect(invoiceCalls()).toHaveLength(calls)
  expect(invoiceCalls().at(-1)![0]).not.toContain('buyer_name')
  await wrapper.get('[aria-label="销售方"]').setValue('离开前输入')
  await router.push('/other');await flushPromises()
  await vi.advanceTimersByTimeAsync(500)
  expect(invoiceCalls()).toHaveLength(calls)
 })
})
async function setup(){const router=createRouter({history:createMemoryHistory(),routes:[{path:'/projects/new',component:CorePage,meta:{coreKind:'projects',coreMode:'new'}},{path:'/projects',component:{template:'<div>项目列表</div>'}},{path:'/system',component:{template:'<div>系统页面</div>'}}]});await router.push('/projects/new');await router.isReady();const wrapper=mount({template:'<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.path"/></keep-alive></router-view>'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises();return{wrapper,router}}
describe('core form operation behavior',()=>{
 beforeEach(()=>{vi.clearAllMocks();mocks.request.mockResolvedValue({code:0,data:{}});mocks.allRows.mockResolvedValue([]);mocks.confirm.mockResolvedValue('confirm')})
 it.each(['projects','suppliers','payers'])('restores the %s layout and keeps search and edit navigation working',async(kind)=>{
  const row={id:7,project_name:'景观工程',name:'往来单位',contact_person:'联系人',project_amount:'1234.50'}
  mocks.request.mockImplementation(async(path:string)=>({code:0,data:path.includes('/dictionary/')?{}:[row],count:1}))
  const router=createRouter({history:createMemoryHistory(),routes:[{path:`/${kind}`,component:CorePage,meta:{coreKind:kind,coreMode:'list'}},{path:`/${kind}/:id/edit`,component:{template:'<div>编辑记录</div>'}}]})
  await router.push('/'+kind);await router.isReady()
  const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.find(`[data-management="${kind}"]`).exists()).toBe(true)
  expect(wrapper.find('.search-grid').exists()).toBe(false)
  const key=kind==='projects'?'project_name':'name'
  await wrapper.get(`[aria-label="${kind==='projects'?'搜索项目名称':kind==='suppliers'?'搜索供应商名称':'筛选付款单位名称'}"]`).setValue('景观')
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([path])=>path.includes(`${key}=%E6%99%AF%E8%A7%82`))).toBe(true)
  if(kind!=='payers'){
   expect(wrapper.find(kind==='projects'?'.project-card':'.supplier-card').exists()).toBe(true)
   await wrapper.findAll('button').find(button=>button.text()==='编辑')!.trigger('click');await flushPromises()
   expect(router.currentRoute.value.path).toBe(`/${kind}/7/edit`)
  }
  wrapper.unmount()
 })
 it('submits a decimal string once while pending then leaves only after success',async()=>{const {wrapper,router}=await setup();await wrapper.find('label input').setValue('新项目');const amount=wrapper.findAll('label').find(x=>x.text().includes('合同金额'))!;await amount.find('input').setValue('123.45');let resolve:any;mocks.request.mockImplementation(()=>new Promise(r=>resolve=r));await wrapper.find('form').trigger('submit');await wrapper.find('form').trigger('submit');expect(mocks.request).toHaveBeenCalledTimes(2); // initial dictionary read + exactly one POST
 const call=mocks.request.mock.calls[1]!;expect(call[0]).toBe('/project/');expect(JSON.parse(call[1].body).project_amount).toBe('123.45');expect(router.currentRoute.value.path).toBe('/projects/new');resolve({code:0,data:{id:7}});await flushPromises();expect(router.currentRoute.value.path).toBe('/projects');await router.push('/projects/new');await flushPromises();expect(wrapper.find('label input').element).toHaveProperty('value','');expect(wrapper.findAll('label').find(x=>x.text().includes('合同金额'))!.find('input').element).toHaveProperty('value','');wrapper.unmount()})
 it('keeps the draft visible and editable after a server failure',async()=>{const {wrapper,router}=await setup();await wrapper.find('label input').setValue('保留草稿');mocks.request.mockRejectedValueOnce(new Error('网络失败'));await wrapper.find('form').trigger('submit');await flushPromises();expect(wrapper.find('label input').element).toHaveProperty('value','保留草稿');expect(wrapper.text()).toContain('网络失败');expect(router.currentRoute.value.path).toBe('/projects/new');expect(wrapper.findAll('button').find(x=>x.text()==='保存')!.attributes('disabled')).toBeUndefined();wrapper.unmount()})
 it('does not reset cached drafts or request a different module after navigation',async()=>{const {wrapper,router}=await setup();await wrapper.find('label input').setValue('缓存草稿');const calls=mocks.request.mock.calls.length;await router.push('/system');await flushPromises();expect(wrapper.text()).toContain('系统页面');expect(mocks.request).toHaveBeenCalledTimes(calls);await router.push('/projects/new');await flushPromises();expect(wrapper.find('label input').element).toHaveProperty('value','缓存草稿');expect(mocks.request).toHaveBeenCalledTimes(calls);wrapper.unmount()})
 it('shows a no-file empty state and Chinese OCR state for manually entered invoices',async()=>{mocks.request.mockImplementation(async(path:string)=>({code:0,data:path.startsWith('/material/invoice?')?[{id:1,invoice_number:'MANUAL1',ocr_status:'pending',file_path:null,file_url:null}]:{}}));const router=createRouter({history:createMemoryHistory(),routes:[{path:'/invoices/:id',component:CorePage,meta:{coreKind:'invoices',coreMode:'detail'}}]});await router.push('/invoices/1');await router.isReady();const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises();expect(wrapper.text()).toContain('此发票尚未上传原文件');expect(wrapper.text()).toContain('待识别');expect(wrapper.find('a[href=""]').exists()).toBe(false);expect(wrapper.find('object').exists()).toBe(false);wrapper.unmount()})
 it('creates an order on the paper form with project prefill, supplier autofill and decimal submission',async()=>{
  mocks.allRows.mockImplementation(async(path:string)=>path==='/project/'?[{id:7,project_name:'项目甲'},{id:8,project_name:'项目乙'}]:path==='/supplier/'?[{id:3,name:'供应商甲',contact_person:'张工',phone:'13800000000'}]:path==='/dictionary/detail/list'?[{code:'stone',value:'石材'}]:[])
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/orders/new',component:CorePage,meta:{coreKind:'orders',coreMode:'new'}},{path:'/orders',component:{template:'<div>订单列表</div>'}}]})
  await router.push('/orders/new?project_id=7');await router.isReady()
  const wrapper=mount({template:'<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.fullPath"/></keep-alive></router-view>'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.find('.order-entry-sheet').exists()).toBe(true)
  expect(wrapper.get('[aria-label="项目"]').element).toHaveProperty('value','7')
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false)
  expect(wrapper.get('[aria-label="材料负责人"]').element).toHaveProperty('value','当前用户昵称')
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select',3);await flushPromises()
  expect(wrapper.get('[aria-label="供应商联系人"]').element).toHaveProperty('value','3')
  expect(wrapper.get('[aria-label="联系电话"]').element).toHaveProperty('value','13800000000')
  for(const [label,value] of Object.entries({'材料名称':'stone','订单金额':'1234.50','材料明细':'采购石材','下料日期':'2026-09-28','预计到场日期':'2026-09-30','材料负责人':'李工','分项目负责人':'王工'})) await wrapper.get(`[aria-label="${label}"]`).setValue(value)
  expect(wrapper.get('.order-entry-balance').text()).toContain('1234.50')
  expect(wrapper.get('.order-entry-capital').text()).toContain('壹仟贰佰叁拾肆元伍角')
  await router.push('/orders/new?project_id=8');await flushPromises()
  expect(wrapper.get('[aria-label="项目"]').element).toHaveProperty('value','8')
  await router.push('/orders/new?project_id=7');await flushPromises()
  expect(wrapper.get('[aria-label="订单金额"]').element).toHaveProperty('value','1234.50')
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select',undefined);await flushPromises()
  expect(wrapper.get('[aria-label="联系电话"]').element).toHaveProperty('value','')
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false)
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select',3);await flushPromises()
  wrapper.getComponent(OrderEntrySheet).vm.$emit('field','supplier_contact_person','自由输入的联系人');await flushPromises()
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false)
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select',3);await flushPromises()
  await wrapper.get('form').trigger('submit');await flushPromises()
  const post=mocks.request.mock.calls.find(([,options])=>options?.method==='POST')!
  expect(post[0]).toBe('/order/')
  expect(JSON.parse(post[1].body)).toMatchObject({project_id:7,supplier_id:3,material_name:'stone',order_amount:'1234.50',supplier_contact_person:'张工',contact_phone:'13800000000',material_details:'采购石材',cutting_time:'2026-09-28',estimated_arrival_time:'2026-09-30',material_manager:'李工',sub_project_manager:'王工',attachments:'[]'})
  expect(router.currentRoute.value.path).toBe('/orders');wrapper.unmount()
 })
 it('opens the new payment as a paper form, prefills the linked order and preserves decimal submission',async()=>{
  mocks.allRows.mockImplementation(async(path:string)=>path==='/order/'?[{id:2,order_number:'D002',project_name:'项目甲',supplier_id:3,material_name:'材料',material_details:'合同材料款',order_amount:'100.00',paid_amount:'20.00'},{id:5,order_number:'D005',project_name:'项目乙',supplier_id:3,material_details:'第二个订单',order_amount:'200.00',paid_amount:'0.00'}]:path==='/supplier/'?[{id:3,name:'收款单位',bank_name:'测试银行',account_number:'123456'}]:path==='/payer/'?[{id:4,name:'付款单位'}]:[])
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/payments/new',component:CorePage,meta:{coreKind:'payments',coreMode:'new'}},{path:'/payments',component:{template:'<div>付款列表</div>'}}]})
  await router.push('/payments/new?order_id=2');await router.isReady()
  const wrapper=mount({template:'<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.fullPath"/></keep-alive></router-view>'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.find('.payment-entry-sheet').exists()).toBe(true)
  expect(wrapper.text()).toContain('付款审批单');expect(wrapper.text()).toContain('测试银行')
  expect(wrapper.get('[aria-label="付款用途"]').element).toHaveProperty('value','合同材料款')
  await wrapper.get('[aria-label="本次实付金额"]').setValue('30.10')
  expect(wrapper.get('[data-testid="payment-total-preview"]').text()).toContain('50.10')
  expect(wrapper.get('[data-testid="payment-balance-preview"]').text()).toContain('49.90')
  await router.push('/payments/new?order_id=5');await flushPromises()
  expect(wrapper.get('[aria-label="付款用途"]').element).toHaveProperty('value','第二个订单')
  await router.push('/payments/new?order_id=2');await flushPromises()
  expect(wrapper.get('[aria-label="本次实付金额"]').element).toHaveProperty('value','30.10')
  await wrapper.get('[aria-label="付款单位"]').setValue('4')
  await wrapper.find('form').trigger('submit');await flushPromises()
  const post=mocks.request.mock.calls.find(([,options])=>options?.method==='POST')!
  expect(post[0]).toBe('/pay/')
  expect(JSON.parse(post[1].body)).toMatchObject({order_id:2,payee_supplier_id:3,current_payment_amount:'30.10',payment_purpose:'合同材料款',invoice_ids:[],attachments:'[]'})
  expect(router.currentRoute.value.path).toBe('/payments');wrapper.unmount()
 })
})


