<script setup lang="ts">
import {computed, ref, watch, onDeactivated} from 'vue'
import {useRoute} from 'vue-router'
import {ElMessage, ElMessageBox} from 'element-plus'
import {allRows, request, safeUrl} from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import TablePrint from './TablePrint.vue'
import {useCardColumns} from './useCardColumns'
import {useDocumentWorkspace} from './useDocumentWorkspace'
import {formatMoney, uppercaseMoney} from './money'
import {parseAttachments, type Row, type Field} from './model'

const route = useRoute()
const cardColumns = useCardColumns('payments')
const materials = ref<Row[]>([]), statuses = ref<Row[]>([])
const deleting = ref(false), tablePrint = ref(false), exporting = ref(false)
const project = ref(''), contact = ref(''), number = ref(''), paymentStatus = ref(''), projectSearch = ref(''), contactSearch = ref(''), orderNumber = ref('')
const projectNameQuery = ref('')
const filters = computed(() => ({project_id: project.value, project_name: project.value ? '' : projectNameQuery.value, supplier_contact_person: contact.value, pay_number: number.value, order_number: orderNumber.value, payment_status: paymentStatus.value}))
const {rows: pagePayments, projects, contacts, totals, count, page, pageCount, busy, error, load} = useDocumentWorkspace('payments', filters)
const fieldLabels: Record<string, string> = {project: '项目名称', order_amount: '订单金额', pay_amount: '付款金额', invoice_amount: '开票金额', status: '付款状态', payer: '付款单位', payee: '收款单位 / 账户', handler: '经办人', purpose: '付款用途', attachments: '附件列表', invoices: '关联发票'}
const visibleFields = ref(Object.keys(fieldLabels)), show = (key: string) => visibleFields.value.includes(key)
const money = (value: unknown) => value == null ? '—' : formatMoney(value).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
const order = (p: Row): Row => p.order_summary || {}
const supplier = (p: Row): Row => p.payee_account || {}
const projectName = (p: Row) => order(p).project_name || p.project_name || ''
const contactName = (p: Row) => order(p).supplier_contact_person || p.supplier_contact_person || ''
const statusText = (p: Row) => statuses.value.find(s => String(s.code) === String(p.payment_status))?.value || p.payment_status || '—'
const material = (p: Row) => materials.value.find(m => String(m.code) === String(order(p).material_name))?.value || order(p).material_name || '—'
const progress = (p: Row) => Number(order(p).order_amount) > 0 && order(p).paid_amount != null ? (Number(order(p).paid_amount) / Number(order(p).order_amount) * 100).toFixed(1) + '%' : '—'
const projectOptions = computed(() => projects.value.map(p => ({id: String(p.id), name: p.project_name})))
const visibleProjects = computed(() => projectOptions.value.filter(p => String(p.name).toLowerCase().includes(projectSearch.value.trim().toLowerCase())))
const visibleContacts = computed(() => contacts.value.filter(c => c.toLowerCase().includes(contactSearch.value.trim().toLowerCase())).sort((a,b) => a.localeCompare(b, 'zh-CN')))
const title = computed(() => `${projectOptions.value.find(p => p.id === project.value)?.name || projectNameQuery.value || '全部项目'} · ${contact.value || '全部联系人'}`)
const printColumns: Field[] = [{key:'pay_number',label:'付款单号'}, {key:'order_number',label:'关联订单'}, {key:'project_name',label:'项目'}, {key:'payer_supplier_name',label:'付款单位'}, {key:'payee_supplier_name',label:'收款单位'}, {key:'current_payment_amount',label:'本次付款',kind:'money'}, {key:'invoice_amount',label:'开票金额',kind:'money'}, {key:'payment_status',label:'付款状态'}, {key:'handler',label:'经办人'}]
function display(p: Row, f: Field) {return f.key === 'project_name' ? projectName(p) : f.key === 'payment_status' ? statusText(p) : f.kind === 'money' ? money(p[f.key] ?? 0) : p[f.key] ?? '—'}
function attachments(p: Row) {try {return parseAttachments(p)} catch {return []}}
function chooseProject(id: string) {projectNameQuery.value = ''; project.value = id; contact.value = ''; contactSearch.value = ''}
function applyQuery() {
  project.value = String(route.query.project_id || '')
  projectNameQuery.value = String(route.query.project_name || '')
  contact.value = String(route.query.supplier_contact_person || '')
  number.value = String(route.query.pay_number || '')
  orderNumber.value = String(route.query.order_number || '')
  paymentStatus.value = String(route.query.payment_status || '')
}
let lastQuery = JSON.stringify(route.query)
watch(() => route.fullPath, () => {if (route.path === '/payments' && JSON.stringify(route.query) !== lastQuery) {lastQuery = JSON.stringify(route.query); applyQuery()}})
applyQuery()
void Promise.all([allRows('/dictionary/detail/list', {dic_id:35}), allRows('/dictionary/detail/list', {dic_id:28})]).then(([m,s]) => {materials.value = m; statuses.value = s}).catch(e => ElMessage.error((e as Error).message))
onDeactivated(() => {tablePrint.value = false})
async function remove(p: Row) {
  if (deleting.value) return
  try {await ElMessageBox.confirm(`确定删除付款单 ${p.pay_number}？此操作无法撤销。`, '删除确认', {type:'warning'})} catch {return}
  deleting.value = true
  try {await request('/pay/' + p.id, {method:'DELETE'}); ElMessage.success('删除成功'); await load()} catch(e) {ElMessage.error((e as Error).message)} finally {deleting.value = false}
}
async function exportCsv() {
  if (exporting.value) return
  exporting.value = true
  try {
  const rows = await allRows('/workspace/payments', filters.value)
  const quote = (v: unknown) => '"' + String(v ?? '').replace(/^[=+\-@]/, "'$&").replace(/"/g, '""') + '"'
  const content = [printColumns.map(f => quote(f.label)).join(','), ...rows.map(p => printColumns.map(f => quote(display(p, f))).join(','))].join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF' + content], {type:'text/csv;charset=utf-8'}))
  const a = document.createElement('a'); a.href = url; a.download = '付款单查询结果.csv'; a.click(); URL.revokeObjectURL(url)
  } catch (e) {ElMessage.error((e as Error).message)} finally {exporting.value = false}
}
</script>

<template>
  <section class="page orders-page payment-page" v-loading="busy">
    <PageHeader title="付款管理" description="按项目与供应商查找付款单，核对付款、发票与支付状态" />
    <div v-if="error" role="alert" class="load-error">{{error}} <button @click="load">重新加载</button></div>
    <div class="orders-workspace">
      <aside class="filter-column" aria-label="项目筛选"><div class="filter-search"><input v-model="projectSearch" aria-label="筛选项目" placeholder="筛选项目…" type="search" /></div><div class="filter-list">
        <button :class="{active:!project}" :aria-pressed="!project" @click="chooseProject('')">全部项目</button>
        <button v-for="p in visibleProjects" :key="p.id" :data-project="p.id" :class="{active:project === p.id}" :aria-pressed="project === p.id" @click="chooseProject(p.id)">{{p.name}}</button>
        <p v-if="!visibleProjects.length" class="muted">没有匹配的项目</p>
      </div></aside>
      <aside class="filter-column" aria-label="联系人筛选"><div class="filter-search"><input v-model="contactSearch" aria-label="筛选联系人" placeholder="筛选联系人…" type="search" /></div><div class="filter-list">
        <button :class="{active:!contact}" :aria-pressed="!contact" @click="contact = ''">全部联系人</button>
        <button v-for="c in visibleContacts" :key="c" :data-contact="c" :class="{active:contact === c}" :aria-pressed="contact === c" @click="contact = c">{{c}}</button>
        <p v-if="!visibleContacts.length" class="muted">没有匹配的联系人</p>
      </div></aside>
      <main class="orders-content" aria-label="付款明细">
        <header class="orders-toolbar"><strong>{{title}} — 付款明细</strong><div class="totals"><span>付款合计<b>¥{{money(totals.paid)}}</b></span><span>开票合计<b>¥{{money(totals.invoiced)}}</b></span></div>
          <div class="order-controls"><input v-model="number" type="search" aria-label="付款单号搜索" placeholder="输入付款单号搜索…" /><input v-model="orderNumber" type="search" aria-label="关联订单号搜索" placeholder="关联订单号…" />
            <label class="card-columns-control">卡片列数<select v-model="cardColumns" aria-label="卡片列数" title="宽度不足时自动减少列数"><option value="auto">自动</option><option value="1">1列</option><option value="2">2列</option><option value="3">3列</option></select></label>
            <select v-model="paymentStatus" aria-label="付款状态筛选"><option value="">全部付款状态</option><option v-for="s in statuses" :key="s.code" :value="String(s.code)">{{s.value}}</option></select>
            <details class="field-picker"><summary>显示字段</summary><div><label v-for="(label,key) in fieldLabels" :key="key"><input v-model="visibleFields" type="checkbox" :value="key" />{{label}}</label></div></details>
            <RouterLink class="primary-button" to="/payments/new">＋ 新增付款单</RouterLink><button :disabled="busy || exporting || !count" @click="exportCsv">{{exporting ? '导出中…' : '导出'}}</button><button :disabled="!pagePayments.length" @click="tablePrint = true">打印本页表格</button>
          </div>
        </header>
        <div class="order-sheets" :data-columns="cardColumns" aria-live="polite">
          <p v-if="!busy && !pagePayments.length" class="empty-state">{{error ? '付款单未能加载，请重试' : '暂无符合条件的付款单'}}</p>
          <article v-for="p in pagePayments" :key="p.id" class="order-sheet payment-sheet">
            <header class="order-sheet-header"><div><h2>付款审批单</h2><small>PAYMENT APPROVAL SHEET</small></div><div class="sheet-meta"><strong>{{p.pay_number}}</strong><span>日期：{{p.create_at?.split(' ')[0] || '—'}}</span></div></header>
            <div class="order-sheet-grid">
              <section class="sheet-panel"><h3>资金往来信息 <small>PAYMENT DETAILS</small></h3><table><tbody>
                <tr v-if="show('pay_amount')"><th>付款总额</th><td><strong class="total-amount money">¥{{money(p.current_payment_amount ?? 0)}}</strong><small class="subline">{{uppercaseMoney(p.current_payment_amount ?? 0)}}</small></td></tr>
                <tr v-if="show('payee')"><th>收款单位</th><td><strong>{{p.payee_supplier_name || '—'}}</strong></td></tr>
                <tr v-if="show('payee')"><th>银行账号</th><td class="money">{{supplier(p).account_number || '—'}}<small class="subline">{{supplier(p).bank_name || '—'}}</small></td></tr>
                <tr v-if="show('payer')"><th>付款单位</th><td>{{p.payer_supplier_name || '—'}}</td></tr>
                <tr v-if="show('invoice_amount')"><th>开票金额</th><td class="money">¥{{money(p.invoice_amount ?? 0)}}</td></tr>
                <tr v-if="show('purpose')"><th>款项用途</th><td class="material-details">{{p.payment_purpose || '—'}}</td></tr>
              </tbody></table></section>
              <section class="sheet-panel"><h3>关联项目概要 <small>PROJECT REF</small></h3><table><tbody>
                <tr v-if="show('project')"><th>项目名称</th><td><strong>{{projectName(p) || '—'}}</strong></td></tr>
                <tr><th>订单编号</th><td>{{order(p).order_number || p.order_number || '未关联订单'}}</td></tr>
                <tr><th>材料 / 服务</th><td>{{material(p)}}</td></tr>
                <tr><th>供应商负责人</th><td>{{contactName(p) || '—'}}</td></tr>
                <tr v-if="show('order_amount')"><th>订单总额</th><td class="money">{{order(p).order_amount != null || p.order_amount != null ? '¥' + money(order(p).order_amount ?? p.order_amount) : '—'}}</td></tr>
                <tr><th>累计已付</th><td class="money">{{order(p).paid_amount != null ? '¥' + money(order(p).paid_amount) : '—'}}</td></tr>
                <tr v-if="show('status')"><th>付款状态</th><td>{{statusText(p)}}</td></tr>
                <tr><th>付款进度</th><td><strong class="payment-progress money">{{progress(p)}}</strong><small class="subline">当前余额：{{order(p).order_balance != null ? '¥' + money(order(p).order_balance) : '—'}}</small></td></tr>
              </tbody></table></section>
            </div>
            <div v-if="show('handler')" class="payment-handler">经办人：{{p.handler || '—'}}</div>
            <section class="related-payments" aria-label="关联订单"><h3>关联订单</h3><div class="payment-list"><RouterLink v-if="p.order_id" class="payment-item payment-link" :to="`/orders/${p.order_id}/edit`" :aria-label="`查看关联订单 ${order(p).order_number || p.order_number}`"><strong>{{order(p).order_number || p.order_number || '查看订单'}}</strong><small>{{projectName(p) || '—'}} · {{contactName(p) || '—'}}</small></RouterLink><span v-else class="muted">未关联订单</span><RouterLink v-if="p.order_id" class="payment-print" :to="`/orders/${p.order_id}/print`">打印订单</RouterLink></div></section>
            <section v-if="show('invoices')" class="related-payments" aria-label="关联发票"><h3>关联发票 <small>{{(p.invoices_list || []).length}} 张</small></h3><div class="payment-list">
              <RouterLink v-for="inv in p.invoices_list || []" :key="inv.id" class="payment-item payment-link" :to="`/invoices/${inv.id}`" :aria-label="`查看发票 ${inv.invoice_number || inv.id}`"><span><strong>{{inv.invoice_number || '无发票号码'}}</strong><b>金额：¥{{money(inv.total_amount ?? 0)}}</b></span><small>{{inv.seller_name || '—'}} · {{inv.invoice_date || '—'}}</small></RouterLink>
              <span v-if="!p.invoices_list?.length" class="muted">暂无关联发票</span>
            </div></section>
            <div v-if="show('attachments') && attachments(p).length" class="sheet-attachments"><span>附件：</span><a v-for="(a,i) in attachments(p)" :key="i" :href="safeUrl(a.url || a.file_path)" target="_blank" rel="noopener">{{a.name || a.filename || '附件'}}</a></div>
            <footer class="sheet-actions"><RouterLink :to="`/payments/${p.id}`">详情</RouterLink><RouterLink :to="{path: `/payments/${p.id}/edit`, query: {action: 'link-invoices'}}" :aria-label="`关联发票 ${p.pay_number}`">关联发票</RouterLink><RouterLink :to="`/payments/${p.id}/edit`" :aria-label="`编辑付款单 ${p.pay_number}`">编辑付款单</RouterLink><RouterLink :to="`/payments/${p.id}/print`" :aria-label="`打印付款单 ${p.pay_number}`">打印付款单</RouterLink><button class="delete-button" :disabled="deleting" @click="remove(p)">删除</button></footer>
          </article>
          <nav v-if="count" class="order-pagination" aria-label="付款单分页"><span>共 {{count}} 条 · 第 {{page}} / {{pageCount}} 页</span><button :disabled="busy || page <= 1" @click="page--">上一页</button><button :disabled="busy || page >= pageCount" @click="page++">下一页</button></nav>
        </div>
      </main>
    </div>
    <TablePrint v-model="tablePrint" title="付款单" :columns="printColumns" :rows="pagePayments" :page="page" :total="count" :display="display" />
  </section>
</template>
<style scoped src="./document-workspace.css"></style>
<style scoped>
.payment-page .order-controls select{max-width:230px;min-width:140px;padding:9px 10px;background:#fff;border:1px solid #d4e1d8;border-radius:5px;color:#355d47;font:inherit}
.payment-page .sheet-panel th{width:110px}.payment-handler{margin-top:12px;font-size:12px;color:#555}.payment-sheet .payment-progress{padding:0;font-size:20px}
select:focus-visible{outline:2px solid #087f78;outline-offset:2px}
</style>
