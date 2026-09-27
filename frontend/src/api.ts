export interface Envelope<T=any>{code:number;data:T;count?:number;msg?:string;message?:string}
export class ApiError extends Error { constructor(message:string,public status=0,public uncertain=false,public response:any=null){super(message)} }
let boundToken=localStorage.getItem('access_token');
export function bindAccessToken(token:string|null){boundToken=token}
function checkIdentity(writing=false){if(localStorage.getItem('access_token')!==boundToken){window.dispatchEvent(new Event('sf-auth-expired'));throw new ApiError('账号已在其他页面改变，请使用原账号重新登录后再操作',0,writing)}}
export async function request<T=any>(path:string,options:RequestInit={}):Promise<Envelope<T>>{
 const publicRequest=path==='/login'||path.startsWith('/portal/');
 if(!publicRequest)checkIdentity();
 const headers=new Headers(options.headers); const token=localStorage.getItem('access_token');
 if(token&&!publicRequest) headers.set('Authorization',`Bearer ${token}`);
 if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
 const abort=new AbortController();const timer=setTimeout(()=>abort.abort(),options.body instanceof FormData?60000:30000);
 const writing=!!options.method && options.method!=='GET';
 let response:Response;
 try{response=await fetch(path.startsWith('/portal/')?path:`/api/v1${path}`,{...options,headers,signal:abort.signal})}
 catch {throw new ApiError(writing?'连接中断，提交结果未确认。请先查看列表核对，勿重复提交。':'连接失败，请检查网络后重试',0,writing)}
 finally{clearTimeout(timer)}
 if(!publicRequest)checkIdentity(writing);
 let data:any;
 try{data=await response.json()}catch{throw new ApiError('服务器返回异常，请稍后重试',response.status,writing)}
 const message=data.msg||data.message||`请求失败（${response.status}）`;
 if(!publicRequest && (response.status===401 || (response.status===422 && /token|signature|subject/i.test(message)) || (response.status===403 && /token|登录|授权/i.test(message)))){
  window.dispatchEvent(new Event('sf-auth-expired'));
  throw new ApiError('登录已过期，请重新登录。当前表单已保留。',response.status);
 }
 if(!response.ok || data.success===false || (data.code!==undefined && data.code!==0))throw new ApiError(message,response.status,writing&&response.status>=500,data);
 return data;
}
export function query(params:Record<string,any>){const q=new URLSearchParams();for(const [k,v] of Object.entries(params))if(v!==''&&v!=null)q.set(k,String(v));return q.toString()}
