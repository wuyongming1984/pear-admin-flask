// @vitest-environment jsdom
import {describe,it,expect,vi,beforeEach,afterEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {createRouter,createMemoryHistory} from 'vue-router'
import CorePage from './CorePage.vue'
import PaymentEntrySheet from './PaymentEntrySheet.vue'
import OrderEntrySheet from './OrderEntrySheet.vue'
import SupplierContactSelect from './SupplierContactSelect.vue'
import AttachmentEditor from '../../components/AttachmentEditor.vue'
const mocks=vi.hoisted(()=>({request:vi.fn(),allRows:vi.fn(),confirm:vi.fn()}))
vi.mock('../../session',()=>({session:{nickname:'当前用户昵称',userName:'login-account'}}))
vi.mock('../../api',()=>({request:mocks.request,allRows:mocks.allRows,query:(p:any)=>new URLSearchParams(p).toString(),safeUrl:(p:any)=>p||''}))
vi.mock('element-plus',()=>({ElMessage:{error:vi.fn(),success:vi.fn(),warning:vi.fn()},ElMessageBox:{confirm:mocks.confirm}}))
vi.mock('../../components/AttachmentEditor.vue',()=>({default:{props:['modelValue','drag'],template:'<div />'}}))
const input={props:['modelValue'],emits:['update:modelValue'],template:'<input :value="modelValue" @input="$emit(\'update:modelValue\',$event.target.value)" />'}
const stubs:any={'el-form':{template:'<form><slot/></form>'},'el-form-item':{props:['label'],template:'<label>{{label}}<slot/></label>'},'el-input':input,'el-select':input,'el-select-v2':input,'el-option':true,'el-date-picker':input,'el-button':{props:['nativeType','disabled','loading'],template:'<button :type="nativeType||\'button\'" :disabled="disabled||loading"><slot/></button>'},'el-alert':{props:['title'],template:'<div role="alert">{{title}}</div>'},'el-dialog':{props:['modelValue','title'],template:'<section v-if="modelValue" role="dialog" :aria-label="title"><slot/><slot name="footer"/></section>'},'el-table':true,'el-table-column':true,'el-pagination':true,'el-descriptions':true,'el-descriptions-item':true,'el-popover':true,'el-checkbox-group':true,'el-checkbox':true,'el-empty':{props:['description'],template:'<p>{{description}}</p>'}}
describe('invoice live search',()=>{
 let wrapper:any
 const invoiceCalls=()=>mocks.request.mock.calls.filter(([url])=>url.startsWith('/material/invoice?'))
 const result=(number:string)=>({code:0,count:1,data:[{id:number,invoice_number:number,buyer_name:'测试购买方',seller_name:'测试销售方',total_amount:'10.00',tax_amount:'1.30',details:[]}]})
 async function open(){
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/invoices',component:CorePage,meta:{coreKind:'invoices',coreMode:'list'}},{path:'/other',component:{template:'<p>其他页面</p>'}},{path:'/payments/:id',component:{template:'<p>付款详情</p>'}}]})
  await router.push('/invoices');await router.isReady()
  wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs:{...stubs,'el-dialog':{props:['modelValue','title'],template:'<section v-if="modelValue" role="dialog" :aria-label="title"><slot/><slot name="footer"/></section>'}},directives:{loading:()=>{}}}});await flushPromises()
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
 it('clears the search through the input and stops pending searches on leave',async()=>{
  const router=await open()
  await wrapper.get('[aria-label="购买方"]').setValue('待查')
  await wrapper.get('[aria-label="购买方"]').setValue('')
  await vi.advanceTimersByTimeAsync(220);await flushPromises()
  const calls=invoiceCalls().length
  await vi.advanceTimersByTimeAsync(500);await flushPromises()
  expect(invoiceCalls()).toHaveLength(calls)
  expect(new URLSearchParams(invoiceCalls().at(-1)![0].split('?')[1]).get('buyer_name')).toBe('')
  await wrapper.get('[aria-label="销售方"]').setValue('离开前输入')
  await router.push('/other');await flushPromises()
  await vi.advanceTimersByTimeAsync(500)
  expect(invoiceCalls()).toHaveLength(calls)
 })
 it('opens a modal, accepts dropped invoices and submits the chosen project once with readable partial results',async()=>{
  await open()
  expect(wrapper.find('input[type="file"]').exists()).toBe(false)
  expect(wrapper.find('.invoice-search').findAll('button').map((b:any)=>b.text())).toEqual(['新增发票 / 上传识别'])
  await wrapper.get('.invoice-add').trigger('click')
  const dialog=wrapper.get('[role="dialog"]')
  const pdf=new File(['pdf'],'新发票.pdf',{type:'application/pdf'})
  const jpg=new File(['image'],'重复发票.jpg',{type:'image/jpeg'})
  await dialog.get('[data-testid="invoice-dropzone"]').trigger('drop',{dataTransfer:{files:[pdf,jpg,new File(['bad'],'程序.exe')]}})
  expect(dialog.text()).toContain('新发票.pdf');expect(dialog.text()).toContain('不支持')
  await dialog.get('[aria-label="所属项目"]').setValue('7')
  let complete:any
  const payment={id:9,pay_number:'FK-009',payee_supplier_name:'销售单位',current_payment_amount:'100'}
  let associationSaved=false
  mocks.request.mockImplementation((url:string, options:any)=>{
   if(url==='/material/invoice/upload')return new Promise(resolve=>complete=resolve)
   if(url.startsWith('/invoice-links/invoices/')){
    if(options?.method==='POST')associationSaved=true
    return Promise.resolve({code:0,data:{seller_name:'销售单位',matched:[payment],linked:associationSaved?[payment]:[]}})
   }
   return Promise.resolve(result('UPLOADED'))
  })
  await dialog.get('[data-testid="invoice-upload-submit"]').trigger('click')
  await dialog.get('[data-testid="invoice-upload-submit"]').trigger('click')
  const calls=mocks.request.mock.calls.filter(([url])=>url==='/material/invoice/upload')
  expect(calls).toHaveLength(1)
  const form=calls[0]![1].body as FormData
  expect(form.getAll('files').map(f=>(f as File).name)).toEqual(['新发票.pdf','重复发票.jpg'])
  expect(form.get('project_id')).toBe('7');expect(form.get('path')).toBe('invoices')
  expect(dialog.get('[data-testid="invoice-upload-close"]').attributes('disabled')).toBeDefined()
  complete({code:0,data:{uploaded:1,failed:1,invoices:[{id:231,file_name:'新发票.pdf',ocr_status:'success',invoice_number:'NEW'}],errors:[{name:'重复发票.jpg',reason:'发票号 OLD 已存在 (ID: 230)'}]}})
  await flushPromises()
  expect(dialog.text()).toContain('成功 1 张');expect(dialog.text()).toContain('未导入 1 张')
  expect(dialog.text()).toContain('已存在 (ID: 230)');expect(dialog.find('pre').exists()).toBe(false)
  expect(wrapper.get('.invoice-cards').text()).toContain('UPLOADED')
  expect(dialog.get('[data-testid="invoice-upload-submit"]').attributes('disabled')).toBeDefined()
  await dialog.get('[aria-label="关联付款单 FK-009"]').setValue(true)
  await dialog.get('[data-testid="save-payment-links"]').trigger('click');await flushPromises()
  expect(dialog.get('[aria-label="已关联付款单"]').text()).toContain('FK-009')
  expect(wrapper.get('.invoice-preview [aria-label="已关联付款单"]').text()).toContain('FK-009')
  const linked=mocks.request.mock.calls.find(([url,o])=>url==='/invoice-links/invoices/231/payments'&&o?.method==='POST')!
  expect(JSON.parse(linked[1].body)).toEqual({payment_ids:[9]})
  await dialog.get('[data-testid="invoice-upload-close"]').trigger('click')
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
 })
 it('accepts file selection, removes queued files and preserves files with an error when upload fails',async()=>{
  await open();await wrapper.get('.invoice-add').trigger('click')
  const dialog=wrapper.get('[role="dialog"]'),input=dialog.get('input[type="file"]')
  const file=new File(['image'],'发票.png',{type:'image/png'})
  Object.defineProperty(input.element,'files',{value:[file],configurable:true})
  await input.trigger('change')
  await dialog.get('[aria-label="移除 发票.png"]').trigger('click')
  expect(dialog.get('[data-testid="invoice-upload-submit"]').attributes('disabled')).toBeDefined()
  await input.trigger('change')
  mocks.request.mockRejectedValueOnce(new Error('连接中断，请先核对列表'))
  await dialog.get('[data-testid="invoice-upload-submit"]').trigger('click');await flushPromises()
  expect(dialog.get('[role="alert"]').text()).toContain('连接中断')
  expect(dialog.text()).toContain('发票.png')
  expect(dialog.get('[data-testid="invoice-upload-close"]').attributes('disabled')).toBeUndefined()
 })
})
async function setup(){const router=createRouter({history:createMemoryHistory(),routes:[{path:'/projects/new',component:CorePage,meta:{coreKind:'projects',coreMode:'new'}},{path:'/projects',component:{template:'<div>项目列表</div>'}},{path:'/system',component:{template:'<div>系统页面</div>'}}]});await router.push('/projects/new');await router.isReady();const wrapper=mount({template:'<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.path"/></keep-alive></router-view>'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises();return{wrapper,router}}
describe('core form operation behavior',()=>{
 beforeEach(()=>{vi.clearAllMocks();mocks.request.mockResolvedValue({code:0,data:{}});mocks.allRows.mockResolvedValue([]);mocks.confirm.mockResolvedValue('confirm')})
 it.each(['orders','payments'])('starts %s detail without waiting for slow options',async(kind)=>{
  let resolveOptions!: (rows:any[])=>void
  mocks.allRows.mockReturnValue(new Promise(resolve=>resolveOptions=resolve))
  const path=`/${kind}/2/edit`,api=kind==='orders'?'/order/2':'/pay/2'
  mocks.request.mockResolvedValue({code:0,data:{id:2,invoices_list:[]}})
  const router=createRouter({history:createMemoryHistory(),routes:[{path:`/${kind}/:id/edit`,component:CorePage,meta:{coreKind:kind,coreMode:'edit'}}]})
  await router.push(path);await router.isReady()
  const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}})
  await flushPromises()
  try { expect(mocks.request).toHaveBeenCalledWith(api) }
  finally {resolveOptions([]);await flushPromises();wrapper.unmount()}
 })
 it('opens payment editing without loading the invoice library, preserves existing links and retries invoice errors',async()=>{
  const invoice={id:8,invoice_number:'LINKED-008',seller_name:'销售公司',total_amount:'10',tax_amount:'1.3'}
  mocks.request.mockResolvedValue({code:0,data:{id:2,pay_number:'FK2',order_id:3,payer_supplier_id:4,payee_supplier_id:5,current_payment_amount:'10',invoices_list:[invoice]}})
  mocks.allRows.mockImplementation(async(path:string)=>path==='/order/'?[{id:3,supplier_id:5,supplier_contact_person:'张工'}]:path==='/supplier/'?[{id:5,name:'销售公司',contact_person:'张工'}]:[])
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/payments/:id/edit',component:CorePage,meta:{coreKind:'payments',coreMode:'edit'}},{path:'/payments',component:{template:'<p>列表</p>'}}]})
  await router.push('/payments/2/edit');await router.isReady()
  const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(mocks.allRows.mock.calls.some(([url])=>url==='/material/invoice')).toBe(false)
  expect(wrapper.get('.payment-invoice-picker').text()).toContain('LINKED-008')
  expect(wrapper.get('.payment-invoice-picker').text()).toContain('11.30')
  mocks.allRows.mockRejectedValueOnce(new Error('发票加载失败'))
  await wrapper.get('[data-testid="choose-invoices"]').trigger('click');await flushPromises()
  expect(wrapper.get('[role="dialog"]').text()).toContain('发票加载失败')
  expect(wrapper.get('[data-testid="confirm-invoice-selection"]').attributes('disabled')).toBeDefined()
  mocks.allRows.mockResolvedValueOnce([invoice])
  await wrapper.get('[data-testid="retry-invoice-options"]').trigger('click');await flushPromises()
  expect(wrapper.get('[data-testid="confirm-invoice-selection"]').attributes('disabled')).toBeUndefined()
  await wrapper.get('[data-testid="cancel-invoice-selection"]').trigger('click')
  await wrapper.get('form').trigger('submit');await flushPromises()
  const put=mocks.request.mock.calls.find(([,o])=>o?.method==='PUT')!
  expect(JSON.parse(put[1].body).invoice_ids).toEqual([8])
  wrapper.unmount()
 })
 it('automatically filters by payee and saves only the manually selected matching invoice',async()=>{
  mocks.allRows.mockImplementation(async(path:string)=>path==='/order/'?[{id:2,supplier_id:3,supplier_contact_person:'张工',order_amount:'100'}]:path==='/supplier/'?[{id:3,name:'销售公司',contact_person:'张工'}]:path==='/payer/'?[{id:4,name:'付款单位'}]:path==='/material/invoice'?[
   {id:8,invoice_number:'MATCH-008',seller_name:'销售公司',total_amount:'10',tax_amount:'1.3'},
   {id:9,invoice_number:'OTHER-009',seller_name:'另一家公司'},
  ]:[])
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/payments/new',component:CorePage,meta:{coreKind:'payments',coreMode:'new'}},{path:'/payments',component:{template:'<p>付款单列表</p>'}}]})
  await router.push('/payments/new?order_id=2');await router.isReady()
  const wrapper=mount({template:'<router-view/>'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  await wrapper.get('[data-testid="choose-invoices"]').trigger('click')
  expect(wrapper.get('.payment-invoice-picker').text()).toContain('MATCH-008')
  expect(wrapper.get('.payment-invoice-picker').text()).not.toContain('OTHER-009')
  await wrapper.get('[aria-label="关联发票 MATCH-008"]').setValue(true)
  await wrapper.get('[data-testid="confirm-invoice-selection"]').trigger('click')
  await wrapper.get('[aria-label="付款单位"]').setValue('4')
  await wrapper.get('[aria-label="本次实付金额"]').setValue('10.00')
  await wrapper.get('form').trigger('submit');await flushPromises()
  const post=mocks.request.mock.calls.find(([url,o])=>url==='/pay/'&&o?.method==='POST')!
  expect(JSON.parse(post[1].body)).toMatchObject({invoice_ids:[8],payee_supplier_id:3,current_payment_amount:'10.00'})
  wrapper.unmount()
 })
 it.each([['orders','new'],['orders','edit'],['payments','new'],['payments','edit']])('enables attachment drops on %s %s forms',async(kind,mode)=>{
  const path=mode==='new'?`/${kind}/new`:`/${kind}/2/edit`
  const router=createRouter({history:createMemoryHistory(),routes:[{path,component:CorePage,meta:{coreKind:kind,coreMode:mode}},{path:`/${kind}`,component:{template:'<div />'}}]})
  await router.push(path);await router.isReady()
  const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.getComponent(AttachmentEditor).props('drag')).not.toBeUndefined()
  wrapper.unmount()
 })
 it('edits an existing order on the paper form while retaining payments, date and attachments',async()=>{
  const order={id:2,order_number:'D002',project_id:7,supplier_id:3,supplier_contact_person:'张工',contact_phone:'13800000000',material_name:'stone',material_details:'原材料明细',order_amount:'100.00',paid_amount:'60.00',order_balance:'40.00',create_at:'2026-09-26 10:00:00',pays_list:[{id:9,pay_number:'P009',current_payment_amount:'60.00'}],attachments:JSON.stringify([{name:'原附件.jpg',url:'/uploads/original.jpg'}])}
  mocks.allRows.mockImplementation(async(path:string)=>path==='/project/'?[{id:7,project_name:'项目甲'}]:path==='/supplier/'?[{id:3,name:'供应商甲',contact_person:'张工',phone:'13800000000'}]:path==='/dictionary/detail/list'?[{code:'stone',value:'石材'}]:[])
  mocks.request.mockResolvedValue({code:0,data:order})
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/orders/:id/edit',component:CorePage,meta:{coreKind:'orders',coreMode:'edit'}},{path:'/orders',component:{template:'<p>订单列表</p>'}},{path:'/payments/:id/edit',component:{template:'<p>付款单</p>'}}]})
  await router.push('/orders/2/edit');await router.isReady()
  const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.find('.order-entry-sheet').exists()).toBe(true)
  expect(wrapper.get('[aria-label="订单编号"]').element).toHaveProperty('value','D002')
  expect(wrapper.get('.order-entry-meta').text()).toContain('2026-09-26')
  expect(wrapper.get('.order-entry-balance').text()).toContain('40.00')
  expect(wrapper.text()).toContain('P009')
  expect(wrapper.text()).not.toContain('新增订单尚无付款记录')
  await wrapper.get('[aria-label="订单金额"]').setValue('120.50')
  expect(wrapper.get('.order-entry-balance').text()).toContain('60.50')
  await wrapper.get('form').trigger('submit');await flushPromises()
  const put=mocks.request.mock.calls.find(([,options])=>options?.method==='PUT')!
  expect(put[0]).toBe('/order/2')
  expect(JSON.parse(put[1].body)).toMatchObject({order_number:'D002',order_amount:'120.50',attachments:order.attachments})
  expect(router.currentRoute.value.path).toBe('/orders');wrapper.unmount()
 })
 it('edits a payment on paper without counting its saved amount twice, including when switching orders',async()=>{
  const payment={id:9,pay_number:'P009',order_id:2,payer_supplier_id:4,payee_supplier_id:3,current_payment_amount:'30.00',payment_purpose:'保留原用途',invoice_amount:'10.00',payment_status:'paid',handler:'王工',create_at:'2026-09-26 10:00:00',invoices_list:[{id:8}],attachments:JSON.stringify([{name:'付款附件.jpg',url:'/uploads/pay.jpg'}])}
  mocks.allRows.mockImplementation(async(path:string)=>path==='/order/'?[{id:2,order_number:'D002',project_name:'项目甲',supplier_id:3,supplier_contact_person:'张工',order_amount:'100.00',paid_amount:'60.00'},{id:5,order_number:'D005',supplier_id:3,supplier_contact_person:'张工',order_amount:'200.00',paid_amount:'20.00'}]:path==='/supplier/'?[{id:3,name:'供应商甲',contact_person:'张工',bank_name:'测试银行',account_number:'123456'}]:path==='/payer/'?[{id:4,name:'付款单位'}]:path==='/material/invoice'?[{id:8,invoice_number:'INV008'}]:[])
  mocks.request.mockResolvedValue({code:0,data:payment})
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/payments/:id/edit',component:CorePage,meta:{coreKind:'payments',coreMode:'edit'}},{path:'/payments',component:{template:'<p>付款列表</p>'}}]})
  await router.push('/payments/9/edit');await router.isReady()
  const wrapper=mount({template:'<router-view />'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.find('.payment-entry-sheet').exists()).toBe(true)
  expect(wrapper.get('[data-testid="payment-order-contact"]').text()).toBe('张工')
  expect(wrapper.get('[aria-label="付款用途"]').element).toHaveProperty('value','保留原用途')
  expect(wrapper.get('.entry-meta').text()).toContain('2026-09-26')
  expect(wrapper.get('[data-testid="payment-total-preview"]').text()).toContain('60.00')
  expect(wrapper.get('[data-testid="payment-balance-preview"]').text()).toContain('40.00')
  await wrapper.get('[aria-label="本次实付金额"]').setValue('40.10')
  expect(wrapper.get('[data-testid="payment-total-preview"]').text()).toContain('70.10')
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','order_id',5);await flushPromises()
  expect(wrapper.get('[data-testid="payment-total-preview"]').text()).toContain('60.10')
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','order_id',2);await flushPromises()
  expect(wrapper.get('[data-testid="payment-total-preview"]').text()).toContain('70.10')
  await wrapper.get('[aria-label="付款用途"]').setValue('修改后用途')
  await wrapper.get('form').trigger('submit');await flushPromises()
  const put=mocks.request.mock.calls.find(([,options])=>options?.method==='PUT')!
  expect(put[0]).toBe('/pay/9')
  expect(JSON.parse(put[1].body)).toMatchObject({pay_number:'P009',order_id:2,current_payment_amount:'40.10',invoice_ids:[8],attachments:payment.attachments,payment_purpose:'修改后用途'})
  expect(router.currentRoute.value.path).toBe('/payments');wrapper.unmount()
 })
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
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select','张工');await flushPromises()
  expect(wrapper.get('[aria-label="供应商联系人"]').element).toHaveProperty('value','张工')
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
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select','张工');await flushPromises()
  wrapper.getComponent(OrderEntrySheet).vm.$emit('field','supplier_contact_person','自由输入的联系人');await flushPromises()
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false)
  wrapper.getComponent(SupplierContactSelect).vm.$emit('select','张工');await flushPromises()
  await wrapper.get('form').trigger('submit');await flushPromises()
  const post=mocks.request.mock.calls.find(([,options])=>options?.method==='POST')!
  expect(post[0]).toBe('/order/')
  expect(JSON.parse(post[1].body)).toMatchObject({project_id:7,supplier_id:3,material_name:'stone',order_amount:'1234.50',supplier_contact_person:'张工',contact_phone:'13800000000',material_details:'采购石材',cutting_time:'2026-09-28',estimated_arrival_time:'2026-09-30',material_manager:'李工',sub_project_manager:'王工',attachments:'[]'})
  expect(router.currentRoute.value.path).toBe('/orders');wrapper.unmount()
 })
 it('opens the new payment as a paper form, prefills the linked order and preserves decimal submission',async()=>{
  mocks.allRows.mockImplementation(async(path:string)=>path==='/order/'?[{id:2,order_number:'D002',project_name:'项目甲',supplier_id:3,supplier_contact_person:'张工',material_name:'材料',material_details:'合同材料款',order_amount:'100.00',paid_amount:'20.00'},{id:5,order_number:'D005',project_name:'项目乙',supplier_id:6,supplier_contact_person:'李工',material_details:'第二个订单',order_amount:'200.00',paid_amount:'0.00'}]:path==='/supplier/'?[{id:3,name:'收款单位',contact_person:'张工',bank_name:'测试银行',account_number:'123456'},{id:6,name:'第二家收款单位',contact_person:'李工',bank_name:'第二家银行',account_number:'654321'},{id:7,name:'同联系人另一单位',contact_person:'张工',bank_name:'另一开户行',account_number:'777777'}]:path==='/payer/'?[{id:4,name:'付款单位'}]:[])
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/payments/new',component:CorePage,meta:{coreKind:'payments',coreMode:'new'}},{path:'/payments',component:{template:'<div>付款列表</div>'}}]})
  await router.push('/payments/new?order_id=2');await router.isReady()
  const wrapper=mount({template:'<router-view v-slot="{Component,route}"><keep-alive><component :is="Component" :key="route.fullPath"/></keep-alive></router-view>'},{global:{plugins:[router],stubs,directives:{loading:()=>{}}}});await flushPromises()
  expect(wrapper.find('.payment-entry-sheet').exists()).toBe(true)
  expect(wrapper.get('[data-testid="payment-order-contact"]').text()).toBe('张工')
  expect(wrapper.text()).toContain('付款审批单');expect(wrapper.text()).toContain('测试银行')
  expect(wrapper.get('[aria-label="收款单位"]').attributes('readonly')).toBeUndefined()
  expect(wrapper.get('[aria-label="收款单位"]').element).toHaveProperty('value','3')
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','order_id',5);await flushPromises()
  expect(wrapper.get('[aria-label="收款单位"]').element).toHaveProperty('value','6')
  expect(wrapper.get('[data-testid="payment-order-contact"]').text()).toBe('李工')
  expect(wrapper.text()).toContain('第二家银行')
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','order_id',undefined);await flushPromises()
  expect(wrapper.get('[aria-label="收款单位"]').element).toHaveProperty('value','')
  expect(wrapper.get('[data-testid="payment-order-contact"]').text()).toBe('—')
  expect(wrapper.text()).not.toContain('第二家银行')
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false)
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','order_id',2);await flushPromises()
  expect(wrapper.get('[aria-label="付款用途"]').element).toHaveProperty('value','合同材料款')
  await wrapper.get('[aria-label="本次实付金额"]').setValue('30.10')
  expect(wrapper.get('[data-testid="payment-total-preview"]').text()).toContain('50.10')
  expect(wrapper.get('[data-testid="payment-balance-preview"]').text()).toContain('49.90')
  await router.push('/payments/new?order_id=5');await flushPromises()
  expect(wrapper.get('[aria-label="付款用途"]').element).toHaveProperty('value','第二个订单')
  await router.push('/payments/new?order_id=2');await flushPromises()
  expect(wrapper.get('[aria-label="本次实付金额"]').element).toHaveProperty('value','30.10')
  await wrapper.get('[aria-label="付款单位"]').setValue('4')
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','payee_supplier_id',6);await flushPromises()
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(mocks.request.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false)
  wrapper.getComponent(PaymentEntrySheet).vm.$emit('field','payee_supplier_id',7);await flushPromises()
  expect(wrapper.text()).toContain('另一开户行');expect(wrapper.text()).toContain('777777')

  await wrapper.find('form').trigger('submit');await flushPromises()
  const post=mocks.request.mock.calls.find(([,options])=>options?.method==='POST')!
  expect(post[0]).toBe('/pay/')
  expect(JSON.parse(post[1].body)).toMatchObject({order_id:2,payee_supplier_id:7,current_payment_amount:'30.10',payment_purpose:'合同材料款',invoice_ids:[],attachments:'[]'})
  expect(router.currentRoute.value.path).toBe('/payments');wrapper.unmount()
 })
})


