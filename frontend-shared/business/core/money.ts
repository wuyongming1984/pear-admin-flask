/** Decimal-string conversion: no binary floating point rounding in printed currency. */
export function uppercaseMoney(value:unknown):string{
 const match=String(value??'0').match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/);if(!match)return '金额格式错误'
 const digits='零壹贰叁肆伍陆柒捌玖';let integer=BigInt(match[2]!);const fraction=(match[3]||'').padEnd(2,'0');let output='';const groups=['','万','亿','万亿','亿亿'];let index=0;
 while(integer>0n){let group=Number(integer%10000n);const original=group;let part='';const units=['','拾','佰','仟'];for(let i=0;i<4;i++){const n=group%10;part=digits[n]+(n?units[i]:'')+part;group=Math.floor(group/10)}part=part.replace(/零+/g,'零').replace(/零$/,'').replace(/^零/,'');output=(part?part+groups[index]: '零')+output;integer/=10000n;if(integer>0n&&original>0&&original<1000)output='零'+output;index++}
 output=output.replace(/零+/g,'零').replace(/零$/,'')||'零';const j=Number(fraction[0]),fen=Number(fraction[1]);return (match[1]?'欠':'')+output+'元'+(j?digits[j]+'角':'')+(fen?(j?'':'零')+digits[fen]+'分':'')+(!j&&!fen?'整':'')
}
export function sumMoney(values:unknown[]):string{let total=0n;for(const value of values){const m=String(value??'0').match(/^(-?)(\d+)(?:\.(\d{0,2}))?$/);if(!m)continue;total+=(m[1]?-1n:1n)*(BigInt(m[2]!)*100n+BigInt((m[3]||'').padEnd(2,'0')))}const negative=total<0n;if(negative)total=-total;return (negative?'-':'')+(total/100n).toString()+'.'+(total%100n).toString().padStart(2,'0')}
/** Display-only formatting; outgoing amount strings remain untouched. */
export function formatMoney(value:unknown):string{if(value===null||value===undefined||value==='')return '—';const raw=String(value),m=raw.match(/^(-?)(\d+)(?:\.(\d*))?$/);if(!m)return raw;const fraction=(m[3]||'').padEnd(3,'0');let cents=BigInt(m[2]!)*100n+BigInt(fraction.slice(0,2));if(Number(fraction[2])>=5)cents+=1n;return (m[1]&&cents!==0n?'-':'')+(cents/100n).toString()+'.'+(cents%100n).toString().padStart(2,'0')}
