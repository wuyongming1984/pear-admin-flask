<script setup lang="ts">
import {ref,watch} from 'vue'
import {View,Hide} from '@element-plus/icons-vue'
import {login} from '../session'

const props=defineProps<{fixedUser?:string;showcase?:boolean}>()
const emit=defineEmits<{
  success:[]
  mood:[value:'idle'|'username'|'password'|'revealed'|'error']
  motion:[value:{isTyping:boolean;isPasswordFocused:boolean;passwordLength:number;showPassword:boolean}]
}>()
const username=ref(props.fixedUser||'')
const password=ref('')
const showPassword=ref(false)
const isTyping=ref(false)
const isPasswordFocused=ref(false)
const busy=ref(false)
const error=ref('')
const invalidField=ref<'username'|'password'|null>(null)

watch([username,isTyping,isPasswordFocused,password,showPassword],()=>{
  if(props.showcase)emit('motion',{isTyping:isTyping.value,isPasswordFocused:isPasswordFocused.value,passwordLength:password.value.length,showPassword:showPassword.value})
},{immediate:true})

function usernameFocus(){isTyping.value=true;emit('mood','username')}
function usernameBlur(){isTyping.value=false;emit('mood','idle')}

function togglePassword(){
  showPassword.value=!showPassword.value
  emit('mood',showPassword.value?'revealed':password.value?'password':'idle')
}
function reportError(message:string,field:'username'|'password'){
  error.value=message
  invalidField.value=field
  // The reference releases the look-away pose even when Enter submits the focused input.
  isPasswordFocused.value=false
  emit('mood','error')
}
async function submit(){
  if(busy.value)return
  error.value=''
  invalidField.value=null
  if(!username.value.trim()){reportError('请输入员工账号','username');return}
  if(!password.value){reportError('请输入密码','password');return}
  busy.value=true
  error.value=''
  try{
    await login(username.value.trim(),password.value)
    password.value=''
    emit('success')
  }catch(e){
    reportError((e as Error).message,'password')
  }finally{busy.value=false}
}
</script>

<template>
  <form v-if="showcase" class="showcase-form" novalidate @submit.prevent="submit">
    <div class="showcase-field" :class="{'is-invalid':invalidField==='username'}">
      <label for="showcase-username">账号</label>
      <input id="showcase-username" v-model="username" name="username" type="text" autocomplete="username" placeholder="请输入您的员工账号" :aria-invalid="invalidField==='username'" :aria-describedby="invalidField==='username'?'showcase-error':undefined" :disabled="!!fixedUser||busy" required @focus="usernameFocus" @blur="usernameBlur" />
    </div>
    <div class="showcase-field" :class="{'is-invalid':invalidField==='password'}">
      <label for="showcase-password">密码</label>
      <div class="showcase-password">
        <input id="showcase-password" v-model="password" name="password" :type="showPassword?'text':'password'" autocomplete="current-password" placeholder="请输入密码" :aria-invalid="invalidField==='password'" :aria-describedby="invalidField==='password'?'showcase-error':undefined" :disabled="busy" required @focus="isPasswordFocused=true;emit('mood',showPassword?'revealed':'password')" @blur="isPasswordFocused=false;emit('mood','idle')" />
        <button type="button" class="showcase-visibility" :aria-label="showPassword?'隐藏密码':'显示密码'" :aria-pressed="showPassword" @click="togglePassword">
          <el-icon :size="18"><View v-if="!showPassword"/><Hide v-else/></el-icon>
        </button>
      </div>
    </div>
    <div class="showcase-help"><span>企业内部账号</span><a href="#/register">忘记密码？</a></div>
    <p v-if="error" id="showcase-error" class="showcase-error" role="alert">{{error}}</p>
    <button class="showcase-submit" type="submit" :disabled="busy"><span class="showcase-submit-text">{{busy?'正在登录…':'登 录'}}</span><span class="showcase-submit-hover" aria-hidden="true">登 录 <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-7-7 7 7-7 7"/></svg></span></button>
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
