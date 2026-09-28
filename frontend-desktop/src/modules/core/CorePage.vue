<script setup lang="ts">
import PageHeader from "../../components/PageHeader.vue";
import {computed,ref,watch,onBeforeUnmount,onActivated,onDeactivated} from 'vue'
import {useRoute,useRouter,onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
import {request,query,allRows,safeUrl} from '../../api'
import AttachmentEditor from '../../components/AttachmentEditor.vue'
import InvoicePaper from './InvoicePaper.vue'
import InvoiceSourcePreview from './InvoiceSourcePreview.vue'
import InvoiceLibrary from './InvoiceLibrary.vue'
import InvoiceUploadDialog from './InvoiceUploadDialog.vue'
import InvoicePaymentLinks from './InvoicePaymentLinks.vue'
import PaymentInvoicePicker from './PaymentInvoicePicker.vue'
import ManagementList from './ManagementList.vue'
import TablePrint from './TablePrint.vue'
import PaymentEntrySheet from './PaymentEntrySheet.vue'
import {session} from '../../session'
import {contactName, suppliersForContact, changeOrderContact, changeOrderSupplier} from './orderContacts'
import SupplierContactSelect from './SupplierContactSelect.vue'
import OrderEntrySheet from './OrderEntrySheet.vue'
import {sumMoney,formatMoney} from './money'
import {schemas,parseAttachments,payload,validate,orderOptionLabel,ocrStatusLabel,type Row,type Field} from './model'
const currentRoute=useRoute();const route={meta:{...currentRoute.meta},params:{...currentRoute.params},query:{...currentRoute.query},path:currentRoute.path};const router=useRouter(); const kind=computed(()=>String(route.meta.coreKind));const schema=computed(()=>schemas[kind.value]!)
const mode=computed(()=>String(route.meta.coreMode||'list')),editing=computed(()=>['edit','new'].includes(mode.value))
const invoiceUploadVisible=ref(false)
onDeactivated(()=>{invoiceUploadVisible.value=false})
const invoiceList=computed(()=>kind.value==='invoices'&&mode.value==='list')
const paperOrder=computed(()=>kind.value==='orders'&&editing.value)
const paperPayment=computed(()=>kind.value==='payments'&&editing.value)
const originalPayment=ref<Row>()
const rows=ref<Row[]>([]),record=ref<Row>({}),attachments=ref<Row[]>([]),invoiceIds=ref<any[]>([]),selection=ref<Row[]>([]),options=ref<Record<string,Row[]>>({}),filters=ref<Row>(Object.fromEntries(Object.entries(route.query).map(([k,v])=>[k,k.endsWith(`_id`)&&v?Number(v):v]))),page=ref(1),limit=ref(20),count=ref(0),busy=ref(false),saving=ref(false),uploading=ref(false),error=ref(''),ready=ref(false),baseline=ref(''),syncOrders=ref<Row[]>([]),syncVisible=ref(false),pendingPayload=ref<Row>({}),uploadReport=ref<Row|null>(null),portalLink=ref('')
const snapshot=()=>JSON.stringify([record.value,attachments.value,invoiceIds.value]); const dirty=computed(()=>editing.value&&ready.value&&snapshot()!==baseline.value)
const listColumns=computed<Field[]>(()=>[{key:'id',label:'ID'},...schema.value.fields.filter(x=>x.kind!=='textarea'),...(kind.value==='orders'?[{key:'paid_amount',label:'累计付款'},{key:'order_balance',label:'订单余额'}]:[]),{key:'create_at',label:'创建时间'}]);const selectedColumns=ref(listColumns.value.map(f=>f.key));const visibleColumns=computed(()=>listColumns.value.filter(f=>selectedColumns.value.includes(f.key)));const tablePrintVisible=ref(false);onDeactivated(()=>{tablePrintVisible.value=false})
const freshRecord=():Row=>kind.value==='payments'?{pay_number:'FK'+Date.now(),order_id:route.query.order_id?Number(route.query.order_id):undefined}:kind.value==='orders'?{material_manager:session.nickname,project_id:route.query.project_id?Number(route.query.project_id):undefined}:kind.value==='payers'?{type_id:1}:{};
const invoiceEditKeys=['invoice_category','deductible','remarks']
const fields=computed(()=>schema.value.fields.filter(f=>kind.value!=='invoices'||mode.value!=='edit'||invoiceEditKeys.includes(f.key)))
const totals=computed(()=>({orders:sumMoney(rows.value.map(x=>x.order_amount)),paid:sumMoney(rows.value.map(x=>x.paid_amount)),balance:sumMoney(rows.value.map(x=>x.order_balance))}));
const selectedOrder=computed(()=>options.value.orders?.find(x=>x.id===record.value.order_id))
const paymentSuppliers=computed(()=>suppliersForContact(options.value.suppliers||[],selectedOrder.value?.supplier_contact_person))
const selectedSupplier=computed(()=>paymentSuppliers.value.find(x=>x.id===record.value.payee_supplier_id))
function opts(f:Field){if(kind.value==='payments'&&editing.value&&f.key==='payee_supplier_id')return paymentSuppliers.value;if(kind.value==='orders'&&editing.value&&f.key==='supplier_id')return suppliersForContact(options.value.suppliers||[],record.value.supplier_contact_person);return options.value[f.source||'']||[]}
function display(row:Row,f:Field){if(invoiceList.value&&f.key==='supplier_id')return row.supplier_name||'—';const v=row[f.key];if(f.kind==='money'||['paid_amount','order_balance','current_payment_amount'].includes(f.key))return formatMoney(v);return opts(f).find(x=>String(x.value)===String(v))?.label??v??'—'}
function fail(e:any){error.value=e.message||String(e);ElMessage.error(error.value)}
async function loadOptions(){
 const needed=new Set((invoiceList.value?schema.value.search:[...schema.value.fields,...schema.value.search]).map(f=>f.source).filter(Boolean));if(kind.value==='payments'){needed.add('invoices');needed.add('materials')}
 const tasks:Record<string,()=>Promise<any>>={projects:()=>allRows('/project/'),orders:()=>allRows('/order/'),suppliers:()=>allRows('/supplier/'),payers:()=>allRows('/payer/'),invoices:()=>allRows('/material/invoice'),materials:()=>allRows('/dictionary/detail/list',{dic_id:35}),statuses:()=>allRows('/dictionary/detail/list',{dic_id:28}),supplierTypes:()=>allRows('/dictionary/detail/list',{dic_id:25})}
 await Promise.all([...needed].map(async key=>{if(!key)return;if(key==='payerTypes'){options.value[key]=[{value:1,label:'单位'},{value:2,label:'个人'}];return}if(tasks[key]){const data=await tasks[key]!();options.value[key]=data.map((x:Row)=>({...x,value:['materials','statuses','supplierTypes'].includes(key)?(key==='supplierTypes'?Number(x.code):String(x.code)):x.id,label:key==='orders'?[x.order_number,x.project_name,x.material_name].filter(Boolean).join(' · '):key==='invoices'?[x.invoice_number,x.seller_name,x.total_amount].filter(Boolean).join(' · '):(x.value||x.project_name||x.name)}));}}))
 if(options.value.orders)options.value.orders=options.value.orders.map(x=>({...x,label:orderOptionLabel(x,options.value.materials)}));
 if([...needed].some(x=>['xmgm','xmzt','categories','deductibles'].includes(x||''))){const r=await request('/dictionary/options?codes=xmgm,xmzt,fpdl,kfdk');for(const [key,code]of Object.entries({xmgm:'xmgm',xmzt:'xmzt',categories:'fpdl',deductibles:'kfdk'}))options.value[key]=r.data?.[code]||[]}
}
let invoiceTimer:ReturnType<typeof setTimeout>|undefined,invoiceController:AbortController|undefined
let invoiceRevision=0,invoiceOptions:Promise<void>|undefined
function stopInvoiceSearch(){
 clearTimeout(invoiceTimer);invoiceTimer=undefined;invoiceRevision++
 invoiceController?.abort();invoiceController=undefined
 if(invoiceList.value)busy.value=false
}
async function loadInvoiceList(){
 stopInvoiceSearch()
 const revision=invoiceRevision,controller=new AbortController()
 invoiceController=controller;busy.value=true;error.value=''
 const timeout=setTimeout(()=>controller.abort(),30000)
 const params=Object.fromEntries(Object.entries(filters.value).map(([key,value])=>[key,typeof value==='string'?value.trim():value]))
 invoiceOptions??=loadOptions().catch(e=>{invoiceOptions=undefined;throw e})
 try{
  const [res]=await Promise.all([request(`${schema.value.api}?${query({...params,page:page.value,limit:limit.value})}`,{signal:controller.signal}),invoiceOptions])
  if(revision!==invoiceRevision)return
  rows.value=res.data;count.value=res.count||0;selection.value=[];ready.value=true
 }catch(e){if(revision===invoiceRevision){rows.value=[];count.value=0;selection.value=[];fail(e)}}
 finally{clearTimeout(timeout);if(revision===invoiceRevision){busy.value=false;invoiceController=undefined}}
}
watch(()=>JSON.stringify(filters.value),()=>{
 if(!invoiceList.value||currentRoute.path!==route.path)return
 stopInvoiceSearch();page.value=1;busy.value=true
 invoiceTimer=setTimeout(()=>{void loadInvoiceList()},200)
},{flush:'sync'})
onBeforeUnmount(stopInvoiceSearch);onDeactivated(stopInvoiceSearch)
async function load(){if(invoiceList.value)return loadInvoiceList();busy.value=true;ready.value=false;error.value='';portalLink.value='';try{
 await loadOptions()
 if(mode.value==='list'){const res=await request(`${schema.value.api}?${query({...filters.value,page:page.value,limit:limit.value})}`);rows.value=res.data;count.value=res.count||0}
 else if(mode.value==='new'){record.value=freshRecord();attachments.value=[];invoiceIds.value=[];if(kind.value==='payments'&&record.value.order_id)changed({key:'order_id',label:'关联订单'})}
 else{let data:Row|undefined;if(kind.value==='payers')data=(await allRows('/payer/')).find(x=>String(x.id)===String(route.params.id));else if(kind.value==='invoices')data=(await request(`/material/invoice?${query({id:route.params.id})}`)).data?.[0];else data=(await request(schema.value.api+route.params.id)).data;if(!data)throw new Error('记录不存在');record.value={...data};attachments.value=schema.value.attachments?parseAttachments(data):[];invoiceIds.value=(data.invoices_list||[]).map((x:Row)=>x.id)}
 if(kind.value==='payments'&&mode.value==='edit')originalPayment.value={order_id:record.value.order_id,current_payment_amount:record.value.current_payment_amount}
 baseline.value=snapshot();ready.value=true
 }catch(e){fail(e)}finally{busy.value=false}}
const unload=(event:BeforeUnloadEvent)=>{if(dirty.value||saving.value||uploading.value){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',unload))
let lastQuery=JSON.stringify(route.query);watch(()=>currentRoute.fullPath,()=>{if(mode.value==='list'&&currentRoute.path===route.path&&JSON.stringify(currentRoute.query)!==lastQuery){lastQuery=JSON.stringify(currentRoute.query);filters.value=Object.fromEntries(Object.entries(currentRoute.query).map(([k,v])=>[k,k.endsWith(`_id`)&&v?Number(v):v]));page.value=1;void load()}});void load();let activatedOnce=false;onActivated(()=>{if(activatedOnce&&!busy.value&&!saving.value&&!uploading.value&&(mode.value==='list'||kind.value==='payments'&&(mode.value==='detail'||editing.value&&!dirty.value)))void load();activatedOnce=true})
const guard=async()=>{if(saving.value||uploading.value)return false;if(dirty.value){try{await ElMessageBox.confirm('尚有未保存的修改，确定离开当前页面？','未保存修改',{type:'warning'});return true}catch{return false}}};onBeforeRouteLeave(guard);onBeforeRouteUpdate(guard)
function changed(f:Field){if(kind.value==='orders'){if(f.key==='supplier_contact_person')changeOrderContact(record.value,options.value.suppliers||[]);if(f.key==='supplier_id')changeOrderSupplier(record.value,options.value.suppliers||[]);}if(kind.value==='payments'&&f.key==='order_id'){const order=selectedOrder.value;record.value.payee_supplier_id=paymentSuppliers.value.find(s=>s.id===order?.supplier_id)?.id ?? (paymentSuppliers.value.length===1?paymentSuppliers.value[0]?.id:undefined);record.value.payment_purpose=order?.material_details||'';}}
function setEntryField(key:string,value:unknown){record.value[key]=value;changed({key,label:key})}
async function search(){page.value=1;await load()}
async function saved(){if(mode.value==='new'){record.value=freshRecord();attachments.value=[];invoiceIds.value=[];if(kind.value==='payments'&&record.value.order_id)changed({key:'order_id',label:'关联订单'})}baseline.value=snapshot();saving.value=false;ElMessage.success('保存成功');await router.push('/'+kind.value)}
async function save(){if(saving.value||uploading.value||!ready.value)return;if(kind.value==='payments'){if(!selectedOrder.value||!selectedSupplier.value){ElMessage.warning('请选择订单联系人关联的收款单位');return}}const invalid=validate(kind.value,record.value);if(invalid){ElMessage.warning(invalid);return}if(kind.value==='orders'){const supplier=options.value.suppliers?.find(s=>s.id===record.value.supplier_id);if(!supplier?.contact_person?.trim()||contactName(supplier.contact_person)!==contactName(record.value.supplier_contact_person)){ElMessage.warning('请从供应商管理中的联系人选择');return}record.value.contact_phone=supplier.phone||''}saving.value=true;error.value='';const data=payload(kind.value,record.value,attachments.value,invoiceIds.value);if(kind.value==='projects'&&attachments.value.some(a=>!String(a.code||'').trim())){saving.value=false;ElMessage.warning('请填写每个附件的编号');return}try{await request(mode.value==='new'?schema.value.api:schema.value.api+(kind.value==='invoices'?'/':'')+record.value.id,{method:mode.value==='new'?'POST':'PUT',body:JSON.stringify(data)});await saved()}catch(e:any){const response=e.response||e.data;if(response?.code===1001||e.code===1001){syncOrders.value=response.data.related_orders;pendingPayload.value=data;syncVisible.value=true}else fail(e)}finally{saving.value=false}}
async function confirmSync(){if(saving.value)return;saving.value=true;try{await request(`/supplier/${record.value.id}/update-with-orders`,{method:'POST',body:JSON.stringify({supplier_data:pendingPayload.value,confirmed_order_ids:syncOrders.value.map(x=>x.id)})});syncVisible.value=false;await saved()}catch(e){fail(e)}finally{saving.value=false}}
async function remove(list:Row[]){if(saving.value||uploading.value||(invoiceList.value&&busy.value)||!list.length)return;try{await ElMessageBox.confirm(`确定删除 ${list.length} 条记录？此操作无法撤销。`,'删除确认',{type:'warning'})}catch{return}saving.value=true;try{if(kind.value==='invoices')await request(schema.value.api,{method:'DELETE',body:JSON.stringify({ids:list.map(x=>x.id)})});else for(const row of list)await request(schema.value.api+row.id,{method:'DELETE'});ElMessage.success('删除成功');await load()}catch(e){fail(e);await load()}finally{saving.value=false}}
async function ocr(list:Row[]){if(saving.value||uploading.value||(invoiceList.value&&busy.value)||!list.length)return;try{await ElMessageBox.confirm('重新识别将更新发票识别字段，重复发票可能由服务器合并。继续？','发票识别')}catch{return}saving.value=true;try{uploadReport.value=await request('/material/invoice/ocr',{method:'POST',body:JSON.stringify({invoice_ids:list.map(x=>x.id)})});await load()}catch(e){fail(e)}finally{saving.value=false}}
async function token(){if(saving.value)return;try{await ElMessageBox.confirm('生成新的对账链接将使旧链接失效，继续？','供应商对账链接')}catch{return}saving.value=true;try{const r=await request(`/supplier/${record.value.id}/token`,{method:'POST'});const match=String(r.data.url||'').match(/^\/portal\/reconcile\/([A-Za-z0-9_-]+)$/);if(!match)throw new Error('对账链接格式不正确');portalLink.value=location.origin+'/pc/#/reconcile/'+match[1]}catch(e){fail(e)}finally{saving.value=false}}
function go(id:any,action=''){router.push(`/${kind.value}/${id}${action?'/'+action:''}`)}
async function exportCsv(){if(saving.value)return;saving.value=true;try{let data=await allRows(schema.value.api,filters.value);if(kind.value==='invoices'&&filters.value.invoice_category)data=data.filter(x=>String(x.invoice_category)===String(filters.value.invoice_category));const columns=[{key:'id',label:'ID'},...schema.value.fields,{key:'create_at',label:'创建时间'}];const quote=(v:any)=>{let text=String(v??'');if(/^[=+@\-\t\r]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"'};const csv=[columns.map(x=>quote(x.label)).join(','),...data.map(row=>columns.map(f=>quote(display(row,f))).join(','))].join('\r\n');const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=schema.value.title+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){fail(e)}finally{saving.value=false}}
</script>
<template><section class="page core-page" v-loading="busy && !invoiceList"><PageHeader :title="schema.title + (mode==='new'?' · 新增':mode==='edit'?' · 编辑':mode==='detail'?' · 详情':'')" :description="mode==='list'?'集中查询业务记录，查看详情与关联信息。':'核对业务信息、金额与附件资料。'"><el-button v-if="mode!=='list'" @click="router.push('/'+kind)">返回列表</el-button></PageHeader>
<el-alert v-if="error" :title="error" type="error" :closable="false" show-icon/><el-button v-if="error&&!ready" @click="load">重新加载</el-button>
<ManagementList v-if="mode==='list' && ['projects','suppliers','payers'].includes(kind)" :kind="kind" :rows="rows" :filters="filters" :options="options" :busy="saving" :display="display" @search="search" @reset="filters={};search()" @add="router.push('/'+kind+'/new')" @edit="go($event.id,'edit')" @detail="go($event.id)" @remove="remove([$event])">
<template #pagination><el-pagination v-model:current-page="page" v-model:page-size="limit" :page-sizes="[20,50,100]" :total="count" layout="total,sizes,prev,pager,next" @change="load"/></template>
<template #tools><el-button :loading="saving" @click="exportCsv">导出查询结果</el-button><el-button :disabled="!rows.length" @click="tablePrintVisible=true">打印本页表格</el-button></template>
</ManagementList>
<template v-else-if="mode==='list' && kind==='invoices'">
<InvoiceLibrary :rows="rows" :count="count" :searching="busy" :busy="saving || uploading || busy" :selection="selection" @selection="selection=$event" @remove="remove" @ocr="ocr" @upload="invoiceUploadVisible=true" @link-busy="saving=$event">
<template #search><el-form class="panel search-grid" @submit.prevent="search">
<el-form-item v-for="f in schema.search.filter(f=>!['search','project_id'].includes(f.key))" :key="f.key"><el-select v-if="f.kind==='select'" v-model="filters[f.key]" :aria-label="f.label" :placeholder="'全部'+f.label" clearable filterable><el-option v-for="o in opts(f)" :key="o.value" :value="o.value" :label="o.label"/></el-select><el-input v-else v-model="filters[f.key]" :aria-label="f.label" :placeholder="'搜索'+f.label+'…'" clearable @keyup.enter="search"/></el-form-item>
</el-form></template>
<template #tools><div class="toolbar"><el-button type="primary" @click="router.push('/'+kind+'/new')">新增</el-button><el-button :loading="saving" @click="exportCsv">导出查询结果</el-button><el-popover placement="bottom" width="320" trigger="click"><template #reference><el-button>显示列</el-button></template><el-checkbox-group v-model="selectedColumns"><el-checkbox v-for="column in listColumns" :key="column.key" :value="column.key">{{column.label}}</el-checkbox></el-checkbox-group><el-button link @click="selectedColumns=listColumns.map(f=>f.key)">全部显示</el-button></el-popover><el-button :disabled="!rows.length||!visibleColumns.length" @click="tablePrintVisible=true">打印本页表格</el-button><template v-if="kind==='invoices'"><el-button :disabled="!selection.length||saving" @click="ocr(selection)">批量识别</el-button><el-button type="danger" :disabled="!selection.length||saving" @click="remove(selection)">批量删除</el-button></template></div>
</template>
<template #pagination><el-pagination v-model:current-page="page" v-model:page-size="limit" :page-sizes="[20,50,100]" :total="count" :pager-count="3" size="small" layout="total,prev,pager,next" @change="load"/></template>
</InvoiceLibrary>
<InvoiceUploadDialog v-model="invoiceUploadVisible" :projects="options.projects || []" :disabled="saving" @busy="uploading=$event" @uploaded="load"/>
</template>
<template v-else-if="mode==='list'"><el-form class="panel search-grid" label-position="top" @submit.prevent="search"><el-form-item v-for="f in schema.search" :key="f.key" :label="f.label"><el-select v-if="f.kind==='select'" v-model="filters[f.key]" clearable filterable><el-option v-for="o in opts(f)" :key="o.value" :value="o.value" :label="o.label"/></el-select><el-date-picker v-else-if="f.kind==='date'" v-model="filters[f.key]" value-format="YYYY-MM-DD"/><el-input v-else v-model="filters[f.key]" clearable @keyup.enter="search"/></el-form-item><div class="actions"><el-button type="primary" @click="search">查询</el-button><el-button @click="filters={};search()">重置</el-button></div></el-form>
<div class="toolbar"><el-button type="primary" @click="router.push('/'+kind+'/new')">新增</el-button><el-button :loading="saving" @click="exportCsv">导出查询结果</el-button><el-popover placement="bottom" width="320" trigger="click"><template #reference><el-button>显示列</el-button></template><el-checkbox-group v-model="selectedColumns"><el-checkbox v-for="column in listColumns" :key="column.key" :value="column.key">{{column.label}}</el-checkbox></el-checkbox-group><el-button link @click="selectedColumns=listColumns.map(f=>f.key)">全部显示</el-button></el-popover><el-button :disabled="!rows.length||!visibleColumns.length" @click="tablePrintVisible=true">打印本页表格</el-button><template v-if="kind==='invoices'"><el-button :disabled="!selection.length||saving" @click="ocr(selection)">批量识别</el-button><el-button type="danger" :disabled="!selection.length||saving" @click="remove(selection)">批量删除</el-button></template></div>
<p v-if="kind===`orders`">本页订单合计：{{totals.orders}} · 付款合计：{{totals.paid}} · 余额合计：{{totals.balance}}</p><el-table :data="rows" border stripe @selection-change="selection=$event"><el-table-column v-if="kind==='invoices'" type="selection"/><el-table-column v-for="f in visibleColumns" :key="f.key" :label="f.label" min-width="145" show-overflow-tooltip><template #default="{row}">{{display(row,f)}}</template></el-table-column><el-table-column fixed="right" label="操作" width="220"><template #default="{row}"><el-button link type="primary" @click="go(row.id)">详情</el-button><el-button link type="primary" @click="go(row.id,'edit')">编辑</el-button><el-button link type="danger" :disabled="saving" @click="remove([row])">删除</el-button><el-button v-if="['orders','payments'].includes(kind)" link @click="go(row.id,'print')">打印</el-button></template></el-table-column></el-table>
<el-pagination v-model:current-page="page" v-model:page-size="limit" :page-sizes="[20,50,100]" :total="count" layout="total,sizes,prev,pager,next" @change="load"/></template>
<template v-else-if="ready"><el-form v-if="editing" :class="paperPayment || paperOrder ? 'document-paper-form' : 'panel'" label-position="top" @submit.prevent="save">
<PaymentEntrySheet v-if="paperPayment" :record="record" :original="originalPayment" :order="selectedOrder" :supplier="selectedSupplier" :options="options" :disabled="saving" @field="setEntryField">
<template #invoices><PaymentInvoicePicker v-model="invoiceIds" :invoices="options.invoices || []" :supplier-name="selectedSupplier?.name" :disabled="saving"/></template>
<template #attachments><AttachmentEditor v-model="attachments" kind="payments" drag :readonly="saving" @busy="uploading=$event"/></template>
<template #actions><el-button type="primary" :loading="saving" :disabled="uploading" native-type="submit">保存付款单</el-button><el-button :disabled="saving||uploading" @click="router.push('/payments')">取消</el-button></template>
</PaymentEntrySheet>
<OrderEntrySheet v-else-if="paperOrder" :record="record" :options="options" :disabled="saving" @field="setEntryField">
<template #attachments><AttachmentEditor v-model="attachments" kind="orders" drag :readonly="saving" @busy="uploading=$event"/></template>
<template #actions><el-button type="primary" :loading="saving" :disabled="uploading" native-type="submit">保存订单</el-button><el-button :disabled="saving||uploading" @click="router.push('/orders')">取消</el-button></template>
</OrderEntrySheet>
<template v-else><div class="form-grid"><el-form-item v-for="f in fields" :key="f.key" :label="f.label" :required="f.required"><SupplierContactSelect v-if="kind==='orders'&&f.key==='supplier_contact_person'" :record="record" :suppliers="options.suppliers||[]" :disabled="saving" @select="setEntryField('supplier_contact_person',$event)"/><el-select v-else-if="f.kind==='select'" v-model="record[f.key]" filterable clearable :disabled="saving" @change="changed(f)"><el-option v-for="o in opts(f)" :key="o.value" :label="o.label" :value="o.value"/></el-select><el-date-picker v-else-if="f.kind==='date'" v-model="record[f.key]" value-format="YYYY-MM-DD" :disabled="saving"/><el-input v-else v-model="record[f.key]" :type="f.kind==='textarea'?'textarea':'text'" :rows="4" :readonly="kind==='orders'&&f.key==='contact_phone'" :disabled="saving" :inputmode="f.kind==='money'?'decimal':undefined" :placeholder="f.key==='order_number'?'留空自动生成':''"/></el-form-item></div>
<el-alert v-if="kind==='invoices'&&mode==='edit'" type="info" title="现有接口支持修改发票大类、抵扣状态及备注；识别字段通过重新识别更新。" :closable="false"/>
<template v-if="kind==='payments'"><el-descriptions title="关联订单及收款账户" :column="2" border><el-descriptions-item label="项目">{{selectedOrder?.project_name}}</el-descriptions-item><el-descriptions-item label="订单金额">{{formatMoney(selectedOrder?.order_amount)}}</el-descriptions-item><el-descriptions-item label="联系人 / 电话">{{selectedSupplier?.contact_person}} / {{selectedSupplier?.phone}}</el-descriptions-item><el-descriptions-item label="开户行 / 账号">{{selectedSupplier?.bank_name}} / {{selectedSupplier?.account_number}}</el-descriptions-item></el-descriptions><el-form-item label="关联发票"><el-select v-model="invoiceIds" multiple filterable clearable :disabled="saving"><el-option v-for="inv in options.invoices" :key="inv.id" :value="inv.id" :label="inv.label"/></el-select></el-form-item></template>
<AttachmentEditor v-if="schema.attachments" v-model="attachments" :kind="kind" :readonly="saving" @busy="uploading=$event"/>
<div v-if="kind===`projects`" class="panel"><el-form-item v-for="(a,i) in attachments" :key="i" :label="`附件编号 · ${a.name||a.filename}`" required><el-input v-model="a.code" :disabled="saving" maxlength="64"/></el-form-item></div><div class="actions"><el-button type="primary" :loading="saving" :disabled="uploading" native-type="submit">保存</el-button><el-button :disabled="saving||uploading" @click="router.push('/'+kind)">取消</el-button></div></template></el-form>
<template v-else><div class="toolbar"><el-button v-if="kind===`projects`" @click="router.push(`/orders?project_id=${record.id}`)">查看项目订单</el-button><el-button type="primary" @click="go(record.id,'edit')">编辑</el-button><el-button v-if="['orders','payments'].includes(kind)" @click="go(record.id,'print')">打印审批单</el-button><el-button v-if="kind==='orders'" @click="router.push('/payments/new?order_id='+record.id)">新增付款单</el-button><el-button v-if="kind==='suppliers'" :loading="saving" @click="token">生成 / 重置对账链接</el-button><el-button v-if="kind==='invoices'" :loading="saving" @click="ocr([record])">重新识别</el-button></div>
<InvoicePaper v-if="kind===`invoices`" :invoice="record"/><el-input v-if="portalLink" :model-value="portalLink" readonly/><el-descriptions :column="2" border><el-descriptions-item v-for="f in schema.fields" :key="f.key" :label="f.label">{{display(record,f)}}</el-descriptions-item><el-descriptions-item label="创建时间">{{record.create_at}}</el-descriptions-item><template v-if="kind==='orders'"><el-descriptions-item label="累计付款">{{formatMoney(record.paid_amount)}}</el-descriptions-item><el-descriptions-item label="订单余额">{{formatMoney(record.order_balance)}}</el-descriptions-item></template></el-descriptions>
<div v-if="attachments.length" class="panel"><h3>附件</h3><p v-for="(a,i) in attachments" :key="i"><a :href="safeUrl(a.url||a.file_path)" target="_blank" rel="noopener">{{a.code}} · {{a.name||a.filename}}</a></p></div>
<div v-if="kind==='orders'" class="panel"><h3>付款记录</h3><el-table :data="record.pays_list||[]"><el-table-column prop="pay_number" label="付款编号"/><el-table-column label="付款金额"><template #default="{row}">{{formatMoney(row.current_payment_amount)}}</template></el-table-column><el-table-column prop="payment_status" label="付款状态"/><el-table-column prop="payer_supplier_name" label="付款单位"/><el-table-column prop="payee_supplier_name" label="收款单位"/><el-table-column prop="handler" label="经办人"/><el-table-column label="操作"><template #default="{row}"><el-button link @click="router.push('/payments/'+row.id)">详情</el-button></template></el-table-column></el-table></div>
<div v-if="kind==='payments'" class="panel"><h3>关联发票</h3><el-table :data="record.invoices_list||[]"><el-table-column prop="invoice_number" label="发票号码"/><el-table-column prop="seller_name" label="销售方"/><el-table-column label="金额"><template #default="{row}">{{formatMoney(row.total_amount)}}</template></el-table-column><el-table-column label="操作"><template #default="{row}"><el-button link @click="router.push('/invoices/'+row.id)">详情与预览</el-button></template></el-table-column></el-table></div>
<template v-if="kind==='invoices'"><div class="panel"><InvoicePaymentLinks :invoice-id="record.id" :disabled="saving" @busy="saving=$event"/><h3>识别结果</h3><p>价税合计：{{sumMoney([record.total_amount,record.tax_amount])}}</p><p>{{ocrStatusLabel(record.ocr_status)}} {{record.ocr_error}}</p><el-table :data="record.details||[]"><el-table-column v-for="(v,key) in record.details?.[0]||{}" :key="key" :prop="String(key)" :label="String(key)" min-width="130"/></el-table><details><summary>原始 OCR 数据</summary><pre>{{record.ocr_result}}</pre></details></div><InvoiceSourcePreview :invoice="record" /></template>
</template></template>
<TablePrint v-model="tablePrintVisible" :title="schema.title" :columns="visibleColumns" :rows="rows" :page="page" :total="count" :display="display"/><el-dialog v-model="syncVisible" title="联系人变更：确认同步所有关联订单" width="850px" :close-on-click-modal="false"><p>保存供应商会同时更新以下全部订单的联系人，请核对后确认。</p><el-table :data="syncOrders"><el-table-column prop="order_number" label="订单编号"/><el-table-column prop="project_name" label="项目"/><el-table-column prop="material_name" label="材料"/><el-table-column label="金额"><template #default="{row}">{{formatMoney(row.order_amount)}}</template></el-table-column></el-table><template #footer><el-button :disabled="saving" @click="syncVisible=false">返回修改</el-button><el-button type="primary" :loading="saving" @click="confirmSync">确认全部并保存</el-button></template></el-dialog>
</section></template>
<style scoped>.search-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.core-page .el-select,.core-page .el-date-editor{width:100%}.core-page .form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 24px}.core-page .panel{margin:16px 0}.core-page .el-pagination{margin-top:20px}.upload-panel{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.upload-panel .el-select,.upload-panel .el-input{width:200px}.upload-panel pre{width:100%;max-height:260px;overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1 small{font-size:16px;font-weight:400}.el-descriptions{margin:16px 0}a{color:#12644d}@media(max-width:800px){.core-page .form-grid{grid-template-columns:1fr}}</style>














