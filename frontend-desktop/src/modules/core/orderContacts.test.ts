// @vitest-environment jsdom
import {expect, test} from 'vitest'
import {mount} from '@vue/test-utils'
import PaymentEntrySheet from './PaymentEntrySheet.vue'
import OrderEntrySheet from './OrderEntrySheet.vue'
import SupplierContactSelect from './SupplierContactSelect.vue'
import {changeOrderContact, changeOrderSupplier} from './orderContacts'
import type {Row} from './model'

const suppliers = [
  {id:1,value:1,name:'甲公司',label:'甲公司',contact_person:'张工',phone:'111'},
  {id:2,value:2,name:'乙公司',label:'乙公司',contact_person:'张工',phone:'222'},
  {id:3,value:3,name:'丙公司',label:'丙公司',contact_person:'李工',phone:'333'},
]
const stubs = {RouterLink:true,'el-form-item':true,'el-select-v2':{props:['modelValue','disabled','options','props'],template:'<div><option v-for="o in options" :value="o[props?.value || \'value\']">{{o[props?.label || \'label\']}}</option></div>'},'el-select':{props:['modelValue','disabled'],template:'<div><slot/></div>'},'el-option':{props:['label','value'],template:'<option :value="value">{{label}}</option>'},'el-input':true,'el-date-picker':true}

test('contact dropdown shows distinct names only and supplier dropdown is limited to that contact',async()=>{
  const wrapper=mount(OrderEntrySheet,{props:{record:{},options:{suppliers},disabled:false},global:{stubs}})
  const contact=wrapper.getComponent(SupplierContactSelect)
  expect(contact.findAll('option').map(o=>o.text())).toEqual(['张工','李工'])
  expect(wrapper.get('[aria-label="供应商"]').findAll('option')).toHaveLength(0)
  await wrapper.setProps({record:{supplier_contact_person:'张工'}})
  expect(wrapper.get('[aria-label="供应商"]').findAll('option').map(o=>o.text())).toEqual(['甲公司','乙公司'])
  await wrapper.setProps({record:{supplier_contact_person:'李工'}})
  expect(wrapper.get('[aria-label="供应商"]').findAll('option').map(o=>o.text())).toEqual(['丙公司'])
  wrapper.unmount()
})

test('multiple companies require a separate choice and phone follows the selected company',()=>{
  const record:Row={supplier_contact_person:'张工'}
  changeOrderContact(record,suppliers)
  expect(record.supplier_id).toBeUndefined()
  expect(record.contact_phone).toBe('')
  record.supplier_id=2;changeOrderSupplier(record,suppliers)
  expect(record).toMatchObject({supplier_contact_person:'张工',supplier_id:2,contact_phone:'222'})
  changeOrderContact(record,suppliers)
  expect(record.supplier_id).toBe(2)
  record.supplier_id=1;changeOrderSupplier(record,suppliers)
  expect(record.contact_phone).toBe('111')
})

test('changing or clearing contacts removes incompatible supplier and phone selections',()=>{
  const record:Row={supplier_contact_person:'张工',supplier_id:2,contact_phone:'222'}
  record.supplier_contact_person='李工';changeOrderContact(record,suppliers)
  expect(record).toMatchObject({supplier_id:3,contact_phone:'333'})
  record.supplier_contact_person='张工';changeOrderContact(record,suppliers)
  expect(record.supplier_id).toBeUndefined()
  expect(record.contact_phone).toBe('')
  record.supplier_id=3;changeOrderSupplier(record,suppliers)
  expect(record.supplier_contact_person).toBe('张工')
  expect(record.supplier_id).toBeUndefined()
  record.supplier_contact_person='';changeOrderContact(record,suppliers)
  expect(record).toMatchObject({supplier_contact_person:'',contact_phone:''})
})


test('payment payee choices include all companies for the order contact and exclude other contacts',async()=>{
  const wrapper=mount(PaymentEntrySheet,{props:{record:{},order:{id:1,supplier_id:1,supplier_contact_person:'张工'},options:{suppliers},disabled:false},global:{stubs}})
  expect(wrapper.get('[aria-label="收款单位"]').findAll('option').map(o=>o.text())).toEqual(['甲公司','乙公司'])
  await wrapper.setProps({order:{id:2,supplier_id:3,supplier_contact_person:'李工'}})
  expect(wrapper.get('[aria-label="收款单位"]').findAll('option').map(o=>o.text())).toEqual(['丙公司'])
  await wrapper.setProps({order:undefined})
  expect(wrapper.get('[aria-label="收款单位"]').findAll('option')).toHaveLength(0)
  wrapper.unmount()
})
