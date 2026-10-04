<script setup lang="ts">
import {onActivated, onBeforeUnmount, ref, watch} from 'vue'
import {request} from '../../api'
import type {Row} from './model'
import PaymentReceiptPicker from './PaymentReceiptPicker.vue'
const props = defineProps<{paymentId:number|string;payment?:Row}>()
const receiptPicker = ref<InstanceType<typeof PaymentReceiptPicker>>()
const rows = ref<Row[]>([]), error = ref(''), count = ref(0), loading = ref(false)
let revision = 0, activated = false
async function load() {
 const current = ++revision
 loading.value = true; error.value = ''
 try {const result = await request(`/payment-receipts?payment_id=${encodeURIComponent(props.paymentId)}&limit=100`); if(!Array.isArray(result.data)) throw new Error('回单列表返回异常，请重试'); if(current === revision) {rows.value = result.data; count.value = result.count || 0}}
 catch(e) {if(current === revision) error.value = e instanceof Error ? e.message : '回单加载失败'}
 finally {if(current === revision) loading.value = false}
}
watch(() => props.paymentId, () => {rows.value = []; void load()}, {immediate:true})
onActivated(() => {if(activated) void load(); activated = true})
onBeforeUnmount(() => {revision++})
</script>
<template>
 <section class="payment-receipts-panel" aria-label="付款单的回单">
  <header><strong>付款回单 <small v-if="count">（{{count}}）</small></strong><div class="receipt-actions"><button aria-label="关联付款回单" @click="receiptPicker?.open([payment || {id:paymentId}])">关联付款回单</button><RouterLink to="/payment-receipts">收集回单</RouterLink></div></header>
  <p v-if="loading" role="status">正在加载回单…</p>
  <p v-else-if="error" role="alert">{{error}} <el-button link @click="load">重试</el-button></p>
  <p v-else-if="!rows.length" class="muted">暂无关联回单，点击“关联付款回单”选择已有回单，或到回单库上传。</p>
  <RouterLink v-for="row in rows" :key="row.id" class="receipt-file" :to="`/payment-receipts?receipt_id=${row.id}`"><span>{{row.receipt_number || row.file_name}}</span><small>{{row.payment_date || '日期未填写'}} · 查看回单</small></RouterLink>
  <PaymentReceiptPicker ref="receiptPicker" @changed="load" />
 </section>
</template>
<style scoped>
.payment-receipts-panel{padding:18px;border:1px solid var(--el-border-color);border-radius:8px;background:var(--el-bg-color);margin:16px 0;font-size:13px}.payment-receipts-panel header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.payment-receipts-panel a{color:var(--el-color-primary)}.receipt-file{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:12px 0;border-bottom:1px solid var(--el-border-color-lighter);overflow-wrap:anywhere}.receipt-file small,.muted{color:var(--el-text-color-secondary)}[role=alert]{color:var(--el-color-danger)}
.receipt-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.receipt-actions button{border:1px solid var(--el-border-color);border-radius:4px;background:var(--el-color-primary-light-9);color:var(--el-color-primary);padding:7px 10px;font:inherit;cursor:pointer}
</style>
