<script setup lang="ts">
import {ref,computed,watch,onBeforeUnmount}from 'vue';import {request,safeUrl}from '../api';import {ElMessageBox}from 'element-plus';
const props=withDefaults(defineProps<{modelValue:any[];kind?:string;readonly?:boolean;drag?:boolean}>(),{kind:'order'});const emit=defineEmits(['update:modelValue','busy','blocked']);
const input=ref<HTMLInputElement>();const queue=ref<{id:number;file:File;status:string;error:string}[]>([]);let next=0,disposed=false;
const busy=computed(()=>queue.value.some(x=>x.status==='uploading'||x.status==='queued'));const blocked=computed(()=>queue.value.some(x=>x.status==='failed'));
watch([busy,blocked],()=>{emit('busy',busy.value||blocked.value);emit('blocked',blocked.value)},{immediate:true,flush:'sync'});
const name=(x:any)=>x.original_filename||x.name||x.filename||'附件';const url=(x:any)=>safeUrl(x.preview_url||x.url||x.file_path);
async function upload(item:any){item.status='uploading';item.error='';try{if(item.file.size>10*1024*1024)throw Error('文件不能超过 10 MB');const body=new FormData();body.append('file',item.file);body.append('path',({orders:'order_attachments',payments:'pay_attachments',projects:'project_attachments'} as Record<string,string>)[props.kind]||`${props.kind}_attachments`);const r=await request('/upload/',{method:'POST',body});if(disposed)return;if(!r.data||!safeUrl(r.data.url||r.data.file_path))throw Error('上传结果缺少文件地址');emit('update:modelValue',[...props.modelValue,{...r.data,name:r.data.original_filename||item.file.name}]);queue.value=queue.value.filter(x=>x.id!==item.id)}catch(e){if(disposed)return;item.status='failed';item.error=(e as Error).message}}
async function enqueue(files:File[]){if(props.readonly||busy.value||disposed)return;for(const file of files)queue.value.push({id:++next,file,status:'queued',error:''});for(const item of queue.value.filter(x=>x.status==='queued')){if(disposed)break;await upload(item)}}
async function select(event:Event){const el=event.target as HTMLInputElement;const files=Array.from(el.files||[]);el.value='';await enqueue(files)}
const dragDepth=ref(0);
const canDrop=computed(()=>props.drag&&!props.readonly&&!busy.value);
const dragging=computed(()=>canDrop.value&&dragDepth.value>0);
watch(canDrop,()=>{dragDepth.value=0});
const hasFiles=(event:DragEvent)=>Array.from(event.dataTransfer?.types||[]).includes('Files');
function dragEnter(event:DragEvent){if(!props.drag||!hasFiles(event))return;event.preventDefault();event.stopPropagation();if(canDrop.value)dragDepth.value++}
function dragOver(event:DragEvent){if(!props.drag||!hasFiles(event))return;event.preventDefault();event.stopPropagation();if(event.dataTransfer)event.dataTransfer.dropEffect=canDrop.value?'copy':'none'}
function dragLeave(){dragDepth.value=Math.max(0,dragDepth.value-1)}
async function drop(event:DragEvent){dragDepth.value=0;if(!props.drag||!hasFiles(event))return;event.preventDefault();event.stopPropagation();if(canDrop.value)await enqueue(Array.from(event.dataTransfer?.files||[]))}
async function remove(index:number){try{await ElMessageBox.confirm('从当前记录移除此附件关联？文件本身不会删除。','移除附件',{type:'warning'});emit('update:modelValue',props.modelValue.filter((_,i)=>i!==index))}catch{}}
onBeforeUnmount(()=>{disposed=true;emit('busy',false);emit('blocked',false)});
</script>
<template>
  <section class="attachment-editor" :class="{'is-dragging':dragging}" @dragenter="dragEnter" @dragover="dragOver" @dragleave="dragLeave" @drop="drop">
    <div class="toolbar">
      <strong>附件 · {{modelValue.length}}</strong>
      <el-button v-if="!readonly" :disabled="busy" @click="input?.click()">选择文件</el-button>
      <input ref="input" type="file" multiple hidden :disabled="readonly||busy" @change="select">
    </div>
    <p v-if="drag&&!readonly" class="attachment-drop-hint" role="status">{{dragging?'松开鼠标即可上传文件':busy?'文件上传中，请稍候…':'将文件拖到此区域上传，支持一次拖入多个文件，也可点击“选择文件”。'}}</p>
    <p v-if="!readonly" class="muted">支持图片、PDF 和业务文件，单个文件不超过 10 MB。</p>
    <el-empty v-if="!modelValue.length&&!queue.length" :image-size="45" description="暂无附件"/>
    <div v-for="(file,i) in modelValue" :key="i" class="attachment-row">
      <el-image v-if="/\.(png|jpe?g|gif|webp)$/i.test(name(file))&&url(file)" :src="url(file)" :preview-src-list="[url(file)]" preview-teleported style="width:48px;height:48px" fit="cover"/>
      <a v-if="url(file)" :href="url(file)" target="_blank" rel="noopener noreferrer">{{name(file)}}</a>
      <span v-else>{{name(file)}}（地址不可用）</span>
      <el-button v-if="!readonly" text type="danger" @click="remove(i)">移除</el-button>
    </div>
    <div v-for="item in queue" :key="item.id" class="attachment-row">
      <span>{{item.file.name}}</span>
      <el-tag :type="item.status==='failed'?'danger':'info'">{{item.status==='failed'?'上传失败':'上传中'}}</el-tag>
      <span>{{item.error}}</span>
      <template v-if="item.status==='failed'">
        <el-button :disabled="busy" @click="upload(item)">重试</el-button>
        <el-button :disabled="busy" @click="queue=queue.filter(x=>x.id!==item.id)">移除失败项</el-button>
      </template>
    </div>
  </section>
</template>
<style scoped>
.attachment-editor { transition: border-color .15s, background-color .15s; }
.attachment-editor.is-dragging { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); outline: 2px solid var(--el-color-primary); outline-offset: -2px; }
.attachment-drop-hint { margin: 12px 0 8px; color: var(--el-color-primary); line-height: 1.6; }
</style>
