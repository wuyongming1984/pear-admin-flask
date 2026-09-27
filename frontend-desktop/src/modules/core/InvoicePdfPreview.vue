<script setup lang="ts">
import {onBeforeUnmount, ref, watch} from 'vue'
import {request} from '../../api'

const props=defineProps<{invoiceId:string|number}>()
type Preview={image:string;page:number;page_count:number}
const page=ref(1),count=ref(0),image=ref(''),busy=ref(false),error=ref('')
const cache=new Map<number,Preview>()
let revision=0,controller:AbortController|undefined,timer:ReturnType<typeof setTimeout>|undefined
function cancel(){revision++;controller?.abort();clearTimeout(timer)}
async function load(target:number){
 cancel()
 const current=revision
 page.value=target;image.value='';error.value='';busy.value=true
 try{
  let data=cache.get(target)
  if(!data){
   controller=new AbortController()
   timer=setTimeout(()=>controller?.abort(),30000)
   const response=await request<Preview>(`/material/invoice/${encodeURIComponent(props.invoiceId)}/preview-page?page=${target}`,{signal:controller.signal})
   if(current!==revision)return
   data=response.data
   if(!data?.image?.startsWith('data:image/png;base64,')||data.page!==target||!Number.isInteger(data.page_count)||data.page_count<target)throw new Error('原文件预览返回异常，请重试。')
   if(cache.size>=5)cache.delete(cache.keys().next().value!)
   cache.set(target,data)
  }
  image.value=data.image;count.value=data.page_count
 }catch(e){if(current===revision)error.value=e instanceof Error?e.message:'原文件加载失败，请重试。'}
 finally{if(current===revision){busy.value=false;clearTimeout(timer)}}
}
watch(()=>props.invoiceId,()=>{cache.clear();count.value=0;void load(1)},{immediate:true})
onBeforeUnmount(cancel)
</script>

<template>
 <div class="pdf-preview" aria-label="PDF原文件预览" :aria-busy="busy">
  <div v-if="count>1" class="pdf-pagination">
   <el-button :disabled="busy||page<=1" @click="load(page-1)">上一页原文件</el-button>
   <span>第 {{page}} / {{count}} 页</span>
   <el-button :disabled="busy||page>=count" @click="load(page+1)">下一页原文件</el-button>
  </div>
  <p v-if="busy" class="pdf-status" role="status">正在加载原文件…</p>
  <div v-else-if="error" class="pdf-status"><p role="alert">{{error}}</p><el-button @click="load(page)">重试加载</el-button></div>
  <img v-else-if="image" class="pdf-page" :src="image" :alt="`发票 PDF 原文件，第 ${page} 页`" @error="error='预览图片加载失败，请重试。';cache.delete(page)" />
 </div>
</template>

<style scoped>
.pdf-preview{min-height:180px;background:#f3f3f3;border:1px solid var(--el-border-color,#ddd);padding:12px}.pdf-page{display:block;width:100%;height:auto;margin:0 auto;background:#fff}.pdf-pagination{display:flex;justify-content:center;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;font-size:13px}.pdf-status{text-align:center;padding:35px 12px;color:var(--el-text-color-secondary)}[role=alert]{color:var(--el-color-danger)}
</style>
