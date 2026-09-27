import {computed, ref, watch, onMounted, onActivated, onDeactivated, onBeforeUnmount, type Ref} from 'vue'
import {request, query} from '../../api'
import type {Row} from './model'

/** Page on the server; cancel superseded requests and never replace a newer selection. */
export function useDocumentWorkspace(kind: 'orders' | 'payments', filters: Ref<Record<string, unknown>>) {
  const rows = ref<Row[]>([]), projects = ref<Row[]>([]), contacts = ref<string[]>([])
  const totals = ref<Record<string, string>>({orders: '0', paid: '0', balance: '0', invoiced: '0'})
  const count = ref(0), page = ref(1), busy = ref(false), error = ref('')
  const pageCount = computed(() => Math.max(1, Math.ceil(count.value / 20)))
  let generation = 0, controller: AbortController | undefined, timer: ReturnType<typeof setTimeout> | undefined
  let timeout: ReturnType<typeof setTimeout> | undefined
  let active = true, activated = false
  function cancel() {generation++; controller?.abort(); clearTimeout(timer); clearTimeout(timeout)}
  async function load() {
    cancel()
    const current = generation
    controller = new AbortController()
    timeout = setTimeout(() => controller?.abort(), 30000)
    busy.value = true; error.value = ''
    try {
      const result = await request(`/workspace/${kind}?${query({...filters.value, page: page.value, limit: 20})}`, {signal: controller.signal})
      if (current !== generation) return
      const lastPage = Math.max(1, Math.ceil((result.count || 0) / 20))
      if (page.value > lastPage) {page.value = lastPage; return}
      rows.value = result.data; count.value = result.count || 0
      projects.value = result.projects; contacts.value = result.contacts
      totals.value = result.totals
    } catch (e) {
      if (current === generation) {rows.value = []; error.value = (e as Error).message || '单据加载失败'}
    } finally {if (current === generation) {clearTimeout(timeout); busy.value = false}}
  }
  watch(filters, () => {page.value = 1}, {flush: 'sync'})
  watch(() => query({...filters.value, page: page.value}), () => {
    cancel(); rows.value = []; error.value = ''
    if (active) {busy.value = true; timer = setTimeout(() => void load(), 180)}
  })
  onMounted(() => void load())
  onActivated(() => {active = true; if (activated) void load(); activated = true})
  onDeactivated(() => {active = false; cancel(); busy.value = false})
  onBeforeUnmount(cancel)
  return {rows, projects, contacts, totals, count, page, pageCount, busy, error, load}
}
