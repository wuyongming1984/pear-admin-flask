<script setup lang="ts">
import PageHeader from "../../components/PageHeader.vue";
import {ref,onMounted,computed} from 'vue'
import {ElMessage,ElMessageBox} from '../../feedback'
import {useSystemDraft} from './useSystemDraft'
import {request} from '../../api'
import {backupPayload,type Row} from './helpers'
const form=ref<Row>({mail_server:'',mail_port:'465',mail_user:'',mail_pass:'',mail_receiver:'',enable_auto_backup:false,backup_time:'01:00'}),hadPassword=ref(false),busy=ref(false),loading=ref(true),ready=ref(false),log=ref('')
const baseline=ref('')
const dirty=computed(()=>ready.value&&JSON.stringify(form.value)!==baseline.value)
const {allowDiscard}=useSystemDraft(dirty,busy,()=>{if(baseline.value)form.value=JSON.parse(baseline.value)})
async function reload(){if(await allowDiscard())await load()}
const fail=(e:unknown)=>ElMessage.error(e instanceof Error?e.message:String(e))
async function load(){loading.value=true;try{const res=await request<Row>('/system/config/backup');form.value=res.data;hadPassword.value=Boolean(form.value.mail_pass);form.value.mail_pass='';baseline.value=JSON.stringify(form.value);ready.value=true}catch(e){fail(e)}finally{loading.value=false}}
async function save(){if(busy.value||!ready.value)return;if(!form.value.mail_server||!form.value.mail_receiver||!Number.isInteger(Number(form.value.mail_port))||Number(form.value.mail_port)<1||Number(form.value.mail_port)>65535||!/^([01]\d|2[0-3]):[0-5]\d$/.test(form.value.backup_time))return ElMessage.warning('请检查服务器、收件邮箱、端口及备份时间');busy.value=true;try{await request('/system/config/backup',{method:'POST',body:JSON.stringify(backupPayload(form.value,hadPassword.value))});ElMessage.success('配置已保存');await load()}catch(e){fail(e)}finally{busy.value=false}}
async function test(){if(busy.value)return;try{await ElMessageBox.confirm('将使用已保存的配置立即执行数据库备份并发送邮件，是否继续？','执行备份',{type:'warning',confirmButtonText:'执行备份'});busy.value=true;const res=await request('/system/backup/test',{method:'POST'});log.value=res.msg||'备份成功';ElMessage.success('备份完成')}catch(e){if(e!=='cancel'&&e!=='close'){log.value=e instanceof Error?e.message:String(e);fail(e)}}finally{busy.value=false}}
onMounted(load)
</script>
<template><section class="page"><PageHeader title="数据备份" description="配置数据库备份邮件和每日自动备份时间。"/><div class="panel" v-loading="loading" style="max-width:850px"><m-form label-width="120px" :disabled="!ready||busy"><m-form-item label="邮件服务器" required><m-input v-model="form.mail_server" placeholder="smtp.example.com"/></m-form-item><m-form-item label="端口" required><m-input v-model="form.mail_port"/></m-form-item><m-form-item label="发送账号"><m-input v-model="form.mail_user"/></m-form-item><m-form-item label="邮箱授权码"><m-input v-model="form.mail_pass" type="password" show-password autocomplete="new-password" :placeholder="hadPassword?'已设置，留空保留原授权码':'请输入邮箱授权码'"/></m-form-item><m-form-item label="收件邮箱" required><m-input v-model="form.mail_receiver"/></m-form-item><m-form-item label="自动备份"><m-switch v-model="form.enable_auto_backup"/></m-form-item><m-form-item label="每日备份时间"><m-time-picker v-model="form.backup_time" format="HH:mm" value-format="HH:mm" :clearable="false"/></m-form-item></m-form><div class="actions"><m-button type="primary" :loading="busy" :disabled="!ready" @click="save">保存配置</m-button><m-button :disabled="busy||!ready" @click="test">立即备份并发送</m-button><m-button :disabled="busy" @click="reload">重新加载</m-button></div><pre v-if="log" style="white-space:pre-wrap">{{log}}</pre></div></section></template>
