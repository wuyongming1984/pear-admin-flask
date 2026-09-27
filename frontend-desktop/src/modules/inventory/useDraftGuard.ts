import {onBeforeUnmount,onMounted,onActivated,onDeactivated,type ComputedRef,type Ref} from 'vue'
import {onBeforeRouteLeave,onBeforeRouteUpdate} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
export function useDraftGuard(dirty:ComputedRef<boolean>,busy?:Ref<boolean>){
 let active=true
 async function allowDiscard(){if(busy?.value){ElMessage.warning('正在提交，请等待结果');return false}if(!dirty.value)return true;try{await ElMessageBox.confirm('有尚未保存的修改，确认放弃？','未保存的修改',{type:'warning',confirmButtonText:'放弃修改',cancelButtonText:'继续编辑'});return true}catch{return false}}
 const guard=()=>allowDiscard();onBeforeRouteLeave(guard);onBeforeRouteUpdate(guard)
 const unload=(event:BeforeUnloadEvent)=>{if(active&&(dirty.value||busy?.value)){event.preventDefault();event.returnValue=''}}
 onMounted(()=>window.addEventListener('beforeunload',unload));onBeforeUnmount(()=>window.removeEventListener('beforeunload',unload))
 onActivated(()=>active=true);onDeactivated(()=>active=false)
 return allowDiscard
}
