<script setup lang="ts">
import {labels, type Row} from './domain'
defineProps<{model:Row,fields:string[],options?:Record<string,Row[]>}>()
</script>
<template><el-form label-position="top" class="form-grid"><el-form-item v-for="field in fields" :key="field" :label="labels[field]||field"><el-select v-if="options?.[field]" v-model="model[field]" clearable filterable :allow-create="!field.endsWith('_id')"><el-option v-for="item in options[field]" :key="item.id??item.name" :label="item.name" :value="item.id??item.name"/></el-select><el-date-picker v-else-if="field==='date'" v-model="model[field]" type="date" value-format="YYYY-MM-DD"/><el-input v-else v-model="model[field]" :type="field==='remark'?'textarea':'text'" :aria-label="labels[field]||field"/></el-form-item></el-form></template>
