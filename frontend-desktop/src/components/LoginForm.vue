<script setup lang="ts">
import {ref,watch} from 'vue'
import {View,Hide} from '@element-plus/icons-vue'
import {login} from '../session'

const props=defineProps<{fixedUser?:string;showcase?:boolean}>()
const emit=defineEmits<{
  success:[]
  mood:[value:'idle'|'username'|'password'|'revealed'|'error']
  motion:[value:{isTyping:boolean;passwordLength:number;showPassword:boolean}]
}>()
const username=ref(props.fixedUser||'')
const password=ref('')
const showPassword=ref(false)
const isTyping=ref(false)
const busy=ref(false)
const error=ref('')

watch([isTyping,password,showPassword],()=>{
  if(props.showcase)emit('motion',{isTyping:isTyping.value,passwordLength:password.value.length,showPassword:showPassword.value})
},{immediate:true})

function usernameFocus(){isTyping.value=true;emit('mood','username')}
function usernameBlur(){isTyping.value=false;emit('mood','idle')}

function togglePassword(){
  showPassword.value=!showPassword.value
  emit('mood',showPassword.value?'revealed':password.value?'password':'idle')
}
async function submit(){
  if(busy.value)return
  if(!username.value.trim()||!password.value){error.value='请输入账号和密码';emit('mood','error');return}
  busy.value=true
  error.value=''
  try{
    await login(username.value.trim(),password.value)
    password.value=''
    emit('success')
  }catch(e){
    error.value=(e as Error).message
    emit('mood','error')
  }finally{busy.value=false}
}
</script>

<template>
  <form v-if="showcase" class="showcase-form" @submit.prevent="submit">
    <p v-if="error" class="showcase-error" role="alert">{{error}}</p>
    <div class="showcase-field">
      <label for="showcase-username">账号</label>
      <input id="showcase-username" v-model="username" name="username" type="text" autocomplete="username" placeholder="请输入您的员工账号" :disabled="!!fixedUser||busy" required @focus="usernameFocus" @blur="usernameBlur" />
    </div>
    <div class="showcase-field">
      <label for="showcase-password">密码</label>
      <div class="showcase-password">
        <input id="showcase-password" v-model="password" name="password" :type="showPassword?'text':'password'" autocomplete="current-password" placeholder="请输入密码" :disabled="busy" required @focus="emit('mood',showPassword?'revealed':'password')" @blur="emit('mood','idle')" />
        <button type="button" class="showcase-visibility" :aria-label="showPassword?'隐藏密码':'显示密码'" :aria-pressed="showPassword" @click="togglePassword">
          <el-icon :size="18"><View v-if="!showPassword"/><Hide v-else/></el-icon>
        </button>
      </div>
    </div>
    <div class="showcase-help"><span>企业内部账号</span><a href="#/register">忘记密码？</a></div>
    <button class="showcase-submit" type="submit" :disabled="busy">{{busy?'正在登录…':'登 录'}}<span aria-hidden="true">→</span></button>
    <p class="showcase-register">还没有账号？ <a href="#/register">查看开通说明</a></p>
  </form>
  <form v-else class="login-form" @submit.prevent="submit">
    <el-alert v-if="error" :title="error" type="error" :closable="false"/>
    <label for="desktop-username">账号</label>
    <el-input id="desktop-username" v-model="username" :disabled="!!fixedUser" autocomplete="username" placeholder="请输入账号" size="large"/>
    <label for="desktop-password">密码</label>
    <el-input id="desktop-password" v-model="password" type="password" show-password autocomplete="current-password" placeholder="请输入密码" size="large"/>
    <el-button native-type="submit" type="primary" size="large" :loading="busy">登录工作台</el-button>
    <p class="muted">账号由管理员统一开通；如无法登录，请联系管理员。 <a href="#/register">账号开通说明</a></p>
  </form>
</template>
