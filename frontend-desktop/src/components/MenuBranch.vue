<script setup lang="ts">
import type{MenuItem}from '../navigation';import{Folder,Document}from '@element-plus/icons-vue';defineProps<{items:MenuItem[];resolve:(item:MenuItem)=>string}>();
</script>
<template><template v-for="item in items" :key="item.id"><el-sub-menu v-if="item.children?.length" :index="'group-'+item.id"><template #title><el-icon aria-hidden="true"><Folder/></el-icon><span>{{item.title}}</span></template><MenuBranch :items="item.children" :resolve="resolve"/></el-sub-menu><el-menu-item v-else :index="resolve(item)"><el-icon aria-hidden="true"><Document/></el-icon><template #title><span>{{item.title}}</span></template></el-menu-item></template></template>
