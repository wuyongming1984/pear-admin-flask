// @vitest-environment jsdom
import {expect,test,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import ElementPlus from 'element-plus'
import LoginForm from './LoginForm.vue'

const login=vi.fn()
vi.mock('../session',()=>({login:(...args:unknown[])=>login(...args)}))

test('showcase login keeps existing account authentication and reacts to password visibility',async()=>{
 login.mockResolvedValue(undefined)
 const wrapper=mount(LoginForm,{props:{showcase:true},global:{plugins:[ElementPlus]}})
 expect(wrapper.text()).toContain('账号')
 expect(wrapper.text()).not.toContain('Google')
 await wrapper.get('input[name="username"]').setValue('staff')
 const password=wrapper.get('input[name="password"]')
 await password.setValue('secret')
 await password.trigger('focus')
 expect(wrapper.emitted('mood')?.at(-1)?.[0]).toBe('password')
 await wrapper.get('[aria-label="显示密码"]').trigger('click')
 expect(wrapper.get('input[name="password"]').attributes('type')).toBe('text')
 await wrapper.get('form').trigger('submit')
 await flushPromises()
 expect(login).toHaveBeenCalledWith('staff','secret')
 expect(wrapper.emitted('success')).toHaveLength(1)
 wrapper.unmount()
})
