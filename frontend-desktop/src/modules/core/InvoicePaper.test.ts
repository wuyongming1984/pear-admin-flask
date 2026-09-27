// @vitest-environment jsdom
import {mount} from '@vue/test-utils'
import {describe,it,expect} from 'vitest'
import InvoicePaper from './InvoicePaper.vue'
import TablePrint from './TablePrint.vue'
describe('native invoice paper and table print',()=>{
 it('renders the original ticket fields, all eight detail columns and exact tax-inclusive total',()=>{
  const invoice={invoice_code:'CODE',invoice_number:'NO123',machine_num:'MACHINE',check_code:'CHECK',invoice_date:'2026-09-24',invoice_name:'增值税专用发票',buyer_name:'买方',buyer_tax_num:'BUYERTAX',buyer_address_phone:'BUYERADDR',buyer_bank_account:'BUYERBANK',seller_name:'卖方',seller_tax_num:'SELLERTAX',seller_address_phone:'SELLERADDR',seller_bank_account:'SELLERBANK',total_amount:'90071992547409.19',tax_amount:'0.29',amount_in_words:'发票金额大写',remarks:'保留备注',payee:'收款员',checker:'复核员',drawer:'开票员',details:[{id:1,name:'钢管',spec:'DN100',unit:'米',quantity:'12.2500',price:'3.1000',amount:'37.98',tax_rate:'13%',tax:'4.94'}]}
  const wrapper=mount(InvoicePaper,{props:{invoice}});for(const value of ['CODE','NO123','MACHINE','CHECK','2026-09-24','BUYERTAX','BUYERADDR','BUYERBANK','SELLERTAX','SELLERADDR','SELLERBANK','DN100','12.2500','3.1000','37.98','13%','4.94','发票金额大写','保留备注','收款员','复核员','开票员','90071992547409.48'])expect(wrapper.text()).toContain(value);expect(wrapper.findAll('thead th')).toHaveLength(8);wrapper.unmount()
 })
 it('prints only selected columns and escapes data instead of rendering HTML',()=>{const wrapper=mount(TablePrint,{props:{modelValue:true,title:'项目管理',columns:[{key:'project_name',label:'项目名称'}],rows:[{id:1,project_name:'<script>alert(1)</script>',project_amount:'100'}],page:2,total:40,display:(row,field)=>row[field.key]},global:{stubs:{'el-dialog':{template:'<div><slot/></div>'},'el-button':true}}});expect(wrapper.findAll('th')).toHaveLength(1);expect(wrapper.text()).toContain('第 2 页');expect(wrapper.text()).toContain('<script>alert(1)</script>');expect(wrapper.find('script').exists()).toBe(false);expect(wrapper.text()).not.toContain('100');wrapper.unmount()})
})
