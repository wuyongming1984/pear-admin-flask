<script setup lang="ts">
import {computed, ref, watch, nextTick, onActivated, onDeactivated} from 'vue'
import {useRoute, onBeforeRouteLeave} from 'vue-router'
import {ElMessage, ElMessageBox} from 'element-plus'
import {allRows, request} from '../../api'
import OrderAttachments from './OrderAttachments.vue'
import PageHeader from '../../components/PageHeader.vue'
import TablePrint from './TablePrint.vue'
import {useCardColumns} from './useCardColumns'
import {useDocumentWorkspace} from './useDocumentWorkspace'
import {formatMoney, sumMoney} from './money'
import {schemas, type Row, type Field} from './model'

const route = useRoute()
const projectList = ref<HTMLElement>(), contactList = ref<HTMLElement>()
let filterScroll = [0, 0]
onBeforeRouteLeave(() => {filterScroll = [projectList.value?.scrollTop || 0, contactList.value?.scrollTop || 0]})
onActivated(async () => {
  await nextTick()
  if (projectList.value) projectList.value.scrollTop = filterScroll[0]!
  if (contactList.value) contactList.value.scrollTop = filterScroll[1]!
})
const cardColumns = useCardColumns('orders')
const materials = ref<Row[]>([]), deleting = ref(false), exporting = ref(false)
const project = ref(''), contact = ref(''), number = ref(''), projectSearch = ref(''), contactSearch = ref('')
const hideSettled = ref(false), tablePrint = ref(false)
const projectNameQuery = ref('')
const filters = computed(() => ({project_id: project.value, project_name: project.value ? '' : projectNameQuery.value, supplier_contact_person: contact.value, order_number: number.value, hide_settled: hideSettled.value ? '1' : ''}))
const {rows: pageOrders, projects, contacts, totals, count, page, pageCount, busy, error, load} = useDocumentWorkspace('orders', filters)
const fieldLabels: Record<string, string> = {project: '项目名称', material: '材料名称', contact: '供应商联系人', manager: '负责人', amount: '订单金额', balance: '当前余额', date: '时间日期', details: '材料明细', payments: '关联付款单'}
const visibleFields = ref(Object.keys(fieldLabels))
const show = (key: string) => visibleFields.value.includes(key)
const money = (value: unknown) => formatMoney(value ?? 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
const paid = (o: Row) => o.paid_amount ?? sumMoney((o.pays_list || []).map((p: Row) => p.current_payment_amount))
const balance = (o: Row) => o.order_balance ?? sumMoney([o.order_amount, String(paid(o)).startsWith('-') ? String(paid(o)).slice(1) : '-' + paid(o)])
const settled = (o: Row) => Math.abs(Number(balance(o))) <= 0.01
const progress = (o: Row) => Number(o.order_amount) > 0 ? (Number(paid(o)) / Number(o.order_amount) * 100).toFixed(1) + '%' : '—'
const status = (o: Row) => settled(o) ? '已结清' : Number(balance(o)) < 0 ? '超额付款' : Number(paid(o)) > 0 ? '部分付款' : '待付款'
const material = (o: Row) => materials.value.find(m => String(m.code) === String(o.material_name))?.value || o.material_name || '—'
const projectOptions = computed(() => projects.value.map(p => ({id: String(p.id), name: p.project_name})))
const visibleProjects = computed(() => projectOptions.value.filter(p => String(p.name).toLowerCase().includes(projectSearch.value.trim().toLowerCase())))
const visibleContacts = computed(() => contacts.value.filter(c => c.toLowerCase().includes(contactSearch.value.trim().toLowerCase())).sort((a,b) => a.localeCompare(b, 'zh-CN')))
const title = computed(() => `${projectOptions.value.find(p => p.id === project.value)?.name || projectNameQuery.value || '全部项目'} · ${contact.value || '全部联系人'}`)
const printColumns = schemas.orders!.fields.filter(f => ['order_number', 'project_id', 'material_name', 'supplier_contact_person', 'order_amount'].includes(f.key))
function display(o: Row, f: Field) {return f.key === 'project_id' ? o.project_name : f.key === 'material_name' ? material(o) : f.kind === 'money' ? money(o[f.key]) : o[f.key] ?? '—'}
function attachmentsSaved(o: Row, files: Row[]) {o.attachments_list = files; o.attachments = JSON.stringify(files)}
function chooseProject(id: string) {projectNameQuery.value = ''; project.value = id}
function paymentEditor(path: string, orderId?: number) {
  return {path, query: {...(orderId == null ? {} : {order_id: orderId}), returnTo: route.fullPath}}
}
function applyQuery() {
  project.value = String(route.query.project_id || '')
  projectNameQuery.value = String(route.query.project_name || '')
  contact.value = String(route.query.supplier_contact_person || '')
  number.value = String(route.query.order_number || '')
}
let lastQuery = JSON.stringify(route.query)
watch(() => route.fullPath, () => {
  if (route.path === '/orders' && JSON.stringify(route.query) !== lastQuery) {
    lastQuery = JSON.stringify(route.query); applyQuery()
  }
})
applyQuery()
void allRows('/dictionary/detail/list', {dic_id: 35}).then(data => {materials.value = data}).catch(e => ElMessage.error((e as Error).message))
onDeactivated(() => {tablePrint.value = false})
async function remove(o: Row) {
  if (deleting.value) return
  try {await ElMessageBox.confirm(`确定删除订单 ${o.order_number}？此操作无法撤销。`, '删除确认', {type: 'warning'})} catch {return}
  deleting.value = true
  try {await request('/order/' + o.id, {method: 'DELETE'}); ElMessage.success('删除成功'); await load()} catch(e) {ElMessage.error((e as Error).message)} finally {deleting.value = false}
}
async function exportCsv() {
  if (exporting.value) return
  exporting.value = true
  try {
  const rows = await allRows('/workspace/orders', filters.value)
  const quote = (value: unknown) => '"' + String(value ?? '').replace(/^[=+\-@]/, "'$&").replace(/"/g, '""') + '"'
  const content = [printColumns.map(f => quote(f.label)).join(','), ...rows.map(o => printColumns.map(f => quote(display(o, f))).join(','))].join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF' + content], {type: 'text/csv;charset=utf-8'}))
  const a = document.createElement('a'); a.href = url; a.download = '订单查询结果.csv'; a.click(); URL.revokeObjectURL(url)
  } catch (e) {ElMessage.error((e as Error).message)} finally {exporting.value = false}
}
</script>

<template>
  <section class="page orders-page">
    <PageHeader title="订单管理" description="按项目与供应商查找订单，跟进采购往来" />
    <div v-if="error" role="alert" class="load-error">{{error}} <button @click="load">重新加载</button></div>
    <div class="orders-workspace">
      <aside class="filter-column" aria-label="项目筛选">
        <div class="filter-search"><input v-model="projectSearch" aria-label="筛选项目" placeholder="筛选项目…" type="search" /></div>
        <div ref="projectList" class="filter-list">
          <button :class="{active: !project}" :aria-pressed="!project" @click="chooseProject('')">全部项目</button>
          <button v-for="p in visibleProjects" :key="p.id" :data-project="p.id" :class="{active: project === p.id}" :aria-pressed="project === p.id" @click="chooseProject(p.id)">{{p.name}}</button>
          <p v-if="!visibleProjects.length" class="muted">没有匹配的项目</p>
        </div>
      </aside>
      <aside class="filter-column" aria-label="联系人筛选">
        <div class="filter-search"><input v-model="contactSearch" aria-label="筛选联系人" placeholder="筛选联系人…" type="search" /></div>
        <div ref="contactList" class="filter-list">
          <button :class="{active: !contact}" :aria-pressed="!contact" @click="contact = ''">全部联系人</button>
          <button v-for="c in visibleContacts" :key="c" :data-contact="c" :class="{active: contact === c}" :aria-pressed="contact === c" @click="contact = c">{{c}}</button>
          <p v-if="!visibleContacts.length" class="muted">没有匹配的联系人</p>
        </div>
      </aside>
      <main class="orders-content" aria-label="订单明细" v-loading="busy">
        <header class="orders-toolbar">
          <strong>{{title}} — 订单明细</strong>
          <div class="totals"><span>订单合计<b>¥{{money(totals.orders)}}</b></span><span>付款合计<b>¥{{money(totals.paid)}}</b></span><span>余额合计<b>¥{{money(totals.balance)}}</b></span></div>
          <div class="order-controls">
            <input v-model="number" aria-label="订单号搜索" placeholder="输入订单号搜索…" type="search" />
            <label class="card-columns-control">卡片列数<select v-model="cardColumns" aria-label="卡片列数" title="宽度不足时自动减少列数"><option value="auto">自动</option><option value="1">1列</option><option value="2">2列</option><option value="3">3列</option></select></label>
            <details class="field-picker"><summary>显示字段</summary><div><label v-for="(label, key) in fieldLabels" :key="key"><input v-model="visibleFields" type="checkbox" :value="key" />{{label}}</label></div></details>
            <RouterLink class="primary-button" :to="{path: '/orders/new', query: project ? {project_id: project} : {}}">＋ 新增订单</RouterLink>
            <label class="settled-toggle"><input v-model="hideSettled" type="checkbox" aria-label="隐藏已结清" />隐藏已结清</label>
            <button @click="exportCsv" :disabled="busy || exporting || !count">{{exporting ? '导出中…' : '导出'}}</button><button @click="tablePrint = true" :disabled="!pageOrders.length">打印本页表格</button>
          </div>
        </header>
        <div class="order-sheets" :data-columns="cardColumns" aria-live="polite">
          <p v-if="!busy && !pageOrders.length" class="empty-state">{{error ? '订单未能加载，请重试' : '暂无符合条件的订单'}}</p>
          <article v-for="o in pageOrders" :key="o.id" class="order-sheet">
            <header class="order-sheet-header"><div><h2>采购订单</h2><small>PURCHASE ORDER</small></div><div class="sheet-meta"><strong>{{o.order_number}}</strong><span v-if="show('date')">下料日期：{{o.cutting_time || '—'}}</span></div></header>
            <div class="order-sheet-grid">
              <section class="sheet-panel"><h3>订单资料 <small>ORDER DETAILS</small></h3><table><tbody>
                <tr v-if="show('project')"><th>项目名称</th><td><strong>{{o.project_name || '—'}}</strong></td></tr>
                <tr v-if="show('material')"><th>材料 / 服务</th><td>{{material(o)}}</td></tr>
                <tr v-if="show('contact')"><th>供应商负责人</th><td>{{o.supplier_contact_person || '—'}}<small v-if="o.supplier_name" class="subline">{{o.supplier_name}}</small></td></tr>
                <tr v-if="show('manager')"><th>负责人</th><td>{{o.material_manager || '—'}}</td></tr>
                <tr v-if="show('date')"><th>预计到场</th><td>{{o.estimated_arrival_time || '—'}}</td></tr>
                <tr v-if="show('details')"><th>材料明细</th><td class="material-details">{{o.material_details || '—'}}</td></tr>
              </tbody></table></section>
              <section class="sheet-panel"><h3>付款概况 <small>PAYMENT SUMMARY</small></h3><table><tbody>
                <tr v-if="show('amount')"><th>订单总额</th><td class="money total-amount">¥{{money(o.order_amount)}}</td></tr>
                <tr><th>累计已付</th><td class="money"><strong>¥{{money(paid(o))}}</strong></td></tr>
                <tr v-if="show('balance')"><th>当前余额</th><td class="money" :class="{overpaid: Number(balance(o)) < 0}">¥{{money(balance(o))}}</td></tr>
                <tr><th>付款状态</th><td>{{status(o)}}</td></tr>
                <tr><th>付款进度</th><td><strong class="payment-progress money">{{progress(o)}}</strong><small class="subline">已关联 {{(o.pays_list || []).length}} 张付款单</small></td></tr>
              </tbody></table></section>
            </div>
            <OrderAttachments :order="o" @saved="attachmentsSaved(o, $event)" />
            <section v-if="show('payments')" class="related-payments" aria-label="关联付款单">
              <h3>关联付款单 <small>{{(o.pays_list || []).length}} 张</small></h3>
              <div class="payment-list"><div v-for="p in o.pays_list || []" :key="p.id" class="payment-item">
                <RouterLink :to="paymentEditor(`/payments/${p.id}/edit`)" :aria-label="`编辑付款单 ${p.pay_number}`" class="payment-link"><span><strong>{{p.pay_number}}</strong><b>¥{{money(p.current_payment_amount)}}</b></span><small>{{p.payer_supplier_name || '—'}} → {{p.payee_supplier_name || '—'}}</small></RouterLink>
                <RouterLink :to="`/payments/${p.id}/print`" :aria-label="`打印付款单 ${p.pay_number}`" class="payment-print">打印</RouterLink>
              </div><span v-if="!o.pays_list?.length" class="muted">暂无关联付款单</span></div>
            </section>
            <footer class="sheet-actions"><RouterLink :to="`/orders/${o.id}`">详情</RouterLink><RouterLink :to="`/orders/${o.id}/edit`">编辑订单</RouterLink><RouterLink class="new-payment-button" :to="paymentEditor('/payments/new', o.id)">新增付款单</RouterLink><RouterLink :to="`/orders/${o.id}/print`">打印订单</RouterLink><button class="delete-button" :disabled="deleting" @click="remove(o)">删除</button></footer>
          </article>
          <nav v-if="count" class="order-pagination" aria-label="订单分页"><span>共 {{count}} 条 · 第 {{page}} / {{pageCount}} 页</span><button :disabled="busy || page <= 1" @click="page--">上一页</button><button :disabled="busy || page >= pageCount" @click="page++">下一页</button></nav>
        </div>
      </main>
    </div>
    <TablePrint v-model="tablePrint" title="采购订单" :columns="printColumns" :rows="pageOrders" :page="page" :total="count" :display="display" />
  </section>
</template>

<style scoped src="./document-workspace.css"></style>
