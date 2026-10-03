import {mobileWorkbenchHref} from '../../../frontend-shared/business/navigation';
export interface MenuItem{id:number|string;title:string;href?:string;children?:MenuItem[];type?:number;[key:string]:any}
const aliases:Record<string,string>={'/views/user.html':'/system/user/index.html','/views/role.html':'/system/role/index.html','/views/department.html':'/system/department/index.html','/system/views/backup.html':'/views/backup.html','/system/backup/index.html':'/views/backup.html','/system/dictionary/index.html':'/system/dictionary/'};
export function normalizePath(path:string){const p='/'+path.replace(/^\/+/, '');return aliases[p]||p}
export function flattenMenus(items:MenuItem[]):MenuItem[]{return items.flatMap(item=>[item,...flattenMenus(item.children||[])])}
export function allowedMenu(path:string|undefined,menus:MenuItem[]){return !path||flattenMenus(menus).some(item=>item.href&&normalizePath(item.href)===normalizePath(path))}
export function routeForMenu(item:MenuItem[],routes:{path:string;meta?:any}[]){const map=new Map<string,string>();for(const route of routes){if((route.meta?.menuPath||route.meta?.legacyMenuPath)&&!route.path.includes(':')){const key=normalizePath(route.meta.menuPath||route.meta.legacyMenuPath);if(!map.has(key))map.set(key,route.path)}}return function(entry:MenuItem){if(mobileWorkbenchHref(entry))return '/';return entry.href?map.get(normalizePath(entry.href))||`/unsupported?menu=${encodeURIComponent(entry.title)}&url=${encodeURIComponent(entry.href)}`:`/unsupported?menu=${encodeURIComponent(entry.title)}`}}

export interface ApplicationEntry extends MenuItem { path:string }
export interface ApplicationGroup { key:string; title:string; icon:string; entries:ApplicationEntry[] }
const applicationSections=[
 {key:'workspace',title:'工作空间',icon:'chart-trending-o'},
 {key:'business',title:'核心业务',icon:'orders-o'},
 {key:'material',title:'材料管理',icon:'apps-o'},
 {key:'nursery',title:'苗圃管理',icon:'cluster-o'},
 {key:'system',title:'系统管理',icon:'setting-o'},
 {key:'other',title:'其他应用',icon:'ellipsis'},
]
function applicationSection(path:string){
 if(path==='/')return 'workspace'
 if(/^\/(overview|workspace|analysis)(\/|$)/.test(path))return 'workspace'
 if(/^\/(projects|orders|payments|suppliers|payers|invoices)(\/|$)/.test(path))return 'business'
 if(path.startsWith('/material/'))return 'material'
 if(path.startsWith('/nursery/'))return 'nursery'
 if(path.startsWith('/system/')||path==='/profile')return 'system'
 return 'other'
}
export function applicationGroups(menus:MenuItem[],routes:{path:string;meta?:any}[],search=''):ApplicationGroup[]{
 const resolve=routeForMenu([],routes)
 const term=search.trim().toLocaleLowerCase()
 const groups=applicationSections.map(section=>({...section,entries:[] as ApplicationEntry[]}))
 for(const menu of flattenMenus(menus)){
  if(!menu.href&&!mobileWorkbenchHref(menu))continue
  const path=resolve(menu)
  const group=groups.find(section=>section.key===applicationSection(path))!
  if(term&&!group.title.toLocaleLowerCase().includes(term)&&!menu.title.toLocaleLowerCase().includes(term))continue
  group.entries.push({...menu,path})
 }
 return groups.filter(group=>group.entries.length)
}
