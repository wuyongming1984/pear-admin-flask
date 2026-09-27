<script setup lang="ts">
import PageHeader from "../../components/PageHeader.vue";
import {ref,onMounted,computed} from 'vue'
import {ElMessage} from '../../feedback'
import {useSystemDraft} from './useSystemDraft'
import {request} from '../../api'
import {passwordError,type Row} from './helpers'
const profile=ref<Row>({}),loading=ref(true),busy=ref(false),oldPassword=ref(''),newPassword=ref(''),confirmation=ref('')
const dirty=computed(()=>Boolean(oldPassword.value||newPassword.value||confirmation.value))
useSystemDraft(dirty,busy,()=>{oldPassword.value='';newPassword.value='';confirmation.value=''})
const fail=(e:unknown)=>ElMessage.error(e instanceof Error?e.message:String(e))
onMounted(async()=>{try{profile.value=(await request<Row>('/user/profile')).data}catch(e){fail(e)}finally{loading.value=false}})
async function save(){if(busy.value)return;const error=passwordError(oldPassword.value,newPassword.value,confirmation.value);if(error)return ElMessage.warning(error);busy.value=true;try{await request('/user/change-password',{method:'POST',body:JSON.stringify({old_password:oldPassword.value,new_password:newPassword.value})});oldPassword.value='';newPassword.value='';confirmation.value='';ElMessage.success('密码修改成功')}catch(e){fail(e)}finally{busy.value=false}}
</script>
<template><section class="page"><PageHeader title="个人资料" description="查看账号信息，管理登录密码。"/><div class="panel" style="max-width:750px" v-loading="loading"><m-descriptions :column="2" border><m-descriptions-item label="用户名">{{profile.username}}</m-descriptions-item><m-descriptions-item label="昵称">{{profile.nickname}}</m-descriptions-item><m-descriptions-item label="邮箱">{{profile.email||'—'}}</m-descriptions-item><m-descriptions-item label="手机">{{profile.mobile||'—'}}</m-descriptions-item></m-descriptions><h2>修改密码</h2><m-form label-width="100px" @submit.prevent="save"><m-form-item label="原密码" required><m-input v-model="oldPassword" type="password" show-password autocomplete="current-password"/></m-form-item><m-form-item label="新密码" required><m-input v-model="newPassword" type="password" show-password autocomplete="new-password" placeholder="至少6位"/></m-form-item><m-form-item label="确认新密码" required><m-input v-model="confirmation" type="password" show-password autocomplete="new-password"/></m-form-item><m-button type="primary" :loading="busy" @click="save">保存密码</m-button></m-form></div></section></template>
