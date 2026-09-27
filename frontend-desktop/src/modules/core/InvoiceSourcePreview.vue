<script setup lang="ts">
import {computed, onBeforeUnmount, ref, shallowRef, watch} from 'vue'
import {request, safeUrl} from '../../api'
import type {Row} from './model'

const props=defineProps<{invoice:Row}>()
const root=ref<HTMLElement>(),source=shallowRef<Row>({})
const refreshing=ref(false),loadFailed=ref(false),error=ref(''),version=ref(0)
let revision=0
watch(()=>[props.invoice.id,props.invoice.file_url,props.invoice.file_path,props.invoice.file_type,props.invoice.file_name],()=>{
 revision++;source.value={...props.invoice};refreshing.value=false;loadFailed.value=false;error.value='';version.value++
},{immediate:true})
onBeforeUnmount(()=>{revision++})
// file_url includes the backend's authorization signature for private objects.
const url=computed(()=>safeUrl(source.value.file_url || source.value.file_path))
const fileKind=computed(()=>{
 const type=String(source.value.file_type||'').toLowerCase().replace(/^\./,'')
 const name=String(source.value.file_name||'').toLowerCase()
 const path=url.value?new URL(url.value,location.origin).pathname.toLowerCase():''
 if(['pdf','application/pdf'].includes(type)||/\.pdf$/.test(name||path))return 'pdf'
 if(['jpg','jpeg','png','webp','gif','image/jpeg','image/png','image/webp','image/gif'].includes(type)||/\.(png|jpe?g|webp|gif)$/.test(name||path))return 'image'
 return 'other'
})
async function refresh(){
 if(refreshing.value||!props.invoice.id)return
 const current=++revision
 refreshing.value=true;error.value=''
 try{
  const response=await request(`/material/invoice?id=${encodeURIComponent(props.invoice.id)}`)
  if(current!==revision)return
  const invoice=response.data?.find((row:Row)=>String(row.id)===String(props.invoice.id))
  if(!invoice)throw new Error('未找到此发票，请刷新发票清单。')
  source.value=invoice;version.value++;loadFailed.value=false
 }catch(e){if(current===revision)error.value=e instanceof Error?e.message:'原文件加载失败，请重试。'}
 finally{if(current===revision)refreshing.value=false}
}
function scrollToPreview(){root.value?.scrollIntoView({behavior:'smooth',block:'start'})}
defineExpose({scrollToPreview})
</script>

<template>
 <section ref="root" class="invoice-source" aria-label="发票原文件">
  <header>
   <div><h3>发票原文件</h3><span v-if="source.file_name" class="source-name">{{source.file_name}}</span></div>
   <div class="source-actions">
    <el-button v-if="source.file_url || source.file_path" :loading="refreshing" @click="refresh">刷新预览</el-button>
    <a v-if="url" :href="url" target="_blank" rel="noopener noreferrer">在新窗口打开</a>
   </div>
  </header>
  <p v-if="error" class="source-error" role="alert">{{error}}</p>
  <el-empty v-if="!url" description="此发票尚未上传原文件" :image-size="70" />
  <p v-else-if="loadFailed" class="source-error" role="alert">原文件暂时无法加载，请点击“刷新预览”重试，或在新窗口打开。</p>
  <object v-else-if="fileKind==='pdf'" :key="`${source.id}-${version}`" :data="url" type="application/pdf" class="source-pdf" aria-label="PDF原文件预览" @error="loadFailed=true">
   <p>浏览器无法嵌入此 PDF，请<a :href="url" target="_blank" rel="noopener noreferrer">在新窗口打开原文件</a>，或点击“刷新预览”重试。</p>
  </object>
  <img v-else-if="fileKind==='image'" :key="`${source.id}-${version}`" :src="url" :alt="source.file_name || '发票原文件图片'" class="source-image" @error="loadFailed=true" />
  <p v-else>此文件格式暂不支持直接预览，请使用上方链接打开原文件。</p>
 </section>
</template>

<style scoped>
.invoice-source{max-width:1100px;margin:24px auto 0;background:var(--el-bg-color,#fff);border:1px solid var(--el-border-color,#ddd);border-radius:6px;padding:20px;scroll-margin-top:16px}
header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px}h3{margin:0 0 6px;font-size:16px}.source-name{font-size:12px;color:var(--el-text-color-secondary);overflow-wrap:anywhere}.source-actions{display:flex;align-items:center;gap:14px;flex-shrink:0;font-size:13px}.source-pdf{display:block;width:100%;height:720px;min-height:480px;border:1px solid var(--el-border-color,#ddd);background:#f3f3f3}.source-image{display:block;width:auto;max-width:100%;height:auto;margin:0 auto}.source-error{color:var(--el-color-danger,#c43b3b);font-size:14px;line-height:1.6}
@media(max-width:760px){.invoice-source{padding:12px}.source-pdf{height:600px}.source-actions{flex-wrap:wrap}}
</style>
