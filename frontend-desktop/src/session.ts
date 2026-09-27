import {reactive} from 'vue'
import {request,bindAccessToken,boundAccessToken} from './api'
import {flattenMenus,normalizePath,type MenuItem} from './navigation'
export const session=reactive({authenticated:!!localStorage.getItem('access_token'),expired:false,menus:[] as MenuItem[],loaded:false,error:'',userName:'',userId:null as number|string|null,identityChanged:false,viewVersion:0})
const menuPaths=(menus:MenuItem[])=>new Set(flattenMenus(menus).filter(x=>x.href).map(x=>normalizePath(x.href!)))
export function invalidateIdentity(){
 if(session.identityChanged)return
 bindAccessToken(null)
 session.identityChanged=true;session.authenticated=false;session.loaded=false;session.expired=false;session.menus=[];session.userId=null;session.userName='';session.error='登录账号已改变，请重新登录。旧页面已关闭以保护数据。';session.viewVersion++
}
export async function loadSession(){
 const [response,profile]=await Promise.all([request<MenuItem[]>('/menu'),request<{id:number|string;username:string}>('/user/profile')])
 if(!profile.data?.username||profile.data.id==null)throw Error('无法确认当前登录账号')
 if(session.userId!==null&&String(session.userId)!==String(profile.data.id)){invalidateIdentity();throw Error('登录账号已改变，请重新登录')}
 const menus=Array.isArray(response)?response:response.data||[]
 const nextPaths=menuPaths(menus)
 const revoked=session.loaded&&[...menuPaths(session.menus)].some(path=>!nextPaths.has(path))
 session.menus=menus;session.userId=profile.data.id;session.userName=profile.data.username;session.loaded=true;session.error=''
 localStorage.setItem('sf-desktop-username',profile.data.username)
 if(revoked)session.viewVersion++
}
export async function login(username:string,password:string){
 const response=await request('/login',{method:'POST',body:JSON.stringify({username,password})})
 if(!response.access_token)throw Error('登录响应缺少凭证')
 localStorage.setItem('access_token',response.access_token);bindAccessToken(response.access_token)
 await loadSession();session.authenticated=true;session.identityChanged=false;session.expired=false
}
export function logout(){localStorage.removeItem('access_token');localStorage.removeItem('sf-desktop-username');bindAccessToken(null);session.authenticated=false;session.loaded=false;session.menus=[];session.expired=false;session.userName='';session.userId=null;session.identityChanged=false;session.viewVersion++}
window.addEventListener('sf-auth-expired',()=>{if(!session.identityChanged)session.expired=true})
window.addEventListener('sf-identity-changed',invalidateIdentity)
window.addEventListener('storage',event=>{if((event.key==='access_token'||event.key===null)&&localStorage.getItem('access_token')!==boundAccessToken())invalidateIdentity()})
