<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, Calendar, Document, Edit, FolderOpened } from '@element-plus/icons-vue'
import { safeUrl } from '../../api'
import { formatMoney } from './money'
import type { Field, Row } from './model'

const props = defineProps<{
  record: Row
  attachments: Row[]
  display: (row: Row, field: Field) => any
}>()
const emit = defineEmits<{ edit: []; orders: [] }>()

const status = computed(() => String(props.display(props.record, {
  key: 'project_status', label: '项目状态', source: 'xmzt',
}) || '未设置状态'))
const statusTone = computed(() => {
  const label = status.value.trim()
  if (/暂停|停工|取消|终止/.test(label)) return 'paused'
  if (/待|筹备|准备|未开/.test(label)) return 'pending'
  if (/开工|在建|施工|进行|实施/.test(label)) return 'active'
  if (/完工|完成|竣工|结算|结束/.test(label)) return 'complete'
  return 'neutral'
})
const scale = computed(() => props.display(props.record, {
  key: 'project_scale', label: '项目规模', source: 'xmgm',
}))
const files = computed(() => props.attachments.map(attachment => ({
  ...attachment,
  id: attachment.id,
  link: safeUrl(attachment.url || attachment.file_path),
  title: attachment.name || attachment.original_filename || attachment.filename || '未命名附件',
  code: attachment.code || attachment.attachment_code || '',
})))
function money(value: unknown) {
  return formatMoney(value).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}
</script>

<template>
  <div class="project-details">
    <header class="project-identity">
      <div class="identity-copy">
        <div class="identity-meta">
          <span class="project-marker"><FolderOpened aria-hidden="true" />项目档案</span>
          <span class="project-code">#{{ record.id }}</span>
          <span class="status-badge" :data-tone="statusTone">{{ status === '—' ? '未设置状态' : status }}</span>
        </div>
        <h2>{{ record.project_name || '未命名项目' }}</h2>
        <p class="project-full-name">{{ record.project_full_name || '尚未填写项目全称' }}</p>
      </div>
      <div class="project-detail-actions">
        <button class="detail-button secondary" type="button" @click="emit('orders')"><Document aria-hidden="true" />查看项目订单<ArrowRight aria-hidden="true" /></button>
        <button class="detail-button primary" type="button" @click="emit('edit')"><Edit aria-hidden="true" />编辑项目</button>
      </div>
    </header>

    <section class="project-finances" aria-labelledby="project-finances-heading">
      <div class="section-heading"><h3 id="project-finances-heading">金额信息</h3><span class="section-note">人民币 / 元</span></div>
      <dl class="finance-grid">
        <div class="contract-amount">
          <dt>合同金额</dt>
          <dd><span v-if="formatMoney(record.project_amount) !== '—'" class="currency-mark">¥</span>{{ money(record.project_amount) }}</dd>
        </div>
        <div class="audit-amount">
          <dt>审价金额</dt>
          <dd><span v-if="formatMoney(record.project_audit_price_amount) !== '—'" class="currency-mark">¥</span>{{ money(record.project_audit_price_amount) }}</dd>
        </div>
        <div class="audit-amount">
          <dt>审计金额</dt>
          <dd><span v-if="formatMoney(record.project_audit_amount) !== '—'" class="currency-mark">¥</span>{{ money(record.project_audit_amount) }}</dd>
        </div>
      </dl>
    </section>

    <div class="project-detail-body">
      <section class="detail-panel project-overview" aria-labelledby="project-overview-heading">
        <div class="section-heading"><h3 id="project-overview-heading">项目概况</h3></div>
        <dl class="overview-fields">
          <div><dt>项目规模</dt><dd>{{ scale || '—' }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ record.create_at || '—' }}</dd></div>
        </dl>
        <div class="project-dates">
          <div class="dates-title"><Calendar aria-hidden="true" /><h4>项目周期</h4></div>
          <dl class="date-fields">
            <div><dt>开始日期</dt><dd>{{ record.start_date || '未设置' }}</dd></div>
            <div><dt>结束日期</dt><dd>{{ record.end_date || '未设置' }}</dd></div>
          </dl>
        </div>
      </section>

      <section class="detail-panel project-documents" aria-labelledby="project-documents-heading">
        <div class="section-heading"><h3 id="project-documents-heading">附件资料</h3><span class="document-count">{{ attachments.length }} 份</span></div>
        <ul v-if="files.length" class="document-list">
          <li v-for="(file, index) in files" :key="file.id || index" class="document-row">
            <span class="document-icon"><Document aria-hidden="true" /></span>
            <div class="document-copy">
              <a v-if="file.link" :href="file.link" target="_blank" rel="noopener" :aria-label="`打开附件：${file.title}`">{{ file.title }}<ArrowRight aria-hidden="true" /></a>
              <span v-else class="document-name">{{ file.title }}</span>
              <span class="document-code">编号：{{ file.code || '未填写' }}<span v-if="!file.link"> · 文件链接不可用</span></span>
            </div>
          </li>
        </ul>
        <div v-else class="documents-empty"><FolderOpened aria-hidden="true" /><p>暂无附件资料</p><span>编辑项目时可上传合同、审价或审计文件。</span></div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.project-details{--project-ink:#214c43;--project-text:#25483b;--project-muted:#62766d;--project-accent:#087f78;--project-line:#eef4f1;color:var(--project-text)}
.project-identity{display:flex;justify-content:space-between;align-items:flex-start;gap:28px;padding:28px 30px;background:#fff;border:1px solid var(--project-line);border-radius:14px 14px 0 0}
.identity-copy{min-width:0;flex:1}.identity-meta{display:flex;gap:12px;align-items:center;flex-wrap:wrap;color:var(--project-muted);font-size:12px}.project-marker{display:inline-flex;align-items:center;gap:6px;font-weight:600;color:var(--project-accent)}.project-marker svg{width:17px;height:17px}.project-code{font-variant-numeric:tabular-nums}
.identity-copy h2{margin:15px 0 7px;color:var(--project-ink);font-size:clamp(23px,2vw,30px);line-height:1.4;font-weight:650;letter-spacing:.025em;overflow-wrap:anywhere}.project-full-name{margin:0;color:var(--project-muted);font-size:14px;line-height:1.75;overflow-wrap:anywhere}
.status-badge{display:inline-flex;align-items:center;padding:5px 10px;border:1px solid #e3eae6;border-radius:6px;background:#f6f8f7;color:#62766d;line-height:1.4}.status-badge[data-tone=active]{color:#087f78;background:#e9f7f4;border-color:#cae8e0}.status-badge[data-tone=complete]{color:#446c8b;background:#eef4f9;border-color:#dbe7ef}.status-badge[data-tone=pending]{color:#916018;background:#fff7e7;border-color:#f3e3bc}.status-badge[data-tone=paused]{color:#91605a;background:#fcf0ed;border-color:#f0d9d3}
.project-detail-actions{display:flex;gap:10px;flex-wrap:wrap;padding-top:3px}.detail-button{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:44px;border:1px solid #dce8e2;border-radius:7px;padding:9px 15px;font:inherit;font-size:13px;cursor:pointer;line-height:1.5;white-space:nowrap;transition:background-color .15s,border-color .15s}.detail-button svg{width:16px;height:16px;flex-shrink:0}.detail-button.secondary{background:#fff;color:var(--project-ink)}.detail-button.secondary:hover{background:#f4f9f6;border-color:#b6d4c7}.detail-button.primary{background:var(--project-accent);border-color:var(--project-accent);color:#fff}.detail-button.primary:hover{background:#076c66;border-color:#076c66}.detail-button:focus-visible,.document-copy a:focus-visible{outline:2px solid var(--project-accent);outline-offset:4px}
.project-finances{padding:24px 30px 30px;background:#fff;border:1px solid var(--project-line);border-top:0;border-radius:0 0 14px 14px}.section-heading{display:flex;align-items:center;gap:9px;min-width:0}.section-heading h3{margin:0;font-size:15px;font-weight:650;color:var(--project-ink)}.section-note{margin-left:auto;font-size:12px;color:var(--project-muted)}
.finance-grid{display:grid;grid-template-columns:1.35fr 1fr 1fr;gap:24px;margin:22px 0 0}.finance-grid>div{min-width:0;padding-left:24px;border-left:1px solid #e6eeea}.finance-grid>div:first-child{padding-left:0;border-left:0}.finance-grid dt{font-size:12px;color:var(--project-muted)}.finance-grid dd{margin:9px 0 0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums;line-height:1.3;letter-spacing:-.025em}.contract-amount dd{font-size:clamp(26px,2.45vw,36px);font-weight:650;color:var(--project-accent)}.audit-amount dd{font-size:clamp(20px,1.8vw,25px);font-weight:600;color:var(--project-ink)}.currency-mark{font-size:.6em;font-weight:500;margin-right:6px;vertical-align:baseline}
.project-detail-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-top:20px}.detail-panel{min-width:0;background:#fff;border:1px solid var(--project-line);border-radius:12px;padding:25px 28px}.overview-fields{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px;margin:25px 0}.overview-fields>div,.date-fields>div{min-width:0}.overview-fields dt,.date-fields dt{font-size:12px;color:var(--project-muted)}.overview-fields dd,.date-fields dd{font-size:14px;color:var(--project-text);margin:7px 0 0;line-height:1.6;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.project-dates{border-top:1px solid var(--project-line);padding-top:22px}.dates-title{display:flex;gap:7px;align-items:center;color:var(--project-accent)}.dates-title svg{width:16px;height:16px}.dates-title h4{font-size:13px;font-weight:600;margin:0}.date-fields{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px;align-items:center;margin:18px 0 0}.document-count{margin-left:auto;flex-shrink:0;font-size:12px;color:var(--project-muted)}
.document-list{margin:16px 0 0;padding:0;list-style:none}.document-row{display:flex;align-items:flex-start;gap:12px;border-bottom:1px solid var(--project-line);padding:13px 0}.document-row:last-child{border-bottom:0;padding-bottom:0}.document-icon{display:flex;align-items:center;justify-content:center;flex-shrink:0;width:36px;height:42px;border:1px solid #e3ece6;border-radius:6px;color:var(--project-accent);background:#f6faf8}.document-icon svg{width:18px;height:18px}.document-copy{flex:1;min-width:0}.document-copy a{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:44px;color:var(--project-ink);font-size:14px;line-height:1.6;text-decoration:none;overflow-wrap:anywhere}.document-copy a:hover{color:var(--project-accent);text-decoration:underline;text-underline-offset:3px}.document-copy a svg{width:15px;height:15px;flex-shrink:0;color:var(--project-accent)}.document-name{display:block;font-size:14px;line-height:1.6;overflow-wrap:anywhere}.document-code{display:block;color:var(--project-muted);font-size:12px;line-height:1.7;overflow-wrap:anywhere;margin-top:2px}.documents-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:178px;text-align:center;padding:20px 0;color:var(--project-muted)}.documents-empty svg{height:30px;width:30px;color:#8aa799}.documents-empty p{margin:12px 0 6px;font-size:14px;color:var(--project-text)}.documents-empty>span{font-size:12px;line-height:1.8}
@media(max-width:1100px){.project-identity{flex-direction:column;gap:20px}.project-detail-actions{padding-top:0}.finance-grid{gap:18px;grid-template-columns:1.1fr 1fr 1fr}.finance-grid>div{padding-left:18px}.detail-panel{padding:24px}}
@media(max-width:760px){.project-identity,.project-finances{padding:22px 20px}.project-detail-actions{width:100%}.project-detail-actions .detail-button{flex:1}.finance-grid{grid-template-columns:minmax(0,1fr);gap:18px}.finance-grid>div{padding:18px 0 0;border-left:0;border-top:1px solid var(--project-line)}.finance-grid>div:first-child{padding-top:0;border-top:0}.project-detail-body{grid-template-columns:minmax(0,1fr);gap:16px;margin-top:16px}.detail-panel{padding:22px 20px}.overview-fields,.date-fields{grid-template-columns:minmax(0,1fr);gap:18px}.contract-amount dd{font-size:30px}.section-note{font-size:11px}}
@media(prefers-reduced-motion:reduce){.detail-button{transition:none}}
</style>
