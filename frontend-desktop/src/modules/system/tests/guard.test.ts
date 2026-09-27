// @vitest-environment jsdom
import {beforeEach,expect,test,vi} from 'vitest'
import {mount} from '@vue/test-utils'
import {defineComponent,ref} from 'vue'
import {useSystemDraft} from '../useSystemDraft'
const mocks=vi.hoisted(()=>({confirm:vi.fn(),warning:vi.fn(),leave:vi.fn(),update:vi.fn()}))
vi.mock('element-plus',()=>({ElMessage:{warning:mocks.warning},ElMessageBox:{confirm:mocks.confirm}}))
vi.mock('vue-router',()=>({onBeforeRouteLeave:mocks.leave,onBeforeRouteUpdate:mocks.update}))
function setup(dirtyValue=true){const dirty=ref(dirtyValue),busy=ref(false),discard=vi.fn(()=>dirty.value=false);let guard:any;const wrapper=mount(defineComponent({setup(){guard=useSystemDraft(dirty,busy,discard);return()=>null}}));return {dirty,busy,discard,wrapper,get guard(){return guard}}}
beforeEach(()=>{vi.clearAllMocks();mocks.confirm.mockResolvedValue('confirm')})
test('route leave cancellation preserves dirty draft and accepted discard resets it',async()=>{const state=setup();mocks.confirm.mockRejectedValueOnce('cancel');expect(await mocks.leave.mock.calls[0][0]()).toBe(false);expect(state.discard).not.toHaveBeenCalled();expect(state.dirty.value).toBe(true);expect(await mocks.update.mock.calls[0][0]()).toBe(true);expect(state.discard).toHaveBeenCalledOnce();state.wrapper.unmount()})
test('busy submission blocks dialog dismissal without prompting or discarding',async()=>{const state=setup();state.busy.value=true;const done=vi.fn();await state.guard.beforeClose(done);expect(done).not.toHaveBeenCalled();expect(state.discard).not.toHaveBeenCalled();expect(mocks.confirm).not.toHaveBeenCalled();state.wrapper.unmount()})
test('clean forms navigate without discard prompt',async()=>{const state=setup(false);expect(await state.guard.allowDiscard()).toBe(true);expect(mocks.confirm).not.toHaveBeenCalled();state.wrapper.unmount()})
test('dirty drafts prevent browser unload and remove listener after unmount',()=>{const state=setup();const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event);expect(event.defaultPrevented).toBe(true);state.wrapper.unmount();const after=new Event('beforeunload',{cancelable:true});window.dispatchEvent(after);expect(after.defaultPrevented).toBe(false)})
