<script setup lang="ts">
import {computed} from 'vue'
import {useRoute,useRouter} from 'vue-router'

const route=useRoute()
const router=useRouter()
const title=computed(()=>route.path==='/forbidden'?'没有访问权限':route.path==='/unsupported'?'此菜单尚未匹配手机页面':'页面不存在')
const description=computed(()=>route.path==='/forbidden'?'当前账号没有此模块权限。':route.path==='/unsupported'?`「${String(route.query.menu||'未知菜单')}」暂时无法在手机端打开，请联系管理员核对菜单地址。`:'请从全部应用选择需要的页面。')
</script>

<template>
 <main class="page mobile-status-page">
  <van-empty :description="title"/>
  <p>{{description}}</p>
  <div class="actions"><van-button type="primary" @click="router.push('/apps')">查看全部应用</van-button><van-button plain @click="router.back()">返回上一页</van-button></div>
 </main>
</template>

<style scoped>
.mobile-status-page{padding-top:48px;text-align:center}.mobile-status-page p{color:#6e8279;line-height:1.7;overflow-wrap:anywhere}.mobile-status-page .actions{justify-content:center;margin-top:28px}
</style>
