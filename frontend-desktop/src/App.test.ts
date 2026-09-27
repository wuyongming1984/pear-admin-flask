// @vitest-environment jsdom
import {beforeEach,afterEach,expect,test,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {defineComponent,onBeforeUnmount} from 'vue'
import {createRouter,createMemoryHistory,onBeforeRouteLeave} from 'vue-router'
import ElementPlus from 'element-plus'
import App from './App.vue'
import {session,logout,invalidateIdentity} from './session'
vi.mock('./router',()=>({routes:[]}))
vi.mock('./components/LoginForm.vue',()=>({default:{template:'<div>FRESH LOGIN FORM</div>'}}))
vi.mock('./components/MenuBranch.vue',()=>({default:{template:'<div/>'}}))
let wrapper:any
beforeEach(()=>{logout();session.authenticated=true;session.loaded=true;session.userName='Account A';session.userId=1;session.menus=[{id:1,title:'Protected',href:'/protected-menu'}]})
afterEach(()=>{wrapper?.unmount();logout();window.innerWidth=1024})
async function setup(){const guard=vi.fn(()=>false),unmounted=vi.fn();const Protected=defineComponent({setup(){onBeforeRouteLeave(guard);onBeforeUnmount(unmounted);return()=> 'PRIVATE ACCOUNT A DRAFT'}});const router=createRouter({history:createMemoryHistory(),routes:[{path:'/protected',component:Protected,meta:{title:'Protected',menuPath:'/protected-menu'}},{path:'/forbidden',component:{template:'<p>FORBIDDEN</p>'},meta:{title:'No access'}},{path:'/',component:{template:'<p>HOME</p>'}}]});await router.push('/protected');await router.isReady();wrapper=mount(App,{global:{plugins:[router,ElementPlus]}});await flushPromises();return {router,guard,unmounted}}
test('external identity reset removes private cached UI even if old draft refuses navigation',async()=>{const {router,guard,unmounted}=await setup();expect(wrapper.text()).toContain('PRIVATE ACCOUNT A DRAFT');invalidateIdentity();await flushPromises();expect(wrapper.text()).not.toContain('PRIVATE ACCOUNT A DRAFT');expect(wrapper.text()).toContain('FRESH LOGIN FORM');expect(unmounted).toHaveBeenCalledOnce();expect(guard).not.toHaveBeenCalled();expect(router.currentRoute.value.path).toBe('/protected')})
test('revoked menu unmounts blocked editor before routing to forbidden',async()=>{const {router,guard,unmounted}=await setup();session.menus=[];session.viewVersion++;await flushPromises();expect(wrapper.text()).not.toContain('PRIVATE ACCOUNT A DRAFT');expect(unmounted).toHaveBeenCalledOnce();expect(router.currentRoute.value.path).toBe('/forbidden');expect(guard).not.toHaveBeenCalled()})

test('phone menu closes with Escape and cannot remain open after a desktop resize',async()=>{
 window.innerWidth=390;await setup()
 const toggle=wrapper.get('[aria-label="展开或收起菜单"]')
 expect(toggle.attributes('aria-expanded')).toBe('false')
 expect(wrapper.get('.sidebar').attributes('inert')).toBeDefined()
 await toggle.trigger('click');await flushPromises()
 expect(toggle.attributes('aria-expanded')).toBe('true')
 expect(wrapper.get('.sidebar').attributes('inert')).toBeUndefined()
 expect(wrapper.get('.workspace').attributes('inert')).toBeDefined()
 window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));await flushPromises()
 expect(toggle.attributes('aria-expanded')).toBe('false')
 await toggle.trigger('click')
 window.innerWidth=1280;window.dispatchEvent(new Event('resize'));await flushPromises()
 window.innerWidth=390;window.dispatchEvent(new Event('resize'));await flushPromises()
 expect(toggle.attributes('aria-expanded')).toBe('false')
 expect(wrapper.get('.workspace').attributes('inert')).toBeUndefined()
})
