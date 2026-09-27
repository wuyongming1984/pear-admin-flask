// @vitest-environment jsdom
import {afterEach,expect,test,vi} from 'vitest'
import {mount} from '@vue/test-utils'
import {nextTick} from 'vue'
import {createMemoryHistory,createRouter} from 'vue-router'
import ElementPlus from 'element-plus'
import Login from './Login.vue'

afterEach(()=>{vi.restoreAllMocks();vi.useRealTimers()})

async function loginPage(){
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/login',component:Login}]})
  await router.push('/login')
  await router.isReady()
  return mount(Login,{global:{plugins:[router,ElementPlus]}})
}

test('each character skews and each pupil looks toward the pointer from its own position',async()=>{
  const wrapper=await loginPage()
  const positions:Record<string,[number,number,number,number]>={
    'character-purple':[70,0,180,400],
    'character-black':[240,0,120,310],
    'character-orange':[0,0,240,200],
    'character-yellow':[310,0,140,230]
  }
  for(const [name,bounds] of Object.entries(positions)){
    wrapper.get(`.${name}`).element.getBoundingClientRect=()=>new DOMRect(...bounds)
  }
  const eyes=wrapper.findAll('.character-eyes i')
  eyes.forEach((eye,index)=>{eye.element.getBoundingClientRect=()=>new DOMRect(100+index*45,100+index*12,18,18)})

  window.dispatchEvent(new MouseEvent('mousemove',{clientX:500,clientY:300}))
  await nextTick()

  expect(wrapper.get('.character-purple').attributes('style')).toContain('skewX(-2.83deg)')
  expect(wrapper.get('.character-black').attributes('style')).toContain('skewX(-1.67deg)')
  expect(eyes[0].attributes('style')).toContain('--pupil-x:')
  expect(eyes[0].attributes('style')).not.toBe(eyes[6].attributes('style'))
  wrapper.unmount()
})

test('username focus, hidden password and revealed password use the demo poses',async()=>{
  const wrapper=await loginPage()
  const username=wrapper.get('input[name="username"]')
  const password=wrapper.get('input[name="password"]')

  await username.trigger('focus')
  expect(wrapper.get('.character-purple').attributes('style')).toContain('translateX(40px)')
  expect(wrapper.get('.character-purple').attributes('style')).toContain('height: 380px')
  expect(wrapper.get('.character-black').attributes('style')).toContain('translateX(20px)')

  await username.trigger('blur')
  await password.setValue('secret')
  expect(wrapper.get('.character-purple').attributes('style')).toContain('height: 380px')
  await wrapper.get('[aria-label="显示密码"]').trigger('click')
  expect(wrapper.get('.character-purple').attributes('style')).toContain('skewX(0deg)')
  expect(wrapper.get('.character-yellow').attributes('style')).toContain('skewX(0deg)')
  expect(wrapper.findAll('.character-eyes i')[0].attributes('style')).toContain('--pupil-x: -4px')
  wrapper.unmount()
})

test('revealing a nonempty password makes the purple character peek briefly',async()=>{
  vi.useFakeTimers()
  vi.spyOn(Math,'random').mockReturnValue(0)
  const wrapper=await loginPage()
  await wrapper.get('input[name="password"]').setValue('secret')
  await wrapper.get('[aria-label="显示密码"]').trigger('click')
  const purpleEye=wrapper.findAll('.character-eyes i')[0]
  expect(purpleEye.attributes('style')).toContain('--pupil-x: -4px')
  vi.advanceTimersByTime(2000)
  await nextTick()
  expect(purpleEye.attributes('style')).toContain('--pupil-x: 4px')
  expect(purpleEye.attributes('style')).toContain('--pupil-y: 5px')
  vi.advanceTimersByTime(800)
  await nextTick()
  expect(purpleEye.attributes('style')).toContain('--pupil-x: -4px')
  wrapper.unmount()
})
