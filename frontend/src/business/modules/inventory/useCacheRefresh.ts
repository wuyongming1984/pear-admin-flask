import {onActivated,onDeactivated} from 'vue'
/** Initial loading is owned by the view; every subsequent cache activation refreshes server state. */
export function useCacheRefresh(refresh:()=>void|Promise<void>){
 let revisiting=false
 onDeactivated(()=>{revisiting=true})
 onActivated(()=>{if(revisiting){revisiting=false;void refresh()}})
}
