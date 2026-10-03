<script setup lang="ts">
import type{MenuItem}from '../navigation';import{mobileWorkbenchHref}from '../../../frontend-shared/business/navigation';import{Folder,Document}from '@element-plus/icons-vue';defineProps<{items:MenuItem[];resolve:(item:MenuItem)=>string}>();
</script>
<template><template v-for="item in items" :key="item.id"><el-sub-menu v-if="item.children?.length" :index="'group-'+item.id"><template #title><el-icon aria-hidden="true"><Folder/></el-icon><span>{{item.title}}</span></template><MenuBranch :items="item.children" :resolve="resolve"/></el-sub-menu><li v-else-if="mobileWorkbenchHref(item)" class="el-menu-item menu-app-item" role="none"><a class="menu-app-link" :href="mobileWorkbenchHref(item)" target="_blank" rel="noopener" role="menuitem" :aria-label="item.title" :title="item.title"><el-icon aria-hidden="true"><Document/></el-icon><span>{{item.title}}</span></a></li><el-menu-item v-else :index="resolve(item)"><el-icon aria-hidden="true"><Document/></el-icon><template #title><span>{{item.title}}</span></template></el-menu-item></template></template>
<style scoped>
.menu-app-item{position:relative}.menu-app-link{position:absolute;inset:0;display:flex;align-items:center;padding:inherit;color:inherit;text-decoration:none}
</style>
