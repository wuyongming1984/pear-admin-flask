<script setup lang="ts">
import {computed, onDeactivated, ref, watch} from 'vue'
import {UploadFilled} from '@element-plus/icons-vue'
import {request} from '../../api'
import {companyMatches, supplierCompanyName} from './companyMatch'
import {invoiceAmounts, invoiceTotalSum, formatInvoiceMoney, type Row} from './model'
const props = defineProps<{modelValue: any[]; invoices: Row[]; supplierName?: string; supplierContact?: string; projectId?: number | string; disabled?: boolean; loading?: boolean; error?: string; recommendation?: Row}>()
const supplierName = computed(() => supplierCompanyName(props.supplierName, props.supplierContact))
const emit = defineEmits<{'update:modelValue': [ids: any[]]; load: [ids?: any[]]; busy: [value: boolean]; uploaded: [invoices: Row[]]}>()
const picker = ref<HTMLInputElement>()
const uploading = ref(false), dragDepth = ref(0), uploadError = ref(''), uploadNotice = ref('')
const locked = computed(() => props.disabled || uploading.value)
const selectionLocked = computed(() => locked.value || props.loading || !!props.error)
async function uploadFiles(incoming: File[]) {
  if (locked.value || !incoming.length) return
  uploadError.value = ''; uploadNotice.value = ''
  const files: File[] = [], rejected: string[] = []
  for (const file of incoming) {
    if (!/\.(pdf|png|jpe?g)$/i.test(file.name) || !file.size) { rejected.push(file.name); continue }
    if (!files.some(item => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)) files.push(file)
  }
  if (rejected.length) uploadError.value = `不支持的格式或空文件：${rejected.join('、')}。请选择 PDF、JPG 或 PNG 发票。`
  if (!files.length) return
  uploading.value = true; emit('busy', true)
  try {
    const data = new FormData()
    files.forEach(file => data.append('files', file))
    data.append('path', 'invoices')
    data.append('reuse_existing', '1')
    if (props.projectId) data.append('project_id', String(props.projectId))
    const response = await request('/material/invoice/upload', {method: 'POST', body: data})
    const returned: Row[] = (response.data?.invoices || []).filter((invoice: Row) => invoice.id != null)
    const invoices = [...new Map(returned.map(invoice => [String(invoice.id), invoice])).values()]
    if (invoices.length) {
      emit('uploaded', invoices)
      const ids = [...props.modelValue]
      for (const invoice of invoices) if (!ids.some(id => String(id) === String(invoice.id))) ids.push(invoice.id)
      emit('update:modelValue', ids)
      const existing = invoices.filter(invoice => invoice.existing).length
      const created = invoices.length - existing
      const pending = invoices.filter(invoice => !['success', 'completed'].includes(invoice.ocr_status)).length
      const notices = [created ? `新上传 ${created} 张，已选中` : '', existing ? `已存在 ${existing} 张，已选中` : ''].filter(Boolean)
      uploadNotice.value = `${notices.join('；')}，保存付款单后完成关联。${pending ? `其中 ${pending} 张尚未识别完成，可在发票库重新识别。` : ''}`
    }
    const errors = (response.data?.errors || []).map((item: Row) => `${item.name}：${item.reason}`)
    if (!invoices.length && !errors.length) errors.push('没有上传成功的发票，请核对后重试。')
    uploadError.value = [uploadError.value, ...errors].filter(Boolean).join('\n')
  } catch (cause) {
    uploadError.value = [uploadError.value, cause instanceof Error ? cause.message : '上传失败，请稍后重试'].filter(Boolean).join('\n')
  } finally { uploading.value = false; emit('busy', false) }
}
function chooseFiles(event: Event) {
  const input = event.target as HTMLInputElement
  void uploadFiles(Array.from(input.files || [])); input.value = ''
}
function drop(event: DragEvent) { dragDepth.value = 0; void uploadFiles(Array.from(event.dataTransfer?.files || [])) }
const key = (name: unknown) => String(name || '').normalize('NFKC').replace(/\s/g, '').toLowerCase()
const matches = (invoice: Row) => companyMatches(invoice.seller_name, supplierName.value)
const selected = (id: any) => props.modelValue.some(value => String(value) === String(id))
const candidates = computed<Row[]>(() => (props.recommendation?.candidates || props.invoices).filter(matches))
const selectedRows = computed(() => props.invoices.filter(invoice => selected(invoice.id)))
const selectedTotal = computed(() => formatInvoiceMoney(props.modelValue.every(id => selectedRows.value.some(invoice => String(invoice.id) === String(id))) ? invoiceTotalSum(selectedRows.value) : null))
const unmatchedSelected = computed(() => selectedRows.value.filter(invoice => !matches(invoice)).length)
const visible = ref(false), search = ref(''), draft = ref<any[]>([])
const fingerprint = (ids: any[]) => JSON.stringify(ids.map(String).sort())
const recommendationSelection = ref('')
watch(() => props.recommendation, value => { recommendationSelection.value = value ? fingerprint(value.selected_invoice_ids || draft.value) : '' })
const stale = computed(() => !!props.recommendation && recommendationSelection.value !== fingerprint(draft.value))
const combinations = computed<Row[]>(() => props.recommendation?.combinations || [])
const draftRows = computed(() => props.invoices.filter(invoice => draftSelected(invoice.id)))
const draftGross = computed(() => !stale.value && props.recommendation?.context?.selected_gross === null ? null : draft.value.every(id => draftRows.value.some(invoice => String(invoice.id) === String(id))) ? invoiceTotalSum(draftRows.value) : null)
const remaining = computed(() => draftGross.value === null || !stale.value && props.recommendation?.context?.remaining === null ? null : invoiceTotalSum([{total_amount: props.recommendation?.context?.target_amount, tax_amount: draftGross.value.startsWith('-') ? draftGross.value.slice(1) : '-' + draftGross.value}]))
const filtered = computed(() => candidates.value.filter(invoice => !key(search.value) || key([invoice.invoice_number, invoice.seller_name, invoice.buyer_name].join(' ')).includes(key(search.value))))
const draftSelected = (id: any) => draft.value.some(value => String(value) === String(id))
function open() { if (!locked.value && !props.loading) { draft.value = [...props.modelValue]; recommendationSelection.value = fingerprint(draft.value); search.value = ''; visible.value = true; emit('load', [...draft.value]) } }
defineExpose({open})
function recalculate() { if (!locked.value && !props.loading) emit('load', [...draft.value]) }
function canChooseCombination(combination: Row) {
  if (selectionLocked.value || stale.value || draftGross.value === null || remaining.value === null || !props.recommendation || !combinations.value.includes(combination)) return false
  if (invoiceTotalSum([{total_amount: combination.total_gross, tax_amount: '0'}]) === null || invoiceTotalSum([{total_amount: combination.difference, tax_amount: '0'}]) === null) return false
  const ids = combination.invoice_ids
  return Array.isArray(ids) && ids.length > 0 && ids.length <= 3 && ids.every(id => candidates.value.some(invoice => String(invoice.id) === String(id) && invoice.can_recommend === true && matches(invoice) && invoiceTotalSum([invoice]) !== null))
}
function chooseCombination(combination: Row) {
  if (!canChooseCombination(combination)) return
  for (const id of combination.invoice_ids) if (!draftSelected(id)) draft.value.push(id)
}
function invoiceNumbers(combination: Row) { return (combination.invoice_ids || []).map((id: any) => props.invoices.find(invoice => String(invoice.id) === String(id))?.invoice_number || id).join(' + ') }
function confirm() { if (!selectionLocked.value) { emit('update:modelValue', [...draft.value]); visible.value = false } }
function remove(id: any) { if (!selectionLocked.value) emit('update:modelValue', props.modelValue.filter(value => String(value) !== String(id))) }
onDeactivated(() => { visible.value = false; dragDepth.value = 0 })
function toggle(invoice: Row, event: Event) {
  if (selectionLocked.value) return
  const ids = draft.value.filter(id => String(id) !== String(invoice.id))
  if ((event.target as HTMLInputElement).checked && matches(invoice)) ids.push(invoice.id)
  draft.value = ids
}
</script>

<template>
  <section class="payment-invoice-picker" :class="{dragging: dragDepth > 0 && !locked}" aria-label="关联发票" :aria-busy="uploading"
    @dragenter.prevent="!locked && dragDepth++" @dragleave.prevent="dragDepth = Math.max(0, dragDepth - 1)" @dragover.prevent @drop.prevent.stop="drop">
    <header><strong>关联发票</strong><span>已选 {{modelValue.length}} 张 · 价税合计 {{selectedTotal}}</span></header>
    <p>选择已有发票，或拖拽上传；已存在的发票会自动选中，随付款单一起保存关联。</p>
    <el-button data-testid="choose-invoices" :disabled="locked || loading" @click="open">选择关联发票</el-button>
    <el-button type="primary" plain data-testid="smart-invoice-recommendations" :disabled="locked || loading" @click="open">智能推荐</el-button>
    <input ref="picker" class="invoice-file-picker" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" aria-label="上传并关联发票" :disabled="locked" @change="chooseFiles" />
    <button type="button" class="payment-invoice-dropzone" data-testid="payment-invoice-dropzone" :disabled="locked" @click="picker?.click()">
      <UploadFilled aria-hidden="true" />
      <strong>{{uploading ? '正在上传并识别发票…' : dragDepth ? '松开鼠标，上传并关联发票' : '拖拽发票到此处，或点击上传'}}</strong>
      <small>支持 PDF、JPG、PNG，可一次上传多张发票</small>
    </button>
    <p v-if="uploadNotice" role="status" class="upload-notice">{{uploadNotice}}</p>
    <p v-if="uploadError" role="alert" class="upload-error">{{uploadError}}</p>
    <div v-if="selectedRows.length" class="invoice-choices" aria-label="已选择的发票">
      <div v-for="invoice in selectedRows" :key="invoice.id" class="invoice-choice selected">
        <span><strong>{{invoice.invoice_number || invoice.file_name || '无发票号码'}}</strong><small>{{invoice.seller_name || '销售方待识别'}}</small><small v-if="supplierName && invoice.seller_name && !matches(invoice)" class="seller-warning">销售方与收款单位名称不匹配，请核对</small></span>
        <span class="invoice-amounts"><b>价税合计：{{invoiceAmounts(invoice).total}}</b><small>不含税金额：{{invoiceAmounts(invoice).untaxed}}</small><small>税额：{{invoiceAmounts(invoice).tax}}</small></span>
        <el-button link :disabled="selectionLocked" :aria-label="`移除发票 ${invoice.invoice_number || invoice.id}`" @click="remove(invoice.id)">移除</el-button>
      </div>
    </div>
    <p v-else class="muted">尚未选择关联发票</p>
    <el-dialog v-model="visible" title="选择关联发票" width="760px" top="5vh" class="payment-invoice-dialog" append-to-body :close-on-click-modal="false">
    <p v-if="loading" role="status">正在加载可关联发票…</p>
    <p v-else-if="error" role="alert">{{error}} <el-button data-testid="retry-invoice-options" :disabled="locked" @click="recalculate">重新加载</el-button></p>
    <p v-else-if="supplierName">供应商名称：{{supplierName}}。已匹配 {{candidates.length}} 张销售方名称相近的发票，请核对后勾选。</p>
    <p v-else>请先选择付款单的收款单位，再选择对应发票。</p>
    <p v-if="unmatchedSelected" class="muted">原有 {{unmatchedSelected}} 张不同销售方的关联已保留，如需取消，可在付款单的已选发票中移除。</p>
    <section v-if="recommendation && !loading && !error" class="recommendation-panel" aria-label="智能关联金额核对">
      <header><strong>智能推荐 · 金额核对</strong><el-button data-testid="recalculate-invoice-recommendations" :disabled="locked" @click="recalculate">重新计算</el-button></header>
      <div class="recommendation-amounts"><span>{{recommendation.context?.amount_basis === 'invoice_amount' ? '开票金额' : '本次实付金额'}}<b>{{formatInvoiceMoney(recommendation.context?.target_amount)}}</b></span><span>当前已选价税合计<b>{{formatInvoiceMoney(draftGross)}}</b></span><span>还差金额<b>{{formatInvoiceMoney(remaining)}}</b></span></div>
      <p>推荐依据用于辅助核对，勾选后还需确认选择并保存付款单。</p>
      <p v-for="reason in recommendation.context?.reasons || []" :key="reason" class="seller-warning">{{reason}}</p>
      <p v-if="draftGross === null || remaining === null" class="seller-warning">金额资料尚待核实，金额组合已停用，可继续逐张核对、勾选。</p>
      <p v-if="recommendation.truncated" class="seller-warning">共 {{recommendation.total_count}} 张候选，本次显示结果已截断，请结合发票号码等信息核对。</p>
      <p v-if="stale" class="seller-warning">已选发票发生变化，旧组合已停用，请重新计算。</p>
      <div v-if="combinations.length" class="invoice-combinations" aria-label="推荐发票组合">
        <p>以下为前 {{recommendation.combination_limit || 30}} 张可推荐发票中，最多 3 张的金额相符组合：</p>
        <div v-for="(combination, index) in combinations" :key="index" class="invoice-combination">
          <span><strong>{{invoiceNumbers(combination)}}</strong><small>价税合计 {{formatInvoiceMoney(combination.total_gross)}} · 差额 {{formatInvoiceMoney(combination.difference)}}</small><small v-for="reason in combination.reasons || []" :key="reason">{{reason}}</small></span>
          <el-button data-testid="choose-invoice-combination" :disabled="!canChooseCombination(combination)" @click="chooseCombination(combination)">勾选此组合</el-button>
        </div>
      </div>
      <p v-else>在本次前 {{recommendation.combination_limit || 30}} 张可推荐发票、最多 3 张的范围内未找到金额相符组合，可继续逐张核对、勾选。</p>
    </section>
    <el-button v-else-if="!loading && !error && supplierName" data-testid="recalculate-invoice-recommendations" :disabled="locked" @click="recalculate">重新计算智能推荐</el-button>
    <input v-model="search" class="invoice-search" type="search" aria-label="搜索可关联发票" placeholder="搜索发票号码、销售方或购买方" />
    <div v-if="!loading && !error && filtered.length" class="invoice-choices">
      <label v-for="invoice in filtered" :key="invoice.id" class="invoice-choice" :class="{selected: draftSelected(invoice.id)}">
        <input type="checkbox" :aria-label="`关联发票 ${invoice.invoice_number || invoice.id}`" :checked="draftSelected(invoice.id)" :disabled="selectionLocked" @change="toggle(invoice, $event)" />
        <span><strong>{{invoice.invoice_number || '无发票号码'}}</strong><small>{{invoice.seller_name || '销售方待识别'}} · {{invoice.invoice_date || '日期待识别'}}</small><small v-if="invoice.reasons?.length" v-for="reason in invoice.reasons" :key="reason" :class="invoice.can_recommend === false ? 'seller-warning' : 'match-label'">{{reason}}</small><small v-else class="match-label">供应商名称与销售方名称相近</small><small v-if="invoice.amount_difference != null">相对本轮计算待补金额差额：{{formatInvoiceMoney(invoice.amount_difference)}}</small><small v-if="invoice.linked_payments?.length" class="seller-warning">已关联付款单 {{invoice.linked_payments.map((pay: Row) => pay.pay_number).join('、')}}，请核对是否重复使用。</small></span>
        <span class="invoice-amounts"><b>价税合计：{{invoiceAmounts(invoice).total}}</b><small>不含税金额：{{invoiceAmounts(invoice).untaxed}}</small><small>税额：{{invoiceAmounts(invoice).tax}}</small></span>
      </label>
    </div>
    <p v-else-if="!loading && !error" class="muted">{{!supplierName ? '选择收款单位后自动筛选发票。' : !candidates.length ? `暂无销售方名称为「${supplierName}」或相近的发票。请核对供应商名称或上传对应发票。` : '匹配发票中没有找到符合搜索条件的单据。'}}</p>
    <template #footer><span class="selection-count">已选 {{draft.length}} 张</span><el-button data-testid="cancel-invoice-selection" @click="visible=false">取消</el-button><el-button type="primary" data-testid="confirm-invoice-selection" :disabled="selectionLocked" @click="confirm">确认选择</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.invoice-choice>.invoice-amounts{flex:0 1 auto;max-width:55%;text-align:right;gap:6px}.invoice-amounts b{font-size:13px;white-space:normal;overflow-wrap:anywhere}.invoice-amounts small{font-size:12px}
.recommendation-panel{padding:14px;margin:12px 0;border:1px solid var(--el-color-primary-light-5);border-radius:6px;background:var(--el-color-primary-light-9)}.recommendation-panel header{align-items:center}.recommendation-amounts{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px}.recommendation-amounts>span{display:flex;flex-direction:column;gap:5px;font-size:12px;color:var(--el-text-color-secondary)}.recommendation-amounts b{font-size:16px;color:var(--el-text-color-primary);font-family:monospace}.invoice-combination{display:flex;align-items:center;gap:12px;padding:10px 0;border-top:1px solid var(--el-border-color)}.invoice-combination>span{display:flex;flex-direction:column;gap:5px;flex:1;min-width:0;overflow-wrap:anywhere}.invoice-combination small{font-size:12px;color:var(--el-text-color-secondary)}.recommendation-panel .seller-warning{color:var(--el-color-warning-dark-2)}
.invoice-file-picker{display:none}.payment-invoice-dropzone{margin-top:12px;width:100%;padding:18px 12px;display:flex;flex-direction:column;align-items:center;gap:8px;border:1px dashed var(--el-border-color-darker);border-radius:6px;background:var(--el-fill-color-lighter);color:var(--el-text-color-regular);font:inherit;cursor:pointer}.payment-invoice-dropzone svg{width:28px;height:28px;color:var(--el-color-primary)}.payment-invoice-dropzone strong{font-size:14px}.payment-invoice-dropzone small{font-size:12px;color:var(--el-text-color-secondary)}.payment-invoice-dropzone:hover,.payment-invoice-dropzone:focus-visible,.dragging .payment-invoice-dropzone{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}.payment-invoice-dropzone:focus-visible{outline:2px solid var(--el-color-primary);outline-offset:2px}.payment-invoice-dropzone:disabled{cursor:wait;opacity:.65}.payment-invoice-picker.dragging{border-color:var(--el-color-primary)}.payment-invoice-picker .upload-notice{color:var(--el-color-success-dark-2)}.payment-invoice-picker .upload-error,.invoice-choice .seller-warning{color:var(--el-color-warning-dark-2);white-space:pre-line;overflow-wrap:anywhere}
.payment-invoice-picker{margin:10px 0 20px;padding:16px;border:1px solid var(--el-border-color);border-radius:8px}.payment-invoice-picker header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.payment-invoice-picker header span,.payment-invoice-picker p,.save-hint{font-size:12px;color:var(--el-text-color-secondary);line-height:1.6}.invoice-choices{max-height:300px;overflow:auto;margin:12px 0}.invoice-choice{display:flex;gap:10px;padding:12px;border:1px solid var(--el-border-color-lighter);border-radius:6px;margin-bottom:8px;align-items:flex-start;cursor:pointer}.invoice-choice.selected{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}.invoice-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.invoice-choice>span{display:flex;flex-direction:column;gap:6px;flex:1;min-width:0;overflow-wrap:anywhere}.invoice-choice small{color:var(--el-text-color-secondary)}.invoice-choice b{white-space:nowrap;font-family:monospace}.invoice-choice .match-label{color:var(--el-color-success-dark-2)}.muted{padding:8px 0}
</style>
<style>
.payment-invoice-dialog{max-width:calc(100vw - 32px)}.payment-invoice-dialog .el-dialog__body{max-height:calc(90vh - 150px);overflow-y:auto}.payment-invoice-dialog .invoice-choices{max-height:45vh}.payment-invoice-dialog .invoice-search{width:100%;box-sizing:border-box;border:1px solid var(--el-border-color);border-radius:6px;padding:10px 12px;font:inherit;color:var(--el-text-color-primary);background:var(--el-bg-color)}.payment-invoice-dialog .selection-count{margin-right:16px;font-size:13px}
</style>
