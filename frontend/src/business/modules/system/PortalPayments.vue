<script setup lang="ts">
import type {Row} from './helpers'
defineProps<{rows:Row[]}>()
const money=(value:any)=>Number(value||0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})
</script>
<template><div class="payments"><div v-for="pay in rows" :key="pay.id" class="payment"><div><span class="muted">{{String(pay.create_at||'').slice(0,10)}} · {{pay.pay_number||pay.payment_number||''}}</span><p>{{pay.payer_supplier_name||pay.payer_name||pay.payer?.name||'—'}} → {{pay.payee_supplier_name||pay.payee_supplier?.name||pay.payee_name||'—'}}</p><p v-if="pay.payment_purpose" class="muted">备注：{{pay.payment_purpose}}</p></div><strong>− ¥ {{money(pay.current_payment_amount)}}</strong></div></div></template>
<style scoped>.payments{background:#f6f9f7;padding:0 16px;border-radius:8px}.payment{display:flex;justify-content:space-between;gap:16px;align-items:center;border-bottom:1px solid #e5eee8;padding:14px 0;font-size:13px}.payment:last-child{border-bottom:none}.payment p{margin:6px 0}.payment strong{color:#348365;white-space:nowrap;font-variant-numeric:tabular-nums}</style>

