import {request,query} from '../api';
export {request,query} from '../api';
export async function allRows(path:string,params:Record<string,any>={}):Promise<any[]>{
 const rows:any[]=[];let last='';
 for(let page=1;page<=1000;page++){
  const response=await request(`${path}${path.includes('?')?'&':'?'}${query({...params,page,limit:500})}`);
  const batch=Array.isArray(response)?response:Array.isArray(response.data)?response.data:response.data?.items||[];
  if(!batch.length)return rows;
  const fingerprint=JSON.stringify(batch);if(fingerprint===last)throw new Error('接口分页未推进，已停止加载，防止遗漏数据');last=fingerprint;
  rows.push(...batch);
  if(response.count!=null?rows.length>=response.count:batch.length<500)return rows;
 }
 throw new Error('数据量过大，请缩小查询范围');
}
export function safeUrl(value:unknown){if(typeof value!=='string'||!value)return '';try{const u=new URL(value,location.origin);return ['http:','https:'].includes(u.protocol)?u.href:''}catch{return ''}}
