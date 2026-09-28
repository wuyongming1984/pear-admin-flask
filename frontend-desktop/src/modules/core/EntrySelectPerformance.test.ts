// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {it, expect, vi} from 'vitest'
import ElementPlus, {ElOption} from 'element-plus'
import PaymentEntrySheet from './PaymentEntrySheet.vue'
import OrderEntrySheet from './OrderEntrySheet.vue'

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
it.each([OrderEntrySheet, PaymentEntrySheet])('keeps large editor dropdowns from mounting every option', async(component) => {
  const choices = Array.from({length: 600}, (_, i) => ({id:i+1,value:i+1,label:`项目${i}`,project_name:`项目${i}`,contact_person:`联系人${i}`,name:`单位${i}`}))
  const wrapper = mount(component, {props:{record:{},options:{projects:choices,orders:choices,suppliers:choices,payers:choices,materials:[],statuses:[]},disabled:false},global:{plugins:[ElementPlus],stubs:{RouterLink:true}}})
  try {
    await flushPromises()
    expect(wrapper.findAllComponents(ElOption).length).toBeLessThan(40)
  } finally {wrapper.unmount()}
})
