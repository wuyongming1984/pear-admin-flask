<script setup lang="ts">
import {computed} from 'vue'
import {formatMoney, sumMoney} from './money'
import type {Row} from './model'
const props = defineProps<{modelValue: any[]; invoices: Row[]; supplierName?: string; disabled?: boolean}>()
const emit = defineEmits<{'update:modelValue': [ids: any[]]}>()
const key = (name: unknown) => String(name || '').normalize('NFKC').replace(/\s/g, '').toLowerCase()
const matches = (invoice: Row) => !!key(props.supplierName) && key(invoice.seller_name) === key(props.supplierName)
const selected = (id: any) => props.modelValue.some(value => String(value) === String(id))
const candidates = computed(() => props.invoices.filter(invoice => matches(invoice) || selected(invoice.id)))
const selectedRows = computed(() => props.invoices.filter(invoice => selected(invoice.id)))
function toggle(invoice: Row, event: Event) {
  if (props.disabled) return
  const ids = props.modelValue.filter(id => String(id) !== String(invoice.id))
  if ((event.target as HTMLInputElement).checked && matches(invoice)) ids.push(invoice.id)
  emit('update:modelValue', ids)
}
</script>

<template>
  <section class="payment-invoice-picker" aria-label="关联发票">
    <header><strong>关联发票</strong><span>已选 {{modelValue.length}} 张 · 价税合计 ¥{{sumMoney(selectedRows.map(i => sumMoney([i.total_amount, i.tax_amount])))}}</span></header>
    <p>{{supplierName ? `按销售方匹配：${supplierName}` : '请先选择收款单位，再选择该单位开具的发票。'}}</p>
    <div v-if="candidates.length" class="invoice-choices">
      <label v-for="invoice in candidates" :key="invoice.id" class="invoice-choice" :class="{selected: selected(invoice.id)}">
        <input type="checkbox" :aria-label="`关联发票 ${invoice.invoice_number || invoice.id}`" :checked="selected(invoice.id)" :disabled="disabled" @change="toggle(invoice, $event)" />
        <span><strong>{{invoice.invoice_number || '无发票号码'}}</strong><small>{{invoice.seller_name || '销售方待识别'}} · {{invoice.invoice_date || '日期待识别'}}</small><small v-if="!matches(invoice)" class="legacy-warning">原有关联，与当前收款单位不匹配；更换收款单位时请取消此项。</small></span>
        <b>¥{{formatMoney(sumMoney([invoice.total_amount, invoice.tax_amount]))}}</b>
      </label>
    </div>
    <p v-else class="muted">{{supplierName ? '暂无销售方匹配的发票，可先到发票管理上传识别。' : '选择收款单位后显示匹配发票'}}</p>
    <small class="save-hint">勾选后随付款单一起保存，发票详情中也会显示该付款单。</small>
  </section>
</template>

<style scoped>
.payment-invoice-picker{margin:10px 0 20px;padding:16px;border:1px solid var(--el-border-color);border-radius:8px}.payment-invoice-picker header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.payment-invoice-picker header span,.payment-invoice-picker p,.save-hint{font-size:12px;color:var(--el-text-color-secondary);line-height:1.6}.invoice-choices{max-height:300px;overflow:auto;margin:12px 0}.invoice-choice{display:flex;gap:10px;padding:12px;border:1px solid var(--el-border-color-lighter);border-radius:6px;margin-bottom:8px;align-items:flex-start;cursor:pointer}.invoice-choice.selected{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}.invoice-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.invoice-choice>span{display:flex;flex-direction:column;gap:6px;flex:1;min-width:0;overflow-wrap:anywhere}.invoice-choice small{color:var(--el-text-color-secondary)}.invoice-choice b{white-space:nowrap;font-family:monospace}.invoice-choice .legacy-warning{color:var(--el-color-warning-dark-2)}.muted{padding:8px 0}
</style>
