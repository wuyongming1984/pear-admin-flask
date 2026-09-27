// @vitest-environment jsdom
import {expect,test,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {reactive,defineComponent} from 'vue'
import Portal from '../Portal.vue'
const mocked=vi.hoisted(()=>({request:vi.fn(),route:{params:{token:'supplier-token'}}}))
vi.mock('../../../api',()=>({request:mocked.request}))
vi.mock('vue-router',()=>({useRoute:()=>mocked.route}))
const stub=defineComponent({template:'<div><slot/><slot name="extra"/></div>'})
const global={stubs:{ElButton:stub,ElResult:stub,ElEmpty:stub},directives:{loading:()=>{}}}
beforeEach(()=>{vi.clearAllMocks();mocked.route=reactive({params:{token:'supplier-token'}})})
test('public reconciliation fetches only scoped token endpoint and renders scoped totals',async()=>{
 mocked.request.mockResolvedValue({code:0,data:{supplier:{name:'Scoped supplier',contact_person:'Contact'},analysis:{total_orders:'200',total_received:'50',outstanding_balance:'150'},grouped_orders:[],unlinked_payments:[]}})
 const wrapper=mount(Portal,{global});await flushPromises();expect(mocked.request).toHaveBeenCalledExactlyOnceWith('/portal/reconcile/supplier-token/data');expect(wrapper.text()).toContain('Scoped supplier');expect(wrapper.text()).toContain('150.00');wrapper.unmount()
})
test('changing to invalid token clears previously rendered supplier data',async()=>{
 mocked.request.mockResolvedValueOnce({code:0,data:{supplier:{name:'Secret supplier'},analysis:{},grouped_orders:[],unlinked_payments:[]}}).mockRejectedValueOnce(new Error('分享链接无效'))
 const wrapper=mount(Portal,{global});await flushPromises();expect(wrapper.text()).toContain('Secret supplier');mocked.route.params.token='invalid';await flushPromises();expect(mocked.request).toHaveBeenLastCalledWith('/portal/reconcile/invalid/data');expect(wrapper.text()).not.toContain('Secret supplier');expect((wrapper.vm as any).error).toBe('分享链接无效');wrapper.unmount()
})
