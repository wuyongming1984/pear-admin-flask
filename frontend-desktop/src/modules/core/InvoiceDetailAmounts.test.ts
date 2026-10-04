// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'
import {beforeEach, expect, it, vi} from 'vitest'
import CorePage from './CorePage.vue'
const mocks=vi.hoisted(()=>({request:vi.fn(),allRows:vi.fn()}))
vi.mock('../../api',()=>({...mocks,query:(p:any)=>new URLSearchParams(p).toString(),safeUrl:()=>''}))
vi.mock('element-plus',()=>({ElMessage:{error:vi.fn()},ElMessageBox:{confirm:vi.fn()}}))
beforeEach(()=>{vi.clearAllMocks();mocks.allRows.mockResolvedValue([])})
it.each([[null,'13','待核实','¥13.00'],['NaN','bad','待核实','待核实'],['100','13','¥100.00','¥13.00']])('validates invoice detail description amounts (%s,%s)',async(total_amount,tax_amount,untaxed,tax)=>{
 mocks.request.mockResolvedValue({code:0,data:[{id:1,total_amount,tax_amount}]})
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/invoices/:id',component:CorePage,meta:{coreKind:'invoices',coreMode:'detail'}}]})
 await router.push('/invoices/1');await router.isReady()
 const wrapper=mount({template:'<router-view/>'},{global:{plugins:[router],stubs:{InvoicePaper:true,InvoicePaymentLinks:true,InvoiceSourcePreview:true,TablePrint:true,'el-button':true,'el-table':true,'el-table-column':true,'el-dialog':true,'el-input':true,'el-descriptions':{template:'<div><slot/></div>'},'el-descriptions-item':{props:['label'],template:'<p :data-label="label"><slot/></p>'}},directives:{loading:()=>{}},config:{warnHandler:()=>{}}}})
 await flushPromises()
 expect(wrapper.get('[data-label="不含税金额"]').text()).toBe(untaxed)
 expect(wrapper.get('[data-label="税额"]').text()).toBe(tax)
 expect(wrapper.text()).not.toContain('NaN')
 expect(mocks.request.mock.calls.every(([,options])=>!options?.method)).toBe(true)
 wrapper.unmount()
})
