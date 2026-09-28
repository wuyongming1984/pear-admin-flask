<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {UploadFilled, Document} from '@element-plus/icons-vue'
import {request} from '../../api'
import type {Row} from './model'
import InvoicePaymentLinks from './InvoicePaymentLinks.vue'

const props = defineProps<{modelValue: boolean; projects: Row[]; disabled?: boolean}>()
const emit = defineEmits<{'update:modelValue': [value: boolean]; busy: [value: boolean]; uploaded: []}>()
const picker = ref<HTMLInputElement>()
const files = ref<File[]>([])
const project = ref<number | string>()
const uploading = ref(false), dragDepth = ref(0), warning = ref(''), error = ref('')
const linking = ref<Array<number | string>>([])
const activeBusy = computed(() => uploading.value || linking.value.length > 0)
watch(activeBusy, value => emit('busy', value), {flush: 'sync'})
function linkBusy(id: number | string, value: boolean) {
  linking.value = linking.value.filter(item => item !== id)
  if (value) linking.value.push(id)
}
const report = ref<{uploaded: number; failed: number; invoices: Row[]; errors: Row[]} | null>(null)
const locked = computed(() => activeBusy.value || props.disabled)
watch(() => props.modelValue, () => { dragDepth.value = 0 })
const fileKey = (file: File) => `${file.name}:${file.size}:${file.lastModified}`
function addFiles(incoming: File[]) {
  if (locked.value) return
  const rejected: string[] = []
  let added = false
  for (const file of incoming) {
    if (!/\.(pdf|png|jpe?g)$/i.test(file.name) || !file.size) { rejected.push(file.name); continue }
    if (!files.value.some(item => fileKey(item) === fileKey(file))) { files.value.push(file); added = true }
  }
  warning.value = rejected.length ? `不支持的格式或空文件：${rejected.join('、')}。请选择 PDF、JPG 或 PNG 发票。` : ''
  if (added) { report.value = null; error.value = '' }
}
function choose(event: Event) {
  const input = event.target as HTMLInputElement
  addFiles(Array.from(input.files || []))
  input.value = ''
}
function drop(event: DragEvent) {
  dragDepth.value = 0
  addFiles(Array.from(event.dataTransfer?.files || []))
}
function close() { if (!activeBusy.value) emit('update:modelValue', false) }
function remove(index: number) { if (!locked.value) files.value.splice(index, 1) }
function sizeLabel(size: number) { return size < 1024 * 1024 ? `${Math.ceil(size / 1024)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB` }
async function upload() {
  if (locked.value || !files.value.length) return
  uploading.value = true; error.value = ''; warning.value = ''; report.value = null
  try {
    const data = new FormData()
    for (const file of files.value) data.append('files', file)
    if (project.value) data.append('project_id', String(project.value))
    data.append('path', 'invoices')
    const response = await request('/material/invoice/upload', {method: 'POST', body: data})
    report.value = response.data
    files.value = []
    emit('uploaded')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '上传失败，请稍后重试'
  } finally { uploading.value = false }
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="新增发票 / 上传识别" width="640px" class="invoice-upload-dialog" append-to-body
    :close-on-click-modal="false" :close-on-press-escape="!activeBusy" :show-close="!activeBusy" :before-close="close" @update:model-value="close">
    <div class="invoice-upload-body" @dragover.prevent @drop.prevent>
      <p class="upload-intro">上传发票后自动识别票面信息，并加入发票清单。</p>
      <el-form label-position="top">
        <el-form-item label="所属项目（选填）">
          <el-select v-model="project" aria-label="所属项目" clearable filterable placeholder="选择发票所属项目" :disabled="locked">
            <el-option v-for="item in projects" :key="item.id" :value="item.id" :label="item.label" />
          </el-select>
        </el-form-item>
      </el-form>
      <input ref="picker" class="file-picker" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" aria-label="选择发票文件" :disabled="locked" @change="choose" />
      <button type="button" class="invoice-dropzone" :class="{dragging: dragDepth > 0}" data-testid="invoice-dropzone" :disabled="locked"
        @click="picker?.click()" @dragenter.prevent="!locked && dragDepth++" @dragleave.prevent="dragDepth = Math.max(0, dragDepth - 1)" @dragover.prevent @drop.prevent.stop="drop">
        <UploadFilled class="upload-icon" aria-hidden="true" />
        <strong>{{dragDepth ? '松开鼠标，添加发票' : '将发票拖拽到这里'}}</strong>
        <span>或 <b>点击选择文件</b></span>
        <small>支持 PDF、JPG、PNG，可一次选择多张发票</small>
      </button>
      <p v-if="warning" class="upload-warning" role="alert">{{warning}}</p>
      <template v-if="files.length">
        <div class="queue-heading"><strong>待上传 {{files.length}} 张</strong><el-button link :disabled="locked" @click="files = []">清空</el-button></div>
        <ul class="upload-files" aria-label="待上传发票">
          <li v-for="(file, index) in files" :key="fileKey(file)">
            <Document class="file-icon" aria-hidden="true" /><span class="file-name">{{file.name}}</span><small>{{sizeLabel(file.size)}}</small>
            <el-button link type="danger" :aria-label="`移除 ${file.name}`" :disabled="locked" @click="remove(index)">移除</el-button>
          </li>
        </ul>
      </template>
      <div v-if="uploading" class="upload-progress" role="status" aria-live="polite">正在上传并识别 {{files.length}} 张发票，请稍候…</div>
      <p v-if="error" class="upload-error" role="alert">{{error}}</p>
      <section v-if="report" class="upload-results" aria-label="上传结果" aria-live="polite">
        <h3>上传成功 {{report.uploaded}} 张<span v-if="report.failed"> · 未导入 {{report.failed}} 张</span></h3>
        <ul>
          <li v-for="item in report.invoices" :key="item.id" :class="item.ocr_status === 'success' ? 'result-success' : 'result-warning'">
            <strong>{{item.file_name}}</strong><span>{{item.ocr_status === 'success' ? '识别成功，已加入发票清单' : '已上传，识别未完成，请在详情中重新识别'}}</span>
            <InvoicePaymentLinks :invoice-id="item.id" :disabled="locked" @busy="linkBusy(item.id, $event)" @changed="emit('uploaded')" />
          </li>
          <li v-for="(item, index) in report.errors" :key="index" class="result-warning"><strong>{{item.name}}</strong><span>{{item.reason}}</span></li>
        </ul>
      </section>
    </div>
    <template #footer>
      <el-button data-testid="invoice-upload-close" :disabled="activeBusy" @click="close">{{report ? '完成' : '取消'}}</el-button>
      <el-button type="primary" data-testid="invoice-upload-submit" :loading="uploading" :disabled="locked || !files.length" @click="upload">{{uploading ? '正在识别…' : `开始上传并识别${files.length ? `（${files.length} 张）` : ''}`}}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.invoice-upload-body{max-height:65vh;overflow-y:auto;padding:0 4px;color:var(--el-text-color-primary)}
.upload-intro{margin:0 0 20px;color:var(--el-text-color-secondary);line-height:1.6}
.file-picker{display:none}.invoice-dropzone{width:100%;min-height:190px;border:1.5px dashed var(--el-border-color-darker);border-radius:10px;background:var(--el-fill-color-lighter);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:10px;color:var(--el-text-color-regular);font:inherit;cursor:pointer;transition:background .15s,border-color .15s}
.invoice-dropzone:hover,.invoice-dropzone.dragging,.invoice-dropzone:focus-visible{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}
.invoice-dropzone:focus-visible{outline:2px solid var(--el-color-primary);outline-offset:3px}.invoice-dropzone:disabled{cursor:wait;opacity:.65}
.upload-icon{width:42px;height:42px;color:var(--el-color-primary)}.invoice-dropzone strong{font-size:17px}.invoice-dropzone b{color:var(--el-color-primary)}.invoice-dropzone small{color:var(--el-text-color-secondary);font-size:12px}
.queue-heading{display:flex;align-items:center;justify-content:space-between;margin-top:18px}.upload-files,.upload-results ul{list-style:none;margin:8px 0 0;padding:0}
.upload-files{max-height:180px;overflow:auto}.upload-files li{display:flex;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--el-border-color-lighter)}.file-icon{width:19px;height:19px;flex-shrink:0;color:var(--el-color-primary)}.file-name{flex:1;min-width:0;overflow-wrap:anywhere}.upload-files small{color:var(--el-text-color-secondary);white-space:nowrap}
.upload-warning,.upload-error,.upload-progress{padding:12px;border-radius:6px;line-height:1.6;overflow-wrap:anywhere}.upload-warning{background:var(--el-color-warning-light-9);color:var(--el-color-warning-dark-2)}.upload-error{background:var(--el-color-danger-light-9);color:var(--el-color-danger)}.upload-progress{margin-top:16px;background:var(--el-color-primary-light-9);color:var(--el-color-primary)}
.upload-results{margin-top:20px}.upload-results h3{font-size:15px;margin:0}.upload-results li{display:flex;flex-direction:column;gap:6px;margin-top:8px;padding:12px;border-radius:6px;overflow-wrap:anywhere}.upload-results li span{font-size:13px;line-height:1.5}.result-success{background:var(--el-color-success-light-9);color:var(--el-color-success-dark-2)}.result-warning{background:var(--el-color-warning-light-9);color:var(--el-color-warning-dark-2)}
</style>
<style>
.invoice-upload-dialog{max-width:calc(100vw - 32px);border-radius:12px}.invoice-upload-dialog .el-dialog__body{padding-top:12px}.invoice-upload-dialog .el-dialog__footer{border-top:1px solid var(--el-border-color-lighter);padding-top:16px}
</style>
