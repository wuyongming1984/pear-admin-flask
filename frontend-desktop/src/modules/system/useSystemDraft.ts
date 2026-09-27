import {onMounted,onBeforeUnmount,onActivated,onDeactivated,type Ref} from 'vue'
import {onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
/** One guard for explicit cancel, navigation and reload. No network requests here. */
export function useSystemDraft(dirty:Ref<boolean>,busy:Ref<boolean>,discard:()=>void){
 let active=true
 async function allowDiscard(){
  if(busy.value){ElMessage.warning('正在提交，请等待结果后继续');return false}
  if(dirty.value){try{await ElMessageBox.confirm('有未保存的修改，确定放弃？','未保存的修改',{type:'warning',confirmButtonText:'放弃修改',cancelButtonText:'继续编辑'})}catch{return false}}
  discard();return true
 }
 const unload=(event:BeforeUnloadEvent)=>{if(active&&(dirty.value||busy.value)){event.preventDefault();event.returnValue=''}}
 onBeforeRouteLeave(allowDiscard);onBeforeRouteUpdate(allowDiscard)
 onMounted(()=>window.addEventListener('beforeunload',unload));onBeforeUnmount(()=>window.removeEventListener('beforeunload',unload));onActivated(()=>active=true);onDeactivated(()=>active=false)
 return {allowDiscard, beforeClose:async(done:()=>void)=>{if(await allowDiscard())done()}}
}
