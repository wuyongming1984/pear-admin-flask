import { reactive } from 'vue';
import { request } from './api';
import type { Kind,RecordData } from './model';
export const session=reactive({ready:false,expired:false,error:'',user:{} as RecordData,menus:[] as RecordData[],dicts:{} as Record<string,{label:string;value:string}[]>});
export const listState=reactive<Record<string,{search:string;status:string;page:number;rows:RecordData[];total:number;scroll:number}>>({});
export const revisions=reactive({project:0,order:0,pay:0});
export function invalidate(kind:Kind){revisions[kind]++; if(kind==='pay')revisions.order++;}
export function can(kind:Kind){let paths:string[]=[];function walk(nodes:RecordData[]){for(const n of nodes){if(n.href)paths.push(n.href);if(n.children)walk(n.children)}}walk(session.menus);return paths.some(p=>kind==='project'?p.includes('/project/'):kind==='order'?p.includes('order_base'):p.includes('pay_base'));}
export function label(dict:string|undefined,value:any){if(!value&&value!==0)return '未设置';return session.dicts[dict||'']?.find(x=>String(x.value)===String(value))?.label||String(value)}
export async function initialize(){
 const [profile,menus,dicts]=await Promise.all([request('/user/profile'),request('/menu'),request('/dictionary/options?codes=xmzt,xmgm,fkzt,clmc')]);
 session.user=profile.data; session.menus=menus as unknown as RecordData[];session.dicts=dicts.data; session.ready=true;session.error='';
}
export function clearSession(){localStorage.removeItem('access_token');localStorage.removeItem('refresh_token');session.ready=false;session.user={};session.menus=[];session.dicts={};for(const key of Object.keys(listState))delete listState[key]}
