import type {RouteRecordRaw} from 'vue-router'
import {schemas} from './model'
const routes:RouteRecordRaw[]=[]
for(const [kind,schema] of Object.entries(schemas)){
 for(const [suffix,mode] of [['','list'],['/new','new'],['/:id','detail'],['/:id/edit','edit']])routes.push({path:`/${kind}${suffix}`,component:()=>import('./CorePage.vue'),meta:{title:schema.title,menuPath:schema.menu,coreKind:kind,coreMode:mode}})
 if(['orders','payments'].includes(kind))routes.push({path:`/${kind}/:id/print`,component:()=>import('./PrintPage.vue'),meta:{title:schema.title+'打印',menuPath:schema.menu,coreKind:kind}})
}
export default routes
