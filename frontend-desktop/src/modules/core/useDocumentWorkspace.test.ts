// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {ref} from 'vue'
import {afterEach, expect, it, vi} from 'vitest'
import {useDocumentWorkspace} from './useDocumentWorkspace'

const mocks = vi.hoisted(() => ({request: vi.fn()}))
vi.mock('../../api', () => ({request: mocks.request, query: (p: any) => new URLSearchParams(p).toString()}))
afterEach(() => {vi.useRealTimers(); vi.clearAllMocks()})

it('loads only a page and ignores slow responses from an earlier filter', async () => {
  vi.useFakeTimers()
  let resolveOld!: (value: any) => void
  mocks.request.mockImplementationOnce(() => new Promise(resolve => {resolveOld = resolve}))
  mocks.request.mockResolvedValue({data: [{id: 2}], count: 1200, projects: [], contacts: ['新联系人'], totals: {paid: '12'}})
  const filters = ref({project_id: ''})
  let state!: ReturnType<typeof useDocumentWorkspace>
  const wrapper = mount({setup() {state = useDocumentWorkspace('payments', filters); return () => null}})
  await flushPromises()
  expect(mocks.request.mock.calls[0][0]).toContain('/workspace/payments?')
  expect(mocks.request.mock.calls[0][0]).toContain('limit=20')
  filters.value = {project_id: '2'}
  await vi.advanceTimersByTimeAsync(250); await flushPromises()
  expect(state.rows.value).toEqual([{id: 2}])
  expect(state.count.value).toBe(1200)
  resolveOld({data: [{id: 1}], count: 1, projects: [], contacts: [], totals: {}})
  await flushPromises()
  expect(state.rows.value).toEqual([{id: 2}])
  state.page.value = 2
  await vi.advanceTimersByTimeAsync(250); await flushPromises()
  expect(mocks.request.mock.calls.at(-1)?.[0]).toContain('page=2')
  filters.value = {project_id: '3'}
  await vi.advanceTimersByTimeAsync(250); await flushPromises()
  expect(state.page.value).toBe(1)
  expect(mocks.request.mock.calls.at(-1)?.[0]).toContain('project_id=3')
  wrapper.unmount()
})
