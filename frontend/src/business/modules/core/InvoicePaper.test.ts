// @vitest-environment jsdom
import {describe, expect, it} from 'vitest'
import {mount} from '@vue/test-utils'
import InvoicePaper from './InvoicePaper.vue'

describe('invoice paper amount display', () => {
  it.each([
    ['100', '13', '113.00', '100.00', '13.00'],
    ['-100', '-13', '-113.00', '-100.00', '-13.00'],
    ['100', 0, '100.00', '100.00', '0.00'],
    ['1.005', '0.005', '1.01', '1.01', '0.01'],
    [undefined, '13', '待核实', '待核实', '13.00'],
    ['100', 'invalid', '待核实', '100.00', '待核实'],
  ])('formats amounts and preserves unknowns (%s, %s)', (untaxed, tax, totalText, untaxedText, taxText) => {
    const wrapper = mount(InvoicePaper, {props: {invoice: {total_amount: untaxed, tax_amount: tax}}})
    expect(wrapper.find('thead').text()).toContain('不含税金额')
    expect(wrapper.find('.invoice-total').text()).toContain(totalText)
    const currency = (value: string) => value === '待核实' ? value : `¥${value}`
    expect(wrapper.findAll('tfoot td').map(cell => cell.text())).toEqual([currency(untaxedText!), '', currency(taxText!)])
    expect(wrapper.text()).not.toContain('NaN')
    wrapper.unmount()
  })
})
