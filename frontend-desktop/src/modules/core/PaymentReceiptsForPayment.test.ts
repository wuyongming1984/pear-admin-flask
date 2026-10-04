// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {expect, it, vi} from 'vitest'
import PaymentReceiptsForPayment from './PaymentReceiptsForPayment.vue'
const mocks = vi.hoisted(() => ({request:vi.fn(),open:vi.fn()}))
vi.mock('../../api',()=>({request:mocks.request}))
it('opens the current payment and refreshes its receipt summary after association changes', async()=>{
 mocks.request.mockResolvedValue({data:[],count:0})
 const payment={id:7,pay_number:'F007',current_payment_amount:'100.00'}
 const wrapper=mount(PaymentReceiptsForPayment,{props:{paymentId:7,payment},global:{stubs:{'el-button':{template:'<button><slot/></button>'},RouterLink:{template:'<a><slot/></a>'},PaymentReceiptPicker:{name:'PaymentReceiptPicker',setup(_, {expose}){expose({open:mocks.open});return{}},template:'<div/>'}}}})
 await flushPromises()
 await wrapper.get('button[aria-label="关联付款回单"]').trigger('click')
 expect(mocks.open).toHaveBeenCalledWith([payment])
 mocks.request.mockResolvedValueOnce({data:[{id:8,receipt_number:'BANK008'}],count:1})
 wrapper.findComponent({name:'PaymentReceiptPicker'}).vm.$emit('changed')
 await flushPromises()
 expect(wrapper.text()).toContain('BANK008')
 wrapper.unmount()
})
