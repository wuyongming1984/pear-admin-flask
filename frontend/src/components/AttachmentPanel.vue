<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { showImagePreview, showToast } from 'vant'
import { request } from '../api'
import type { Attachment } from '../model'

const props = defineProps<{
  modelValue: Attachment[]
  kind: 'project' | 'order' | 'pay'
  readonly?: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [value: Attachment[]]
  busy: [value: boolean]
  blocked: [value: boolean]
}>()

type UploadItem = {
  key: number
  file: File
  status: 'queued' | 'uploading' | 'failed'
  error: string
}
const maxSize = 10 * 1024 * 1024
const uploads = ref<UploadItem[]>([])
const cameraInput = ref<HTMLInputElement>()
const galleryInput = ref<HTMLInputElement>()
const fileInput = ref<HTMLInputElement>()
let nextKey = 0
let disposed = false
const busy = computed(() => uploads.value.some(item => item.status !== 'failed'))
const blocked = computed(() => uploads.value.some(item => item.status === 'failed'))
watch(busy, value => emit('busy', value), { immediate: true, flush: 'sync' })
watch(blocked, value => emit('blocked', value), { immediate: true, flush: 'sync' })

function nameOf(item: Attachment) {
  return String(item.original_filename || item.name || item.filename || '附件')
}

function sizeOf(size: unknown) {
  const bytes = Number(size)
  if (!Number.isFinite(bytes) || bytes <= 0) return ''
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function safeUrl(item: Attachment): string | undefined {
  const value = item.preview_url || item.url || item.file_path
  if (typeof value !== 'string' || !value.trim()) return undefined
  try {
    const parsed = new URL(value, window.location.origin)
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : undefined
  } catch {
    return undefined
  }
}

function isImage(item: Attachment) {
  const filename = nameOf(item)
  let pathname = ''
  try { pathname = new URL(safeUrl(item) || '', window.location.origin).pathname } catch { /* No preview URL. */ }
  return /\.(jpe?g|png|gif|webp|bmp|avif|heic|heif)$/i.test(filename) || /\.(jpe?g|png|gif|webp|bmp|avif)$/i.test(pathname)
}

function previewImage(item: Attachment) {
  const url = safeUrl(item)
  if (url) showImagePreview({ images: [url], closeable: true })
  else showToast('此附件暂时无法预览')
}

async function upload(item: UploadItem) {
  if (props.readonly || disposed) return
  if (item.file.size > maxSize) {
    item.status = 'failed'
    item.error = '文件超过 10 MB，请移除此项后重新选择'
    return
  }
  item.status = 'uploading'
  item.error = ''
  const form = new FormData()
  form.append('file', item.file)
  form.append('path', `${props.kind}_attachments`)
  if (props.kind === 'project') form.append('attachment_code', 'mobile')
  try {
    const response = await request<Attachment>('/upload/', { method: 'POST', body: form })
    if (disposed) return
    if (!response.data || typeof response.data !== 'object' || !safeUrl(response.data)) {
      throw new Error('上传结果缺少附件地址，请重试')
    }
    // Preserve the server's original storage URL and all attachment metadata.
    const attachment = { ...response.data, name: response.data.name || response.data.original_filename || item.file.name }
    emit('update:modelValue', [...props.modelValue, attachment])
    uploads.value = uploads.value.filter(entry => entry.key !== item.key)
  } catch (error) {
    if (disposed) return
    item.status = 'failed'
    item.error = error instanceof Error ? error.message : '上传失败，请检查网络后重试'
  }
}

async function selectFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (props.readonly || busy.value) return
  const batch = files.map(file => ({ key: ++nextKey, file, status: 'queued' as const, error: '' }))
  uploads.value.push(...batch)
  // Access reactive queue entries so changes also update save-blocking state.
  for (const entry of batch) {
    const item = uploads.value.find(candidate => candidate.key === entry.key)
    if (item && !disposed) await upload(item)
  }
}

function retry(item: UploadItem) {
  if (!busy.value && !props.readonly) void upload(item)
}

function discard(item: UploadItem) {
  if (item.status === 'failed') uploads.value = uploads.value.filter(entry => entry.key !== item.key)
}

onBeforeUnmount(() => {
  disposed = true
  emit('busy', false)
  emit('blocked', false)
})
</script>

<template>
  <section class="attachment-panel" aria-label="附件">
    <div class="attachment-heading">
      <h3>附件</h3>
      <span>{{ modelValue.length }} 个附件</span>
    </div>
    <p v-if="!readonly" class="attachment-help">拍照或选择文件，单个文件不超过 10 MB。已上传附件暂不支持删除。</p>

    <div v-if="!readonly" class="attachment-actions">
      <van-button icon="photograph" size="small" :disabled="busy" @click="cameraInput?.click()">拍照</van-button>
      <van-button icon="photo-o" size="small" :disabled="busy" @click="galleryInput?.click()">相册</van-button>
      <van-button icon="description-o" size="small" :disabled="busy" @click="fileInput?.click()">选文件</van-button>
      <input ref="cameraInput" class="file-input" type="file" accept="image/*" capture="environment" aria-label="拍照上传附件" :disabled="busy" @change="selectFiles">
      <input ref="galleryInput" class="file-input" type="file" accept="image/*" multiple aria-label="从相册选择附件" :disabled="busy" @change="selectFiles">
      <input ref="fileInput" class="file-input" type="file" multiple aria-label="选择文档或其他附件" :disabled="busy" @change="selectFiles">
    </div>

    <p v-if="!modelValue.length && !uploads.length" class="attachment-empty">暂无附件</p>
    <ul v-else class="attachment-list">
      <li v-for="(item, index) in modelValue" :key="`${item.id || item.code || item.url || item.file_path || 'attachment'}-${index}`" class="attachment-row">
        <span class="file-icon" aria-hidden="true"><van-icon :name="isImage(item) ? 'photo-o' : 'description-o'" /></span>
        <div class="attachment-info">
          <p class="attachment-name">{{ nameOf(item) }}</p>
          <p class="attachment-meta"><span class="status-success">已上传</span><span v-if="sizeOf(item.size)">{{ sizeOf(item.size) }}</span></p>
        </div>
        <button v-if="safeUrl(item) && isImage(item)" class="preview-link" type="button" :aria-label="`预览 ${nameOf(item)}`" @click="previewImage(item)">预览</button>
        <a v-else-if="safeUrl(item)" class="preview-link" :href="safeUrl(item)" target="_blank" rel="noopener noreferrer" :aria-label="`打开 ${nameOf(item)}`">打开</a>
        <span v-else class="unavailable">暂无预览</span>
      </li>
      <li v-for="item in uploads" :key="`pending-${item.key}`" class="attachment-row" :class="{ 'upload-failed': item.status === 'failed' }">
        <span class="file-icon" aria-hidden="true"><van-icon :name="item.status === 'failed' ? 'warning-o' : 'description-o'" /></span>
        <div class="attachment-info" aria-live="polite">
          <p class="attachment-name">{{ item.file.name }}</p>
          <p v-if="item.status === 'failed'" class="attachment-error">{{ item.error }}</p>
          <p v-else class="attachment-meta"><van-loading size="12" />{{ item.status === 'queued' ? '等待上传' : '正在上传' }}</p>
        </div>
        <div v-if="item.status === 'failed' && !readonly" class="retry-actions">
          <button v-if="item.file.size <= maxSize" class="preview-link" type="button" :disabled="busy" :aria-label="`重新上传 ${item.file.name}`" @click="retry(item)">重试</button>
          <button class="discard-link" type="button" :aria-label="`移除失败文件 ${item.file.name}`" @click="discard(item)">移除</button>
        </div>
      </li>
    </ul>
    <p v-if="busy" class="queue-note" role="status">附件上传中，请稍候再保存。</p>
    <p v-else-if="blocked" class="queue-note attachment-error" role="status">请重试或移除上传失败的文件后再保存。</p>
  </section>
</template>

<style scoped>
.attachment-panel { min-width: 0; color: #243746; }
.attachment-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.attachment-heading h3 { font-size: 15px; margin: 0; font-weight: 650; }
.attachment-heading > span { color: #7b8b98; font-size: 12px; }
.attachment-help, .queue-note { margin: 9px 0 12px; font-size: 12px; line-height: 1.7; color: #71818e; }
.attachment-actions { display: flex; flex-wrap: wrap; gap: 9px; margin: 14px 0; }
.attachment-actions :deep(.van-button) { color: #137f7a; border-color: #d8e9e7; background: #f3f9f8; border-radius: 8px; min-height: 40px; padding: 0 13px; }
.file-input { display: none; }
.attachment-empty { padding: 21px 12px; margin: 12px 0 0; text-align: center; border: 1px dashed #dde6e9; border-radius: 10px; color: #8b9aa5; font-size: 13px; }
.attachment-list { list-style: none; padding: 0; margin: 12px 0 0; }
.attachment-row { display: flex; align-items: center; gap: 10px; padding: 12px 0; border-bottom: 1px solid #edf1f3; min-width: 0; }
.attachment-row:last-child { border-bottom: 0; }
.file-icon { display: grid; place-items: center; flex: 0 0 36px; width: 36px; height: 40px; border-radius: 8px; background: #eef6f6; color: #258f89; font-size: 22px; }
.attachment-info { flex: 1; min-width: 0; }
.attachment-name { margin: 0; font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
.attachment-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 5px 0 0; color: #8b98a2; font-size: 11px; }
.status-success { color: #29968c; }
.preview-link, .discard-link { flex-shrink: 0; border: 0; background: none; padding: 10px 4px; color: #13877f; font: inherit; font-size: 12px; text-decoration: none; cursor: pointer; }
.preview-link:disabled { opacity: .4; cursor: default; }
.discard-link { color: #8b7371; }
.retry-actions { display: flex; flex-direction: column; flex-shrink: 0; }
.retry-actions button { padding: 6px 4px; }
.attachment-error { color: #c25a47; font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; margin: 4px 0 0; }
.upload-failed .file-icon { color: #c67c5d; background: #fcf3ed; }
.unavailable { flex-shrink: 0; color: #94a0a9; font-size: 11px; }
.queue-note { padding: 9px 11px; background: #f7fafb; border-radius: 8px; }
.preview-link:focus-visible, .discard-link:focus-visible { outline: 2px solid #15958b; outline-offset: 2px; border-radius: 4px; }
</style>
