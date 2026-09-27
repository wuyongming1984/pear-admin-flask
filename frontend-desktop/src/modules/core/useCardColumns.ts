import {ref, watch} from 'vue'

/** Keep each workspace's preferred card density without changing its filters. */
export function useCardColumns(workspace: 'orders' | 'payments') {
  const storageKey = `sf-${workspace}-card-columns`
  const columns = ref('auto')
  try {
    const saved = localStorage.getItem(storageKey)
    if (saved && ['auto', '1', '2', '3'].includes(saved)) columns.value = saved
  } catch { /* Layout still works when browser storage is unavailable. */ }
  watch(columns, value => {
    try { localStorage.setItem(storageKey, value) } catch { /* Keep the current selection in memory. */ }
  })
  return columns
}
