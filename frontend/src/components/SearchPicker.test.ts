// @vitest-environment jsdom
import {it,expect,vi} from 'vitest';
import {mount,flushPromises} from '@vue/test-utils';
import SearchPicker from './SearchPicker.vue';
import {request} from '../api';
vi.mock('../api',()=>({request:vi.fn().mockResolvedValue({data:[{id:1,project_name:'工程'}],count:1}),query:()=>''}));
it('loads options when first mounted already open',async()=>{
 const wrapper=mount(SearchPicker,{props:{show:true,title:'项目',source:'project'},global:{stubs:{'van-popup':{template:'<div><slot/></div>'},'van-search':true,'van-cell':true,'van-loading':true,'van-empty':true,'van-button':true}}});
 await flushPromises();expect(request).toHaveBeenCalledWith('/project/?');
 expect(wrapper.findAll('van-cell-stub')).toHaveLength(1);wrapper.unmount();
});
