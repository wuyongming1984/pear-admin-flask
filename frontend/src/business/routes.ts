import core from './modules/core/routes';
import inventory from './modules/inventory/routes';
import system from './modules/system/routes';
export default [...[['/overview','/view/analysis/index.html'],['/analysis','/view/analysis/index.html'],['/workspace','/view/console/index.html']].map(([path,menuPath])=>({path,component:()=>import('./Overview.vue'),meta:{menuPath,title:'经营概览'}})),...core,...inventory,...system,{path:'/material/invoice',redirect:'/invoices'}];
