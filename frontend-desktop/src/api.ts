export interface Envelope<T=any>{code:number;data:T;count?:number;msg?:string;message?:string;[key:string]:any}
export class ApiError extends Error{constructor(message:string,public status=0,public uncertain=false,public response:any=null){super(message)}get data(){return this.response?.data}get code(){return this.response?.code}}
let boundToken=localStorage.getItem('access_token')
let tokenGeneration=0
export function bindAccessToken(token:string|null){boundToken=token;tokenGeneration++}
export function boundAccessToken(){return boundToken}
export function assertBoundSession(writeStarted=false){
 if(localStorage.getItem('access_token')!==boundToken){window.dispatchEvent(new Event('sf-identity-changed'));throw new ApiError(writeStarted?'登录账号已在其他页面改变，原账号提交结果尚未确认，请核对后再操作':'登录账号已在其他页面改变，请重新登录；旧页面请求已阻止',0,writeStarted)}
}
export function query(params:Record<string,any>={}){const q=new URLSearchParams();for(const [k,v]of Object.entries(params))if(v!==''&&v!=null)q.set(k,String(v));return q.toString()}
export async function request<T=any>(path:string,options:RequestInit={}):Promise<Envelope<T>>{
 const publicRequest=path==='/login'||path.startsWith('/portal/');
 if(!publicRequest)assertBoundSession();
 const generation=tokenGeneration;
 const headers=new Headers(options.headers);if(!publicRequest&&boundToken)headers.set('Authorization',`Bearer ${boundToken}`);else headers.delete('Authorization');
 if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json');
 const writing=!!options.method&&!['GET','HEAD'].includes(options.method.toUpperCase());
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),options.body instanceof FormData?120000:30000);
 let response:Response;
 try{response=await fetch(path.startsWith('/api/')||path.startsWith('/portal/')?path:`/api/v1${path}`,{...options,headers,signal:options.signal||controller.signal})}
 catch{throw new ApiError(writing?'连接中断，提交结果尚未确认。请先核对列表，勿重复提交。':'网络连接失败，请重试',0,writing)}finally{clearTimeout(timer)}
 if(!publicRequest){assertBoundSession(writing);if(generation!==tokenGeneration)throw new ApiError('会话已更新，旧请求结果已丢弃',response.status,writing)}
 let data:any;try{data=await response.json()}catch{throw new ApiError('服务器返回异常',response.status,writing)}
 if(!publicRequest){assertBoundSession(writing);if(generation!==tokenGeneration)throw new ApiError('会话已更新，旧请求结果已丢弃',response.status,writing)}
 const message=data.msg||data.message||`请求失败（${response.status}）`;
 if(!publicRequest&&(response.status===401||(response.status===403&&/token|登录|授权/i.test(message))||(response.status===422&&/token|signature|subject/i.test(message))))window.dispatchEvent(new Event('sf-auth-expired'));
 if(!response.ok||data.success===false||(data.code!==undefined&&data.code!==0))throw new ApiError(message,response.status,writing&&response.status>=500,data);
 return data;
}
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
