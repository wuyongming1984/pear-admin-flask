<script setup lang="ts">
import {computed,onBeforeUnmount,onMounted,reactive,ref,watch} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {Star} from '@element-plus/icons-vue'
import LoginForm from '../components/LoginForm.vue'
import './login.css'

type Character='purple'|'black'|'orange'|'yellow'
type Position={faceX:number;faceY:number;bodySkew:number}
type FormMotion={isTyping:boolean;passwordLength:number;showPassword:boolean}
type Mood='idle'|'username'|'password'|'revealed'|'error'

const router=useRouter()
const route=useRoute()
const scene=ref<HTMLElement|null>(null)
const mood=ref<Mood>('idle')
const formMotion=reactive<FormMotion>({isTyping:false,passwordLength:0,showPassword:false})
const positions=reactive<Record<Character,Position>>({
  purple:{faceX:0,faceY:0,bodySkew:0},
  black:{faceX:0,faceY:0,bodySkew:0},
  orange:{faceX:0,faceY:0,bodySkew:0},
  yellow:{faceX:0,faceY:0,bodySkew:0}
})
const pupils=reactive(Array.from({length:8},()=>({x:0,y:0})))
const purpleBlink=ref(false)
const blackBlink=ref(false)
const lookingAtEachOther=ref(false)
const purplePeeking=ref(false)
const hidingPassword=computed(()=>formMotion.passwordLength>0&&!formMotion.showPassword)
const revealedPassword=computed(()=>formMotion.passwordLength>0&&formMotion.showPassword)
const characters:Character[]=['purple','black','orange','yellow']
const timers=new Set<ReturnType<typeof setTimeout>>()
let lookingTimer:ReturnType<typeof setTimeout>|undefined
let peekTimer:ReturnType<typeof setTimeout>|undefined
let peekEndTimer:ReturnType<typeof setTimeout>|undefined

function later(callback:()=>void,delay:number){
  const timer=setTimeout(()=>{timers.delete(timer);callback()},delay)
  timers.add(timer)
  return timer
}
function cancel(timer:ReturnType<typeof setTimeout>|undefined){
  if(timer!==undefined){clearTimeout(timer);timers.delete(timer)}
}
const clamp=(value:number,min:number,max:number)=>Math.max(min,Math.min(max,value))
const round=(value:number)=>Math.round(value*100)/100

function updateMouse(event:MouseEvent){
  if(!scene.value)return
  for(const character of characters){
    const element=scene.value.querySelector<HTMLElement>(`.character-${character}`)
    if(!element)continue
    const rect=element.getBoundingClientRect()
    const deltaX=event.clientX-(rect.left+rect.width/2)
    const deltaY=event.clientY-(rect.top+rect.height/3)
    positions[character]={
      faceX:round(clamp(deltaX/20,-15,15)),
      faceY:round(clamp(deltaY/30,-10,10)),
      bodySkew:round(clamp(-deltaX/120,-6,6))
    }
  }
  scene.value.querySelectorAll<HTMLElement>('.character-eyes i').forEach((element,index)=>{
    const rect=element.getBoundingClientRect()
    const deltaX=event.clientX-(rect.left+rect.width/2)
    const deltaY=event.clientY-(rect.top+rect.height/2)
    const distance=Math.min(Math.hypot(deltaX,deltaY),index<4?(index<2?5:4):5)
    const angle=Math.atan2(deltaY,deltaX)
    pupils[index]={x:round(Math.cos(angle)*distance),y:round(Math.sin(angle)*distance)}
  })
}

function characterStyle(character:Character){
  const skew=positions[character].bodySkew
  if(character==='purple')return {
    height:formMotion.isTyping||hidingPassword.value?'380px':'340px',
    transform:revealedPassword.value?'skewX(0deg)':formMotion.isTyping||hidingPassword.value
      ?`skewX(${round(skew-12)}deg) translateX(40px)`:`skewX(${skew}deg)`
  }
  if(character==='black')return {
    transform:revealedPassword.value?'skewX(0deg)':lookingAtEachOther.value
      ?`skewX(${round(skew*1.5+10)}deg) translateX(20px)`
      :formMotion.isTyping||hidingPassword.value?`skewX(${round(skew*1.5)}deg)`:`skewX(${skew}deg)`
  }
  return {transform:`skewX(${revealedPassword.value?0:skew}deg)`}
}

function faceStyle(character:Character){
  const pos=positions[character]
  const base:Record<Character,[number,number]>={purple:[58,36],black:[31,28],orange:[91,68],yellow:[60,31]}
  let [left,top]=base[character]
  if(revealedPassword.value){
    [left,top]=({purple:[20,35],black:[10,28],orange:[50,85],yellow:[20,35]} as Record<Character,[number,number]>)[character]
  }else if(lookingAtEachOther.value&&character==='purple'){
    [left,top]=[55,65]
  }else if(lookingAtEachOther.value&&character==='black'){
    [left,top]=[32,12]
  }else{
    left+=pos.faceX
    top+=pos.faceY
  }
  return {left:`${left}px`,top:`${top}px`}
}

function pupilStyle(index:number){
  let {x,y}=pupils[index]
  if(revealedPassword.value){
    if(index<2){x=purplePeeking.value?4:-4;y=purplePeeking.value?5:-4}
    else if(index<4){x=-4;y=-4}
    else{x=-5;y=-4}
  }else if(lookingAtEachOther.value){
    if(index<2){x=3;y=4}
    else if(index<4){x=0;y=-4}
  }
  return {'--pupil-x':`${x}px`,'--pupil-y':`${y}px`}
}

function mouthStyle(){
  return revealedPassword.value?{left:'10px',top:'88px'}:{
    left:`${round(51+positions.yellow.faceX)}px`,
    top:`${round(75+positions.yellow.faceY)}px`
  }
}

function scheduleBlink(character:'purple'|'black'){
  later(()=>{
    if(character==='purple')purpleBlink.value=true
    else blackBlink.value=true
    later(()=>{
      if(character==='purple')purpleBlink.value=false
      else blackBlink.value=false
      scheduleBlink(character)
    },150)
  },3000+Math.random()*4000)
}
function schedulePeek(){
  peekTimer=later(()=>{
    purplePeeking.value=true
    peekEndTimer=later(()=>{
      purplePeeking.value=false
      schedulePeek()
    },800)
  },2000+Math.random()*3000)
}

watch(()=>formMotion.isTyping,typing=>{
  cancel(lookingTimer)
  if(typing){
    lookingAtEachOther.value=true
    lookingTimer=later(()=>{lookingAtEachOther.value=false},800)
  }else lookingAtEachOther.value=false
})
watch(revealedPassword,revealed=>{
  cancel(peekTimer)
  cancel(peekEndTimer)
  purplePeeking.value=false
  if(revealed&&!(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches))schedulePeek()
})

onMounted(()=>{
  window.addEventListener('mousemove',updateMouse)
  if(!(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)){
    scheduleBlink('purple')
    scheduleBlink('black')
  }
})
onBeforeUnmount(()=>{
  window.removeEventListener('mousemove',updateMouse)
  for(const timer of timers)clearTimeout(timer)
  timers.clear()
})

function done(){
  const next=String(route.query.next||'/')
  router.replace(next.startsWith('/')&&!next.startsWith('//')?next:'/')
}
</script>

<template>
  <div class="animated-login">
    <aside class="animated-login-art" aria-label="四个陪伴你登录的彩色角色">
      <div class="animated-login-brand"><span class="animated-login-brand-mark">SF</span><span>业务管理系统</span></div>
      <div class="animated-login-center">
        <p class="animated-login-kicker">WELCOME TO SF WORKSPACE</p>
        <h1>让工作，<br>变得更有条理。</h1>
        <p class="animated-login-lead">项目、订单、付款与发票，<br>在一个清晰的工作台里相遇。</p>
        <div ref="scene" class="characters-scene" :data-mood="mood" aria-hidden="true">
          <div class="login-character character-purple" :style="characterStyle('purple')">
            <div class="character-eyes" :class="{'is-blinking':purpleBlink}" :style="faceStyle('purple')"><i v-for="index in [0,1]" :key="index" :style="pupilStyle(index)"/></div>
          </div>
          <div class="login-character character-black" :style="characterStyle('black')">
            <div class="character-eyes" :class="{'is-blinking':blackBlink}" :style="faceStyle('black')"><i v-for="index in [2,3]" :key="index" :style="pupilStyle(index)"/></div>
          </div>
          <div class="login-character character-orange" :style="characterStyle('orange')">
            <div class="character-eyes" :style="faceStyle('orange')"><i v-for="index in [4,5]" :key="index" :style="pupilStyle(index)"/></div><span class="character-mouth"/>
          </div>
          <div class="login-character character-yellow" :style="characterStyle('yellow')">
            <div class="character-eyes" :style="faceStyle('yellow')"><i v-for="index in [6,7]" :key="index" :style="pupilStyle(index)"/></div><span class="character-mouth" :style="mouthStyle()"/>
          </div>
        </div>
      </div>
      <div class="animated-login-footer"><span>清晰记录 · 有序协作</span><span>仅供内部员工使用</span></div>
    </aside>
    <main class="animated-login-main">
      <div class="animated-login-panel">
        <div class="animated-login-mobile-brand">SF <span>业务管理系统</span></div>
        <el-icon class="animated-login-star" :size="26"><Star/></el-icon>
        <p class="animated-login-overline">YOUR WORKSPACE AWAITS</p>
        <h2>欢迎回来！</h2>
        <p class="animated-login-description">使用员工账号登录，继续今天的工作。</p>
        <LoginForm showcase @success="done" @mood="mood=$event" @motion="Object.assign(formMotion,$event)"/>
        <div class="animated-login-bottom"><a href="/m/">切换到手机端 <span aria-hidden="true">↗</span></a></div>
      </div>
    </main>
  </div>
</template>
