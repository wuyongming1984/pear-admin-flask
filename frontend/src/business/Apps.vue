<script setup lang="ts">
import {computed,ref} from 'vue';import {session} from '../store';import routes from './routes';import {applicationGroups} from './navigation';
const search=ref('');const groups=computed(()=>applicationGroups(session.menus as any,routes,search.value));
</script>
<template><main class="page"><header class="page-header"><h1>全部应用</h1><router-link to="/">返回首页</router-link></header><van-search v-model="search" placeholder="搜索业务模块"/><section v-for="group in groups" :key="group.title" :aria-label="group.title"><h2 class="section-title">{{group.title}}</h2><van-cell-group inset><van-cell v-for="entry in group.entries" :key="entry.id" :title="entry.title" :label="entry.path.startsWith('/unsupported')?'此菜单尚未匹配手机页面':''" :to="entry.path" is-link/></van-cell-group></section><van-empty v-if="!groups.length" description="没有匹配的已授权模块"/></main></template>
