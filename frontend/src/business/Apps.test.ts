// @vitest-environment jsdom
import {afterEach,expect,it} from 'vitest'
import {mount} from '@vue/test-utils'
import Apps from './Apps.vue'
import {session} from '../store'

const oldMenus=session.menus
afterEach(()=>{session.menus=oldMenus})

it('shows authorized desktop modules as mobile links and explains unknown menus',()=>{
 session.menus=[
  {id:1,title:'材料管理',children:[{id:2,title:'材料计划',href:'/view/material/planning'}]},
  {id:3,title:'苗圃管理',children:[{id:4,title:'苗圃库存',href:'/nursery/inventory'}]},
  {id:5,title:'系统管理',children:[{id:6,title:'数据备份',href:'/views/backup.html'},
   {id:7,title:'旧自定义页',href:'/old/custom'}]}
 ] as any
 const wrapper=mount(Apps,{global:{stubs:{RouterLink:{template:'<a><slot/></a>'},'van-search':true,
  'van-cell-group':{template:'<div><slot/></div>'},'van-cell':{props:['title','to','label'],template:'<a :href="to">{{title}} {{label}}</a>'},'van-empty':true}}})
 expect(wrapper.find('a[href="/material/planning"]').text()).toContain('材料计划')
 expect(wrapper.find('a[href="/nursery/inventory"]').text()).toContain('苗圃库存')
 expect(wrapper.find('a[href="/system/backup"]').text()).toContain('数据备份')
 expect(wrapper.find('a[href^="/unsupported?menu="]').text()).toContain('旧自定义页')
 expect(wrapper.text()).not.toContain('供应商管理')
 wrapper.unmount()
})
