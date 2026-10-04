// @vitest-environment jsdom
import {mount,flushPromises} from '@vue/test-utils'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {installControls as ElementPlus} from '../../controls';import {ElMessageBox} from '../../feedback'
import {defineComponent,h,KeepAlive,ref} from 'vue'
import Material from './Material.vue'
import Nursery from './Nursery.vue'
const api=vi.hoisted(()=>({request:vi.fn(),allRows:vi.fn()}))
vi.mock('../../api',()=>api)
vi.mock('vue-router',()=>({onBeforeRouteLeave:vi.fn(),onBeforeRouteUpdate:vi.fn()}))
const mountPage=(component:any,view:string)=>mount(component,{props:{view},global:{plugins:[ElementPlus],stubs:{RouterLink:{template:'<a><slot/></a>'}}}})
beforeEach(()=>{api.request.mockReset();api.allRows.mockReset();api.allRows.mockResolvedValue([]);api.request.mockImplementation(async(path:string)=>({code:0,data:path==='/material/options'?{projects:[],suppliers:[]}:[],success:true,msg:'完成'}));localStorage.clear()})
describe('native inventory workflows',()=>{
 it.each([
  ['100','13','¥113.00','¥100.00','¥13.00'],
  ['100',0,'¥100.00','¥100.00','¥0.00'],
  ['-100','-13','¥-113.00','¥-100.00','¥-13.00'],
  ['1.005','0.005','¥1.01','¥1.01','¥0.01'],
  ['100',null,'待核实','¥100.00','待核实'],
  ['NaN','13','待核实','待核实','¥13.00'],
 ])('labels all three invoice amounts in the material invoice picker (%s, %s)',async(untaxed,tax,totalText,untaxedText,taxText)=>{
  const invoice={id:88,invoice_number:'LOCAL-INV88',seller_name:'本地测试单位',total_amount:untaxed,tax_amount:tax};api.allRows.mockImplementation(async(path:string)=>path==='/material/invoice'?[invoice]:[]);const wrapper=mountPage(Material,'inbound');await flushPromises();const vm=wrapper.vm as any;vm.selected=[{id:4}];await vm.batch('invoice');await flushPromises();const name=vm.options.invoice_id[0].name;expect(name).toContain(`价税合计 ${totalText}`);expect(name).toContain(`不含税金额 ${untaxedText}`);expect(name).toContain(`税额 ${taxText}`);expect(name).not.toContain('NaN');expect(invoice).toMatchObject({total_amount:untaxed,tax_amount:tax});expect(api.request.mock.calls.every(call=>!call[1]?.method||call[1].method==='GET')).toBe(true);wrapper.unmount()
 })
 it('retains mobile card row checkbox selection and opens generate-inbound',async()=>{
  api.allRows.mockResolvedValue([{id:7,project_id:1,material_name:'红砖',planned_remaining_quantity:'12.50'}]);const wrapper=mount(Material,{attachTo:document.body,props:{view:'planning'},global:{plugins:[ElementPlus],stubs:{RouterLink:{template:'<a><slot/></a>'}}}});await flushPromises();const input=wrapper.find('.m-select-row input[type="checkbox"]');expect(input.exists()).toBe(true);(input.element as HTMLInputElement).click();await flushPromises();expect((wrapper.vm as any).selected.map((r:any)=>r.id)).toEqual([7]);const generate=wrapper.findAll('button').find(b=>b.text()==='生成入库计划')!;await generate.trigger('click');await flushPromises();expect((wrapper.vm as any).dialog).toBe('generate');expect((wrapper.vm as any).items[0].id).toBe(7);wrapper.unmount()
 })
 it('retains mobile card header label select-all and supports deselection',async()=>{
  api.allRows.mockResolvedValue([{id:7,material_name:'红砖',planned_remaining_quantity:'12.50'}]);const wrapper=mount(Material,{attachTo:document.body,props:{view:'planning'},global:{plugins:[ElementPlus],stubs:{RouterLink:{template:'<a><slot/></a>'}}}});await flushPromises();const label=wrapper.find('.m-select-all');expect(label.exists()).toBe(true);(label.element as HTMLLabelElement).click();await vi.waitFor(()=>expect((wrapper.vm as any).selected.map((r:any)=>r.id)).toEqual([7]));(label.element as HTMLLabelElement).click();await vi.waitFor(()=>expect((wrapper.vm as any).selected).toEqual([]));wrapper.unmount()
 })
 it('generates inbound from selected planning with the entered fractional quantity',async()=>{const wrapper=mountPage(Material,'planning');await flushPromises();const vm=wrapper.vm as any;vm.selected=[{id:7,material_name:'红砖',planned_remaining_quantity:'12.50'}];await vm.batch('generate');vm.items[0].quantity='1.25';await vm.submitBatch();expect(api.request).toHaveBeenCalledWith('/material/planning/generate_inbound',{method:'POST',body:JSON.stringify({items:[{id:7,quantity:'1.25'}]})});wrapper.unmount()})
 it('uses saved sales quantities for batch outbound without introducing a quantity override',async()=>{const wrapper=mountPage(Material,'inventory');await flushPromises();const vm=wrapper.vm as any;vm.selected=[{id:9,seller_quantity:'2.50',current_stock:'9.00'}];await vm.batch('outbound');vm.form.direct_confirm=true;await vm.submitBatch();expect(api.request).toHaveBeenCalledWith('/material/outbound/batch',expect.objectContaining({method:'POST',body:JSON.stringify({direct_confirm:true,recipient:'',remark:'',items:[{inventory_id:9}]})}));wrapper.unmount()})
 it('keeps linked invoice fields when editing inbound',async()=>{const wrapper=mountPage(Material,'inbound');await flushPromises();const vm=wrapper.vm as any;vm.edit({id:4,project_id:1,material_name:'水泥',inbound_quantity:'8.25',inbound_price:'11.23',invoice_id:88,batch_number:'B1',status:'pending'});await vm.save();const body=JSON.parse(api.request.mock.calls.find(c=>c[0]==='/material/inbound/4')![1].body);expect(body.invoice_id).toBe(88);expect(body.inbound_quantity).toBe('8.25');wrapper.unmount()})
 it('edits nursery order using transaction IDs and preserves original remark',async()=>{const wrapper=mountPage(Nursery,'orders');await flushPromises();const vm=wrapper.vm as any;vm.editOrder({order_no:'OUT1',create_at:'2026-09-24 08:00',operator:'王',destination:'工地',items:[{id:6,plant_id:10,quantity:'2.5',price:'3.2',remark:'原备注'}]});vm.items[0].quantity='1.25';await vm.save();const body=JSON.parse(api.request.mock.calls.find(c=>c[0]==='/nursery/order/OUT1')![1].body);expect(body.items).toEqual([{id:6,quantity:'1.25',price:'3.2'}]);expect(body.remark).toBe('原备注');wrapper.unmount()})
 it('keeps nursery editor open on success:false and prevents concurrent submissions',async()=>{const wrapper=mountPage(Nursery,'inbound');await flushPromises();const vm=wrapper.vm as any;vm.newInbound();vm.form.name='红枫';vm.form.quantity='3';api.request.mockResolvedValueOnce({success:false,msg:'库存操作失败'});await vm.save();expect(vm.dialog).toBe('inbound');vm.busy=true;const count=api.request.mock.calls.length;await vm.save();expect(api.request.mock.calls.length).toBe(count);wrapper.unmount()})
 it('loads fresh inventory before applying the inverse quantity change',async()=>{const wrapper=mountPage(Material,'inventory');await flushPromises();const vm=wrapper.vm as any;vm.edit({id:9,current_stock:'20',seller_quantity:'1',tax_rate:'0.13'});vm.form.seller_quantity='5';api.request.mockResolvedValueOnce({code:0,data:{current_stock:'10',seller_quantity:'2'}});await vm.save();expect(api.request).toHaveBeenCalledWith('/material/inventory/9',{method:'PUT',body:JSON.stringify({id:9,seller_quantity:'5',current_stock:'7'})});wrapper.unmount()})
 it('does not submit a planning form without a project',async()=>{const wrapper=mountPage(Material,'planning');await flushPromises();const vm=wrapper.vm as any;vm.edit();vm.form.material_name='红砖';vm.form.planned_total_quantity='5';vm.form.planned_price='1';await vm.save();expect(api.request.mock.calls.some(c=>c[1]?.method==='POST')).toBe(false);expect(vm.dialog).toBe('edit');wrapper.unmount()})
 it('retains a dirty nursery draft when discard is cancelled',async()=>{const wrapper=mountPage(Nursery,'inbound');await flushPromises();const vm=wrapper.vm as any;vm.newInbound();vm.form.name='未保存红枫';const confirm=vi.spyOn(ElMessageBox,'confirm').mockRejectedValueOnce('cancel');await vm.closeEditor();expect(vm.dialog).toBe('inbound');expect(vm.form.name).toBe('未保存红枫');confirm.mockRestore();wrapper.unmount()})
 it('refreshes cached nursery stock on return without clearing draft lines or header',async()=>{
  const show=ref(true),Other=defineComponent({render:()=>h('div','其他页面')});let available='10';api.request.mockImplementation(async()=>({code:0,data:[{id:1,name:'红枫',spec:'H3',unit:'株',quantity:available,price:'123.50'}]}))
  const shell=defineComponent({setup:()=>()=>h(KeepAlive,null,{default:()=>show.value?h(Nursery,{view:'outbound',key:'outbound'}):h(Other)})})
  const wrapper=mount(shell,{global:{plugins:[ElementPlus],stubs:{RouterLink:{template:'<a><slot/></a>'}}}});await flushPromises();const vm=wrapper.findComponent(Nursery).vm as any;vm.addStock(1);vm.items[0].quantity='2.25';vm.items[0].price='130.75';vm.form.destination='待保存工地';show.value=false;await flushPromises();available='25';show.value=true;await flushPromises();expect(vm.stock[0].quantity).toBe('25');expect(vm.items[0]).toMatchObject({quantity:'2.25',price:'130.75',available:'25'});expect(vm.form.destination).toBe('待保存工地');expect(api.request.mock.calls.filter(c=>c[0]==='/nursery/inventory?all=1')).toHaveLength(2);wrapper.unmount()
 })
 it('refreshes cached material rows while retaining filters page and open editor',async()=>{
  const show=ref(true),Other=defineComponent({render:()=>h('div')});let name='旧材料';api.allRows.mockImplementation(async()=>Array.from({length:90},(_,i)=>({id:i+1,material_name:name,project_name:'项目',current_stock:'10',seller_quantity:'2',seller_price:'123.5'})))
  const shell=defineComponent({setup:()=>()=>h(KeepAlive,null,{default:()=>show.value?h(Material,{view:'inventory',key:'inventory'}):h(Other)})})
  const wrapper=mount(shell,{global:{plugins:[ElementPlus],stubs:{RouterLink:{template:'<a><slot/></a>'}}}});await flushPromises();const vm=wrapper.findComponent(Material).vm as any;vm.project=7;vm.page=2;vm.search='材料';vm.edit(vm.rows[0]);vm.form.seller_quantity='6';show.value=false;await flushPromises();name='新材料';show.value=true;await flushPromises();expect(vm.rows[0].material_name).toBe('新材料');expect(vm.project).toBe(7);expect(vm.page).toBe(2);expect(vm.search).toBe('材料');expect(vm.dialog).toBe('edit');expect(vm.form.seller_quantity).toBe('6');expect(api.allRows).toHaveBeenLastCalledWith('/material/inventory',expect.objectContaining({project_id:7}));wrapper.unmount()
 })
 it('keeps nursery transaction filters and page while refreshing cached rows',async()=>{
  const show=ref(true),Other=defineComponent({render:()=>h('div')});let amount='123.5';api.allRows.mockImplementation(async()=>Array.from({length:90},(_,i)=>({id:i+1,type:'in',plant_name:'红枫',quantity:'2.25',price:amount})))
  const shell=defineComponent({setup:()=>()=>h(KeepAlive,null,{default:()=>show.value?h(Nursery,{view:'transactions',key:'transactions'}):h(Other)})})
  const wrapper=mount(shell,{global:{plugins:[ElementPlus],stubs:{RouterLink:{template:'<a><slot/></a>'}}}});await flushPromises();const vm=wrapper.findComponent(Nursery).vm as any;vm.page=2;vm.search='红枫';vm.type='in';show.value=false;await flushPromises();amount='125.7';show.value=true;await flushPromises();expect(vm.rows[0].price).toBe('125.7');expect(vm.page).toBe(2);expect(vm.search).toBe('红枫');expect(vm.type).toBe('in');expect(wrapper.text()).toContain('125.70');expect(wrapper.text()).toContain('入库');wrapper.unmount()
 })
})



