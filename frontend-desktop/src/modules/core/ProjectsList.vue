<script setup lang="ts">
import { Calendar, Delete, Document, Edit, FolderOpened, Plus, Search } from '@element-plus/icons-vue'
import { formatMoney } from './money'
import type { Field, Row } from './model'

const props = defineProps<{
  rows: Row[]
  total?: number
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
  const text = formatMoney(value)
  return text === '—' ? text : text.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}
function status(row: Row) {
  return String(props.display(row, { key: 'project_status', label: '项目状态', source: 'xmzt' }))
}
function statusTone(row: Row) {
  const label = status(row)
  if (/暂停|停工|取消|终止/.test(label)) return 'paused'
  if (/待|筹备|准备|未开/.test(label)) return 'pending'
  if (/开工|在建|施工|进行|实施/.test(label)) return 'active'
  if (/完工|完成|竣工|结算|结束/.test(label)) return 'complete'
  return 'neutral'
}
function attachmentCount(row: Row) {
  try {
    const raw = row.attachments_list ?? row.attachments ?? []
    const items = typeof raw === 'string' ? JSON.parse(raw) : raw
    return Array.isArray(items) ? items.length : 0
  } catch { return 0 }
}
</script>

<template>
  <div class="projects-list">
    <form class="project-search" @submit.prevent="emit('search')">
      <div class="search-fields">
        <label class="search-input"><Search aria-hidden="true" /><input v-model="filters.project_name" aria-label="搜索项目名称" placeholder="搜索项目名称…" @input="filters.project_name === '' && emit('search')" /></label>
        <select v-model="filters.project_status" aria-label="项目状态" @change="emit('search')">
          <option :value="undefined">全部项目状态</option>
          <option v-for="option in options.xmzt || []" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <button type="submit" class="query-button">查询</button>
        <button v-if="Object.values(filters).some(Boolean)" type="button" class="reset-button" @click="emit('reset')">重置</button>
      </div>
      <button type="button" class="primary-button" @click="emit('add')"><Plus aria-hidden="true" />新增项目</button>
    </form>

    <div class="list-caption" role="status"><span>项目档案 <b>{{ total ?? rows.length }}</b><span class="count-unit">个项目</span></span><span class="caption-hint">点击项目名称查看详情与附件</span></div>
    <div class="project-grid">
      <article v-for="row in rows" :key="row.id" class="project-card" :aria-label="row.project_name || '未命名项目'">
        <header class="project-card-heading">
          <div class="project-symbol"><FolderOpened aria-hidden="true" /></div>
          <div class="project-identity">
            <div class="project-title-row"><button type="button" class="project-title" @click="emit('detail', row)">{{ row.project_name || '未命名项目' }}</button><span class="status-badge" :data-tone="statusTone(row)"><i aria-hidden="true" />{{ status(row) === '—' ? '未设置状态' : status(row) }}</span></div>
            <p class="project-full-name">{{ row.project_full_name || '暂未填写项目全称' }}</p>
          </div>
          <span class="project-id">#{{ row.id }}</span>
        </header>

        <div class="project-financials">
          <div class="contract-amount"><span class="field-label">合同金额 <small>元</small></span><strong><small v-if="amount(row.project_amount) !== '—'">¥</small>{{ amount(row.project_amount) }}</strong></div>
          <dl class="audit-amounts"><div><dt>审价金额<span>元</span></dt><dd>{{ amount(row.project_audit_price_amount) }}</dd></div><div><dt>审计金额<span>元</span></dt><dd>{{ amount(row.project_audit_amount) }}</dd></div></dl>
        </div>

        <div class="project-meta">
          <div class="meta-item"><span class="meta-label">项目规模</span><span>{{ display(row, { key: 'project_scale', label: '项目规模', source: 'xmgm' }) }}</span></div>
          <div class="meta-item project-period"><span class="meta-label"><Calendar aria-hidden="true" />项目周期</span><span>{{ row.start_date || '待填写' }}<span class="date-divider">至</span>{{ row.end_date || '待填写' }}</span></div>
        </div>
        <footer class="project-card-footer">
          <button type="button" class="attachment-button" :aria-label="'查看' + (row.project_name || '项目') + '的资料附件'" @click="emit('detail', row)"><Document aria-hidden="true" /><span>{{ attachmentCount(row) ? attachmentCount(row) + ' 份附件' : '暂无附件' }}</span></button>
          <div class="project-actions"><button type="button" class="edit-button" @click="emit('edit', row)"><Edit aria-hidden="true" />编辑</button><button type="button" class="delete-button" :disabled="busy" :aria-label="'删除' + (row.project_name || '项目')" @click="emit('remove', row)"><Delete aria-hidden="true" />删除</button></div>
        </footer>
      </article>
    </div>
    <div v-if="!rows.length" class="projects-empty"><FolderOpened aria-hidden="true" /><h2>{{ Object.values(filters).some(Boolean) ? '没有找到匹配的项目' : '还没有项目档案' }}</h2><p>{{ Object.values(filters).some(Boolean) ? '试试其他项目名称，或重置筛选条件。' : '新增项目，记录合同金额、项目周期与相关资料。' }}</p><button v-if="Object.values(filters).some(Boolean)" type="button" class="query-button" @click="emit('reset')">重置筛选</button><button v-else type="button" class="primary-button" @click="emit('add')"><Plus aria-hidden="true" />新增项目</button></div>
  </div>
</template>

<style scoped>
.projects-list{--project-ink:#25483b;--project-muted:#62766d;--project-line:#e3ece6;color:var(--project-ink);font-family:'Microsoft YaHei','PingFang SC',sans-serif}
button,input,select{font:inherit}button{cursor:pointer}button:disabled{opacity:.5;cursor:not-allowed}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #087f78;outline-offset:3px}button svg{width:16px;height:16px;flex-shrink:0}
.project-search{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:18px;background:#fff;border:1px solid var(--project-line);border-radius:12px;margin:4px 0 22px}.search-fields{display:flex;align-items:center;gap:10px;flex-wrap:wrap;min-width:0}.search-input{display:flex;align-items:center;gap:10px;border:1px solid #d7e2db;border-radius:7px;padding:0 12px;min-width:0;width:300px;background:#fafcfb}.search-input>svg{width:18px;height:18px;color:#6b8076;flex-shrink:0}.search-input input{width:100%;min-width:0;height:42px;border:0;background:transparent;color:#25483b;outline-offset:0}.search-input:focus-within{border-color:#087f78}.search-fields select{height:44px;max-width:100%;min-width:150px;padding:0 28px 0 12px;color:#3c5b4d;border:1px solid #d7e2db;border-radius:7px;background:#fff}
.primary-button,.query-button,.reset-button{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:44px;padding:10px 17px;border-radius:7px;white-space:nowrap;font-size:13px}.primary-button{color:#fff;background:#087f78;border:1px solid #087f78;flex-shrink:0}.primary-button:hover{background:#06665f}.query-button{background:#f0f6f3;border:1px solid #d7e5dc;color:#275e47}.reset-button{background:transparent;border:1px solid transparent;color:#62766d;padding-inline:8px}.query-button:hover,.reset-button:hover{background:#e5f0e9}
.list-caption{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 2px 14px;font-size:14px}.list-caption b{margin-left:10px;font-size:16px;color:#214c43}.count-unit{font-size:12px;color:#62766d;margin-left:6px}.caption-hint{font-size:12px;color:#62766d}
.project-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:18px}.project-card{min-width:0;border:1px solid var(--project-line);border-radius:12px;background:#fff;overflow:hidden;transition:border-color .15s,box-shadow .15s}.project-card:hover{border-color:#a6cbbb;box-shadow:0 6px 20px #214c4308}.project-card-heading{display:flex;align-items:flex-start;gap:12px;padding:22px 22px 18px;min-width:0}.project-symbol{display:grid;place-items:center;width:40px;height:40px;flex-shrink:0;border-radius:9px;background:#eaf3ee;color:#36715b}.project-symbol svg{width:22px;height:22px}.project-identity{min-width:0;flex:1}.project-title-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.project-title{min-width:0;max-width:100%;text-align:left;overflow-wrap:anywhere;color:#214c43;border:0;padding:0;background:transparent;font-size:17px;line-height:1.65;font-weight:700}.project-title:hover{color:#087f78;text-decoration:underline;text-underline-offset:4px}.project-full-name{margin:6px 0 0;color:#62766d;line-height:1.7;font-size:12px;overflow-wrap:anywhere}.project-id{color:#788c82;font-size:11px;white-space:nowrap;margin-top:7px}
.status-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:5px;font-size:11px;line-height:1.6;white-space:nowrap;color:#65746f;background:#f0f3f1;border:1px solid #e3e9e5}.status-badge i{width:5px;height:5px;border-radius:50%;background:currentColor}.status-badge[data-tone=active]{color:#086b58;background:#eaf7f1;border-color:#cce9dc}.status-badge[data-tone=complete]{color:#446c8b;background:#eef4f9;border-color:#dbe7ef}.status-badge[data-tone=pending]{color:#8a621c;background:#fcf6e9;border-color:#efe2c0}.status-badge[data-tone=paused]{color:#98644c;background:#faf0eb;border-color:#efdcd1}
.project-financials{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:20px;margin:0 22px;padding:18px 0;border-top:1px solid #edf2ef;border-bottom:1px solid #edf2ef;align-items:center}.field-label{font-size:12px;color:#62766d}.field-label small{font-size:10px;color:#78877f;margin-left:5px}.contract-amount{min-width:0}.contract-amount strong{display:block;color:#087f78;font-family:'Bahnschrift','DIN Alternate','Microsoft YaHei',sans-serif;font-size:28px;line-height:1.4;font-weight:600;font-variant-numeric:tabular-nums;overflow-wrap:anywhere;margin-top:7px;letter-spacing:-.5px}.contract-amount strong small{font-size:16px;margin-right:5px;font-weight:400}.audit-amounts{display:grid;gap:10px;margin:0;padding-left:18px;border-left:1px solid #e3ece6;min-width:0}.audit-amounts>div{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}.audit-amounts dt{font-size:11px;color:#62766d;white-space:nowrap}.audit-amounts dt span{font-size:10px;margin-left:4px;color:#78877f}.audit-amounts dd{font-size:14px;color:#36564a;font-weight:600;font-variant-numeric:tabular-nums;overflow-wrap:anywhere;margin:0;min-width:0}
.project-meta{display:flex;flex-wrap:wrap;gap:12px 26px;padding:16px 22px 18px;font-size:12px}.meta-item{display:flex;flex-direction:column;gap:7px;min-width:0;overflow-wrap:anywhere}.meta-label{color:#62766d;display:flex;align-items:center;gap:5px;font-size:11px}.meta-label svg{width:12px;height:12px}.date-divider{padding:0 8px;color:#84958b}.project-card-footer{display:flex;justify-content:space-between;align-items:center;gap:12px;border-top:1px solid #edf2ef;background:#fbfcfb;padding:9px 16px}.attachment-button,.edit-button,.delete-button{display:inline-flex;align-items:center;justify-content:center;gap:5px;min-height:36px;border:0;border-radius:5px;padding:7px 6px;background:transparent;font-size:12px}.attachment-button{color:#62766d;min-width:0;text-align:left}.attachment-button:hover,.edit-button:hover{color:#087f78;background:#eaf3ee}.project-actions{display:flex;gap:12px;flex-shrink:0}.edit-button{color:#36715b}.delete-button{color:#7b827c}.delete-button:hover{color:#b24f42;background:#fcf0ec}
.projects-empty{border:1px dashed #cbdcd2;border-radius:12px;background:#fff;text-align:center;padding:44px 20px}.projects-empty>svg{width:44px;height:44px;color:#7b9d8a;margin-bottom:12px}.projects-empty h2{font-size:17px;margin-bottom:10px}.projects-empty p{color:#62766d;font-size:13px;margin-bottom:20px}
@media(min-width:1700px){.project-grid{grid-template-columns:repeat(auto-fit,minmax(490px,1fr))}}
@media(max-width:1100px){.project-search{align-items:flex-start}.search-input{width:260px}}
@media(max-width:600px){.project-search{padding:14px;flex-wrap:wrap;gap:12px}.search-fields{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;width:100%}.search-input{grid-column:1/-1;width:100%}.search-fields select{width:100%;min-width:0}.project-search>.primary-button{width:100%}.caption-hint{display:none}.project-grid{grid-template-columns:minmax(0,1fr);gap:14px}.project-card-heading{padding:18px 16px 15px;gap:10px}.project-symbol{width:34px;height:34px}.project-symbol svg{width:19px;height:19px}.project-title{font-size:16px;min-height:44px}.project-id{display:none}.project-financials{margin:0 16px;grid-template-columns:minmax(0,1fr);gap:14px}.contract-amount strong{font-size:28px}.audit-amounts{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;border-left:0;padding-left:0}.audit-amounts>div{display:block}.audit-amounts dd{margin-top:6px}.project-meta{padding:16px;gap:16px 24px}.project-card-footer{padding:6px 10px;gap:4px}.project-actions{gap:5px}.attachment-button,.edit-button,.delete-button{min-height:44px}.reset-button{grid-column:1/-1;justify-self:start}}
@media(prefers-reduced-motion:reduce){.project-card{transition:none}}
</style>
