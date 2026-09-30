<script setup lang="ts">
import {ref, watch} from 'vue'
import AttachmentEditor from '../../components/AttachmentEditor.vue'
import {request} from '../../api'
import {parseAttachments, type Row} from './model'

const props = defineProps<{order: Row}>()
const emit = defineEmits<{saved: [files: Row[]]}>()
const files = ref<Row[]>([]), saving = ref(false), dirty = ref(false)
const loadError = ref(''), saveError = ref(''), saved = ref(false)
let revision = 0
watch(() => [props.order.attachments, props.order.attachments_list], () => {
  if (dirty.value || saving.value) return
  try {files.value = parseAttachments(props.order); loadError.value = ''}
  catch {loadError.value = '附件数据无法读取，请在订单详情中核对后再上传。'}
}, {immediate: true})

function update(value: Row[]) {
  files.value = value; revision++; dirty.value = true; saved.value = false
  // A failed save retains the uploaded files until the user explicitly retries.
  if (!saveError.value) void save()
}
async function save() {
  if (saving.value || loadError.value) return
  saving.value = true; saveError.value = ''
  try {
    while (dirty.value) {
      const current = revision, snapshot = [...files.value]
      await request(`/order/${props.order.id}`, {method: 'PUT', body: JSON.stringify({attachments: JSON.stringify(snapshot)})})
      if (current === revision) {dirty.value = false; saved.value = true}
      emit('saved', snapshot)
    }
  } catch (e) {
    saveError.value = `附件关联尚未保存：${(e as Error).message}。请重试保存。`
  } finally {saving.value = false}
}
</script>

<template>
  <section class="order-attachments" aria-label="订单附件">
    <p v-if="loadError" role="alert" class="attachment-error">{{loadError}}</p>
    <AttachmentEditor v-else :model-value="files" kind="orders" drag @update:model-value="update" />
    <div v-if="saveError" role="alert" class="attachment-error">
      {{saveError}} <button class="retry-save" :disabled="saving" @click="save">重试保存</button>
    </div>
    <p v-else-if="saving || saved" class="save-status" role="status">{{saving ? '正在保存附件…' : '附件已保存'}}</p>
  </section>
</template>

<style scoped>
.order-attachments { margin-top: 16px; min-width: 0; }
.order-attachments :deep(.attachment-editor) { margin: 0; font-size: 13px; }
.order-attachments :deep(.attachment-row) { flex-wrap: wrap; }
.order-attachments :deep(.attachment-row > a) { min-width: 0; overflow-wrap: anywhere; }
.save-status { margin: 8px 0 0; color: #607569; font-size: 12px; }
.attachment-error { margin: 8px 0; color: #a84232; font-size: 13px; line-height: 1.6; }
.retry-save { padding: 5px 10px; border: 1px solid #d4e1d8; border-radius: 4px; background: #fff; color: #356b56; cursor: pointer; }
</style>
