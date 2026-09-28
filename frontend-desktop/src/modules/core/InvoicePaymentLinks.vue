<script setup lang="ts">
import {computed, onActivated, onBeforeUnmount, ref, watch} from 'vue'
import {request} from '../../api'
import {formatMoney} from './money'
import type {Row} from './model'
const props = defineProps<{invoiceId: number | string; disabled?: boolean}>()
const emit = defineEmits<{busy: [value: boolean]; changed: []}>()
const linked = ref<Row[]>([]), matched = ref<Row[]>([]), selected = ref<number[]>([])
const seller = ref(''), loading = ref(false), saving = ref(false), error = ref(''), saved = ref(false)
let revision = 0
const candidates = computed(() => matched.value.filter(p => !linked.value.some(item => item.id === p.id)))
const url = () => `/invoice-links/invoices/${props.invoiceId}/payments`
function apply(data: Row) { linked.value = data.linked || []; matched.value = data.matched || []; seller.value = data.seller_name || '' }
async function load() {
  const current = ++revision
  linked.value = []; matched.value = []; selected.value = []; error.value = ''; saved.value = false; loading.value = true
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
    <header><strong>关联付款单</strong><span v-if="seller">销售方：{{seller}}</span></header>
    <p v-if="loading" role="status">正在匹配付款单…</p>
    <div v-if="error" role="alert" class="link-error">{{error}} <el-button v-if="!seller" link @click="load">重新加载</el-button></div>
    <div v-if="linked.length" class="linked-payments" aria-label="已关联付款单">
      <div v-for="pay in linked" :key="pay.id" class="linked-payment"><span class="linked-label">已关联</span><RouterLink :to="`/payments/${pay.id}`">{{pay.pay_number}}</RouterLink><span>{{pay.project_name || pay.payee_supplier_name}}</span><b>¥{{formatMoney(pay.current_payment_amount)}}</b></div>
    </div>
    <p v-else-if="!loading && !error" class="muted">暂未关联付款单</p>
    <div v-if="candidates.length" class="payment-choices">
      <p>已找到销售方匹配的付款单，勾选后保存关联：</p>
      <label v-for="pay in candidates" :key="pay.id" class="payment-choice">
        <input v-model="selected" type="checkbox" :value="pay.id" :aria-label="`关联付款单 ${pay.pay_number}`" :disabled="saving || disabled" />
        <span><strong>{{pay.pay_number}}</strong><small>{{pay.project_name || '未关联项目'}} · {{pay.create_at || '日期未填写'}}</small><small>{{pay.payment_purpose || pay.payee_supplier_name}}</small></span>
        <b>¥{{formatMoney(pay.current_payment_amount)}}</b>
      </label>
    </div>
    <p v-else-if="!loading && !error" class="muted">{{!seller ? '销售方尚未识别，请完善发票销售方后再关联。' : linked.length ? '匹配的付款单已全部关联' : '未找到收款单位与此销售方一致的付款单。'}}</p>
    <footer v-if="candidates.length || saved"><span v-if="saved" role="status" class="link-success">关联已保存，付款单中也可查看此发票。</span><el-button v-if="candidates.length" type="primary" data-testid="save-payment-links" :loading="saving" :disabled="disabled || loading || !selected.length" @click="save">保存关联{{selected.length ? `（${selected.length} 张）` : ''}}</el-button></footer>
  </section>
</template>

<style scoped>
.invoice-payment-links{width:100%;box-sizing:border-box;color:var(--el-text-color-primary);background:var(--el-bg-color);border:1px solid var(--el-border-color);border-radius:8px;padding:16px;margin:16px auto;max-width:1100px;font-size:13px}.invoice-payment-links header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}.invoice-payment-links header span,.muted,.payment-choices>p{font-size:12px;color:var(--el-text-color-secondary);line-height:1.6}.payment-choices{max-height:260px;overflow:auto}.payment-choice{display:flex;gap:10px;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--el-border-color-lighter);cursor:pointer}.payment-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.payment-choice>span{display:flex;flex-direction:column;flex:1;min-width:0;gap:5px;overflow-wrap:anywhere}.payment-choice small{color:var(--el-text-color-secondary)}.payment-choice b{white-space:nowrap;font-family:monospace}.linked-payment{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px;border-radius:6px;background:var(--el-color-success-light-9);margin-top:10px}.linked-payment a{color:var(--el-color-primary)}.linked-payment b{margin-left:auto}.linked-label,.link-success{color:var(--el-color-success-dark-2)}.link-error{margin-top:12px;color:var(--el-color-danger);line-height:1.6}.invoice-payment-links footer{display:flex;align-items:center;justify-content:flex-end;gap:12px;margin-top:14px;flex-wrap:wrap}
</style>
