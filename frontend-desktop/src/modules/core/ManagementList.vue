<script setup lang="ts">
import { Delete, Edit, Link, Plus } from '@element-plus/icons-vue'
import { formatMoney } from './money'
import type { Field, Row } from './model'

defineProps<{
  kind: string
  rows: Row[]
  filters: Row
  options: Record<string, Row[]>
  busy: boolean
  display: (row: Row, field: Field) => any
}>()
const emit = defineEmits<{
  search: []
  reset: []
  add: []
  edit: [row: Row]
  detail: [row: Row]
  remove: [row: Row]
}>()
function amount(value: unknown) {
  const formatted = formatMoney(value)
  return formatted === '—' ? formatted : '¥ ' + formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}
const payerColumns = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: '付款单位名称' },
  { key: 'type_id', label: '类型', source: 'payerTypes' },
  { key: 'bank_name', label: '开户行名称' },
  { key: 'account_number', label: '银行账号' },
  { key: 'remark', label: '备注' },
  { key: 'create_at', label: '创建时间' },
]
</script>

<template>
  <div class="management-list" :data-management="kind">
    <form v-if="kind !== 'payers'" class="management-toolbar" @submit.prevent="emit('search')">
      <template v-if="kind === 'projects'">
        <input v-model="filters.project_name" aria-label="搜索项目名称" placeholder="搜索项目名称..." @input="filters.project_name === '' && emit('search')" />
        <select v-model="filters.project_status" aria-label="项目状态" @change="emit('search')">
          <option :value="undefined">所有状态</option>
          <option v-for="option in options.xmzt || []" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </template>
      <template v-else>
        <input v-model="filters.name" aria-label="搜索供应商名称" placeholder="搜索供应商名称..." @input="filters.name === '' && emit('search')" />
        <input v-model="filters.contact_person" aria-label="搜索联系人" placeholder="搜索联系人..." @input="filters.contact_person === '' && emit('search')" />
      </template>
      <button type="submit" class="subtle-button">查询</button>
      <button v-if="Object.values(filters).some(Boolean)" type="button" class="subtle-button" @click="emit('reset')">重置</button>
      <button type="button" class="add-button" @click="emit('add')"><Plus />{{ kind === 'projects' ? '新增项目' : '新增供应商' }}</button>
    </form>

    <div v-if="kind === 'projects'" class="project-card-container">
      <article v-for="row in rows" :key="row.id" class="project-card">
        <div class="card-left">
          <div class="card-header-row">
            <span class="card-id">#{{ row.id }}</span>
            <button class="card-title" :title="row.project_full_name" @click="emit('detail', row)">{{ row.project_name }}</button>
            <span class="card-status">{{ display(row, { key: 'project_status', label: '项目状态', source: 'xmzt' }) }}</span>
          </div>
          <div class="card-subtitle">{{ row.project_full_name || '暂无全称' }}</div>
        </div>
        <div class="card-middle">
          <div class="card-item"><span class="card-label">项目规模</span><span class="card-value">{{ display(row, { key: 'project_scale', label: '项目规模', source: 'xmgm' }) }}</span></div>
          <div class="card-item"><span class="card-label">合同金额</span><span class="card-value card-amount">{{ amount(row.project_amount) }}</span></div>
          <div class="card-item"><span class="card-label">审价金额</span><span class="card-value card-amount">{{ amount(row.project_audit_price_amount) }}</span></div>
          <div class="card-item"><span class="card-label">审计金额</span><span class="card-value card-amount">{{ amount(row.project_audit_amount) }}</span></div>
          <div class="card-item"><span class="card-label">项目周期</span><span class="card-value">{{ row.start_date || '—' }} ~ {{ row.end_date || '—' }}</span></div>
        </div>
        <div class="card-actions project-actions">
          <button class="subtle-button" @click="emit('edit', row)"><Edit />编辑</button>
          <button class="subtle-button" :disabled="busy" @click="emit('remove', row)"><Delete />删除</button>
        </div>
      </article>
    </div>

    <div v-else-if="kind === 'suppliers'" class="supplier-grid">
      <article v-for="row in rows" :key="row.id" class="supplier-card">
        <header class="supplier-header">
          <div class="supplier-name-row">
            <strong>{{ row.contact_person || '未命名' }}</strong>
            <button class="supplier-name" :title="row.name" @click="emit('detail', row)">{{ row.name || '未命名供应商' }}</button>
          </div>
          <div class="supplier-meta"><span class="card-type-badge">{{ display(row, { key: 'type_id', label: '供应商类型', source: 'supplierTypes' }) }}</span><span class="card-id">#{{ row.id }}</span></div>
        </header>
        <div class="supplier-body">
          <div class="info-row"><span>电话:</span><span class="info-value">{{ row.phone || '—' }}</span></div>
          <div class="info-row"><span>银行:</span><span class="info-value">{{ row.bank_name || '—' }}</span></div>
          <div class="info-row"><span>账户:</span><span class="info-value">{{ row.account_number || '—' }}</span></div>
        </div>
        <div class="card-actions supplier-actions">
          <button class="subtle-button" title="查看详情与对账链接" aria-label="查看详情与对账链接" @click="emit('detail', row)"><Link /></button>
          <button class="subtle-button" @click="emit('edit', row)"><Edit />编辑</button>
          <button class="subtle-button" :disabled="busy" @click="emit('remove', row)"><Delete />删除</button>
        </div>
      </article>
    </div>

    <div v-else class="payer-panel">
      <div class="payer-toolbar"><button type="button" class="add-button" @click="emit('add')"><Plus />新增付款单位</button></div>
      <form @submit.prevent="emit('search')">
        <div class="payer-table-scroll">
          <table class="payer-table">
            <thead>
              <tr><th v-for="column in payerColumns" :key="column.key" scope="col">{{ column.label }}</th><th scope="col">操作</th></tr>
              <tr class="payer-filter-row">
                <td v-for="column in payerColumns" :key="column.key">
                  <select v-if="column.key === 'type_id'" v-model="filters.type_id" aria-label="筛选类型" @change="emit('search')"><option :value="undefined">全部</option><option :value="1">单位</option><option :value="2">个人</option></select>
                  <input v-else-if="!['id','create_at'].includes(column.key)" v-model="filters[column.key]" :aria-label="'筛选' + column.label" :placeholder="'筛选' + column.label" />
                </td>
                <td><div class="card-actions"><button class="subtle-button" type="submit">查询</button><button class="subtle-button" type="button" @click="emit('reset')">重置</button></div></td>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td v-for="column in payerColumns" :key="column.key">{{ display(row, column) }}</td>
                <td><div class="card-actions"><button type="button" class="subtle-button" @click="emit('edit', row)"><Edit />编辑</button><button type="button" class="subtle-button" :disabled="busy" @click="emit('remove', row)"><Delete />删除</button></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </form>
    </div>
    <el-empty v-if="!rows.length" :description="kind === 'projects' ? '暂无项目数据' : '暂无数据'" :image-size="70" />
    <div class="management-pagination"><slot name="pagination" /><details class="management-extra"><summary>更多操作</summary><div><slot name="tools" /></div></details></div>
  </div>
</template>

<style scoped>
.management-list{color:#25483b}.management-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0 18px}
input,select{box-sizing:border-box;height:40px;border:1px solid #dce6df;border-radius:7px;padding:0 12px;color:#45604f;background:#fff;font:inherit;max-width:100%}.management-toolbar input{width:250px}.management-toolbar select{min-width:150px}
button{font:inherit;cursor:pointer}button:disabled{cursor:not-allowed;opacity:.5}button svg{height:15px;width:15px;flex-shrink:0}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #087f78;outline-offset:3px}
.add-button,.subtle-button{display:inline-flex;align-items:center;justify-content:center;gap:5px;white-space:nowrap;border-radius:6px}.add-button{padding:10px 18px;color:#fff;border:0;background:#087f78;min-height:40px}.management-toolbar .add-button{margin-left:auto}.subtle-button{color:#547663;background:#f7faf8;border:1px solid #e0e9e2;padding:7px 12px}.subtle-button:hover{color:#087f78;background:#eaf4ed}
.project-card-container{display:grid;gap:16px}.project-card{display:grid;grid-template-columns:minmax(220px,1fr) auto;gap:18px;padding:22px;background:#fff;border:1px solid #e2ebe6;border-radius:12px}.project-card:hover{border-color:#a6cbbb;box-shadow:0 4px 18px #20452f08}.card-left{grid-column:1;min-width:0}.card-header-row{display:flex;align-items:center;flex-wrap:wrap;gap:8px}.card-title{color:#244639;white-space:normal;overflow-wrap:anywhere;font-size:16px;border:0;background:transparent;padding:0;text-align:left}.card-id{color:#8a9d91;font-size:12px}.card-subtitle{color:#819486;margin-top:5px;font-size:13px}.card-status{color:#407d5e;background:#edf6ef;border:1px solid #dbeadf;white-space:nowrap;font-size:12px}.card-middle{grid-row:2;grid-column:1/-1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:18px;border-top:1px solid #edf2ef;padding-top:16px}.card-item{min-width:0;line-height:1.8}.card-label{color:#8b9c90;font-size:11px;margin-right:4px}.card-value{color:#476352;white-space:normal;overflow-wrap:anywhere;font-size:13px}.card-amount{color:#087f78;font-variant-numeric:tabular-nums;font-weight:650}.card-actions{display:flex;gap:8px}.project-actions{grid-column:2;grid-row:1;align-self:start}
.supplier-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px}.supplier-card{background:#fff;border:1px solid #e0eae3;border-radius:12px;padding:21px;min-width:0}.supplier-header{padding-bottom:16px;border-bottom:1px solid #edf2ee}.supplier-name-row{display:flex;align-items:baseline;gap:8px;min-width:0}.supplier-name-row strong{font-size:18px;white-space:nowrap}.supplier-name{border:0;background:transparent;padding:0;color:#2b4f3b;font-size:16px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:left}.supplier-meta{display:flex;justify-content:space-between;align-items:center;margin-top:8px}.card-type-badge{font-size:11px;color:#63876b;background:#edf5ef;padding:4px 8px;border-radius:5px}.supplier-body{padding:16px 0}.info-row{display:flex;align-items:baseline;gap:7px;margin:10px 0;font-size:12px;color:#8da08f}.info-row>span:first-child{flex-shrink:0}.info-value{color:#496c53;overflow-wrap:anywhere;min-width:0}.supplier-actions{justify-content:flex-end;padding-top:12px;border-top:1px solid #edf2ee}
.payer-panel{margin-top:24px;background:#fff;padding:18px;border:1px solid #e0e9e2;border-radius:12px}.payer-toolbar{margin-bottom:16px}.payer-table-scroll{overflow-x:auto}.payer-table{border-collapse:collapse;table-layout:fixed;width:100%;min-width:1160px;font-size:13px}.payer-table th,.payer-table td{padding:12px 10px;text-align:left;border-bottom:1px solid #edf2ee;overflow-wrap:anywhere}.payer-table th{background:#f6f9f7;color:#476352;font-weight:600}.payer-table th:first-child{width:60px}.payer-table th:nth-child(3){width:80px}.payer-table th:last-child{width:174px}.payer-table th:nth-child(7){width:160px}.payer-table tbody tr:hover{background:#f7faf8}.payer-filter-row input,.payer-filter-row select{width:100%;min-width:0;height:30px;padding:0 7px;font-size:12px}.management-pagination{margin-top:18px;overflow-x:auto}
.management-extra{margin-top:16px;font-size:12px;color:#63876b}.management-extra summary{cursor:pointer;display:list-item}.management-extra>div{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.payer-table th:last-child,.payer-table td:last-child{position:sticky;right:0;background:#fff;box-shadow:-3px 0 5px #20452f08}.payer-table th:last-child{background:#f6f9f7}
@media(max-width:1100px){.card-middle{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){.project-card{grid-template-columns:minmax(0,1fr);padding:18px}.project-actions{grid-column:1;grid-row:3}.card-middle{grid-template-columns:repeat(2,minmax(0,1fr))}.management-toolbar input{flex:1 1 180px;min-width:0}.management-toolbar .add-button{margin-left:0}.supplier-grid{grid-template-columns:minmax(0,1fr)}.payer-panel{padding:12px}}
</style>
