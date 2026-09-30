// @vitest-environment jsdom
import {mount, flushPromises} from '@vue/test-utils'
import {beforeEach, expect, it, vi} from 'vitest'
import OrderAttachments from './OrderAttachments.vue'
const mocks = vi.hoisted(() => ({request: vi.fn()}))
vi.mock('../../api', () => ({request: mocks.request, safeUrl: (v: string) => v || ''}))
vi.mock('element-plus', () => ({ElMessageBox: {confirm: vi.fn().mockResolvedValue('confirm')}}))
const old = {name: '原合同.pdf', url: '/old.pdf', id: 9}
function setup(order: any = {id: 1, attachments_list: [old]}) {
  return mount(OrderAttachments, {props: {order}, global: {stubs: {
    'el-button': {template: '<button><slot/></button>'}, 'el-empty': true, 'el-image': true, 'el-tag': true,
  }}})
}
async function drop(w: any, names = ['甲.pdf', '乙.pdf']) {
  await w.get('.attachment-editor').trigger('drop', {dataTransfer: {types: ['Files'], files: names.map(n => new File(['pdf'], n))}})
  await flushPromises()
}
beforeEach(() => {
  vi.clearAllMocks()
  mocks.request.mockImplementation(async (path, options) => path === '/upload/' ? {data: {url: '/' + options.body.get('file').name}} : {code: 0})
})
it('uploads multiple files and persists the full attachment list only to its order', async () => {
  const w = setup(); await drop(w)
  const writes = mocks.request.mock.calls.filter(([p]) => p === '/order/1')
  expect(writes.length).toBeGreaterThan(0)
  expect(writes.at(-1)![1].method).toBe('PUT')
  const payload = JSON.parse(writes.at(-1)![1].body)
  expect(Object.keys(payload)).toEqual(['attachments'])
  expect(JSON.parse(payload.attachments).map((a: any) => a.name)).toEqual(['原合同.pdf', '甲.pdf', '乙.pdf'])
  expect(JSON.parse(payload.attachments)[0]).toMatchObject(old)
  expect(w.text()).toContain('已保存'); w.unmount()
})
it('serializes saves when another upload finishes during an in-flight save', async () => {
  let resolve: any
  mocks.request.mockImplementation(async (path, options) => path === '/upload/' ? {data: {url: '/' + options.body.get('file').name}} : new Promise(r => {resolve = r}))
  const w = setup(); await drop(w)
  expect(mocks.request.mock.calls.filter(([p]) => p === '/order/1')).toHaveLength(1)
  resolve({code: 0}); await flushPromises()
  const writes = mocks.request.mock.calls.filter(([p]) => p === '/order/1')
  expect(writes).toHaveLength(2)
  expect(JSON.parse(JSON.parse(writes[1]![1].body).attachments)).toHaveLength(3)
  resolve({code: 0}); await flushPromises(); w.unmount()
})
it('keeps uploaded files visible after save failure and retries without uploading again', async () => {
  let fail = true
  mocks.request.mockImplementation(async (path) => {
    if (path === '/upload/') return {data: {url: '/new.pdf'}}
    if (fail) throw Error('保存失败')
    return {code: 0}
  })
  const w = setup(); await drop(w, ['合同.pdf'])
  expect(w.get('[role="alert"]').text()).toContain('保存失败')
  expect(w.text()).toContain('合同.pdf')
  fail = false; await w.get('button.retry-save').trigger('click'); await flushPromises()
  expect(mocks.request.mock.calls.filter(([p]) => p === '/upload/')).toHaveLength(1)
  expect(w.find('[role="alert"]').exists()).toBe(false); w.unmount()
})
it('persists removal of the last attachment as an empty list', async () => {
  const w = setup()
  await w.findAll('button').find(b => b.text() === '移除')!.trigger('click'); await flushPromises()
  expect(mocks.request).toHaveBeenCalledWith('/order/1', {method: 'PUT', body: JSON.stringify({attachments: '[]'})})
  w.unmount()
})
it('blocks editing malformed attachment data instead of erasing it', async () => {
  const w = setup({id: 2, attachments: 'broken'})
  expect(w.find('.attachment-editor').exists()).toBe(false)
  expect(w.get('[role="alert"]').text()).toContain('附件')
  expect(mocks.request).not.toHaveBeenCalled(); w.unmount()
})
