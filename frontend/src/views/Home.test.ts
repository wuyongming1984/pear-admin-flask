// @vitest-environment jsdom
import {afterEach,expect,it,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import Home from './Home.vue'
import {session} from '../store'

const mocks=vi.hoisted(()=>({request:vi.fn()}))
vi.mock('../api',()=>({request:mocks.request}))
vi.mock('../components/RecordCard.vue',()=>({default:{template:'<div />'}}))

const previousMenus=session.menus
const previousUser=session.user
afterEach(()=>{session.menus=previousMenus;session.user=previousUser;vi.clearAllMocks()})

it('renders all authorized application modules directly on the mobile home',async()=>{
 session.user={username:'employee',nickname:'测试员工'} as any
 session.menus=[
  {id:1,title:'项目管理',href:'/project/info/project_info.html'},
  {id:2,title:'材料管理',children:[{id:3,title:'材料计划',href:'/view/material/planning'}]},
  {id:4,title:'苗圃管理',children:[{id:5,title:'苗圃库存',href:'/nursery/inventory'}]},
 ] as any
 mocks.request.mockResolvedValue({count:1,data:[]})
 const wrapper=mount(Home,{global:{stubs:{
  RouterLink:{props:['to'],template:'<a :href="to"><slot/></a>'},
  'van-icon':true,'van-loading':true,'van-button':true,'van-empty':true,
 }}})
 await flushPromises()
 expect(wrapper.find('section[aria-label="核心业务"] a[href="/projects"]').text()).toContain('项目管理')
 expect(wrapper.find('section[aria-label="材料管理"] a[href="/material/planning"]').text()).toContain('材料计划')
 expect(wrapper.find('section[aria-label="苗圃管理"] a[href="/nursery/inventory"]').text()).toContain('苗圃库存')
 expect(wrapper.find('a[href="/suppliers"]').exists()).toBe(false)
 expect(wrapper.find('a[href="/apps"]').text()).toContain('搜索应用')
 wrapper.unmount()
})
