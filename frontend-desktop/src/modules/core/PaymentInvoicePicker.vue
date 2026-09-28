<script setup lang="ts">
import {computed, onDeactivated, ref} from 'vue'
import {formatMoney, sumMoney} from './money'
import type {Row} from './model'
const props = defineProps<{modelValue: any[]; invoices: Row[]; supplierName?: string; disabled?: boolean}>()
const emit = defineEmits<{'update:modelValue': [ids: any[]]}>()
const key = (name: unknown) => String(name || '').normalize('NFKC').replace(/\s/g, '').toLowerCase()
const matches = (invoice: Row) => !!key(props.supplierName) && key(invoice.seller_name) === key(props.supplierName)
const selected = (id: any) => props.modelValue.some(value => String(value) === String(id))
const candidates = computed(() => props.invoices.filter(invoice => matches(invoice) || selected(invoice.id)))
const selectedRows = computed(() => props.invoices.filter(invoice => selected(invoice.id)))
const visible = ref(false), search = ref(''), draft = ref<any[]>([])
const filtered = computed(() => candidates.value.filter(invoice => !key(search.value) || key([invoice.invoice_number, invoice.seller_name, invoice.buyer_name].join(' ')).includes(key(search.value))))
const draftSelected = (id: any) => draft.value.some(value => String(value) === String(id))
function open() { if (!props.disabled) { draft.value = [...props.modelValue]; search.value = ''; visible.value = true } }
function confirm() { if (!props.disabled) { emit('update:modelValue', [...draft.value]); visible.value = false } }
function remove(id: any) { if (!props.disabled) emit('update:modelValue', props.modelValue.filter(value => String(value) !== String(id))) }
onDeactivated(() => { visible.value = false })
function toggle(invoice: Row, event: Event) {
  if (props.disabled) return
  const ids = draft.value.filter(id => String(id) !== String(invoice.id))
  if ((event.target as HTMLInputElement).checked && matches(invoice)) ids.push(invoice.id)
  draft.value = ids
}
</script>

<template>
  <section class="payment-invoice-picker" aria-label="关联发票">
    <header><strong>关联发票</strong><span>已选 {{modelValue.length}} 张 · 价税合计 ¥{{sumMoney(selectedRows.map(i => sumMoney([i.total_amount, i.tax_amount])))}}</span></header>
    <p>由你选择需要关联的发票，确认后随付款单一起保存。</p>
    <el-button data-testid="choose-invoices" :disabled="disabled" @click="open">选择关联发票</el-button>
    <div v-if="selectedRows.length" class="invoice-choices" aria-label="已选择的发票">
      <div v-for="invoice in selectedRows" :key="invoice.id" class="invoice-choice selected">
        <span><strong>{{invoice.invoice_number || '无发票号码'}}</strong><small>{{invoice.seller_name || '销售方待识别'}}</small></span>
        <b>¥{{formatMoney(sumMoney([invoice.total_amount, invoice.tax_amount]))}}</b>
        <el-button link :disabled="disabled" :aria-label="`移除发票 ${invoice.invoice_number || invoice.id}`" @click="remove(invoice.id)">移除</el-button>
      </div>
    </div>
    <p v-else class="muted">尚未选择关联发票</p>
    <el-dialog v-model="visible" title="选择关联发票" width="760px" class="payment-invoice-dialog" append-to-body :close-on-click-modal="false">
    <p>{{supplierName ? `按销售方匹配：${supplierName}` : '请先选择收款单位，再选择该单位开具的发票。'}}</p>
    <input v-model="search" class="invoice-search" type="search" aria-label="搜索可关联发票" placeholder="搜索发票号码、销售方或购买方" />
    <div v-if="filtered.length" class="invoice-choices">
      <label v-for="invoice in filtered" :key="invoice.id" class="invoice-choice" :class="{selected: draftSelected(invoice.id)}">
        <input type="checkbox" :aria-label="`关联发票 ${invoice.invoice_number || invoice.id}`" :checked="draftSelected(invoice.id)" :disabled="disabled" @change="toggle(invoice, $event)" />
        <span><strong>{{invoice.invoice_number || '无发票号码'}}</strong><small>{{invoice.seller_name || '销售方待识别'}} · {{invoice.invoice_date || '日期待识别'}}</small><small v-if="!matches(invoice)" class="legacy-warning">原有关联，与当前收款单位不匹配；更换收款单位时请取消此项。</small></span>
        <b>¥{{formatMoney(sumMoney([invoice.total_amount, invoice.tax_amount]))}}</b>
      </label>
    </div>
    <p v-else class="muted">{{search ? '没有找到符合搜索条件的发票' : supplierName ? '暂无销售方匹配的发票，可先到发票管理上传识别。' : '选择收款单位后显示匹配发票'}}</p>
    <template #footer><span class="selection-count">已选 {{draft.length}} 张</span><el-button data-testid="cancel-invoice-selection" @click="visible=false">取消</el-button><el-button type="primary" data-testid="confirm-invoice-selection" :disabled="disabled" @click="confirm">确认选择</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.payment-invoice-picker{margin:10px 0 20px;padding:16px;border:1px solid var(--el-border-color);border-radius:8px}.payment-invoice-picker header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.payment-invoice-picker header span,.payment-invoice-picker p,.save-hint{font-size:12px;color:var(--el-text-color-secondary);line-height:1.6}.invoice-choices{max-height:300px;overflow:auto;margin:12px 0}.invoice-choice{display:flex;gap:10px;padding:12px;border:1px solid var(--el-border-color-lighter);border-radius:6px;margin-bottom:8px;align-items:flex-start;cursor:pointer}.invoice-choice.selected{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}.invoice-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.invoice-choice>span{display:flex;flex-direction:column;gap:6px;flex:1;min-width:0;overflow-wrap:anywhere}.invoice-choice small{color:var(--el-text-color-secondary)}.invoice-choice b{white-space:nowrap;font-family:monospace}.invoice-choice .legacy-warning{color:var(--el-color-warning-dark-2)}.muted{padding:8px 0}
</style>
<style>
.payment-invoice-dialog{max-width:calc(100vw - 32px)}.payment-invoice-dialog .invoice-choices{max-height:45vh}.payment-invoice-dialog .invoice-search{width:100%;box-sizing:border-box;border:1px solid var(--el-border-color);border-radius:6px;padding:10px 12px;font:inherit;color:var(--el-text-color-primary);background:var(--el-bg-color)}.payment-invoice-dialog .selection-count{margin-right:16px;font-size:13px}
</style>
