<script setup lang="ts">
defineProps<{title:string;description?:string}>();
</script>
<template><header class="page-heading"><div><div class="eyebrow">SF / BUSINESS WORKSPACE</div><h1>{{title}}</h1><p v-if="description">{{description}}</p></div><div class="actions"><slot/></div></header></template>
