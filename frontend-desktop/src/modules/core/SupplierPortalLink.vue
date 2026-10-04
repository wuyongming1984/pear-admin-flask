<script setup lang="ts">
import {ref} from 'vue'
import {ElMessage} from 'element-plus'
import {allRows, request} from '../../api'
import type {Row} from './model'

const props = defineProps<{contact: string}>()
const busy = ref(false), visible = ref(false), link = ref('')
const linkInput = ref<HTMLInputElement>()

async function open() {
  if (busy.value) return
  busy.value = true
  link.value = ''
  try {
    const name = props.contact.trim()
    const candidates = await allRows('/supplier/', {contact_person: name, mode: 'slim'})
    // The portal aggregates all suppliers with this exact contact, across projects.
    const supplier = candidates.filter((s: Row) => String(s.contact_person || '').trim() === name)
      .sort((a: Row, b: Row) => Number(a.id) - Number(b.id))[0]
    if (!name || !supplier) throw new Error('未找到该联系人的供应商，请先在供应商管理中完善联系人资料')
    const response = await request(`/supplier/${supplier.id}/token`, {
      method: 'POST', body: JSON.stringify({reuse_existing: true}),
    })
    const path = String(response.data?.url || '')
    if (!/^\/portal\/reconcile\/[A-Za-z0-9_-]+$/.test(path)) throw new Error('对账链接格式不正确，请重试')
    link.value = new URL(path, location.origin).href
    visible.value = true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '获取对账链接失败')
  } finally {
    busy.value = false
  }
}

async function copy() {
  try {
    if (navigator.clipboard?.writeText) {
      try {await navigator.clipboard.writeText(link.value); ElMessage.success('对账链接已复制'); return} catch { /* Fall back on HTTP or denied clipboard access. */ }
    }
    linkInput.value?.focus()
    linkInput.value?.select()
    if (!document.execCommand?.('copy')) throw new Error('请选中链接后手动复制')
    ElMessage.success('对账链接已复制')
  } catch {
    ElMessage.error('自动复制失败，请选中链接后手动复制')
  }
}
</script>

<template>
  <button type="button" class="portal-link-button" :disabled="busy"
    :aria-label="`获取${contact}的电子对账链接`" :title="`${contact} · 电子对账链接`" @click.stop="open">
    <span v-if="busy" aria-hidden="true">…</span>
    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m10 13 4-4m-6 7-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m0 2 1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/></svg>
  </button>
  <el-dialog v-if="visible" v-model="visible" :title="`${contact} · 电子对账链接`" width="min(560px, calc(100vw - 32px))" append-to-body destroy-on-close>
    <p class="portal-help">复制链接发送给供应商，对方无需登录即可查看该联系人全部项目的订单、付款和余额。</p>
    <input ref="linkInput" class="portal-link-input" :value="link" aria-label="电子对账链接" readonly @focus="linkInput?.select()" />
    <p class="portal-note">获取已有链接不会使旧链接失效。如需重置，请到供应商详情操作。</p>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <a class="portal-open" :href="link" target="_blank" rel="noopener noreferrer">打开对账单</a>
      <el-button type="primary" @click="copy">复制链接</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.portal-help{margin:0 0 14px;line-height:1.7;color:#455e52}.portal-note{font-size:12px;color:#7b8c83;line-height:1.6;margin:12px 0 0}
.portal-link-input{box-sizing:border-box;width:100%;padding:10px 12px;border:1px solid #cddfd5;border-radius:5px;color:#136d65;font:13px Arial,sans-serif}
.portal-open{display:inline-block;margin:0 12px;padding:8px 0;color:#087f78}.portal-link-input:focus-visible,.portal-open:focus-visible{outline:2px solid #087f78;outline-offset:2px}
</style>
