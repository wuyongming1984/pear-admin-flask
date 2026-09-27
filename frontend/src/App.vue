<script setup lang="ts">
import { computed,onMounted,onUnmounted,ref,watch } from 'vue';import {useRoute} from 'vue-router';
import {request,bindAccessToken} from './api';import {allowedMenu} from './business/navigation';import {session,initialize,can} from './store';
const loadError=ref(false);const reloadPage=()=>location.reload();const pageFailed=()=>loadError.value=true;
const route=useRoute();const login=ref(false);const username=ref('');const password=ref('');const pending=ref(false);const error=ref('');const boot=ref(true);
const active=computed(()=>{const section=route.path.split('/')[1];return ({'':'home',projects:'project',orders:'order',payments:'pay',invoices:'invoice',me:'me',profile:'me'} as Record<string,string>)[section]||''});
const tabs=[{key:'home',path:'/',name:'首页',icon:'wap-home-o'},{key:'project',path:'/project',name:'项目',icon:'apps-o'},{key:'order',path:'/order',name:'订单',icon:'orders-o'},{key:'pay',path:'/pay',name:'付款',icon:'balance-list-o'},{key:'invoice',path:'/invoices',name:'发票',icon:'description'},{key:'me',path:'/me',name:'我的',icon:'user-o'}];
const visibleTabs=computed(()=>tabs.filter(t=>t.key==='invoice'?allowedMenu('/view/material/invoice',session.menus as any):!['project','order','pay'].includes(t.key)||can(t.key as any)));
function expired(){session.expired=true;login.value=true;error.value='登录已过期，当前页面内容已保留';username.value=session.user.username||'';}
async function start(){if(route.meta.public){boot.value=false;login.value=false;return}boot.value=true;error.value='';try{if(localStorage.getItem('access_token'))await initialize();else login.value=true}catch(e){if(!login.value)error.value=(e as Error).message}finally{boot.value=false}}
async function submit(){if(pending.value)return;pending.value=true;error.value='';try{
 if(session.expired && session.user.username && username.value!==session.user.username)throw new Error('请使用原账号重新登录，避免将当前表单提交到其他账号');
 const r=await request('/login',{method:'POST',body:JSON.stringify({username:username.value,password:password.value})});localStorage.setItem('access_token',r.data?.access_token||(r as any).access_token);localStorage.setItem('refresh_token',r.data?.refresh_token||(r as any).refresh_token);
 bindAccessToken(localStorage.getItem('access_token'));await initialize();password.value='';login.value=false;session.expired=false;
}catch(e){error.value=(e as Error).message}finally{pending.value=false}}
watch(()=>route.meta.public,(v)=>{if(v)login.value=false;else if(!session.ready)void start()});
onMounted(()=>{window.addEventListener('sf-page-load-failed',pageFailed);window.addEventListener('sf-auth-expired',expired);start()});onUnmounted(()=>{window.removeEventListener('sf-auth-expired',expired);window.removeEventListener('sf-page-load-failed',pageFailed)});
</script>
<template>
 <div class="app-shell"><div v-if="loadError" class="m-alert error" role="alert">页面资源加载失败，请刷新后重试。<van-button size="small" @click="reloadPage">重新加载</van-button></div>
  <router-view v-if="route.meta.public"/><van-empty v-else-if="session.ready&&!allowedMenu(route.meta.menuPath as string,session.menus as any)" description="当前账号没有此模块权限"/><router-view v-else-if="session.ready" v-slot="{Component}"><keep-alive :include="['BusinessList','CorePage','Material','Nursery','Records','Dictionary','Backup']"><component :is="Component" :key="route.path"/></keep-alive></router-view>
  <main v-else class="boot"><van-loading v-if="boot" vertical color="#087f78">正在连接工作台</van-loading><template v-else-if="!login"><van-empty :description="error||'暂时无法加载'"/><van-button type="primary" @click="start">重新连接</van-button></template></main>
  <van-tabbar v-if="session.ready&&!route.meta.public" :model-value="active" route safe-area-inset-bottom fixed placeholder class="bottom-nav">
   <van-tabbar-item v-for="t in visibleTabs" :key="t.key" :name="t.key" :to="t.path" :icon="t.icon">{{t.name}}</van-tabbar-item>
  </van-tabbar>
  <van-popup v-model:show="login" :close-on-click-overlay="false" position="bottom" :style="{height:'100%'}" :z-index="3000">
   <div class="login-page"><div class="brand-mark">SF<span>WORKSPACE</span></div><div class="login-intro"><span class="eyebrow">随时连接 · 高效协作</span><h1>{{session.expired?'欢迎回来':'把工作，带在身边。'}}</h1><p>项目、订单与付款<br>一个清晰的移动工作台。</p></div>
    <van-form @submit="submit"><van-cell-group inset><van-field v-model="username" label="账号" name="username" placeholder="请输入账号" autocomplete="username" :readonly="session.expired && !!session.user.username" :rules="[{required:true,message:'请填写账号'}]"/><van-field v-model="password" type="password" label="密码" name="password" placeholder="请输入密码" autocomplete="current-password" :rules="[{required:true,message:'请填写密码'}]"/></van-cell-group><p v-if="error" class="form-error" role="alert">{{error}}</p><div class="form-actions"><van-button block round type="primary" native-type="submit" :loading="pending">{{session.expired?'重新登录，继续操作':'登录工作台'}}</van-button></div></van-form>
    <router-link class="desktop-link" to="/register" @click="login=false">账号开通说明</router-link><a class="desktop-link" href="/">使用电脑版 →</a><small class="login-footer">SF 管理系统 · 移动工作台</small>
   </div>
  </van-popup>
 </div>
</template>
