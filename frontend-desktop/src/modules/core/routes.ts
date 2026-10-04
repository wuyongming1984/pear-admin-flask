import type {RouteRecordRaw} from 'vue-router'
import {schemas} from './model'
const routes:RouteRecordRaw[]=[]
routes.push({path:'/payment-receipts',component:()=>import('./ReceiptLibrary.vue'),meta:{title:'付款回单库',menuPath:'/view/payment-receipts'}})
for(const [kind,schema] of Object.entries(schemas)){
 for(const [suffix,mode] of [['','list'],['/new','new'],['/:id','detail'],['/:id/edit','edit']])routes.push({path:`/${kind}${suffix}`,component:mode==='list'&&kind==='orders'?()=>import('./OrdersWorkspace.vue'):mode==='list'&&kind==='payments'?()=>import('./PaymentsWorkspace.vue'):()=>import('./CorePage.vue'),meta:{title:schema.title,menuPath:schema.menu,coreKind:kind,coreMode:mode}})
 if(['orders','payments'].includes(kind))routes.push({path:`/${kind}/:id/print`,component:()=>import('./PrintPage.vue'),meta:{title:schema.title+'打印',menuPath:schema.menu,coreKind:kind}})
}
export default routes
