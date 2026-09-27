<script setup lang="ts">
import {computed} from 'vue'
import {formatMoney, sumMoney, uppercaseMoney} from './money'
import {suppliersForContact} from './orderContacts'
import type {Row} from './model'

const props = defineProps<{record: Row; original?: Row; order?: Row; supplier?: Row; options: Record<string, Row[]>; disabled: boolean}>()
const payeeOptions = computed(() => suppliersForContact(props.options.suppliers || [], props.order?.supplier_contact_person))
const emit = defineEmits<{field: [key: string, value: unknown]}>()
const update = (key: string, value: unknown) => emit('field', key, value)
const materialName = computed(() => props.options.materials?.find(m => String(m.code) === String(props.order?.material_name))?.label || props.order?.material_name || '—')
const validAmount = computed(() => /^-?\d+(\.\d{0,2})?$/.test(String(props.record.current_payment_amount ?? '')))
const originalAmount = computed(() => props.original && String(props.original.order_id) === String(props.order?.id) ? String(props.original.current_payment_amount ?? 0) : '0')
const paymentTotal = computed(() => props.order && validAmount.value ? sumMoney([props.order.paid_amount ?? 0, originalAmount.value.startsWith('-') ? originalAmount.value.slice(1) : '-' + originalAmount.value, props.record.current_payment_amount]) : null)
const balance = computed(() => paymentTotal.value === null ? null : sumMoney([props.order?.order_amount, paymentTotal.value.startsWith('-') ? paymentTotal.value.slice(1) : '-' + paymentTotal.value]))
const progress = computed(() => paymentTotal.value !== null && Number(props.order?.order_amount) > 0 ? (Number(paymentTotal.value) / Number(props.order?.order_amount) * 100).toFixed(1) + '%' : '—')
const date = computed(() => props.record.create_at?.split(/[T ]/)[0] || (props.record.id != null ? '—' : new Date().toLocaleDateString('sv-SE')))
</script>

<template>
  <div class="payment-entry">
    <article class="payment-entry-sheet" :aria-label="record.id != null ? '编辑付款审批单' : '新增付款审批单'">
      <header class="entry-header">
        <div><h2>付款审批单</h2><small>PAYMENT APPROVAL SHEET</small></div>
        <div class="entry-meta"><label for="entry-pay-number">付款单编号 <span class="required">*</span></label><el-input id="entry-pay-number" aria-label="付款单编号" :model-value="record.pay_number" :disabled="disabled" @update:model-value="update('pay_number', $event)"/><span>日期：{{date}}</span></div>
      </header>
      <div class="entry-grid">
        <section class="entry-panel" aria-label="资金往来信息">
          <h3>资金往来信息 <small>PAYMENT DETAILS</small></h3>
          <div class="entry-row"><label for="entry-amount">付款总额 <span class="required">*</span></label><div class="entry-value"><el-input id="entry-amount" class="entry-amount" aria-label="本次实付金额" inputmode="decimal" placeholder="0.00" :model-value="record.current_payment_amount" :disabled="disabled" @update:model-value="update('current_payment_amount', $event)"><template #prefix>¥</template></el-input><span class="entry-capital">{{record.current_payment_amount ? uppercaseMoney(record.current_payment_amount) : '填写金额后显示大写'}}</span></div></div>
          <div class="entry-row"><label for="entry-payee">收款单位 <span class="required">*</span></label><div class="entry-value"><el-select id="entry-payee" aria-label="收款单位" :model-value="supplier?.id" filterable clearable :disabled="disabled || !order" :placeholder="order ? '选择收款单位' : '请先选择关联订单'" @update:model-value="update('payee_supplier_id', $event)"><el-option v-for="s in payeeOptions" :key="s.id" :value="s.id" :label="s.name"/></el-select><small>{{!order ? '选择订单后显示可选单位' : !payeeOptions.length ? '未找到订单联系人关联的供应商单位，请先完善供应商信息' : '仅可选择订单联系人「' + order.supplier_contact_person + '」关联的单位'}}</small></div></div>
          <div class="entry-row"><span class="entry-label">银行账号</span><div class="entry-value entry-account"><strong>{{supplier?.account_number || '—'}}</strong><small>{{supplier?.bank_name || '选择收款单位后显示开户行'}}</small></div></div>
          <div class="entry-row"><label for="entry-payer">付款单位 <span class="required">*</span></label><div class="entry-value"><el-select id="entry-payer" aria-label="付款单位" filterable clearable placeholder="选择付款单位" :model-value="record.payer_supplier_id" :disabled="disabled" @update:model-value="update('payer_supplier_id', $event)"><el-option v-for="p in options.payers" :key="p.id" :value="p.id" :label="p.label"/></el-select></div></div>
          <div class="entry-row entry-purpose"><label for="entry-purpose">款项用途</label><div class="entry-value"><el-input id="entry-purpose" aria-label="付款用途" type="textarea" :rows="5" placeholder="填写本次付款用途" :model-value="record.payment_purpose" :disabled="disabled" @update:model-value="update('payment_purpose', $event)"/></div></div>
        </section>
        <section class="entry-panel" aria-label="关联项目概要">
          <h3>关联项目概要 <small>PROJECT REF</small></h3>
          <div class="entry-row"><span class="entry-label">项目名称</span><div class="entry-value"><strong>{{order?.project_name || '选择关联订单后显示'}}</strong></div></div>
          <div class="entry-row"><label for="entry-order">订单编号 <span class="required">*</span></label><div class="entry-value"><el-select id="entry-order" aria-label="关联订单" filterable clearable placeholder="选择关联订单" :model-value="record.order_id" :disabled="disabled" @update:model-value="update('order_id', $event)"><el-option v-for="o in options.orders" :key="o.id" :value="o.id" :label="o.label"/></el-select></div></div>
          <div class="entry-row"><span class="entry-label">供应商联系人</span><div class="entry-value" data-testid="payment-order-contact">{{order?.supplier_contact_person || '—'}}</div></div>
          <div class="entry-row"><span class="entry-label">材料服务</span><div class="entry-value">{{materialName}}</div></div>
          <div class="entry-row"><span class="entry-label">订单总额</span><div class="entry-value entry-money">{{order ? '¥ ' + formatMoney(order.order_amount) : '—'}}</div></div>
          <div class="entry-row"><span class="entry-label">累计已付</span><div class="entry-value"><strong class="entry-money" data-testid="payment-total-preview">{{paymentTotal !== null ? '¥ ' + paymentTotal : '—'}}</strong><small>含本次填写金额，保存后生效</small></div></div>
          <div class="entry-row entry-progress"><span class="entry-label">付款进度</span><div class="entry-value"><strong>{{progress}}</strong><small data-testid="payment-balance-preview">预计剩余未付：{{balance !== null ? '¥ ' + balance : '—'}}</small><small>当前已付：{{order ? '¥ ' + formatMoney(order.paid_amount ?? 0) : '—'}}</small></div></div>
        </section>
      </div>
      <div class="entry-approvals">
        <section><h3><label for="entry-handler">经办人 / Handler</label></h3><div class="entry-signature"><el-input id="entry-handler" aria-label="经办人" placeholder="填写经办人" :model-value="record.handler" :disabled="disabled" @update:model-value="update('handler', $event)"/></div><small>Date: . . . . / . . / . .</small></section>
        <section v-for="title in ['项目负责人 / PM', '副总经理审批', '总经理审批']" :key="title"><h3>{{title}}</h3><div class="entry-signature"></div><small>Date: . . . . / . . / . .</small></section>
      </div>
    </article>
    <section class="entry-extra" aria-label="付款状态、发票及附件">
      <div class="entry-extra-fields">
        <el-form-item label="付款状态"><el-select aria-label="付款状态" clearable placeholder="选择付款状态" :model-value="record.payment_status" :disabled="disabled" @update:model-value="update('payment_status', $event)"><el-option v-for="s in options.statuses" :key="s.value" :value="s.value" :label="s.label"/></el-select></el-form-item>
        <el-form-item label="开票金额"><el-input aria-label="开票金额" inputmode="decimal" placeholder="0.00" :model-value="record.invoice_amount" :disabled="disabled" @update:model-value="update('invoice_amount', $event)"/></el-form-item>
      </div>
      <slot name="invoices"/>
      <slot name="attachments"/>
      <div class="entry-actions"><slot name="actions"/></div>
    </section>
  </div>
</template>

<style scoped>
.payment-entry{max-width:1100px;margin:0 auto;color:#171717}.payment-entry-sheet{background:#fff;border:1px solid #d8dfda;box-shadow:0 3px 12px #18352c0a;padding:32px}.entry-header{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;border-bottom:2px solid #222;padding-bottom:14px;margin-bottom:16px}.entry-header h2{font:700 28px SimSun,serif;margin:0 0 6px}.entry-header small{font-size:10px;letter-spacing:1.6px}.entry-meta{display:flex;flex-direction:column;gap:5px;text-align:right;width:250px;max-width:100%;font:12px Consolas,monospace}.entry-meta label{color:#666;font-family:inherit}.entry-meta :deep(input){text-align:right;font-weight:600}.required{color:#b54934}.entry-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:14px}.entry-panel{border:1px solid #333;display:flex;flex-direction:column;min-width:0}.entry-panel h3{display:flex;justify-content:space-between;align-items:center;gap:6px;background:#f2f2f2;border-bottom:1px solid #333;margin:0;padding:8px 10px;font-size:13px}.entry-panel h3 small{font-size:10px;font-weight:400;color:#555}.entry-row{display:flex;border-bottom:1px solid #ddd;min-width:0;min-height:43px}.entry-row:last-child{border-bottom:0}.entry-row>label,.entry-label{display:flex;align-items:center;gap:4px;flex:0 0 100px;padding:9px 10px;border-right:1px solid #ddd;font-size:12px;color:#444;box-sizing:border-box}.entry-value{flex:1;min-width:0;padding:7px 9px;display:flex;flex-direction:column;justify-content:center;gap:5px;font-size:13px;overflow-wrap:anywhere}.entry-value small{font-size:11px;color:#777}.entry-amount :deep(input){font:700 23px Consolas,monospace}.entry-capital{font-size:12px;color:#555}.entry-account strong,.entry-money{font-family:Consolas,monospace}.entry-purpose,.entry-progress{flex:1}.entry-purpose>label{align-items:flex-start;padding-top:16px}.entry-progress strong{font:700 25px Consolas,monospace}.entry-approvals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid #333;margin-top:16px}.entry-approvals>section{border-right:1px solid #333;display:flex;flex-direction:column;min-width:0;min-height:145px}.entry-approvals>section:last-child{border-right:0}.entry-approvals h3{font-size:12px;text-align:center;background:#f2f2f2;border-bottom:1px solid #333;margin:0;padding:7px 3px}.entry-signature{flex:1;display:flex;align-items:center;justify-content:center;padding:10px}.entry-approvals small{text-align:right;color:#999;padding:5px;font:10px Consolas,monospace}.entry-extra{margin-top:18px;padding:22px;background:white;border:1px solid #d8dfda;border-radius:6px}.entry-extra-fields{display:grid;grid-template-columns:1fr 1fr;gap:20px}.entry-actions{display:flex;justify-content:flex-end;gap:10px;border-top:1px solid #e1e6e2;padding-top:16px;margin-top:16px}.payment-entry :deep(.el-input__wrapper),.payment-entry :deep(.el-select__wrapper){box-shadow:0 0 0 1px #dbe2dd inset;border-radius:3px;background:#fcfdfc}.payment-entry :deep(.el-input__wrapper.is-focus),.payment-entry :deep(.el-select__wrapper.is-focused){box-shadow:0 0 0 1px #087f78 inset}.payment-entry :deep(.el-select){width:100%}.payment-entry :deep(.el-textarea__inner){box-shadow:0 0 0 1px #dbe2dd inset;border-radius:3px;background:#fcfdfc}.entry-extra :deep(.toolbar){padding:0;background:transparent;border:0}.entry-extra :deep(.el-empty){padding:10px}
@media(max-width:1100px){.payment-entry-sheet{padding:22px}.entry-row>label,.entry-label{flex-basis:85px;padding:8px}.entry-grid{gap:10px}}
@media(max-width:800px){.entry-grid{grid-template-columns:1fr}.entry-header{align-items:flex-start;flex-wrap:wrap}.entry-meta{text-align:left}.entry-meta :deep(input){text-align:left}.entry-approvals{grid-template-columns:repeat(2,minmax(0,1fr))}.entry-approvals>section:nth-child(2){border-right:0}.entry-approvals>section:nth-child(-n+2){border-bottom:1px solid #333}.entry-extra-fields{grid-template-columns:1fr;gap:0}.payment-entry-sheet,.entry-extra{padding:16px}}
</style>
