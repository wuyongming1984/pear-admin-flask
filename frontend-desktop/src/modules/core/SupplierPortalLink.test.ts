// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import ElementPlus from 'element-plus'
import {afterEach, beforeEach, expect, it, vi} from 'vitest'
import SupplierPortalLink from './SupplierPortalLink.vue'

const mocks = vi.hoisted(() => ({allRows: vi.fn(), request: vi.fn(), error: vi.fn(), success: vi.fn()}))
vi.mock('../../api', () => ({allRows: mocks.allRows, request: mocks.request}))
vi.mock('element-plus', async importOriginal => ({...await importOriginal<typeof import('element-plus')>(), ElMessage: {error: mocks.error, success: mocks.success}}))
let wrapper: ReturnType<typeof mount> | undefined
const clipboard = vi.fn()
beforeEach(() => {
  vi.clearAllMocks()
  Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: clipboard}})
  clipboard.mockResolvedValue(undefined)
  mocks.allRows.mockResolvedValue([{id: 9, name: '相似姓名', contact_person: '张三丰'}, {id: 42, name: '供应商', contact_person: ' 张三 '}])
  mocks.request.mockImplementation(async path => ({code: 0, data: {url: path === '/supplier/42/token' ? '/portal/reconcile/existing-token' : '/portal/reconcile/wrong-contact'}}))
})
afterEach(() => {wrapper?.unmount(); document.body.innerHTML = ''; vi.restoreAllMocks()})
async function setup(contact = '张三') {
  wrapper = mount(SupplierPortalLink, {props: {contact}, attachTo: document.body, global: {plugins: [ElementPlus], stubs: {teleport: true, transition: true}}})
  await wrapper.get('button').trigger('click'); await flushPromises()
  return wrapper
}
it('opens the exact contact link while leaving the surrounding contact selection untouched', async () => {
  const onClick = vi.fn()
  const parent = document.createElement('div'); document.body.appendChild(parent); parent.addEventListener('click', onClick)
  wrapper = mount(SupplierPortalLink, {props: {contact: '张三'}, attachTo: parent, global: {plugins: [ElementPlus], stubs: {teleport: true, transition: true}}})
  await wrapper.get('button').trigger('click'); await flushPromises()
  expect(onClick).not.toHaveBeenCalled()
  expect(wrapper.get('input[aria-label="电子对账链接"]').element).toHaveProperty('value', 'http://localhost:3000/portal/reconcile/existing-token')
  expect(mocks.request).toHaveBeenCalledWith('/supplier/42/token', {method: 'POST', body: '{"reuse_existing":true}'})
  expect(wrapper.get('a').attributes('href')).toBe('http://localhost:3000/portal/reconcile/existing-token')
})
it('copies the complete displayed reconciliation link', async () => {
  const w = await setup()
  await w.findAll('button').find(b => b.text() === '复制链接')!.trigger('click'); await flushPromises()
  expect(clipboard).toHaveBeenCalledWith('http://localhost:3000/portal/reconcile/existing-token')
  expect(mocks.success).toHaveBeenCalledWith('对账链接已复制')
})
it('uses the selectable input when clipboard access fails and reports a failed fallback honestly', async () => {
  clipboard.mockRejectedValue(new Error('Denied'))
  Object.defineProperty(document, 'execCommand', {configurable: true, value: vi.fn(() => false)})
  const w = await setup()
  await w.findAll('button').find(b => b.text() === '复制链接')!.trigger('click'); await flushPromises()
  const input = w.get('input').element as HTMLInputElement
  expect(input.selectionEnd! - input.selectionStart!).toBe(input.value.length)
  expect(mocks.success).not.toHaveBeenCalled()
  expect(mocks.error).toHaveBeenCalledWith('自动复制失败，请选中链接后手动复制')
})
it('never generates a link for a merely similar contact', async () => {
  mocks.allRows.mockResolvedValue([{id: 9, name: '相似姓名', contact_person: '张三丰'}])
  const w = await setup()
  expect(mocks.request).not.toHaveBeenCalled()
  expect(w.find('input').exists()).toBe(false)
  expect(mocks.error).toHaveBeenCalledWith('未找到该联系人的供应商，请先在供应商管理中完善联系人资料')
})
it('rejects an external URL instead of presenting it as a reconciliation link', async () => {
  mocks.request.mockResolvedValue({code: 0, data: {url: 'https://elsewhere.test/portal/reconcile/token'}})
  const w = await setup()
  expect(w.find('input').exists()).toBe(false)
  expect(mocks.error).toHaveBeenCalledWith('对账链接格式不正确，请重试')
})
it('prevents concurrent generation and restores the button after a network error', async () => {
  let reject!: (error: Error) => void
  mocks.allRows.mockImplementation(() => new Promise((_, no) => {reject = no}))
  wrapper = mount(SupplierPortalLink, {props: {contact: '张三'}, global: {plugins: [ElementPlus]}})
  await wrapper.get('button').trigger('click')
  expect(wrapper.get('button').attributes('disabled')).toBeDefined()
  await wrapper.get('button').trigger('click')
  expect(mocks.allRows).toHaveBeenCalledTimes(1)
  reject(new Error('网络连接失败')); await flushPromises()
  expect(wrapper.get('button').attributes('disabled')).toBeUndefined()
  expect(mocks.error).toHaveBeenCalledWith('网络连接失败')
})
