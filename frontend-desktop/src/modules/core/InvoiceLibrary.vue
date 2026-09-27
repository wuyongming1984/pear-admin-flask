<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {useRouter} from 'vue-router'
import {safeUrl} from '../../api'
import InvoicePaper from './InvoicePaper.vue'
import {formatMoney, sumMoney} from './money'
import {ocrStatusLabel, type Row} from './model'

const props = defineProps<{rows: Row[]; count: number; busy: boolean; searching?: boolean; selection: Row[]}>()
const emit = defineEmits<{selection: [rows: Row[]]; remove: [rows: Row[]]; ocr: [rows: Row[]]}>()
const router = useRouter()
const activeId = ref<any>()
const active = computed(() => props.rows.find(row => row.id === activeId.value) || props.rows[0])
const uploadVisible = ref(false), moreVisible = ref(false)
watch(() => props.rows, rows => {
  if (!rows.some(row => row.id === activeId.value)) activeId.value = rows[0]?.id
  emit('selection', [])
})
function toggle(row: Row, checked: unknown) {
  emit('selection', checked ? [...props.selection.filter(item => item.id !== row.id), row] : props.selection.filter(item => item.id !== row.id))
}
const amount = (row: Row) => formatMoney(sumMoney([row.total_amount, row.tax_amount]))
</script>

<template>
  <div class="invoice-library">
    <aside class="invoice-sidebar" aria-label="发票清单">
      <header><strong>发票清单</strong><span class="invoice-count">{{count}}</span></header>
      <div class="invoice-search">
        <el-button type="primary" class="invoice-add" @click="uploadVisible = !uploadVisible">新增发票 / 上传识别</el-button>
        <slot name="search" />
      </div>
      <div class="invoice-batch">
        <el-checkbox :model-value="!!rows.length && selection.length === rows.length" :indeterminate="selection.length > 0 && selection.length < rows.length" @change="emit('selection', $event ? [...rows] : [])">本页全选</el-checkbox>
        <span role="status" aria-live="polite">{{searching ? '正在查找…' : `找到 ${count} 张 · 已选 ${selection.length} 张`}}</span>
      </div>
      <div class="invoice-cards" :aria-busy="searching">
        <div v-for="row in rows" :key="row.id" class="invoice-card" :class="{active: active?.id === row.id}">
          <el-checkbox class="invoice-check" :aria-label="`选择发票 ${row.invoice_number || row.id}`" :model-value="selection.some(item => item.id === row.id)" @change="toggle(row, $event)" />
          <button class="invoice-select" :aria-pressed="active?.id === row.id" @click="activeId = row.id">
            <strong>{{row.buyer_name || '未识别购买方'}}</strong>
            <span class="invoice-number">{{row.invoice_number || '暂无发票号码'}}</span>
            <span>{{row.seller_name || '未识别销售方'}}</span>
            <span class="invoice-card-bottom"><time>{{row.invoice_date || '日期待识别'}}</time><b>¥{{amount(row)}}</b></span>
          </button>
        </div>
        <el-empty v-if="!rows.length && !searching" description="暂无符合条件的发票" :image-size="60" />
      </div>
      <div class="invoice-pagination"><slot name="pagination" /></div>
    </aside>

    <main class="invoice-content">
      <header class="invoice-content-header">
        <strong>发票详情库</strong>
        <div class="invoice-actions">
          <el-button v-if="active && safeUrl(active.file_path)" tag="a" :href="safeUrl(active.file_path)" target="_blank" rel="noopener noreferrer">查看原文件</el-button>
          <el-button v-if="active" :disabled="busy" @click="router.push(`/invoices/${active.id}/edit`)">编辑大类 / 抵扣</el-button>
          <el-button @click="moreVisible = !moreVisible">更多操作</el-button>
        </div>
      </header>
      <div v-if="uploadVisible" class="invoice-extra"><slot name="upload" /></div>
      <div v-if="moreVisible" class="invoice-extra"><slot name="tools" /></div>
      <div class="invoice-preview">
        <template v-if="active">
          <div class="invoice-detail-actions">
            <span>{{ocrStatusLabel(active.ocr_status)}}</span>
            <div>
              <el-button link :disabled="busy" @click="emit('ocr', [active])">重新识别</el-button>
              <el-button link @click="router.push(`/invoices/${active.id}`)">关联付款与详情</el-button>
              <el-button link type="danger" :disabled="busy" @click="emit('remove', [active])">删除</el-button>
            </div>
          </div>
          <InvoicePaper :invoice="active" />
        </template>
        <el-empty v-else description="请选择或上传发票，查看票面详情" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.invoice-library{display:grid;grid-template-columns:300px minmax(0,1fr);gap:16px;height:calc(100dvh - 228px);min-height:560px}
.invoice-sidebar,.invoice-content{min-width:0;border:1px solid var(--el-border-color);border-radius:8px;background:var(--el-bg-color);display:flex;flex-direction:column;overflow:hidden}
.invoice-sidebar>header,.invoice-content-header{padding:15px 18px;border-bottom:1px solid var(--el-border-color);display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:65px}
.invoice-sidebar>header{flex-shrink:0;color:var(--el-color-primary)}.invoice-count{background:var(--el-color-primary-light-9);padding:2px 9px;border-radius:12px;font-size:12px}
.invoice-search{padding:14px;border-bottom:1px solid var(--el-border-color);flex-shrink:0;overflow:auto}.invoice-add{width:100%;margin-bottom:12px}
.invoice-search :deep(.search-grid){display:grid;grid-template-columns:1fr;gap:0;padding:0;margin:0;border:0;background:transparent;box-shadow:none}.invoice-search :deep(.el-form-item){margin-bottom:10px}.invoice-search :deep(.el-form-item__label){font-size:12px;padding:0;height:auto;line-height:22px}.invoice-search :deep(.el-select){width:100%}.invoice-search :deep(.actions){justify-content:flex-start;gap:6px}.invoice-search :deep(.actions .el-button+.el-button){margin-left:0}
.invoice-batch{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:5px 14px;font-size:12px;color:var(--el-text-color-secondary)}
.invoice-cards{flex:1;min-height:0;overflow:auto;padding:0 10px 10px}.invoice-card{display:flex;align-items:flex-start;border:1px solid transparent;border-radius:6px;margin-bottom:8px;padding:10px 8px;background:var(--el-fill-color-light)}.invoice-card.active{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9);box-shadow:inset 3px 0 var(--el-color-primary)}.invoice-check{height:22px;margin-right:7px}.invoice-select{padding:0;text-align:left;border:0;background:none;color:var(--el-text-color-primary);cursor:pointer;display:flex;flex-direction:column;gap:7px;min-width:0;width:100%;font-size:12px}.invoice-select>strong{font-size:14px}.invoice-select>span,.invoice-select>strong{max-width:100%;overflow-wrap:anywhere}.invoice-number{font-family:monospace;color:var(--el-color-primary)}.invoice-card-bottom{display:flex;justify-content:space-between;gap:8px;width:100%;color:var(--el-text-color-secondary)}.invoice-card-bottom b{color:var(--el-color-primary);white-space:nowrap}
.invoice-pagination{flex-shrink:0;border-top:1px solid var(--el-border-color);padding:8px}.invoice-pagination :deep(.el-pagination){margin:0;justify-content:center;gap:3px}.invoice-pagination :deep(.el-pagination__sizes){margin-right:0}
.invoice-actions{display:flex;flex-wrap:wrap;gap:8px}.invoice-actions :deep(.el-button+.el-button){margin-left:0}.invoice-content-header>strong{white-space:nowrap}.invoice-preview{background:#e6e6e6;padding:20px;flex:1;min-height:0;overflow:auto}.invoice-preview :deep(.invoice-paper){max-width:1100px;margin:0 auto;min-height:600px;border-radius:0;padding:36px;box-shadow:0 5px 20px #0002}.invoice-detail-actions{display:flex;justify-content:space-between;align-items:center;gap:12px;max-width:1100px;margin:0 auto 12px;color:#536b63;font-size:12px}.invoice-extra{padding:14px;max-height:320px;overflow:auto;border-bottom:1px solid var(--el-border-color)}.invoice-extra :deep(.panel){margin:0;padding:0;border:0}.invoice-extra :deep(.upload-panel){display:flex;flex-wrap:wrap;gap:12px}.invoice-extra :deep(.el-select),.invoice-extra :deep(.el-input){max-width:230px}
.invoice-library .invoice-sidebar .invoice-search :deep(.search-grid){margin:0}
.invoice-library .invoice-pagination :deep(.el-pagination){margin:0;padding:0;border-top:0}
@media(min-width:761px) and (max-height:850px){
 .invoice-search{padding:10px 14px}
 .invoice-search :deep(.el-form-item){margin-bottom:7px}
 .invoice-search :deep(.el-input__wrapper),.invoice-search :deep(.el-select__wrapper){min-height:32px;height:32px}
 .invoice-search :deep(.el-button){min-height:32px;height:32px}
 .invoice-library .invoice-sidebar .invoice-search :deep(.search-grid){padding:0}
}
@media(max-width:1100px){.invoice-library{grid-template-columns:260px minmax(0,1fr)}.invoice-content-header{align-items:flex-start;flex-direction:column}.invoice-preview{padding:12px}}
@media(max-width:760px){.invoice-library{height:auto;min-height:0;grid-template-columns:1fr}.invoice-sidebar{max-height:600px}.invoice-search{max-height:260px}.invoice-cards{max-height:260px}.invoice-preview{max-height:850px}.invoice-preview :deep(.invoice-paper){padding:20px}.invoice-content-header{flex-direction:row;flex-wrap:wrap}}
</style>
