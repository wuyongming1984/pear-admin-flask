// @vitest-environment jsdom
import {expect,it} from 'vitest';
import {mount,flushPromises} from '@vue/test-utils';
import {createRouter,createMemoryHistory} from 'vue-router';
import ElementPlus,{ElMenu} from 'element-plus';
import MenuBranch from './MenuBranch.vue';
import {routeForMenu} from '../navigation';

it('uses a native mobile link while keeping business menu navigation in the desktop router',async()=>{
 const routes=[
  {path:'/',component:{template:'<p>Overview</p>'}},
  {path:'/orders',component:{template:'<p>Orders</p>'},meta:{menuPath:'/order_pay/base/order_base.html'}}
 ];
 const router=createRouter({history:createMemoryHistory(),routes});
 await router.push('/');await router.isReady();
 const wrapper=mount({components:{ElMenu,MenuBranch},setup:()=>({
  items:[{id:124,title:'工作空间',children:[{id:155,title:'移动端工作台',href:'/m/'}]},
   {id:132,title:'订单',href:'/order_pay/base/order_base.html'}],
  resolve:routeForMenu([],routes)
 }),template:'<el-menu router :default-openeds="[\'group-124\']"><MenuBranch :items="items" :resolve="resolve"/></el-menu>'},{global:{plugins:[router,ElementPlus]}});
 try{
  const link=wrapper.get('a[href="/m/"]');
  expect(link.text()).toContain('移动端工作台');
  expect(link.attributes('target')).toBe('_blank');
  expect(link.attributes('rel')).toContain('noopener');
  await link.trigger('click');await flushPromises();
  expect(router.currentRoute.value.path).toBe('/');
  const order=wrapper.findAll('.el-menu-item').find(item=>item.text()==='订单')!;
  await order.trigger('click');await flushPromises();
  expect(router.currentRoute.value.path).toBe('/orders');
 }finally{wrapper.unmount()}
});
