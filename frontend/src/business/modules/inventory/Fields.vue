<script setup lang="ts">
import {labels, type Row} from './domain'
defineProps<{model:Row,fields:string[],options?:Record<string,Row[]>}>()
</script>
<template><m-form label-position="top" class="form-grid"><m-form-item v-for="field in fields" :key="field" :label="labels[field]||field"><m-select v-if="options?.[field]" v-model="model[field]" clearable filterable :allow-create="!field.endsWith('_id')"><m-option v-for="item in options[field]" :key="item.id??item.name" :label="item.name" :value="item.id??item.name"/></m-select><m-date-picker v-else-if="field==='date'" v-model="model[field]" type="date" value-format="YYYY-MM-DD"/><m-input v-else v-model="model[field]" :type="field==='remark'?'textarea':'text'" :inputmode="/quantity|price|stock|ratio|rate|amount/.test(field)?'decimal':undefined" :aria-label="labels[field]||field"/></m-form-item></m-form></template>
