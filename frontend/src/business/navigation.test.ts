// @vitest-environment jsdom
import{it,expect}from'vitest';import{allowedMenu,routeForMenu,applicationGroups}from'./navigation';
import routes from './routes';
it('maps aliases but never grants missing menu access',()=>{const menus=[{id:1,title:'system',children:[{id:2,title:'字典',href:'/system/dictionary/'}]}];expect(allowedMenu('/system/dictionary/index.html',menus)).toBe(true);expect(allowedMenu('/views/user.html',menus)).toBe(false)});
it('unknown menus remain visible with explicit explanation route',()=>{const resolve=routeForMenu([],[{path:'/system/users',meta:{menuPath:'/system/user/index.html'}}]);expect(resolve({id:1,title:'用户',href:'/views/user.html'})).toBe('/system/users');expect(resolve({id:2,title:'未知模块',href:'/old/custom'})).toContain('/unsupported?menu=')});

it('maps own profile menu independently of role grants',()=>{const resolve=routeForMenu([],[{path:'/profile',meta:{menuPath:'',legacyMenuPath:'/view/system/person.html'}}]);expect(resolve({id:1,title:'个人中心',href:'/view/system/person.html'})).toBe('/profile');expect(allowedMenu('',[])).toBe(true)});

it('opens every current desktop business menu in a native mobile page',()=>{
 const currentMenus=[
  '/view/console/index.html','/view/analysis/index.html',
  '/project/info/project_info.html','/order_pay/base/order_base.html','/order_pay/base/pay_base.html',
  '/supplier/info/supplier_info.html','/payer/info/payer_info.html','/view/material/invoice',
  '/system/user/index.html','/system/role/index.html','/system/department/index.html','/system/rights/index.html',
  '/system/dictionary/','/view/system/person.html','/views/backup.html',
  ...['dashboard','planning','inbound','inventory','outbound','outbound_records'].map(x=>`/view/material/${x}`),
  ...['dashboard','inventory','inbound','outbound','orders','transactions','logs','settings'].map(x=>`/nursery/${x}`)
 ];
 const resolve=routeForMenu([],routes);
 for(const href of currentMenus){const path=resolve({id:href,title:href,href});expect(path,href).not.toContain('/unsupported');expect(routes.some(route=>route.path===path),href).toBe(true)}
});

it('groups only authorized application links for the mobile home',()=>{
 const menus=[
  {id:1,title:'项目',href:'/project/info/project_info.html'},
  {id:2,title:'材料管理',children:[{id:3,title:'材料计划',href:'/view/material/planning'}]},
  {id:4,title:'苗圃管理',children:[{id:5,title:'苗圃库存',href:'/nursery/inventory'}]},
  {id:6,title:'系统管理',children:[{id:7,title:'数据备份',href:'/views/backup.html'}]},
  {id:8,title:'旧菜单',href:'/old/custom'},
 ];
 const groups=applicationGroups(menus,routes);
 expect(groups.map(group=>group.title)).toEqual(['核心业务','材料管理','苗圃管理','系统管理','其他应用']);
 expect(groups.flatMap(group=>group.entries.map(entry=>entry.path))).toEqual([
  '/projects','/material/planning','/nursery/inventory','/system/backup',
  expect.stringContaining('/unsupported?menu=')
 ]);
 expect(groups.flatMap(group=>group.entries.map(entry=>entry.title))).not.toContain('供应商管理');
 expect(applicationGroups(menus,routes,'苗圃').map(group=>group.title)).toEqual(['苗圃管理']);
});
