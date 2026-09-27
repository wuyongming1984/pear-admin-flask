<script setup lang="ts">
import {computed} from 'vue'
import type {Row} from './model'
import {contactName, contactNames} from './orderContacts'
const props=defineProps<{record:Row;suppliers:Row[];disabled:boolean}>()
defineEmits<{select:[name:string|undefined]}>()
const contacts=computed(()=>contactNames(props.suppliers))
const selected=computed(()=>contactName(props.record.supplier_contact_person) || undefined)
</script>
<template>
  <el-select aria-label="供应商联系人" :model-value="selected" filterable clearable placeholder="输入联系人姓名查找并选择" :disabled="disabled" @update:model-value="$emit('select', $event || undefined)">
    <el-option v-for="name in contacts" :key="name" :value="name" :label="name"/>
  </el-select>
</template>
