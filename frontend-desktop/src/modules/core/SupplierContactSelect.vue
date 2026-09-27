<script setup lang="ts">
import {computed} from 'vue'
import type {Row} from './model'
const props=defineProps<{record:Row;suppliers:Row[];disabled:boolean}>()
defineEmits<{select:[id:number|undefined]}>()
const contacts=computed(()=>props.suppliers.filter(s=>String(s.contact_person||'').trim()))
const selected=computed(()=>contacts.value.find(s=>s.id===props.record.supplier_id&&s.contact_person===props.record.supplier_contact_person)?.id)
</script>
<template>
  <el-select aria-label="供应商联系人" :model-value="selected" filterable clearable placeholder="输入联系人姓名查找并选择" :disabled="disabled" @update:model-value="$emit('select', $event || undefined)">
    <el-option v-for="s in contacts" :key="s.id" :value="s.id" :label="`${s.contact_person} · ${s.name}${s.phone ? ' · ' + s.phone : ''}`"/>
  </el-select>
</template>
