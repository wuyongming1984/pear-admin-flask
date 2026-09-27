import type {RouteRecordRaw} from 'vue-router'
const material={dashboard:'材料看板',planning:'材料策划',inbound:'材料入库',inventory:'材料库存',outbound:'材料出库',outbound_records:'出库记录'}
const nursery={dashboard:'苗圃看板',inventory:'苗圃库存',inbound:'苗木入库',outbound:'苗木出库',orders:'苗圃出库单',logs:'苗圃日志',history:'苗圃流水',transactions:'苗圃流水',settings:'苗圃设置'}
export const routes:RouteRecordRaw[]=[...Object.entries(material).map(([view,title])=>({path:`/material/${view}`,component:()=>import('./Material.vue'),props:{view},meta:{title,menuPath:`/view/material/${view}`}})),...Object.entries(nursery).map(([view,title])=>({path:`/nursery/${view}`,component:()=>import('./Nursery.vue'),props:{view},meta:{title,menuPath:`/nursery/${['history','transactions'].includes(view)?'transactions':view}`}}))]
export default routes

