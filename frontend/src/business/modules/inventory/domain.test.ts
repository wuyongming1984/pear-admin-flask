import {describe,it,expect} from 'vitest'
import {numeric,planPayload,outboundItems,settingsValue,inventoryEdit,displayValue} from './domain'
describe('inventory business payloads',()=>{
 it('keeps amount strings and initializes planning remainder from quantity',()=>{const source={planned_total_quantity:'12.35',planned_price:'999999999.99',project_id:3};expect(planPayload(source)).toEqual({...source,planned_remaining_quantity:'12.35'});expect(source).not.toHaveProperty('planned_remaining_quantity')})
 it.each(['NaN','Infinity','-1','','  '])('rejects invalid quantity %s',v=>expect(()=>numeric(v,'数量',true)).toThrow())
 it('allows zero prices but rejects zero movement',()=>{expect(numeric('0','价格')).toBe('0');expect(()=>numeric('0','数量',true)).toThrow()})
 it('checks duplicate nursery stock selections against combined available quantity',()=>{expect(()=>outboundItems([{plant_id:1,name:'红枫',quantity:'6',price:'2',available:'10'},{plant_id:1,name:'红枫',quantity:'5',price:'3',available:'10'}])).toThrow('库存不足')})
 it('permits mixed inventory and noninventory while preserving quantity precision',()=>{expect(outboundItems([{plant_id:1,name:'红枫',quantity:'1.25',price:'2.15',available:'10'},{name:'运输',quantity:'1',price:'20',is_non_inventory:true}])).toEqual([{plant_id:1,name:'红枫',quantity:'1.25',price:'2.15'},{name:'运输',quantity:'1',price:'20',is_non_inventory:true}])})
 it('does not silently treat an unselected stock line as noninventory',()=>expect(()=>outboundItems([{name:'x',quantity:1,price:2}])).toThrow('请选择库存'))
 it('migrates existing nursery browser settings without discarding names',()=>expect(settingsValue(JSON.stringify({category:['苗木'],location:['A区'],'non-inventory':['运费',{name:'工具',unit:'件',guide_price:7}]}))).toEqual({category:['苗木'],location:['A区'],'non-inventory':[{name:'运费',unit:'株',guide_price:0},{name:'工具',unit:'件',guide_price:7}]}))
 it('refuses malformed settings instead of replacing stored settings',()=>expect(()=>settingsValue('{bad')).toThrow())
 it('keeps the stock plus sales sum when assigning sales quantity',()=>expect(inventoryEdit('seller_quantity','5',{seller_quantity:'2',current_stock:'10'})).toEqual({seller_quantity:'5',current_stock:'7'}))
 it('inversely updates sales when changing stock without clamping the result',()=>expect(inventoryEdit('current_stock','15',{seller_quantity:'2',current_stock:'10'})).toEqual({current_stock:'15',seller_quantity:'-3'}))
 it('recalculates price and tax from profit ratio using legacy cent rounding',()=>expect(inventoryEdit('profit_ratio','1.13',{latest_price:'100',tax_rate:'0.13'})).toEqual({profit_ratio:'1.13',seller_price:'113.00',tax_amount:'13.00',price_no_tax:'100.00'}))
 it('interprets the tax rate editor as a percentage and recomputes tax',()=>expect(inventoryEdit('tax_rate','13',{seller_price:'113'})).toEqual({tax_rate:'0.13',tax_amount:'13.00',price_no_tax:'100.00'}))
 it('updates dependent tax values when selling price changes',()=>expect(inventoryEdit('seller_price','226',{tax_rate:'0.13'})).toEqual({seller_price:'226',tax_amount:'26.00',price_no_tax:'200.00'}))
 it('formats financial columns with two decimals without rounding quantities',()=>{expect(displayValue('price','123.5')).toBe('123.50');expect(displayValue('total','0')).toBe('0.00');expect(displayValue('quantity','1.255')).toBe('1.255')})
 it('translates inbound outbound and fulfillment statuses',()=>{expect(displayValue('type','in')).toBe('入库');expect(displayValue('type','out')).toBe('出库');expect(displayValue('status','pending','inbound')).toBe('待入库');expect(displayValue('status','completed','outbound')).toBe('已出库')})
})
