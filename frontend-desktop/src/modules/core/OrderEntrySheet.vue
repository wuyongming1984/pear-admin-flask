<script setup lang="ts">
import SupplierContactSelect from './SupplierContactSelect.vue'
import {formatMoney, uppercaseMoney} from './money'
import {schemas, type Row} from './model'

defineProps<{record: Row; options: Record<string, Row[]>; disabled: boolean}>()
const emit = defineEmits<{field: [key: string, value: unknown]}>()
const field = (key: string) => schemas.orders!.fields.find(f => f.key === key)!
const rows = [
  ['project_id'],
  ['material_name', 'supplier_id'],
  ['material_details'],
  ['order_amount', 'balance'],
  ['cutting_time', 'estimated_arrival_time'],
  ['supplier_contact_person', 'contact_phone'],
  ['material_manager', 'sub_project_manager'],
]
const date = new Date().toLocaleDateString('sv-SE')
</script>

<template>
  <article class="order-entry-sheet" aria-label="新增采购订单审批单">
    <header class="order-entry-header"><h2>采购订单审批单</h2><p>项目管理系统标准单据</p></header>
    <div class="order-entry-meta">
      <label for="entry-order-number">单据编号：<el-input id="entry-order-number" aria-label="订单编号" placeholder="留空自动生成" :model-value="record.order_number" :disabled="disabled" @update:model-value="emit('field', 'order_number', $event)"/></label>
      <span>填单日期：{{date}}</span>
    </div>
    <table class="order-entry-table">
      <colgroup><col class="label-column"/><col/><col class="label-column"/><col/></colgroup>
      <tbody>
        <tr v-for="(keys, index) in rows" :key="index">
          <template v-for="key in keys" :key="key">
            <template v-if="key === 'balance'"><th scope="row">当前余额</th><td class="order-entry-balance"><strong>{{record.order_amount ? '¥ ' + formatMoney(record.order_amount) : '—'}}</strong><small>新增订单尚无付款记录</small></td></template>
            <template v-else>
              <th scope="row"><label :for="'entry-order-' + key">{{field(key).label}}<span v-if="field(key).required" class="required"> *</span></label></th>
              <td :colspan="keys.length === 1 ? 3 : 1">
                <SupplierContactSelect v-if="key === 'supplier_contact_person'" :id="'entry-order-' + key" :record="record" :suppliers="options.suppliers || []" :disabled="disabled" @select="emit('field', 'supplier_id', $event)"/>
                <el-select v-else-if="field(key).kind === 'select'" :id="'entry-order-' + key" :aria-label="field(key).label" :model-value="record[key]" filterable clearable :placeholder="'选择' + field(key).label" :disabled="disabled" @update:model-value="emit('field', key, $event)"><el-option v-for="option in options[field(key).source!]" :key="option.value" :value="option.value" :label="option.label"/></el-select>
                <el-date-picker v-else-if="field(key).kind === 'date'" :id="'entry-order-' + key" :aria-label="field(key).label" :model-value="record[key]" value-format="YYYY-MM-DD" :placeholder="'选择' + field(key).label" :disabled="disabled" @update:model-value="emit('field', key, $event)"/>
                <el-input v-else :id="'entry-order-' + key" :aria-label="field(key).label" :class="{'order-entry-amount': key === 'order_amount'}" :model-value="record[key]" :type="field(key).kind === 'textarea' ? 'textarea' : 'text'" :rows="3" :readonly="key === 'contact_phone'" :inputmode="field(key).kind === 'money' ? 'decimal' : undefined" :placeholder="key === 'contact_phone' ? '选择联系人后自动带出' : field(key).kind === 'money' ? '0.00' : '填写' + field(key).label" :disabled="disabled" @update:model-value="emit('field', key, $event)"/>
                <small v-if="key === 'order_amount'" class="order-entry-capital">{{record.order_amount ? uppercaseMoney(record.order_amount) : '填写金额后显示大写'}}</small>
              </td>
            </template>
          </template>
        </tr>
        <tr><th scope="row">付款记录</th><td colspan="3" class="order-entry-note">保存订单后，可在订单卡片下方新增付款单。</td></tr>
        <tr><th scope="row">附件文件</th><td colspan="3"><slot name="attachments"/></td></tr>
      </tbody>
    </table>
    <div class="order-entry-approvals"><section v-for="title in ['材料员 / 经办人', '项目经理审批', '财务审核', '公司领导审批']" :key="title"><h3>{{title}}</h3><div class="signature-line"></div><small>日期：　　/　　/　　</small></section></div>
    <footer class="order-entry-actions"><slot name="actions"/></footer>
  </article>
</template>

<style scoped>
.order-entry-sheet{max-width:1100px;box-sizing:border-box;margin:0 auto;padding:32px;background:#fff;border:1px solid #d8dfda;box-shadow:0 3px 12px #18352c0a;color:#171717}.order-entry-header{text-align:center;border-bottom:2px solid #222;padding-bottom:18px;margin-bottom:18px}.order-entry-header h2{font:700 28px SimSun,serif;letter-spacing:4px;margin:0 0 10px}.order-entry-header p{margin:0;color:#555;font:14px SimSun,serif}.order-entry-meta{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;font-size:12px}.order-entry-meta label{display:flex;align-items:center;white-space:nowrap}.order-entry-meta .el-input{width:230px}.order-entry-table{width:100%;border-collapse:collapse;table-layout:fixed}.label-column{width:115px}.order-entry-table th,.order-entry-table td{border:1px solid #333;padding:9px 12px;text-align:left;vertical-align:middle;overflow-wrap:anywhere}.order-entry-table th{font:14px SimSun,serif;background:#f5f5f5}.order-entry-table td{font-size:13px}.required{color:#b54934}.order-entry-capital,.order-entry-balance small{display:block;margin-top:6px;font-size:12px;color:#777}.order-entry-balance strong{font:700 20px Consolas,monospace}.order-entry-amount :deep(input){font:700 22px Consolas,monospace}.order-entry-note{color:#777}.order-entry-approvals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;margin-top:26px}.order-entry-approvals section{min-width:0;padding-top:10px}.order-entry-approvals h3{font:700 13px SimSun,serif;margin:0;text-align:center}.signature-line{height:52px;border-bottom:1px solid #333;margin-bottom:10px}.order-entry-approvals small{font-size:11px;color:#777}.order-entry-actions{display:flex;justify-content:flex-end;gap:10px;border-top:1px solid #e1e6e2;padding-top:18px;margin-top:24px}.order-entry-sheet :deep(.el-select),.order-entry-sheet :deep(.el-date-editor.el-input){width:100%;min-width:0}.order-entry-sheet :deep(.el-input__wrapper),.order-entry-sheet :deep(.el-select__wrapper),.order-entry-sheet :deep(.el-textarea__inner){box-shadow:0 0 0 1px #dbe2dd inset;border-radius:3px;background:#fcfdfc}.order-entry-sheet :deep(.el-input__wrapper.is-focus),.order-entry-sheet :deep(.el-select__wrapper.is-focused),.order-entry-sheet :deep(.el-textarea__inner:focus){box-shadow:0 0 0 1px #087f78 inset}.order-entry-table :deep(.toolbar){margin:0;padding:0;background:transparent;border:0;flex-wrap:wrap}.order-entry-table :deep(.el-empty){padding:10px}.order-entry-table :deep(.panel){padding:0;border:0;box-shadow:none}
@media(max-width:1100px){.order-entry-sheet{padding:22px}.label-column{width:92px}.order-entry-table th,.order-entry-table td{padding:8px}}
@media(max-width:700px){.order-entry-sheet{padding:16px}.order-entry-header h2{font-size:23px;letter-spacing:2px}.order-entry-meta{flex-wrap:wrap}.order-entry-meta .el-input{width:190px}.order-entry-table colgroup{display:none}.order-entry-table,.order-entry-table tbody{display:block}.order-entry-table tr{display:grid;grid-template-columns:100px minmax(0,1fr)}.order-entry-table th,.order-entry-table td{border:0;border-bottom:1px solid #ccc}.order-entry-table{border:1px solid #333}.order-entry-table th{border-right:1px solid #ccc}.order-entry-approvals{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
