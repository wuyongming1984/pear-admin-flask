export type Kind = 'project' | 'order' | 'pay';
export type RecordData = Record<string, any>;
export interface Attachment { id?: number|null; code?:string; name?:string; filename?:string; original_filename?:string; url?:string; file_path?:string; size?:number; [key:string]:any }
export interface Field { key:string; label:string; type?:'money'|'date'|'textarea'|'select'|'relation'; required?:boolean; dict?:string; source?:'project'|'supplier'|'order'|'payer'; hint?:string }
export const config:Record<Kind,{title:string;icon:string;name:string;amount:string;search:string;dict?:string;status?:string;fields:Field[]}>= {
 project:{title:'项目',icon:'apps-o',name:'project_name',amount:'project_amount',search:'project_name',dict:'xmzt',status:'project_status',fields:[
 {key:'project_name',label:'项目名称',required:true},{key:'project_full_name',label:'项目全称'},
 {key:'project_scale',label:'项目类型',type:'select',dict:'xmgm'},{key:'project_status',label:'项目状态',type:'select',dict:'xmzt',required:true},
 {key:'project_amount',label:'合同金额',type:'money',required:true},{key:'project_audit_price_amount',label:'审价金额',type:'money'},{key:'project_audit_amount',label:'审计金额',type:'money'},
 {key:'start_date',label:'开始日期',type:'date'},{key:'end_date',label:'结束日期',type:'date'}]},
 order:{title:'订单',icon:'orders-o',name:'order_number',amount:'order_amount',search:'order_number',fields:[
 {key:'order_number',label:'订单编号',hint:'新增时留空自动生成'},{key:'project_id',label:'关联项目',type:'relation',source:'project',required:true},
 {key:'supplier_id',label:'供应商',type:'relation',source:'supplier',required:true},{key:'supplier_contact_person',label:'供应商联系人'},{key:'contact_phone',label:'联系电话'},
 {key:'material_name',label:'材料名称',type:'select',dict:'clmc',required:true},{key:'order_amount',label:'订单金额',type:'money',required:true},
 {key:'cutting_time',label:'下料日期',type:'date'},{key:'estimated_arrival_time',label:'预计到场',type:'date'},
 {key:'material_manager',label:'材料负责人'},{key:'sub_project_manager',label:'项目负责人'},{key:'material_details',label:'材料明细',type:'textarea'}]},
 pay:{title:'付款',icon:'balance-list-o',name:'pay_number',amount:'current_payment_amount',search:'pay_number',dict:'fkzt',status:'payment_status',fields:[
 {key:'pay_number',label:'付款单号',required:true},{key:'order_id',label:'关联订单',type:'relation',source:'order',required:true},
 {key:'payer_supplier_id',label:'付款单位',type:'relation',source:'payer',required:true},{key:'payee_supplier_id',label:'收款供应商',type:'relation',source:'supplier',required:true},
 {key:'current_payment_amount',label:'付款金额',type:'money',required:true},{key:'invoice_amount',label:'开票金额',type:'money'},
 {key:'payment_status',label:'付款状态',type:'select',dict:'fkzt',required:true},{key:'handler',label:'经办人',required:true},{key:'payment_purpose',label:'付款用途',type:'textarea'}]}
};
export function validMoney(v:string):boolean {return /^(?:0|[1-9]\d{0,15})(?:\.\d{1,2})?$/.test(v)}
export function money(v:unknown):string {if(v===null||v===undefined||v==='')return '—';const n=Number(v); return Number.isFinite(n)?new Intl.NumberFormat('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n):'—'}
export function attachmentsOf(row:RecordData):Attachment[]{
 let value=row.attachments;
 if(typeof value==='string'){try{value=JSON.parse(value)}catch{throw new Error('原附件数据无法读取，请在电脑端检查后再编辑')}}
 if(!Array.isArray(value)) value=row.attachments_list||[];
 return value.map((a:Attachment,index:number)=>{const preview=(row.attachments_list||[])[index];return {...a,...(a.file_path?{url:a.file_path}:{}),...(preview?.url&&preview.url!==(a.file_path||a.url)?{preview_url:preview.url}:{})}});
}
export function payloadFor(kind:Kind,form:RecordData,attachments?:Attachment[]):RecordData{
 const data:RecordData={};
 for(const f of config[kind].fields){if(form[f.key]!==undefined) data[f.key]=f.type==='money'&&!f.required&&form[f.key]===''?null:form[f.key]}
 if(attachments!==undefined)data.attachments=JSON.stringify(attachments.map(({preview_url,...a})=>({...a,...(a.file_path?{url:a.file_path}:{})})));
 return data;
}
export const relationName=(source:string,row:RecordData)=>String(row[source==='project'?'project_name':source==='order'?'order_number':'name']||row.id||'');
