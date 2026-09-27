import type { RouteRecordRaw } from 'vue-router'
import Records from './Records.vue'
export const routes: RouteRecordRaw[] = [
  ...[
    ['users', '用户管理', '/system/user/index.html'], ['roles', '角色管理', '/system/role/index.html'],
    ['departments', '部门管理', '/system/department/index.html'], ['rights', '权限管理', '/system/rights/index.html'],
  ].map(([kind, title, menuPath]) => ({ path: `/system/${kind}`, component: Records, props: { kind }, meta: { title, menuPath } })),
  { path: '/system/dictionary', component: () => import('./Dictionary.vue'), meta: { title: '数据字典', menuPath: '/system/dictionary/index.html' } },
  { path: '/system/backup', component: () => import('./Backup.vue'), meta: { title: '数据备份', menuPath: '/system/backup/index.html' } },
  { path: '/profile', component: () => import('./Profile.vue'), meta: { title: '个人资料', menuPath: '', legacyMenuPath: '/view/system/person.html' } },
  { path: '/reconcile/:token', component: () => import('./Portal.vue'), meta: { title: '供应商对账单', menuPath: '', public: true } },
]
export default routes
