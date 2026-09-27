export type Row = Record<string, any>
export function ocrStatusLabel(status:unknown):string{return ({pending:'待识别',processing:'识别中',success:'识别成功',completed:'识别完成',failed:'识别失败'} as Record<string,string>)[String(status)]||String(status||'未识别')}
export function orderOptionLabel(order:Row,materials:Row[]=[]):string{return [order.order_number,order.project_name,materials.find(m=>String(m.code??m.value)===String(order.material_name))?.label||materials.find(m=>String(m.code??m.value)===String(order.material_name))?.value||order.material_name].filter(Boolean).join(' · ')}
export type Field = { key:string; label:string; required?:boolean; kind?:string; source?:string }
const f=(key:string,label:string,kind='text',required=false,source?:string):Field=>({key,label,kind,required,source})
export const schemas:Record<string,{title:string;api:string;menu:string;fields:Field[];search:Field[];attachments?:boolean}>={
 projects:{title:'项目管理',api:'/project/',menu:'/project/info/project_info.html',attachments:true,fields:[f('project_name','项目名称','text',true),f('project_full_name','项目全称'),f('project_scale','项目规模','select',false,'xmgm'),f('project_status','项目状态','select',false,'xmzt'),f('start_date','开始日期','date'),f('end_date','结束日期','date'),f('project_amount','合同金额','money'),f('project_audit_price_amount','审价金额','money'),f('project_audit_amount','审计金额','money')],search:[]},
 orders:{title:'采购订单',api:'/order/',menu:'/order_pay/base/order_base.html',attachments:true,fields:[f('order_number','订单编号'),f('project_id','项目','select',true,'projects'),f('material_name','材料名称','select',true,'materials'),f('supplier_id','供应商','select',true,'suppliers'),f('supplier_contact_person','供应商联系人','text',true),f('contact_phone','联系电话'),f('cutting_time','下料日期','date'),f('estimated_arrival_time','预计到场日期','date'),f('order_amount','订单金额','money',true),f('material_manager','材料负责人'),f('sub_project_manager','分项目负责人'),f('material_details','材料明细','textarea')],search:[]},
 payments:{title:'付款管理',api:'/pay/',menu:'/order_pay/base/pay_base.html',attachments:true,fields:[f('pay_number','付款单编号','text',true),f('order_id','关联订单','select',true,'orders'),f('payer_supplier_id','付款单位','select',true,'payers'),f('payee_supplier_id','收款单位','select',true,'suppliers'),f('current_payment_amount','本次实付金额','money',true),f('invoice_amount','开票金额','money'),f('payment_status','付款状态','select',false,'statuses'),f('handler','经办人'),f('payment_purpose','付款用途','textarea')],search:[]},
 suppliers:{title:'供应商管理',api:'/supplier/',menu:'/supplier/info/supplier_info.html',fields:[f('type_id','供应商类型','select',true,'supplierTypes'),f('name','供应商名称','text',true),f('contact_person','联系人','text',true),f('phone','联系电话','text',true),f('email','邮箱'),f('bank_name','开户行','text',true),f('account_number','银行账号','text',true),f('address','地址','textarea'),f('remark','备注','textarea')],search:[]},
 payers:{title:'付款单位',api:'/payer/',menu:'/payer/info/payer_info.html',fields:[f('type_id','单位类型','select',true,'payerTypes'),f('name','单位名称','text',true),f('bank_name','开户行'),f('account_number','银行账号'),f('remark','备注','textarea')],search:[]},
 invoices:{title:'发票管理',api:'/material/invoice',menu:'/view/material/invoice',fields:[f('invoice_number','发票号码','text',true),f('invoice_code','发票代码'),f('invoice_date','开票日期','date'),f('project_id','项目','select',false,'projects'),f('supplier_id','供应商','select',false,'suppliers'),f('buyer_name','购买方名称'),f('buyer_tax_num','购买方税号'),f('buyer_address_phone','购买方地址电话'),f('buyer_bank_account','购买方银行账号'),f('seller_name','销售方名称'),f('seller_tax_num','销售方税号'),f('seller_address_phone','销售方地址电话'),f('seller_bank_account','销售方银行账号'),f('invoice_type','发票类型'),f('invoice_name','发票名称'),f('check_code','校验码'),f('machine_num','机器编号'),f('password_area','密码区'),f('province','省份'),f('city','城市'),f('total_amount','不含税金额','money'),f('tax_amount','税额','money'),f('tax_rate','税率'),f('amount_in_words','金额大写'),f('payee','收款人'),f('checker','复核人'),f('drawer','开票人'),f('invoice_category','发票大类','select',false,'categories'),f('deductible','是否抵扣','select',false,'deductibles'),f('remarks','备注','textarea')],search:[]}
}
schemas.projects.search=schemas.projects.fields.filter(x=>['project_name','project_full_name','project_scale','project_status','project_amount'].includes(x.key))
schemas.orders.search=[f('project_id','项目筛选','select',false,'projects'),...schemas.orders.fields.filter(x=>!['material_details','supplier_id','project_id'].includes(x.key)),f('project_name','项目名称'),f('supplier_name','供应商名称'),f('create_at','创建日期','date')]
schemas.payments.search=[f('pay_number','付款编号'),f('order_number','订单编号'),f('payer_supplier_name','付款单位'),f('payee_supplier_name','收款单位'),f('project_name','项目名称'),f('supplier_contact_person','供应商联系人'),f('payment_status','付款状态','select',false,'statuses'),f('handler','经办人'),f('create_at','创建日期','date')]
schemas.suppliers.search=schemas.suppliers.fields
schemas.payers.search=schemas.payers.fields
schemas.invoices.search=[f('search','号码 / 购买方 / 销售方'),f('project_id','项目','select',false,'projects'),f('invoice_number','发票号码'),f('buyer_name','购买方'),f('seller_name','销售方'),f('invoice_category','发票大类','select',false,'categories')]
export function parseAttachments(row:Row):Row[]{
 const raw=row.attachments_list??row.attachments??[]; const items=typeof raw==='string'?JSON.parse(raw):raw
 if(!Array.isArray(items))throw new Error('附件数据格式不正确，无法安全编辑');
 return items.map((a:Row)=>({...a,code:a.code??a.attachment_code,url:a.url??a.file_path,name:a.name??a.original_filename??a.filename}))
}
export function payload(kind:string,row:Row,attachments:Row[],invoiceIds:any[]):Row{
 const schema=schemas[kind]!; const keys=schema.fields.map(x=>x.key)
 const result:Row={}; for(const key of keys)if(row[key]!==undefined)result[key]=row[key]
 if(row.id)result.id=row.id
 if(row.create_at)result.create_at=row.create_at
 if(schema.attachments)result.attachments=JSON.stringify(attachments)
 if(kind==='payments')result.invoice_ids=[...invoiceIds]
 if(kind==='invoices'&&row.id)return {invoice_category:row.invoice_category,deductible:row.deductible,remarks:row.remarks}
 return result
}
export function validate(kind:string,row:Row):string{
 for(const field of schemas[kind]!.fields){
  if(kind==='invoices'&&row.id&&!['invoice_category','deductible','remarks'].includes(field.key))continue
  const value=row[field.key]; if(field.required&&(value===null||value===undefined||String(value).trim()===''))return `${field.label}不能为空`
  if(field.kind==='money'&&value!==null&&value!==undefined&&value!==''&&!/^-?\d+(\.\d{1,2})?$/.test(String(value)))return `${field.label}请输入最多两位小数的金额`
 }return ''
}




