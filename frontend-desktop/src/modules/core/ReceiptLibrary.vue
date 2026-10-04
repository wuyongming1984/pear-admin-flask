<script setup lang="ts">
import {computed, onActivated, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import {onBeforeRouteLeave, onBeforeRouteUpdate, useRoute} from 'vue-router'
import {ElMessage, ElMessageBox, type UploadUserFile} from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import {query, request, safeUrl} from '../../api'
import {formatMoney} from './money'
import type {Row} from './model'
import InvoicePdfPreview from './InvoicePdfPreview.vue'
import ReceiptPaymentLinks from './ReceiptPaymentLinks.vue'

const route = useRoute()
const rows = ref<Row[]>([]), active = ref<Row>(), count = ref(0), page = ref(1), limit = ref(20)
const keyword = ref(''), status = ref(''), loading = ref(false), error = ref('')
const uploadVisible = ref(false), files = ref<UploadUserFile[]>([]), uploading = ref(false), reports = ref<string[]>([])
const editVisible = ref(false), draft = ref<Row>({}), editSaving = ref(false), editError = ref(''), baseline = ref('')
const recognizing = ref(false), recognitionNote = ref(''), recognitionWarnings = ref<string[]>([])
const editReceiptId = ref<number>()
const deleting = ref(false), linking = ref(false), imageError = ref(false), previewVersion = ref(0)
const paymentLinks = ref<InstanceType<typeof ReceiptPaymentLinks>>()
const busy = computed(() => loading.value || uploading.value || editSaving.value || recognizing.value || deleting.value || linking.value)
const dirty = computed(() => editVisible.value && JSON.stringify(draft.value) !== baseline.value)
const fileUrl = computed(() => safeUrl(active.value?.file_url || active.value?.file_path))
let revision = 0, searchTimer:ReturnType<typeof setTimeout>|undefined, activated = false

function fail(e:unknown) {error.value = e instanceof Error ? e.message : '操作失败，请重试'}
async function load(preferred?:number) {
 const current = ++revision
 loading.value = true; error.value = ''
 try {
  const result = await request(`/payment-receipts?${query({q:keyword.value,linked:status.value,page:page.value,limit:limit.value})}`)
  let chosen = (result.data || []).find((row:Row) => row.id === (preferred || active.value?.id)) || result.data?.[0]
  if(preferred && chosen?.id !== preferred) chosen = (await request(`/payment-receipts/${preferred}`)).data
  if(current !== revision) return
  rows.value = result.data || []; count.value = result.count || 0; active.value = chosen
 } catch(e) {if(current === revision) fail(e)}
 finally {if(current === revision) loading.value = false}
}
onMounted(() => {void load(Number(route.query.receipt_id) || undefined)})
onActivated(() => {if(activated && !busy.value && !dirty.value) void load(Number(route.query.receipt_id) || undefined); activated = true})
onBeforeUnmount(() => {revision++; clearTimeout(searchTimer)})
watch([keyword,status], () => {clearTimeout(searchTimer); searchTimer = setTimeout(() => {page.value = 1; void load()}, 300)})
watch(() => route.query.receipt_id, value => {if(route.path === '/payment-receipts' && !busy.value && !dirty.value) void load(Number(value) || undefined)})
watch(() => active.value?.id, () => {imageError.value = false; previewVersion.value++})
function pick(row:Row) {if(!busy.value) {active.value = row; imageError.value = false}}
async function refreshPreview() {if(!busy.value && active.value) {await load(active.value.id); imageError.value = false; previewVersion.value++}}
function edit() {
 if(!active.value || busy.value) return
 clearTimeout(searchTimer); editReceiptId.value = active.value.id
 draft.value = Object.fromEntries(['receipt_number','payment_date','payer_name','payee_name','amount','bank_name','remarks'].map(key => [key,active.value?.[key] ?? '']))
 baseline.value = JSON.stringify(draft.value); editError.value = ''; recognitionNote.value = ''; recognitionWarnings.value = []; editVisible.value = true
}
async function recognize() {
 if(!active.value || busy.value) return
 const id = active.value.id, current = revision
 edit(); recognizing.value = true
 try {
  const result = await request(`/payment-receipts/${id}/recognize`)
  if(current !== revision || active.value?.id !== id) return
  const fields = result.data?.fields || {}
  let filled = 0
  for(const key of ['receipt_number','payment_date','payer_name','payee_name','amount','bank_name']) {
   if((draft.value[key] == null || draft.value[key] === '') && fields[key] != null && fields[key] !== '') {
    draft.value[key] = fields[key]; filled++
   }
  }
  recognitionNote.value = filled ? `已识别并填入 ${filled} 项空白信息，请核对原件后保存。已有信息已保留。` : '未补充空白信息，请对照原件核对并手工填写。已有信息已保留。'
  recognitionWarnings.value = Array.isArray(result.data?.warnings) ? result.data.warnings : []
 } catch(e) {if(current === revision) editError.value = e instanceof Error ? e.message : '回单识别失败，可手工填写'}
 finally {recognizing.value = false}
}
async function saveInfo() {
 if(!active.value || editSaving.value || recognizing.value) return
 if(!editReceiptId.value || active.value.id !== editReceiptId.value) {editError.value = '当前回单已切换，请关闭表单后重新编辑，避免保存到其他回单'; return}
 const id = editReceiptId.value
 editSaving.value = true; editError.value = ''
 try {
  const result = await request(`/payment-receipts/${id}`, {method:'PUT',body:JSON.stringify(draft.value)})
  active.value = result.data; rows.value = rows.value.map(row => row.id === result.data.id ? result.data : row)
  editVisible.value = false; editReceiptId.value = undefined; ElMessage.success('回单信息已保存')
 } catch(e) {editError.value = e instanceof Error ? e.message : '保存失败'}
 finally {editSaving.value = false}
}
async function closeEdit(done?:()=>void) {
 if(editSaving.value || recognizing.value) return
 if(dirty.value) {try {await ElMessageBox.confirm('回单信息尚未保存，放弃修改？','未保存的修改',{type:'warning'})} catch {return}}
 editVisible.value = false; editReceiptId.value = undefined; done?.()
}
function closeUpload(done:()=>void) {if(!uploading.value) done()}
async function canLeave() {
 if(uploading.value || editSaving.value || recognizing.value || linking.value || deleting.value) return false
 if(dirty.value) {try {await ElMessageBox.confirm('回单信息尚未保存，放弃修改并离开？','未保存的修改',{type:'warning'})} catch {return false}}
 editVisible.value = false; editReceiptId.value = undefined
 return true
}
onBeforeRouteLeave(canLeave)
onBeforeRouteUpdate(canLeave)
async function remove() {
 if(!active.value || busy.value) return
 const id = active.value.id
 try {await ElMessageBox.confirm('删除此回单记录并解除所有关联？付款单和原文件将保留。','删除回单',{type:'warning'})} catch {return}
 deleting.value = true
 try {await request(`/payment-receipts/${id}`,{method:'DELETE'}); active.value = undefined; await load(); ElMessage.success('回单记录已删除')}
 catch(e) {fail(e)} finally {deleting.value = false}
}
function openUpload() {if(busy.value) return; files.value = []; reports.value = []; uploadVisible.value = true}
async function upload() {
 if(uploading.value || !files.value.length) return
 uploading.value = true; reports.value = []
 let lastId:number|undefined
 try {
  for(const file of [...files.value]) {
   if(!file.raw) continue
   if(file.raw.size > 20*1024*1024) {reports.value.push(`${file.name}：超过 20 MB，请移除后重试`); continue}
   if(!/\.(pdf|png|jpe?g|webp)$/i.test(file.name)) {reports.value.push(`${file.name}：文件格式不支持`); continue}
   const form = new FormData(); form.append('file',file.raw)
   try {
    const result = await request('/payment-receipts/upload',{method:'POST',body:form})
    lastId = result.data.id; files.value = files.value.filter(item => item.uid !== file.uid)
    reports.value.push(`${file.name}：${result.data.reused ? '文件已存在，保留原记录' : '收集成功'}`)
   } catch(e) {
    reports.value.push(`${file.name}：${e instanceof Error ? e.message : '上传失败'}`)
    // An uncertain write is never retried automatically.
    if((e as any)?.uncertain) break
   }
  }
  if(lastId) {keyword.value = ''; status.value = ''; page.value = 1; clearTimeout(searchTimer); await load(lastId)}
 } finally {uploading.value = false}
}
</script>

<template>
 <section class="receipt-page">
  <PageHeader title="付款回单库" description="收集银行回单，关联付款单，方便核对与留档"><el-button :disabled="busy" @click="load()">刷新</el-button></PageHeader>
  <p v-if="error" role="alert" class="page-error">{{error}} <el-button link :disabled="busy" @click="load()">重新加载</el-button></p>
  <div class="receipt-library">
   <aside class="receipt-sidebar" aria-label="付款回单清单">
    <header><strong>回单清单</strong><span class="receipt-count">{{count}}</span></header>
    <div class="receipt-search">
     <el-button type="primary" class="upload-trigger" :disabled="busy" @click="openUpload">上传付款回单</el-button>
     <input v-model="keyword" aria-label="搜索付款回单" placeholder="搜索流水号、单位或文件名…" :disabled="uploading || linking" />
     <select v-model="status" aria-label="回单关联状态" :disabled="uploading || linking"><option value="">全部回单</option><option value="unlinked">未关联付款单</option><option value="linked">已关联付款单</option></select>
    </div>
    <p class="list-status" role="status">{{loading ? '正在查找…' : `共 ${count} 份回单`}}</p>
    <div class="receipt-cards" :aria-busy="loading">
     <button v-for="row in rows" :key="row.id" class="receipt-card" :class="{active:active?.id === row.id}" :aria-pressed="active?.id === row.id" :disabled="busy" @click="pick(row)">
      <strong>{{row.payee_name || row.file_name}}</strong><span class="receipt-number">{{row.receipt_number || '流水号待填写'}}</span>
      <span>{{row.payer_name || '付款单位待填写'}}</span><div class="receipt-card-bottom"><time>{{row.payment_date || '日期待填写'}}</time><b>{{row.amount == null ? '金额待填写' : `¥${formatMoney(row.amount)}`}}</b></div>
      <small :class="{'is-linked':row.payments?.length}">{{row.payments?.length ? `已关联 ${row.payments.length} 张付款单` : '未关联付款单'}}</small>
     </button>
     <el-empty v-if="!rows.length && !loading" description="暂无符合条件的回单" :image-size="60" />
    </div>
    <div class="receipt-pagination"><el-pagination v-model:current-page="page" :page-size="limit" :total="count" :pager-count="3" size="small" layout="prev,pager,next" :disabled="busy" @current-change="load()" /></div>
   </aside>
   <main class="receipt-content">
    <header class="receipt-content-header"><strong>付款回单详情</strong><div class="receipt-actions"><el-button v-if="active" :disabled="busy" @click="paymentLinks?.scrollToLinks()">关联付款单</el-button><el-button v-if="active" data-testid="recognize-receipt" :loading="recognizing" :disabled="busy" @click="recognize">识别回单信息</el-button><el-button v-if="active" :disabled="busy" @click="edit">编辑回单信息</el-button><el-button v-if="active" type="danger" plain :disabled="busy" @click="remove">删除</el-button></div></header>
    <div v-if="active" class="receipt-details">
     <section class="receipt-info" aria-label="回单信息">
      <header><div><h2>{{active.payee_name || '付款回单'}}</h2><p>{{active.receipt_number || active.file_name}}</p></div><span class="receipt-amount">{{active.amount == null ? '金额待填写' : `¥${formatMoney(active.amount)}`}}</span></header>
      <dl><div><dt>付款日期</dt><dd>{{active.payment_date || '待填写'}}</dd></div><div><dt>银行</dt><dd>{{active.bank_name || '待填写'}}</dd></div><div><dt>付款单位</dt><dd>{{active.payer_name || '待填写'}}</dd></div><div><dt>收款单位</dt><dd>{{active.payee_name || '待填写'}}</dd></div><div class="wide"><dt>备注</dt><dd>{{active.remarks || '无'}}</dd></div></dl>
     </section>
     <section class="receipt-source" aria-label="回单原文件">
      <header><div><strong>回单原文件</strong><small>{{active.file_name}}</small></div><div class="source-actions"><el-button :disabled="busy" @click="refreshPreview">刷新预览</el-button><a v-if="fileUrl" :href="fileUrl" target="_blank" rel="noopener noreferrer">打开原文件</a></div></header>
      <InvoicePdfPreview v-if="active.file_type==='pdf'" :key="`${active.id}:${previewVersion}`" :invoice-id="active.id" :endpoint="`/payment-receipts/${active.id}/preview-page`" document-label="付款回单" />
      <p v-else-if="imageError" role="alert">回单图片加载失败，请刷新预览或打开原文件。</p>
      <img v-else-if="fileUrl" class="receipt-image" :src="fileUrl" :alt="active.file_name" @error="imageError=true" />
      <el-empty v-else description="原文件暂时不可用" />
     </section>
     <ReceiptPaymentLinks ref="paymentLinks" :key="JSON.stringify([active.id,active.payee_name,active.payer_name,active.amount,active.payment_date])" :receipt-id="active.id" :disabled="uploading || editSaving || recognizing || deleting" @busy="linking=$event" @changed="load()" />
    </div>
    <el-empty v-else description="上传或选择付款回单，查看原文件并关联付款单" />
   </main>
  </div>
  <el-dialog v-model="uploadVisible" title="上传付款回单" width="620px" :close-on-click-modal="false" :close-on-press-escape="!uploading" :show-close="!uploading" :before-close="closeUpload">
   <p class="muted">支持 PDF、PNG、JPG、WebP，可多选或拖入；每份文件不超过 20 MB。上传后可编辑信息并关联付款单。</p>
   <el-upload v-model:file-list="files" drag multiple :auto-upload="false" :disabled="uploading" accept=".pdf,.png,.jpg,.jpeg,.webp" :limit="50" :on-exceed="()=>ElMessage.warning('每次最多上传 50 份回单')"><div class="receipt-drop"><strong>拖入付款回单，或点击选择文件</strong><span>PDF / 图片</span></div></el-upload>
   <ul v-if="reports.length" class="upload-reports" aria-live="polite"><li v-for="(report,index) in reports" :key="index">{{report}}</li></ul>
   <template #footer><el-button :disabled="uploading" @click="uploadVisible=false">{{files.length ? '关闭' : '完成'}}</el-button><el-button type="primary" :loading="uploading" :disabled="!files.length || uploading" @click="upload">开始上传{{files.length ? `（${files.length} 份）` : ''}}</el-button></template>
  </el-dialog>
  <el-dialog v-model="editVisible" title="编辑回单信息" width="620px" :close-on-click-modal="false" :close-on-press-escape="!editSaving && !recognizing" :show-close="!editSaving && !recognizing" :before-close="closeEdit">
   <p v-if="recognizing" role="status" class="muted">正在识别回单信息…</p>
   <p v-if="recognitionNote" role="status" class="muted">{{recognitionNote}}</p>
   <p v-for="(warning,index) in recognitionWarnings" :key="index" class="page-error">{{warning}}</p>
   <p v-if="editError" role="alert" class="page-error">{{editError}}</p>
   <form class="receipt-form" @submit.prevent="saveInfo">
    <label>银行流水号 / 回单编号<input v-model="draft.receipt_number" maxlength="128" aria-label="回单编号" :disabled="editSaving || recognizing" /></label>
    <label>付款日期<input v-model="draft.payment_date" type="date" aria-label="回单付款日期" :disabled="editSaving || recognizing" /></label>
    <label>付款单位<input v-model="draft.payer_name" maxlength="255" aria-label="回单付款单位" :disabled="editSaving || recognizing" /></label>
    <label>收款单位<input v-model="draft.payee_name" maxlength="255" aria-label="回单收款单位" :disabled="editSaving || recognizing" /></label>
    <label>付款金额（元）<input v-model="draft.amount" inputmode="decimal" aria-label="回单金额" :disabled="editSaving || recognizing" placeholder="保留两位小数" /></label>
    <label>银行<input v-model="draft.bank_name" maxlength="255" aria-label="回单银行" :disabled="editSaving || recognizing" /></label>
    <label class="wide">备注<textarea v-model="draft.remarks" rows="3" maxlength="4000" aria-label="回单备注" :disabled="editSaving || recognizing" /></label>
   </form>
   <template #footer><el-button :disabled="editSaving || recognizing" @click="closeEdit()">取消</el-button><el-button type="primary" :loading="editSaving" :disabled="recognizing" @click="saveInfo">保存回单信息</el-button></template>
  </el-dialog>
 </section>
</template>

<style scoped>
.receipt-library{display:grid;grid-template-columns:300px minmax(0,1fr);gap:16px;height:calc(100dvh - 228px);min-height:560px}.receipt-sidebar,.receipt-content{display:flex;flex-direction:column;min-width:0;background:var(--el-bg-color);border:1px solid var(--el-border-color);border-radius:8px;overflow:hidden}.receipt-sidebar>header,.receipt-content-header{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px 18px;border-bottom:1px solid var(--el-border-color);min-height:65px;box-sizing:border-box;flex-shrink:0}.receipt-sidebar>header{color:var(--el-color-primary)}.receipt-count{padding:2px 9px;border-radius:12px;background:var(--el-color-primary-light-9);font-size:12px}.receipt-search{padding:14px;display:flex;flex-direction:column;gap:10px;border-bottom:1px solid var(--el-border-color)}.receipt-search input,.receipt-search select,.receipt-form input,.receipt-form textarea{width:100%;min-width:0;box-sizing:border-box;border:1px solid var(--el-border-color);border-radius:4px;background:var(--el-bg-color);color:var(--el-text-color-primary);padding:10px 12px;font:inherit}.receipt-search input,.receipt-search select{font-size:13px}.list-status{font-size:12px;color:var(--el-text-color-secondary);margin:8px 14px}.receipt-cards{flex:1;min-height:0;overflow:auto;padding:0 10px 10px}.receipt-card{display:flex;flex-direction:column;gap:7px;width:100%;text-align:left;padding:12px;margin-bottom:8px;background:var(--el-fill-color-light);color:var(--el-text-color-primary);border:1px solid transparent;border-radius:6px;cursor:pointer;font-size:12px;overflow-wrap:anywhere}.receipt-card.active{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9);box-shadow:inset 3px 0 var(--el-color-primary)}.receipt-card:disabled{cursor:wait}.receipt-card strong{font-size:14px}.receipt-number{color:var(--el-color-primary);font-family:monospace}.receipt-card-bottom{display:flex;justify-content:space-between;gap:10px;color:var(--el-text-color-secondary)}.receipt-card-bottom b{color:var(--el-color-primary);white-space:nowrap}.receipt-card small{color:var(--el-text-color-secondary)}.is-linked{color:var(--el-color-success-dark-2)!important}.receipt-pagination{border-top:1px solid var(--el-border-color);padding:10px;flex-shrink:0}.receipt-pagination :deep(.el-pagination){justify-content:center}.receipt-actions{display:flex;gap:8px;flex-wrap:wrap}.receipt-actions :deep(.el-button+.el-button){margin-left:0}.receipt-details{flex:1;min-height:0;overflow:auto;background:var(--el-fill-color-light);padding:20px;display:flex;flex-direction:column;gap:16px}.receipt-info,.receipt-source{padding:20px;border:1px solid var(--el-border-color);border-radius:8px;background:var(--el-bg-color)}.receipt-info header,.receipt-source header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}.receipt-info h2{margin:0;font-size:20px;overflow-wrap:anywhere}.receipt-info header p{margin:8px 0 0;color:var(--el-text-color-secondary);font-size:13px;overflow-wrap:anywhere}.receipt-amount{font-size:24px;font-weight:600;color:var(--el-color-primary);white-space:nowrap}.receipt-info dl{display:grid;grid-template-columns:1fr 1fr;gap:16px 24px;margin:20px 0 0;font-size:13px}.receipt-info dt{color:var(--el-text-color-secondary);margin-bottom:6px}.receipt-info dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}.wide{grid-column:1/-1}.receipt-source header{margin-bottom:16px}.receipt-source header>div:first-child{display:flex;flex-direction:column;gap:6px;min-width:0}.receipt-source small{color:var(--el-text-color-secondary);overflow-wrap:anywhere}.source-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.source-actions a{font-size:13px;color:var(--el-color-primary)}.receipt-image{display:block;max-width:100%;height:auto;margin:auto;border:1px solid var(--el-border-color-lighter)}.receipt-form{display:grid;grid-template-columns:1fr 1fr;gap:18px}.receipt-form label{display:flex;flex-direction:column;gap:8px;font-size:13px;min-width:0}.receipt-drop{padding:20px;display:flex;flex-direction:column;gap:10px}.receipt-drop span,.muted{font-size:13px;color:var(--el-text-color-secondary);line-height:1.7}.upload-reports{padding-left:20px;font-size:13px;line-height:1.8;max-height:200px;overflow:auto;overflow-wrap:anywhere}.page-error,[role=alert]{color:var(--el-color-danger)}.receipt-search input:focus,.receipt-search select:focus,.receipt-form input:focus,.receipt-form textarea:focus{outline:2px solid var(--el-color-primary-light-5);outline-offset:1px}
@media(max-width:1100px){.receipt-library{grid-template-columns:260px minmax(0,1fr)}.receipt-content-header{flex-wrap:wrap}.receipt-details{padding:12px}}
@media(max-width:760px){.receipt-library{height:auto;min-height:0;grid-template-columns:1fr}.receipt-sidebar{max-height:550px}.receipt-cards{max-height:280px}.receipt-details{overflow:visible}.receipt-info,.receipt-source{padding:14px}.receipt-info dl,.receipt-form{grid-template-columns:1fr}.receipt-amount{font-size:22px}.receipt-content-header{padding:12px}.receipt-form input,.receipt-form textarea,.receipt-search input,.receipt-search select{min-height:44px}}
</style>
