// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import AttachmentPanel from './AttachmentPanel.vue'
import { request } from '../api'
import { showImagePreview } from 'vant'
import type { Attachment, Kind } from '../model'

vi.mock('../api', () => ({ request: vi.fn() }))
vi.mock('vant', () => ({ showImagePreview: vi.fn(), showToast: vi.fn() }))

const wrappers: VueWrapper[] = []
function render(kind: Kind = 'project', attachments: Attachment[] = [], readonly = false) {
  const wrapper = mount(AttachmentPanel, {
    props: { kind, modelValue: attachments, readonly,
      'onUpdate:modelValue': (value: Attachment[]) => { void wrapper.setProps({ modelValue: value }) } },
    global: { stubs: {
      'van-button': { props: ['disabled'], template: '<button :disabled="disabled"><slot /></button>' },
      'van-icon': true, 'van-loading': true,
    } },
  })
  wrappers.push(wrapper)
  return wrapper
}
async function choose(wrapper: VueWrapper, ...files: File[]) {
  const input = wrapper.get('input[aria-label="选择文档或其他附件"]')
  Object.defineProperty(input.element, 'files', { value: files, configurable: true })
  await input.trigger('change')
}
function latest(wrapper: VueWrapper, name: string) {
  const events = wrapper.emitted(name)
  return events?.[events.length - 1]?.[0]
}
const uploaded = (name: string): Attachment => ({
  id: null, filename: `20260924_storage.${name.split('.').pop()}`,
  original_filename: name, url: `/uploads/project_attachments/${encodeURIComponent(name)}`,
  size: 1234, code: 'mobile', custom_metadata: 'retained',
})
beforeEach(() => vi.resetAllMocks())
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

describe('AttachmentPanel upload contract', () => {
  it('preserves originals and Chinese image/PDF metadata across a sequential project upload', async () => {
    const original = Object.freeze({ id: 8, code: '旧合同', name: '原合同.pdf',
      url: 'https://oss.example/old.pdf?Signature=preview', file_path: 'https://oss.example/old.pdf',
      filename: 'old.pdf', size: 4321, custom_metadata: { keep: true } })
    const image = uploaded('现场照片.jpg')
    const pdf = uploaded('采购合同.pdf')
    vi.mocked(request).mockResolvedValueOnce({ code: 0, data: image }).mockResolvedValueOnce({ code: 0, data: pdf })
    const wrapper = render('project', [original])
    const files = [new File(['image'], '现场照片.jpg', { type: 'image/jpeg' }), new File(['pdf'], '采购合同.pdf', { type: 'application/pdf' })]
    await choose(wrapper, ...files)
    await flushPromises()
    expect(request).toHaveBeenCalledTimes(2)
    for (let index = 0; index < 2; index++) {
      const [url, options] = vi.mocked(request).mock.calls[index]!
      expect(url).toBe('/upload/')
      expect(options?.method).toBe('POST')
      const form = options?.body as FormData
      expect(form.get('file')).toBe(files[index])
      expect(form.get('path')).toBe('project_attachments')
      expect(form.get('attachment_code')).toBe('mobile')
      expect(form.has('project_id')).toBe(false)
    }
    expect(latest(wrapper, 'update:modelValue')).toEqual([
      original, { ...image, name: '现场照片.jpg' }, { ...pdf, name: '采购合同.pdf' },
    ])
    expect(wrapper.text()).toContain('现场照片.jpg')
    expect(wrapper.text()).toContain('采购合同.pdf')
    expect(latest(wrapper, 'busy')).toBe(false)
    expect(latest(wrapper, 'blocked')).toBe(false)
    expect(wrapper.find('.discard-link').exists()).toBe(false)
  })

  it.each(['order', 'pay'] as const)('uses the %s path without changing metadata or creating a project association', async kind => {
    const data = { ...uploaded('付款凭证.pdf'), code: null }
    vi.mocked(request).mockResolvedValue({ code: 0, data })
    const wrapper = render(kind)
    await choose(wrapper, new File(['pdf'], '付款凭证.pdf'))
    await flushPromises()
    const form = vi.mocked(request).mock.calls[0]![1]?.body as FormData
    expect(form.get('path')).toBe(`${kind}_attachments`)
    expect(form.has('project_id')).toBe(false)
    expect(form.has('attachment_code')).toBe(false)
    expect(latest(wrapper, 'update:modelValue')).toEqual([{ ...data, name: '付款凭证.pdf' }])
  })

  it('blocks saving after failure, retains the File through auth expiry, and retries only on demand', async () => {
    const file = new File(['pdf'], '重试合同.pdf')
    let finish!: (value: { code: number; data: Attachment }) => void
    vi.mocked(request).mockRejectedValueOnce(new Error('登录已过期，请重新登录。当前表单已保留。'))
      .mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    const wrapper = render()
    await choose(wrapper, file)
    await flushPromises()
    expect(request).toHaveBeenCalledTimes(1)
    expect(latest(wrapper, 'busy')).toBe(false)
    expect(latest(wrapper, 'blocked')).toBe(true)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.text()).toContain('登录已过期')
    await wrapper.get('button[aria-label="重新上传 重试合同.pdf"]').trigger('click')
    expect(latest(wrapper, 'busy')).toBe(true)
    expect((vi.mocked(request).mock.calls[1]![1]?.body as FormData).get('file')).toBe(file)
    finish({ code: 0, data: uploaded(file.name) })
    await flushPromises()
    expect(latest(wrapper, 'busy')).toBe(false)
    expect(latest(wrapper, 'blocked')).toBe(false)
    expect(wrapper.find('.upload-failed').exists()).toBe(false)
  })

  it('rejects files above 10 MB locally and clears blocked only when discarded', async () => {
    const wrapper = render()
    const file = new File(['large'], '超大合同.pdf')
    Object.defineProperty(file, 'size', { value: 10 * 1024 * 1024 + 1 })
    await choose(wrapper, file)
    await flushPromises()
    expect(request).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('文件超过 10 MB')
    expect(latest(wrapper, 'blocked')).toBe(true)
    expect(latest(wrapper, 'busy')).toBe(false)
    await wrapper.get('button[aria-label="移除失败文件 超大合同.pdf"]').trigger('click')
    expect(latest(wrapper, 'blocked')).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('previews the signed image URL without changing stored data and hides unsafe links', async () => {
    const image = { ...uploaded('现场.jpg'), preview_url: 'https://oss.example/site.jpg?Signature=preview', url: 'https://oss.example/site.jpg', file_path: 'https://oss.example/site.jpg' }
    const pdf = uploaded('合同.pdf')
    const wrapper = render('project', [image, pdf, { name: '恶意.pdf', url: 'javascript:alert(1)' }], true)
    expect(wrapper.find('input[type=file]').exists()).toBe(false)
    expect(wrapper.find('.attachment-actions').exists()).toBe(false)
    await wrapper.get('button[aria-label="预览 现场.jpg"]').trigger('click')
    expect(showImagePreview).toHaveBeenCalledWith({ images: [image.preview_url], closeable: true })
    expect(wrapper.get('a').attributes()).toMatchObject({ target: '_blank', rel: 'noopener noreferrer' })
    expect(wrapper.findAll('a')).toHaveLength(1)
    expect(wrapper.text()).toContain('暂无预览')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(image.file_path).toBe('https://oss.example/site.jpg')
    expect(request).not.toHaveBeenCalled()
  })

  it('keeps busy throughout a queued batch and retains a failed item while the next upload succeeds', async () => {
    let resolveSecond!: (value: { code: number; data: Attachment }) => void
    vi.mocked(request).mockRejectedValueOnce(new Error('网络故障'))
      .mockImplementationOnce(() => new Promise(resolve => { resolveSecond = resolve }))
    const wrapper = render()
    await choose(wrapper, new File(['1'], '失败.jpg'), new File(['2'], '成功.pdf'))
    await flushPromises()
    expect(wrapper.emitted('busy')).toEqual([[false], [true]])
    expect(latest(wrapper, 'blocked')).toBe(true)
    resolveSecond({ code: 0, data: uploaded('成功.pdf') })
    await flushPromises()
    expect(latest(wrapper, 'busy')).toBe(false)
    expect(latest(wrapper, 'blocked')).toBe(true)
    expect(latest(wrapper, 'update:modelValue')).toHaveLength(1)
    await wrapper.get('button[aria-label="移除失败文件 失败.jpg"]').trigger('click')
    expect(latest(wrapper, 'blocked')).toBe(false)
  })
})
