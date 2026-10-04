<script setup lang="ts">
import {computed, onBeforeUnmount, onDeactivated, ref} from 'vue'
import {onBeforeRouteLeave, onBeforeRouteUpdate} from 'vue-router'
import {ElMessage, ElMessageBox} from 'element-plus'
import {query, request} from '../../api'
import {formatMoney} from './money'
import type {Row} from './model'

const emit = defineEmits<{changed: []; busy: [value:boolean]}>()
const visible = ref(false), payments = ref<Row[]>([]), paymentId = ref<number>()
const payment = computed(() => payments.value.find(row => Number(row.id) === paymentId.value))
const linked = ref<Row[]>([]), candidates = ref<Row[]>([]), selected = ref<number[]>([])
const keyword = ref(''), page = ref(1), count = ref(0)
const loading = ref(false), saving = ref(false), uncertain = ref(false), loadFailed = ref(false), error = ref('')
const locked = computed(() => loading.value || saving.value || uncertain.value || loadFailed.value)
let revision = 0
const endpoint = (id:number) => `/payment-receipts/for-payment/${id}`
const payer = (row:Row) => row.payer_supplier_name || row.payer_name || '未填写付款单位'
const payee = (row:Row) => row.payee_supplier_name || '未填写收款单位'
const receiptLabel = (row:Row) => row.receipt_number || row.file_name || `回单 ${row.id}`
const receiptMoney = (row:Row) => row.amount == null ? '金额待填写' : `¥${formatMoney(row.amount)}`

function apply(data:Row) {
 if(!Array.isArray(data?.linked) || !Array.isArray(data?.candidates)) throw new Error('回单列表返回异常，请重新加载核对')
 if(data.payment && Number(data.payment.id) === paymentId.value) payments.value = payments.value.map(row => Number(row.id) === paymentId.value ? data.payment : row)
 linked.value = data.linked; candidates.value = data.candidates; count.value = Number(data.count) || 0
}
function reset() {
 revision++; visible.value = false; loading.value = false; paymentId.value = undefined
 linked.value = []; candidates.value = []; selected.value = []; count.value = 0
 keyword.value = ''; page.value = 1; error.value = ''; uncertain.value = false; loadFailed.value = false
}
async function close() {
 if(saving.value) {ElMessage.warning('正在保存回单关联，请等待完成'); return false}
 reset(); return true
}
async function beforeClose(done:() => void) {if(await close()) done()}
async function open(rows:Row[], selectedPaymentId?:number) {
 if(saving.value) return
 reset(); payments.value = rows.filter(row => Number(row.id) > 0); visible.value = true
 paymentId.value = payments.value.some(row => Number(row.id) === selectedPaymentId) ? selectedPaymentId : payments.value.length === 1 ? Number(payments.value[0]!.id) : undefined
 if(paymentId.value) void load()
}
defineExpose({open,close,busy:saving})

async function load(clearSelection = true) {
 const id = paymentId.value
 if(!id) return
 const current = ++revision
 loading.value = true; error.value = ''
 try {
  const result = await request(`${endpoint(id)}?${query({q:keyword.value,page:page.value})}`)
  if(current !== revision || id !== paymentId.value) return
  apply(result.data)
  if(clearSelection) selected.value = []
  else selected.value = selected.value.filter(receiptId => !linked.value.some(row => Number(row.id) === receiptId))
  uncertain.value = false; loadFailed.value = false
 } catch(cause) {
  if(current === revision) {error.value = cause instanceof Error ? cause.message : '回单加载失败，请重试'; loadFailed.value = true}
 } finally {if(current === revision) loading.value = false}
}
async function changePayment(event:Event) {
 const input = event.target as HTMLSelectElement
 const next = Number(input.value) || undefined
 if(saving.value) {input.value = paymentId.value ? String(paymentId.value) : ''; return}
 revision++; paymentId.value = next; selected.value = []; linked.value = []; candidates.value = []
 keyword.value = ''; page.value = 1; count.value = 0; loading.value = false; error.value = ''; uncertain.value = false; loadFailed.value = false
 if(next) void load()
}
async function search() {
 if(locked.value) return
 page.value = 1; void load()
}
async function turn(step:number) {
 if(locked.value) return
 page.value += step; void load()
}
async function save() {
 const id = paymentId.value
 if(!id || locked.value || !selected.value.length) return
 const current = revision
 const ids = [...selected.value]
 saving.value = true; emit('busy',true); error.value = ''
 try {
  const result = await request(endpoint(id),{method:'POST',body:JSON.stringify({receipt_ids:ids})})
  if(current !== revision || id !== paymentId.value) return
  apply(result.data); selected.value = []; keyword.value = ''; page.value = 1; uncertain.value = false; emit('changed')
 } catch(cause) {
  if(current === revision) {
   error.value = cause instanceof Error ? cause.message : '关联保存失败，请重试'
   uncertain.value = !!(cause as {uncertain?:boolean})?.uncertain
  }
 } finally {saving.value = false; emit('busy',false)}
}
async function unlink(row:Row) {
 const id = paymentId.value, current = revision
 if(!id || locked.value) return
 try {await ElMessageBox.confirm(`解除回单 ${receiptLabel(row)} 与付款单 ${payment.value?.pay_number} 的关联？回单文件仍保留在回单库。`,'解除关联',{type:'warning',confirmButtonText:'解除关联',cancelButtonText:'取消'})} catch {return}
 if(saving.value || current !== revision || id !== paymentId.value) return
 saving.value = true; emit('busy',true); error.value = ''
 try {
  await request(`/payment-receipts/${row.id}/payments/${id}`,{method:'DELETE'})
  if(current !== revision || id !== paymentId.value) return
  linked.value = linked.value.filter(item => Number(item.id) !== Number(row.id)); emit('changed')
  await load(false)
 } catch(cause) {
  if(current === revision) {
   error.value = cause instanceof Error ? cause.message : '解除关联失败，请重试'
   uncertain.value = !!(cause as {uncertain?:boolean})?.uncertain
  }
 } finally {saving.value = false; emit('busy',false)}
}
function blockNavigation(event:Event) {if(saving.value) event.preventDefault()}
async function leave() {return !visible.value || await close()}
onBeforeRouteLeave(leave)
onBeforeRouteUpdate(leave)
onDeactivated(() => {if(!saving.value && !selected.value.length) reset()})
onBeforeUnmount(() => {revision++})
</script>

<template>
 <el-dialog v-model="visible" title="关联付款回单" width="780px" class="payment-receipt-dialog" append-to-body :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="beforeClose">
  <section class="payment-receipt-picker" :aria-busy="loading || saving">
   <div v-if="!payments.length" class="muted"><slot name="empty">订单尚无付款单，请先新增付款单。</slot></div>
   <template v-else>
    <label class="payment-target">付款单
     <select :value="paymentId || ''" aria-label="选择付款单" :disabled="saving" @change="changePayment">
      <option value="" disabled>请选择付款单</option>
      <option v-for="row in payments" :key="row.id" :value="row.id">{{row.pay_number}} · ¥{{formatMoney(row.current_payment_amount)}} · {{payee(row)}}</option>
     </select>
    </label>
    <p v-if="!payment" class="muted">请选择付款单，再勾选对应付款回单。</p>
    <template v-else>
     <div class="current-payment" aria-label="当前付款单"><strong>{{payment.pay_number}}</strong><b>¥{{formatMoney(payment.current_payment_amount)}}</b><span>{{payer(payment)}} → {{payee(payment)}}</span></div>
     <p class="picker-hint">核对付款单位、收款单位、日期及金额后勾选保存。原有回单关联会保留。</p>
     <p v-if="error" role="alert" class="picker-error">{{error}} <el-button data-testid="retry-payment-receipts" link :disabled="saving || loading" @click="load()">重新加载核对</el-button></p>
     <p v-if="uncertain" class="picker-error">提交结果尚未确认，请先重新加载核对关联，之后再选择保存。</p>
     <div class="linked-receipts" aria-label="已关联付款回单">
      <header><strong>已关联回单</strong><span>{{linked.length}} 张</span></header>
      <div v-for="row in linked" :key="row.id" class="linked-receipt">
       <span><RouterLink :to="`/payment-receipts?receipt_id=${row.id}`" :aria-disabled="saving" @click="blockNavigation">{{receiptLabel(row)}}</RouterLink><small>{{row.payment_date || '日期未填写'}} · {{row.payee_name || '收款单位未填写'}}</small></span>
       <b>{{receiptMoney(row)}}</b><el-button type="danger" link :aria-label="`解除回单 ${receiptLabel(row)} 的关联`" :disabled="locked" @click="unlink(row)">解除关联</el-button>
      </div>
      <p v-if="!linked.length && !loading && !loadFailed" class="muted">暂未关联付款回单</p>
     </div>
     <form class="receipt-search" @submit.prevent="search"><input v-model="keyword" type="search" aria-label="搜索付款回单" placeholder="搜索回单号、文件名、付款或收款单位…" :disabled="locked" /><el-button native-type="submit" :disabled="locked">查找回单</el-button></form>
     <p v-if="loading" role="status">正在加载付款回单…</p>
     <div v-else class="receipt-choices" aria-label="待关联付款回单">
      <label v-for="row in candidates" :key="row.id" class="receipt-choice" :class="{selected:selected.includes(Number(row.id))}">
       <input v-model="selected" type="checkbox" :value="Number(row.id)" :aria-label="`关联回单 ${receiptLabel(row)}`" :disabled="locked" />
       <span><strong>{{receiptLabel(row)}} <small v-if="row.recommended" class="recommend">收款单位相近，请核对</small></strong><small>{{row.payment_date || '日期未填写'}} · {{row.bank_name || '银行未填写'}}</small><small>{{row.payer_name || '付款单位未填写'}} → {{row.payee_name || '收款单位未填写'}}</small><small v-if="row.remarks">{{row.remarks}}</small></span>
       <b>{{receiptMoney(row)}}</b>
      </label>
      <p v-if="!candidates.length && !error" class="muted">没有符合条件的待关联回单，可前往付款回单库上传。</p>
     </div>
     <div v-if="count>20" class="receipt-pages"><el-button :disabled="locked || page<=1" @click="turn(-1)">上一页</el-button><span>{{page}} / {{Math.ceil(count/20)}} · {{count}} 张</span><el-button data-testid="next-receipt-page" :disabled="locked || page*20>=count" @click="turn(1)">下一页</el-button></div>
    </template>
   </template>
  </section>
  <template #footer><div class="receipt-picker-footer"><RouterLink to="/payment-receipts" :aria-disabled="saving" @click="blockNavigation">打开回单库 / 上传回单</RouterLink><span v-if="payment">已勾选 {{selected.length}} 张</span><el-button :disabled="saving" @click="close">关闭</el-button><el-button type="primary" data-testid="save-payment-receipts" :disabled="!payment || locked || !selected.length" :loading="saving" @click="save">保存关联</el-button></div></template>
 </el-dialog>
</template>

<style scoped>
.payment-receipt-picker{font-size:13px;color:var(--el-text-color-primary)}.payment-target{display:flex;gap:12px;align-items:center;font-weight:600}.payment-target select,.receipt-search input{min-width:0;border:1px solid var(--el-border-color);border-radius:5px;padding:10px 12px;background:var(--el-bg-color);color:var(--el-text-color-primary);font:inherit}.payment-target select{flex:1;width:100%}.current-payment{display:grid;grid-template-columns:1fr auto;gap:8px;padding:12px;margin-top:12px;background:var(--el-color-primary-light-9);border:1px solid var(--el-color-primary-light-7);border-radius:6px;overflow-wrap:anywhere}.current-payment span{grid-column:1/-1;color:var(--el-text-color-regular)}.current-payment b,.receipt-choice b,.linked-receipt b{font-family:monospace;white-space:nowrap}.picker-hint,.muted,.receipt-choice small,.linked-receipt small{font-size:12px;line-height:1.6;color:var(--el-text-color-secondary)}.picker-error{color:var(--el-color-danger);overflow-wrap:anywhere}.linked-receipts{margin:16px 0;padding-bottom:10px;border-bottom:1px solid var(--el-border-color-lighter)}.linked-receipts header{display:flex;gap:10px;align-items:center}.linked-receipts header>span{color:var(--el-text-color-secondary);font-size:12px}.linked-receipt{display:flex;gap:10px;align-items:center;padding:10px;margin-top:8px;border-radius:5px;background:var(--el-color-success-light-9)}.linked-receipt>span,.receipt-choice>span{display:flex;flex-direction:column;gap:4px;flex:1;min-width:0;overflow-wrap:anywhere}.linked-receipt a,.receipt-picker-footer a{color:var(--el-color-primary)}.receipt-search{display:flex;gap:10px;margin:14px 0 8px}.receipt-search input{flex:1}.receipt-choices{max-height:310px;overflow:auto}.receipt-choice{display:flex;align-items:flex-start;gap:10px;padding:12px;border:1px solid var(--el-border-color-lighter);border-radius:6px;margin:8px 0;cursor:pointer}.receipt-choice.selected{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}.receipt-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.receipt-choice .recommend{color:var(--el-color-success-dark-2);display:inline-block}.receipt-pages{display:flex;justify-content:center;gap:12px;align-items:center;margin-top:14px}.receipt-pages span{font-size:12px;color:var(--el-text-color-secondary)}.receipt-picker-footer{display:flex;gap:10px;justify-content:flex-end;align-items:center;flex-wrap:wrap}.receipt-picker-footer>a{margin-right:auto;font-size:13px}.receipt-picker-footer>span{font-size:12px;color:var(--el-text-color-secondary)}a[aria-disabled=true]{pointer-events:none;opacity:.6}@media(max-width:600px){.payment-target{align-items:flex-start;flex-direction:column;gap:8px}.receipt-search{flex-wrap:wrap}.receipt-search input{min-width:100%;box-sizing:border-box}.linked-receipt{flex-wrap:wrap}.linked-receipt>span{min-width:calc(100% - 20px)}.receipt-choice{padding:10px 8px;gap:7px}.receipt-picker-footer>a{width:100%;text-align:left}.current-payment{grid-template-columns:1fr}.current-payment b{grid-row:2}.current-payment span{grid-row:3}}
</style>
<style>
.payment-receipt-dialog{max-width:calc(100vw - 32px);margin-top:8vh!important}.payment-receipt-dialog .el-dialog__body{max-height:70vh;overflow:auto}.payment-receipt-dialog .el-dialog__footer{border-top:1px solid var(--el-border-color-lighter);padding-top:14px}@media(max-width:600px){.payment-receipt-dialog{max-width:calc(100vw - 16px);margin-top:3vh!important}.payment-receipt-dialog .el-dialog__body{max-height:72vh}}
</style>
