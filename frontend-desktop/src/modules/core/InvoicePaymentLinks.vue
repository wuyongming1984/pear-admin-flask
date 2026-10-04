<script setup lang="ts">
import {computed, onActivated, onBeforeUnmount, ref, watch} from 'vue'
import {request} from '../../api'
import {formatMoney, sumMoney} from './money'
import {formatInvoiceMoney, type Row} from './model'
const props = defineProps<{invoiceId: number | string; disabled?: boolean}>()
const emit = defineEmits<{busy: [value: boolean]; changed: []}>()
const linked = ref<Row[]>([]), matched = ref<Row[]>([]), selected = ref<number[]>([])
const seller = ref(''), loading = ref(false), saving = ref(false), error = ref(''), saved = ref(false)
const recommendation = ref<Row>({})
let revision = 0
const candidates = computed(() => matched.value.filter(p => !linked.value.some(item => item.id === p.id)))
const knownAmount = (value: unknown) => formatInvoiceMoney(value) !== '待核实'
const selectedAmount = computed(() => {
  const amounts = [...linked.value, ...candidates.value.filter(p => selected.value.includes(p.id))].map(p => p.current_payment_amount)
  return amounts.every(knownAmount) ? sumMoney(amounts) : null
})
const amountDifference = computed(() => {
  const target = recommendation.value.context?.target_amount, amount = selectedAmount.value
  return knownAmount(target) && amount !== null ? sumMoney([target, amount.startsWith('-') ? amount.slice(1) : `-${amount}`]) : null
})
const combinations = computed(() => knownAmount(recommendation.value.context?.target_amount) && knownAmount(recommendation.value.context?.remaining)
  ? (recommendation.value.combinations || []).filter((group: Row) => Array.isArray(group.payment_ids) && group.payment_ids.length && group.payment_ids.every((id: number) => candidates.value.some(p => p.id === id && p.can_recommend))) : [])
const locked = computed(() => loading.value || saving.value || props.disabled)
function chooseCombination(group: Row) {
  if (locked.value || error.value || selected.value.length || !combinations.value.includes(group)) return
  selected.value = [...group.payment_ids]
}
function paymentNumbers(group: Row) { return group.payment_ids.map((id: number) => candidates.value.find(p => p.id === id)?.pay_number || id).join('、') }
const url = () => `/invoice-links/invoices/${props.invoiceId}/payments`
function apply(data: Row) { linked.value = data.linked || []; matched.value = data.matched || []; seller.value = data.seller_name || ''; recommendation.value = data }
async function load() {
  const current = ++revision
  linked.value = []; matched.value = []; selected.value = []; recommendation.value = {}; error.value = ''; saved.value = false; loading.value = true
  try { const result = await request(url()); if (revision === current) apply(result.data || {}) }
  catch (cause) { if (revision === current) error.value = cause instanceof Error ? cause.message : '关联付款单加载失败' }
  finally { if (revision === current) loading.value = false }
}
watch(() => props.invoiceId, load, {immediate: true})
let activated = false
onActivated(() => { if (activated) void load(); activated = true })
onBeforeUnmount(() => { revision++ })
async function save() {
  if (saving.value || loading.value || props.disabled || !selected.value.length) return
  const current = revision
  saving.value = true; emit('busy', true); error.value = ''; saved.value = false
  try {
    const result = await request(url(), {method: 'POST', body: JSON.stringify({payment_ids: selected.value})})
    if (revision !== current) return
    apply(result.data || {}); selected.value = []; saved.value = true; emit('changed')
  } catch (cause) { if (revision === current) error.value = cause instanceof Error ? cause.message : '保存关联失败' }
  finally { saving.value = false; emit('busy', false) }
}
</script>

<template>
  <section class="invoice-payment-links" aria-label="关联付款单" :aria-busy="loading || saving">
    <header><strong>智能关联付款单</strong><span v-if="seller">销售方：{{seller}}</span></header>
    <p v-if="loading" role="status">正在匹配付款单…</p>
    <div v-if="error" role="alert" class="link-error">{{error}} <el-button v-if="!seller" link @click="load">重新加载</el-button></div>
    <div v-if="linked.length" class="linked-payments" aria-label="已关联付款单">
      <div v-for="pay in linked" :key="pay.id" class="linked-payment"><span class="linked-label">已关联</span><RouterLink :to="`/payments/${pay.id}`">{{pay.pay_number}}</RouterLink><span>{{pay.project_name || pay.payee_supplier_name}}</span><b>{{formatInvoiceMoney(pay.current_payment_amount)}}</b></div>
    </div>
    <p v-else-if="!loading && !error" class="muted">暂未关联付款单</p>
    <div v-if="!loading && recommendation.context" class="smart-amount-check" data-testid="payment-amount-check">
      <strong>金额核对</strong><span>发票价税合计 {{formatInvoiceMoney(recommendation.context.target_amount)}} · 已关联及勾选付款 {{formatInvoiceMoney(selectedAmount)}} · 差额 {{formatInvoiceMoney(amountDifference)}}</span>
      <small v-for="reason in recommendation.context.reasons || []" :key="reason">{{reason}}</small>
      <small>金额用于核对；一张发票可关联多次付款，请结合实际业务确认。</small>
    </div>
    <div v-if="!loading && !error && combinations.length" class="smart-combinations" aria-label="智能推荐付款组合">
      <strong>智能推荐</strong>
      <div v-for="(group, index) in combinations" :key="index" class="smart-combination">
        <span>{{paymentNumbers(group)}}<small>合计 ¥{{formatMoney(group.total_gross)}} · {{(group.reasons || []).join('；')}}</small></span>
        <el-button native-type="button" data-testid="choose-payment-combination" :disabled="locked || !!selected.length" @click="chooseCombination(group)">勾选此组合</el-button>
      </div>
      <small v-if="selected.length">已有勾选项，请先清除勾选后再使用推荐组合。</small>
    </div>
    <p v-if="!loading && !error && recommendation.context" class="muted">组合仅核对排名靠前的 {{recommendation.combination_limit || 30}} 条可推荐付款单，每组最多 3 张。{{!combinations.length ? '本次未找到金额合计一致的组合，可继续手动勾选。' : '请核对后保存关联。'}}<span v-if="recommendation.truncated">候选较多，仅展示前 200 条。</span></p>
    <div v-if="candidates.length" class="payment-choices">
      <p>已综合单位、金额、项目和日期排序，请核对推荐依据后勾选保存：</p>
      <label v-for="pay in candidates" :key="pay.id" class="payment-choice">
        <input v-model="selected" type="checkbox" :value="pay.id" :aria-label="`关联付款单 ${pay.pay_number}`" :disabled="locked" />
        <span><strong>{{pay.pay_number}}</strong><small>{{pay.project_name || '未关联项目'}} · {{pay.create_at || '日期未填写'}}</small><small>{{pay.payment_purpose || pay.payee_supplier_name}}</small><small v-if="pay.reasons?.length" :class="pay.can_recommend ? 'match-reasons' : 'match-warning'">{{pay.reasons.join('；')}}</small><small v-if="pay.amount_difference != null">与初始待核对金额差额 ¥{{formatMoney(pay.amount_difference)}}</small></span>
        <b>{{formatInvoiceMoney(pay.current_payment_amount)}}</b>
      </label>
    </div>
    <p v-else-if="!loading && !error" class="muted">{{!seller ? '销售方尚未识别，请完善发票销售方后再关联。' : linked.length ? '匹配的付款单已全部关联' : '未找到收款单位名称与此销售方相近的付款单。'}}</p>
    <footer v-if="candidates.length || saved"><span v-if="saved" role="status" class="link-success">关联已保存，付款单中也可查看此发票。</span><el-button v-if="candidates.length" type="primary" data-testid="save-payment-links" :loading="saving" :disabled="disabled || loading || !selected.length" @click="save">保存关联{{selected.length ? `（${selected.length} 张）` : ''}}</el-button></footer>
  </section>
</template>

<style scoped>
.invoice-payment-links{width:100%;box-sizing:border-box;color:var(--el-text-color-primary);background:var(--el-bg-color);border:1px solid var(--el-border-color);border-radius:8px;padding:16px;margin:16px auto;max-width:1100px;font-size:13px}.invoice-payment-links header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}.invoice-payment-links header span,.muted,.payment-choices>p{font-size:12px;color:var(--el-text-color-secondary);line-height:1.6}.payment-choices{max-height:260px;overflow:auto}.payment-choice{display:flex;gap:10px;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--el-border-color-lighter);cursor:pointer}.payment-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.payment-choice>span{display:flex;flex-direction:column;flex:1;min-width:0;gap:5px;overflow-wrap:anywhere}.payment-choice small{color:var(--el-text-color-secondary)}.payment-choice b{white-space:nowrap;font-family:monospace}.linked-payment{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px;border-radius:6px;background:var(--el-color-success-light-9);margin-top:10px}.linked-payment a{color:var(--el-color-primary)}.linked-payment b{margin-left:auto}.linked-label,.link-success{color:var(--el-color-success-dark-2)}.link-error{margin-top:12px;color:var(--el-color-danger);line-height:1.6}.invoice-payment-links footer{display:flex;align-items:center;justify-content:flex-end;gap:12px;margin-top:14px;flex-wrap:wrap}
</style>
<style scoped>
.smart-amount-check,.smart-combinations{margin-top:14px;padding:12px;border-radius:6px;background:var(--el-fill-color-light);display:flex;flex-direction:column;gap:8px;line-height:1.6}.smart-amount-check small,.smart-combinations small{font-size:12px;color:var(--el-text-color-secondary)}.smart-combination{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 0}.smart-combination>span{flex:1;min-width:0;overflow-wrap:anywhere}.smart-combination small{display:block}.payment-choice .match-reasons{color:var(--el-color-success-dark-2)}.payment-choice .match-warning{color:var(--el-color-warning-dark-2)}
</style>
