export type Row = Record<string, any>
const moneyFields=new Set(['price','total_price','total','planned_price','planned_total_amount','inbound_price','latest_price','total_value','seller_price','tax_amount','price_no_tax','invoice_amount','total_inventory_value'])
export function displayValue(field:string,value:unknown,view=''):string {
 if(value==null||value==='')return '—'
 if(field==='type')return ({in:'入库',out:'出库'} as Record<string,string>)[String(value)]||String(value)
 if(field==='status')return ({pending:view==='inbound'?'待入库':'待出库',completed:view==='inbound'?'已入库':'已出库'} as Record<string,string>)[String(value)]||String(value)
 if(moneyFields.has(field)&&Number.isFinite(Number(value)))return Number(value).toFixed(2)
 return String(value)
}
export const labels: Record<string,string> = {inventory_id:'库存材料',recipient:'领用人',id:'编号',project_id:'项目',project_name:'项目',supplier_id:'供应商',supplier_name:'供应商',material_name:'材料名称',material_spec:'规格',material_unit:'单位',planned_total_quantity:'策划总量',planned_remaining_quantity:'策划余量',planned_price:'策划单价',planned_total_amount:'策划合价',pending_inbound_quantity:'待入库量',batch_number:'批次',batch_sub_number:'分号',inbound_quantity:'入库量',inbound_price:'入库单价',current_stock:'现有库存',latest_price:'最近入库单价',total_value:'库存总值',seller_price:'销售单价',seller_quantity:'计划销售数量',profit_ratio:'利润系数',tax_rate:'税率（小数）',tax_amount:'税额',price_no_tax:'不含税单价',seller_name:'销售商',outbound_quantity:'出库数量',completed_sales_quantity:'完成销售数量',invoice_id:'关联发票',invoice_number:'发票号码',status:'状态',create_at:'时间',name:'名称',category:'大类',spec:'规格',unit:'单位',quantity:'数量',price:'单价',location:'位置',operator:'操作员',remark:'备注',destination:'去向',date:'日期',plant_name:'苗木名称',order_no:'单号',total_price:'合价',total:'总金额',item_count:'项目数',type:'类型',guide_price:'指导价'}
export const materialColumns:Record<string,string[]>={planning:['project_name','material_name','material_spec','material_unit','planned_total_quantity','planned_remaining_quantity','pending_inbound_quantity','planned_price','planned_total_amount','supplier_name','batch_number'],inbound:['project_name','batch_number','batch_sub_number','material_name','material_spec','material_unit','inbound_quantity','inbound_price','supplier_name','status','invoice_number'],inventory:['project_name','material_name','material_spec','material_unit','current_stock','latest_price','total_value','supplier_name','seller_name','seller_quantity','seller_price','profit_ratio','tax_rate','tax_amount','price_no_tax'],outbound:['project_name','batch_number','material_name','material_spec','material_unit','seller_quantity','completed_sales_quantity','seller_price','seller_name','tax_rate','invoice_number','status']}
export function numeric(value:unknown, label:string, positive=false):string {const s=String(value??'').trim();if(!s || !Number.isFinite(Number(s)) || Number(s)<0 || (positive && Number(s)===0))throw new Error(`${label}必须为${positive?'大于0':'非负'}的有限数字`);return s}
export function planPayload(form:Row):Row {const p={...form}; p.planned_total_quantity=numeric(p.planned_total_quantity,'策划总量');p.planned_price=numeric(p.planned_price,'策划单价');p.planned_remaining_quantity=p.planned_total_quantity;return p}
export function settingsValue(raw:string|null):Row {const v=raw?JSON.parse(raw):{};return {category:Array.isArray(v.category)?v.category:[],location:Array.isArray(v.location)?v.location:[],'non-inventory':Array.isArray(v['non-inventory'])?v['non-inventory'].map((x:any)=>typeof x==='string'?{name:x,unit:'株',guide_price:0}:x):[]}}
export function outboundItems(items:Row[]):Row[]{if(!items.length)throw new Error('请添加出库项目');const totals=new Map<any,number>();for(const x of items){numeric(x.quantity,'数量',true);numeric(x.price,'单价');if(!x.is_non_inventory){if(!x.plant_id)throw new Error('请选择库存');const qty=(totals.get(x.plant_id)||0)+Number(x.quantity);totals.set(x.plant_id,qty);if(qty>Number(x.available))throw new Error(`${x.name}库存不足`)}else if(!x.name)throw new Error('请输入名称')}return items.map(({available,...x})=>x)}
export function inventoryEdit(field:string,value:unknown,current:Row):Row {
 const raw=String(value??'').trim(),n=Number(raw);if(!raw||!Number.isFinite(n))throw Error('请输入有限数字')
 if(field==='seller_quantity')return {seller_quantity:raw,current_stock:String(Number(current.current_stock||0)-(n-Number(current.seller_quantity||0)))}
 if(field==='current_stock')return {current_stock:raw,seller_quantity:String(Number(current.seller_quantity||0)-(n-Number(current.current_stock||0)))}
 if(n<0)throw Error('价格、税率和系数不能为负数')
 if(['profit_ratio','seller_price','tax_rate'].includes(field)){
  const ratio=n||1.05,rate=field==='tax_rate'?n/100:Number(current.tax_rate||0)
  const price=field==='profit_ratio'?(Number(current.latest_price||0)*ratio).toFixed(2):field==='seller_price'?raw:String(current.seller_price||0)
  const tax=(Number(price)/(1+rate)*rate).toFixed(2),net=(Number(price)-Number(tax)).toFixed(2)
  return {...(field==='profit_ratio'?{profit_ratio:String(ratio),seller_price:price}:field==='tax_rate'?{tax_rate:String(rate)}:{seller_price:price}),tax_amount:tax,price_no_tax:net}
 }
 if(!['tax_amount','price_no_tax'].includes(field))throw Error('不支持的库存字段')
 return {[field]:raw}
}

