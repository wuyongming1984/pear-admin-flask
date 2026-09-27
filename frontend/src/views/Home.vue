<script setup lang="ts">
import {computed,ref,onMounted} from 'vue'
import {request} from '../api'
import {session,can} from '../store'
import {config,type Kind,type RecordData} from '../model'
import routes from '../business/routes'
import {applicationGroups} from '../business/navigation'
import RecordCard from '../components/RecordCard.vue'

const kinds:Kind[]=['project','order','pay']
const availableKinds=computed(()=>kinds.filter(can))
const groups=computed(()=>applicationGroups(session.menus as any,routes))
const counts=ref<Record<string,number>>({})
const recent=ref<RecordData[]>([])
const error=ref('')
const loading=ref(false)

async function load(){
 loading.value=true;error.value=''
 try{
  await Promise.all(availableKinds.value.map(async kind=>{
   const result=await request(`/${kind}/?limit=3&page=1`)
   counts.value[kind]=result.count||0
   if(kind==='order')recent.value=result.data
  }))
 }catch(e){error.value=(e as Error).message}
 finally{loading.value=false}
}
const date=new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'long'}).format(new Date())
onMounted(load)
</script>

<template>
 <main class="page home-page">
  <header class="home-header"><div class="brand-inline">SF<span>移动工作台</span></div><router-link to="/me" class="avatar" aria-label="我的账户">{{(session.user.nickname||session.user.username||'我').slice(0,1)}}</router-link></header>
  <section class="welcome"><p class="eyebrow">{{date}}</p><h1>你好，{{session.user.nickname||session.user.username}}<span class="greeting-dot">。</span></h1><p>让每一笔业务，清晰有序。</p></section>
  <section class="overview"><div class="overview-label"><span>业务概览</span><van-icon name="chart-trending-o" size="22"/></div><div class="stat-row"><router-link v-for="kind in availableKinds" :key="kind" :to="`/${kind}`"><strong>{{counts[kind]??'—'}}</strong><span>{{config[kind].title}}{{kind==='project'?'总数':'单据'}} <van-icon name="arrow" size="11"/></span></router-link></div><div class="overview-foot"><span class="live-dot"></span>与电脑后台共享业务数据</div></section>

  <template v-if="availableKinds.length"><div class="section-heading"><h2>快捷录入</h2><span>少一步切换，多一分效率</span></div><div class="quick-grid"><router-link v-for="kind in availableKinds" :key="kind" :to="`/${kind}/new`"><span class="quick-icon"><van-icon :name="config[kind].icon" size="25"/></span><b>新增{{config[kind].title}}</b><small>快速填写 <van-icon name="plus"/></small></router-link></div></template>

  <section class="home-applications" aria-labelledby="home-apps-title">
   <div class="section-heading"><h2 id="home-apps-title">全部应用</h2><router-link to="/apps">搜索应用 <van-icon name="arrow"/></router-link></div>
   <p v-if="!groups.length" class="empty-hint">当前账号暂无已授权应用，请联系管理员。</p>
   <section v-for="group in groups" :key="group.key" class="home-app-group" :aria-label="group.title">
    <header class="home-app-group-header"><div><van-icon :name="group.icon"/><h3>{{group.title}}</h3></div><span>{{group.entries.length}} 项</span></header>
    <div class="home-app-grid"><router-link v-for="entry in group.entries" :key="entry.id" class="home-app-link" :to="entry.path"><span>{{entry.title}}</span><van-icon name="arrow"/><small v-if="entry.path.startsWith('/unsupported')">菜单地址待核对</small></router-link></div>
   </section>
  </section>

  <div v-if="can('order')" class="section-heading"><h2>最近订单</h2><router-link to="/order">查看全部 <van-icon name="arrow"/></router-link></div>
  <van-loading v-if="loading" class="center-loading"/><div v-if="error" class="error-panel" role="alert">{{error}}<van-button size="small" plain @click="load">重试</van-button></div>
  <RecordCard v-for="row in recent" :key="row.id" kind="order" :row="row"/><van-empty v-if="!loading&&!error&&can('order')&&!recent.length" description="还没有订单，从第一笔录入开始"/>
 </main>
</template>

<style scoped>
.home-applications{margin-top:28px}.home-applications>.section-heading{margin-bottom:14px}.home-app-group{margin:0 0 16px;padding:15px;background:#fff;border:1px solid #dfe9e3;border-radius:16px;box-shadow:0 6px 24px #173c3708}
.home-app-group-header,.home-app-group-header>div{display:flex;align-items:center;gap:9px}.home-app-group-header{justify-content:space-between;margin-bottom:13px}.home-app-group-header .van-icon{color:#087f78;font-size:18px}.home-app-group-header h3{font-size:15px;color:#203635}.home-app-group-header>span{font-size:11px;color:#849991}
.home-app-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.home-app-link{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:4px;min-height:56px;padding:11px 10px;background:#f5f9f7;border:1px solid #e5eee9;border-radius:11px;color:#2b554a;font-size:13px;font-weight:600;line-height:1.4}.home-app-link span{min-width:0;overflow-wrap:anywhere}.home-app-link .van-icon{color:#7ca89b}.home-app-link small{grid-column:1/-1;font-size:10px;font-weight:400;color:#9b6d42}
@media(max-width:374px){.home-app-group{padding:12px}.home-app-grid{gap:7px}.home-app-link{padding:9px 8px;font-size:12px}}
</style>
