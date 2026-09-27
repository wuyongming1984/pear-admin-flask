// @vitest-environment jsdom
import {mount,flushPromises} from '@vue/test-utils'
import {createRouter,createMemoryHistory} from 'vue-router'
import {describe,it,expect,vi} from 'vitest'
import PrintPage from './PrintPage.vue'
import Printorder from './Printorder.vue'
vi.mock('qrcode',()=>({default:{toDataURL:vi.fn(async()=>'data:image/png;base64,test')}}))
vi.mock('../../api',()=>({allRows:vi.fn(async()=>[{code:'001',value:'水泥'}]),request:vi.fn(async(path:string)=>({data:path==='/pay/1'?{id:1,pay_number:'FK1',order_id:2,current_payment_amount:'20.0',payee_supplier_id:3}:path==='/order/2'?{id:2,order_number:'D2',material_name:'001',order_amount:'100',order_balance:'80.0',paid_amount:'20.0'}:{bank_name:'测试银行',account_number:'123'}}))}))
describe('approval print toolbar',()=>{
 it('uses one Element Plus toolbar print action and uniform amount displays',async()=>{const router=createRouter({history:createMemoryHistory(),routes:[{path:'/payments/:id/print',component:PrintPage,meta:{coreKind:'payments'}}]});await router.push('/payments/1/print');await router.isReady();const print=vi.spyOn(window,'print').mockImplementation(()=>{});const wrapper=mount(PrintPage,{global:{plugins:[router],stubs:{'el-button':{props:['disabled'],template:'<button :disabled="disabled"><slot/></button>'},'el-alert':true},directives:{loading:()=>{}}}});await flushPromises();expect(wrapper.findAll('button')).toHaveLength(2);expect(wrapper.find('#order-balance').text()).toBe('80.00');expect(wrapper.find('#paid-total').text()).toBe('20.00');expect(wrapper.find('#amount-small').text()).toBe('20.00');expect(wrapper.find('#material-name').text()).toBe('水泥');await wrapper.findAll('button').find(x=>x.text()==='打印单据')!.trigger('click');expect(print).toHaveBeenCalledOnce();wrapper.unmount();print.mockRestore()})
 it('order paper contains no embedded legacy action button',()=>{const wrapper=mount(Printorder,{props:{values:{},qr:''}});expect(wrapper.find('button').exists()).toBe(false);wrapper.unmount()})
})
