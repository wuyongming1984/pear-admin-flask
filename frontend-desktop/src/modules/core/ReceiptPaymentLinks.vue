<script setup lang="ts">
import {computed, onBeforeUnmount, ref, watch} from 'vue'
import {ElMessageBox} from 'element-plus'
import {query, request} from '../../api'
import {formatMoney} from './money'
import type {Row} from './model'

const props = defineProps<{receiptId: number|string; disabled?: boolean}>()
const emit = defineEmits<{changed: []; busy: [value: boolean]}>()
const root = ref<HTMLElement>()
defineExpose({scrollToLinks:() => root.value?.scrollIntoView({behavior:'smooth',block:'start'})})
const linked = ref<Row[]>([]), candidates = ref<Row[]>([]), selected = ref<number[]>([])
const keyword = ref(''), page = ref(1), count = ref(0), loading = ref(false), saving = ref(false), error = ref('')
const locked = computed(() => props.disabled || loading.value || saving.value)
let revision = 0
const endpoint = () => `/payment-receipts/${props.receiptId}/payments`
function apply(data:Row) {linked.value = data.linked || []; candidates.value = data.candidates || []; count.value = data.count || 0}
async function load() {
 const current = ++revision
 loading.value = true; error.value = ''; selected.value = []
 try {const result = await request(`${endpoint()}?${query({q:keyword.value, page:page.value})}`); if(current === revision) apply(result.data || {})}
 catch(e) {if(current === revision) error.value = e instanceof Error ? e.message : '付款单加载失败'}
 finally {if(current === revision) loading.value = false}
}
watch(() => props.receiptId, () => {linked.value = []; candidates.value = []; keyword.value = ''; page.value = 1; void load()}, {immediate:true})
onBeforeUnmount(() => {revision++})
async function save() {
 if(locked.value || !selected.value.length) return
 const current = revision
 saving.value = true; emit('busy',true); error.value = ''
 try {
  const result = await request(endpoint(), {method:'POST',body:JSON.stringify({payment_ids:selected.value})})
  if(current !== revision) return
  apply(result.data || {}); selected.value = []; keyword.value = ''; page.value = 1; emit('changed')
 } catch(e) {if(current === revision) error.value = e instanceof Error ? e.message : '关联保存失败'}
 finally {saving.value = false; emit('busy',false)}
}
async function unlink(pay:Row) {
 if(locked.value) return
 try {await ElMessageBox.confirm(`解除与付款单 ${pay.pay_number} 的关联？`, '解除关联', {type:'warning'})} catch {return}
 const current = revision
 saving.value = true; emit('busy',true); error.value = ''
 try {await request(`${endpoint()}/${pay.id}`, {method:'DELETE'}); if(current === revision) {await load(); emit('changed')}}
 catch(e) {if(current === revision) error.value = e instanceof Error ? e.message : '解除关联失败'}
 finally {saving.value = false; emit('busy',false)}
}
function search() {if(locked.value) return; page.value = 1; void load()}
function turn(step:number) {if(locked.value) return; page.value += step; void load()}
</script>

<template>
 <section ref="root" class="receipt-links" aria-label="回单关联付款单" :aria-busy="loading || saving">
  <header><strong>关联付款单</strong><span>核对单位、金额及用途后勾选保存</span></header>
  <p v-if="error" role="alert" class="link-error">{{error}} <el-button :disabled="saving" link @click="load">重新加载</el-button></p>
  <div class="linked-payments" aria-label="已关联付款单">
   <div v-for="pay in linked" :key="pay.id" class="linked-payment">
    <span class="linked-label">已关联</span><RouterLink :to="`/payments/${pay.id}/edit`">{{pay.pay_number}}</RouterLink>
    <span>{{pay.project_name || pay.payee_supplier_name}}</span><b>¥{{formatMoney(pay.current_payment_amount)}}</b>
    <el-button type="danger" link :disabled="locked" @click="unlink(pay)">解除关联</el-button>
   </div>
   <p v-if="!linked.length && !loading" class="muted">暂未关联付款单</p>
  </div>
  <form class="payment-search" @submit.prevent="search">
   <input v-model="keyword" aria-label="搜索待关联付款单" placeholder="搜索付款编号、项目或单位…" :disabled="locked" />
   <el-button :disabled="locked" native-type="submit">查找付款单</el-button>
  </form>
  <p v-if="loading" role="status">正在查找付款单…</p>
  <div v-else class="payment-choices">
   <label v-for="pay in candidates" :key="pay.id" class="payment-choice">
    <input v-model="selected" type="checkbox" :value="pay.id" :aria-label="`关联付款单 ${pay.pay_number}`" :disabled="locked" />
    <span><strong>{{pay.pay_number}} <small v-if="pay.recommended" class="recommend">收款单位相近</small></strong>
     <small>{{pay.project_name || '未关联项目'}} · {{pay.create_at || '日期未填写'}}</small>
     <small>{{pay.payer_name || '未填写付款单位'}} → {{pay.payee_supplier_name || '未填写收款单位'}}</small>
     <small v-if="pay.payment_purpose">{{pay.payment_purpose}}</small></span>
    <b>¥{{formatMoney(pay.current_payment_amount)}}</b>
   </label>
   <p v-if="!candidates.length && !error" class="muted">没有符合条件的待关联付款单</p>
  </div>
  <footer>
   <div v-if="count>20" class="candidate-pages"><el-button :disabled="locked || page<=1" @click="turn(-1)">上一页</el-button><span>{{page}} / {{Math.ceil(count/20)}}</span><el-button :disabled="locked || page*20>=count" @click="turn(1)">下一页</el-button></div>
   <el-button type="primary" data-testid="save-receipt-links" :loading="saving" :disabled="locked || !selected.length" @click="save">保存关联{{selected.length ? `（${selected.length} 张）` : ''}}</el-button>
  </footer>
 </section>
</template>

<style scoped>
.receipt-links{background:var(--el-bg-color);border:1px solid var(--el-border-color);border-radius:8px;padding:18px;font-size:13px}.receipt-links header{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.receipt-links header>span,.muted,.payment-choice small{color:var(--el-text-color-secondary);font-size:12px;line-height:1.6}.linked-payment{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px;background:var(--el-color-success-light-9);border-radius:6px;margin-top:10px}.linked-payment a{color:var(--el-color-primary)}.linked-label,.recommend{color:var(--el-color-success-dark-2)!important}.linked-payment b{margin-left:auto}.payment-search{display:flex;gap:10px;margin:16px 0 8px}.payment-search>input{flex:1;min-width:0;border:1px solid var(--el-border-color);border-radius:4px;padding:9px 12px;background:var(--el-bg-color);color:var(--el-text-color-primary);font:inherit}.payment-choices{max-height:340px;overflow:auto}.payment-choice{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid var(--el-border-color-lighter);cursor:pointer;align-items:flex-start}.payment-choice input{margin-top:3px;accent-color:var(--el-color-primary)}.payment-choice>span{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px;overflow-wrap:anywhere}.payment-choice b,.linked-payment b{white-space:nowrap;font-family:monospace}footer{display:flex;justify-content:flex-end;align-items:center;gap:12px;flex-wrap:wrap;margin-top:14px}.candidate-pages{display:flex;align-items:center;gap:8px;margin-right:auto}.link-error{color:var(--el-color-danger)}@media(max-width:600px){.receipt-links{padding:12px}.payment-search{flex-wrap:wrap}.payment-search>input{min-width:100%}}
</style>
