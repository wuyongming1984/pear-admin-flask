<script setup lang="ts">defineProps<{title:string;description?:string}>();
</script>
<template><header class="page-header"><div><router-link to="/apps">‹ 全部应用</router-link><h1>{{title}}</h1><p>{{description}}</p></div><div class="actions"><slot/></div></header></template>
