import {describe,expect,it} from 'vitest'
import {formatInvoiceMoney,invoiceAmounts,invoiceTotal,invoiceTotalSum} from './model'

describe('invoice display amounts',()=>{
 it('shows the inclusive total and labels its two separate source amounts',()=>{
  expect(invoiceTotal({total_amount:'100',tax_amount:'13'})).toBe('113.00')
  expect(invoiceAmounts({total_amount:'100',tax_amount:'13'})).toEqual({total:'¥113.00',untaxed:'¥100.00',tax:'¥13.00'})
 })
 it.each([
  [{total_amount:100,tax_amount:0},'100.00'],
  [{total_amount:'-100',tax_amount:'-13'},'-113.00'],
  [{total_amount:' 100.00 ',tax_amount:' 13 '},'113.00'],
  [{total_amount:0.1,tax_amount:0.2},'0.30'],
  [{total_amount:'1.005',tax_amount:0},'1.01'],
  [{total_amount:'-1.005',tax_amount:0},'-1.01'],
  [{total_amount:'0.004',tax_amount:'0.004'},'0.01'],
  [{total_amount:'9007199254740993.10',tax_amount:'0.20'},'9007199254740993.30'],
  [{total_amount:1e-7,tax_amount:0.01},'0.01'],
  [{total_amount:'1.25e2',tax_amount:'1.3e1'},'138.00'],
 ])('adds the original decimal precision before rounding (%o)',(invoice,total)=>{
  expect(invoiceTotal(invoice)).toBe(total)
  expect(invoiceAmounts(invoice).total).toBe(`¥${total}`)
 })
 it.each([undefined,null,'','   ','bad','NaN','Infinity',NaN,Infinity,-Infinity,true,false,{},[],new Number(1)])('does not invent zero for an absent or invalid amount (%o)',value=>{
  expect(invoiceTotal({total_amount:value,tax_amount:13})).toBeNull()
  expect(invoiceTotal({total_amount:100,tax_amount:value})).toBeNull()
  expect(formatInvoiceMoney(value)).toBe('待核实')
 })
 it('retains known components when another component needs verification',()=>{
  expect(invoiceAmounts({total_amount:'100'})).toEqual({total:'待核实',untaxed:'¥100.00',tax:'待核实'})
  expect(invoiceAmounts(null)).toEqual({total:'待核实',untaxed:'待核实',tax:'待核实'})
 })
 it.each([
  ['0','¥0.00'],[0,'¥0.00'],['-0.004','¥0.00'],['-1.005','¥-1.01'],
  [' 100.2 ','¥100.20'],['9007199254740993.01','¥9007199254740993.01'],
  [1e21,'¥1000000000000000000000.00'],[1e-7,'¥0.00'],['2.999','¥3.00'],
 ])('formats RMB with exactly two decimal places (%o)',(value,expected)=>{
  expect(formatInvoiceMoney(value)).toBe(expected)
 })
 it('totals selected invoice source values without rounding every invoice first',()=>{
  expect(invoiceTotalSum([{total_amount:'100',tax_amount:'13'},{total_amount:'-10',tax_amount:'0'}])).toBe('103.00')
  expect(invoiceTotalSum([{total_amount:'0.004',tax_amount:0},{total_amount:'0.004',tax_amount:0}])).toBe('0.01')
  expect(invoiceTotalSum([{total_amount:'-0.004',tax_amount:0},{total_amount:'-0.004',tax_amount:0}])).toBe('-0.01')
  expect(invoiceTotalSum([])).toBe('0.00')
 })
 it('marks a selected-invoice sum as unverified when any source component is invalid',()=>{
  expect(invoiceTotalSum([{total_amount:100,tax_amount:13},{total_amount:10}])).toBeNull()
  expect(invoiceTotalSum([{total_amount:100,tax_amount:13},{total_amount:10,tax_amount:'bad'}])).toBeNull()
 })
})
