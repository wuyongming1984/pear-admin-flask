/** Display-only invoice fields: total_amount is the tax-exclusive amount in the API. */
export type InvoiceAmountSource = {
 total_amount?:unknown
 tax_amount?:unknown
}

type Decimal = {value:bigint;scale:number}
type InvoiceSource = InvoiceAmountSource | null | undefined
const unverified = '待核实'

/** Parse decimal values without coercing empty fields, booleans or objects to zero. */
function decimal(value:unknown):Decimal|null{
 if(typeof value!=='string'&&typeof value!=='number')return null
 if(typeof value==='number'&&!Number.isFinite(value))return null
 const raw=String(value).trim()
 const match=raw.match(/^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/)
 if(!match)return null
 const exponent=Number(match[5]||0)
 // Includes the complete finite Number range while preventing unbounded exponent expansion.
 if(!Number.isSafeInteger(exponent)||Math.abs(exponent)>1000)return null
 const fraction=match[3]??match[4]??''
 let scale=fraction.length-exponent
 let coefficient=BigInt((match[2]||'0')+fraction)*(match[1]==='-'?-1n:1n)
 if(scale<0){coefficient*=10n**BigInt(-scale);scale=0}
 return {value:coefficient,scale}
}

function add(left:Decimal,right:Decimal):Decimal{
 const scale=Math.max(left.scale,right.scale)
 return {value:left.value*10n**BigInt(scale-left.scale)+right.value*10n**BigInt(scale-right.scale),scale}
}

/** Round half away from zero only after decimal addition, including red invoices. */
function twoDecimals(amount:Decimal):string{
 const negative=amount.value<0n
 const value=negative?-amount.value:amount.value
 let cents:bigint
 if(amount.scale<=2)cents=value*10n**BigInt(2-amount.scale)
 else{
  const divisor=10n**BigInt(amount.scale-2)
  cents=value/divisor
  if((value%divisor)*2n>=divisor)cents+=1n
 }
 return (negative&&cents!==0n?'-':'')+(cents/100n).toString()+'.'+(cents%100n).toString().padStart(2,'0')
}

function inclusiveDecimal(invoice:InvoiceSource):Decimal|null{
 const untaxed=decimal(invoice?.total_amount)
 const tax=decimal(invoice?.tax_amount)
 return untaxed&&tax?add(untaxed,tax):null
}

/** Tax-inclusive display amount; a missing component requires verification, even if tax is usually zero. */
export function invoiceTotal(invoice:InvoiceSource):string|null{
 const total=inclusiveDecimal(invoice)
 return total?twoDecimals(total):null
}

export function formatInvoiceMoney(value:unknown):string{
 const amount=decimal(value)
 return amount?'¥'+twoDecimals(amount):unverified
}

/** Every invoice view uses the same display contract; stored values remain untouched. */
export function invoiceAmounts(invoice:InvoiceSource):{total:string;untaxed:string;tax:string}{
 return {total:formatInvoiceMoney(invoiceTotal(invoice)),untaxed:formatInvoiceMoney(invoice?.total_amount),tax:formatInvoiceMoney(invoice?.tax_amount)}
}

/** Sum original invoice decimals and round once; unknown components make the sum unverified. */
export function invoiceTotalSum(invoices:readonly InvoiceSource[]):string|null{
 let total:Decimal={value:0n,scale:0}
 for(const invoice of invoices){
  const amount=inclusiveDecimal(invoice)
  if(!amount)return null
  total=add(total,amount)
 }
 return twoDecimals(total)
}
