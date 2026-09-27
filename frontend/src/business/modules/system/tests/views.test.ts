// @vitest-environment jsdom
import {beforeEach, expect, test, vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {defineComponent} from 'vue'
import Records from '../Records.vue'
import Backup from '../Backup.vue'
import Dictionary from '../Dictionary.vue'
import Profile from '../Profile.vue'
const api=vi.hoisted(()=>({request:vi.fn(),allRows:vi.fn()}))
const messages=vi.hoisted(()=>({error:vi.fn(),success:vi.fn(),warning:vi.fn(),confirm:vi.fn()}))
vi.mock('../../../api',()=>api)
vi.mock('vue-router',()=>({onBeforeRouteLeave:vi.fn(),onBeforeRouteUpdate:vi.fn()}))
vi.mock('../../../feedback',()=>({ElMessage:messages,ElMessageBox:{confirm:messages.confirm}}))
const stub=defineComponent({template:'<div><slot/><slot name="footer"/></div>'})
const global={stubs:Object.fromEntries(['RouterLink','MButton','MInput','MTable','MTag','MPagination','MDialog','MForm','MFormItem','MSwitch','MSelect','MOption','MInputNumber','MDatePicker','MCheckboxGroup','MCheckbox','MTree','MTimePicker','MDescriptions','MDescriptionsItem'].map(x=>[x,stub]).concat([['MTableColumn',defineComponent({template:'<div/>'})]])),directives:{loading:()=>{}}}
beforeEach(()=>{vi.clearAllMocks();api.allRows.mockResolvedValue([]);api.request.mockResolvedValue({code:0,data:[]});messages.confirm.mockResolvedValue('confirm')})
test('user editing sends no empty password and issues no automatic role grant',async()=>{
 const wrapper=mount(Records,{props:{kind:'users'},global});await flushPromises();const vm=wrapper.vm as any
 vm.edit({id:7,username:'alice',nickname:'Alice',email:'old@example.com',create_at:'2026-01-01 00:00:00'});vm.form.nickname='Alice changed';await vm.save()
 expect(api.request).toHaveBeenCalledTimes(1);const [path,options]=api.request.mock.calls[0];expect(path).toBe('/user/7');expect(options.method).toBe('PUT');expect(JSON.parse(options.body)).toMatchObject({nickname:'Alice changed',email:'old@example.com'});expect(JSON.parse(options.body)).not.toHaveProperty('password');wrapper.unmount()
})
test('authorization starts from server-owned roles and can explicitly clear all',async()=>{
 api.allRows.mockResolvedValue([{id:1,name:'Operator'},{id:2,name:'Viewer'}]);api.request.mockResolvedValue({code:0,data:[2]})
 const wrapper=mount(Records,{props:{kind:'users'},global});await flushPromises();const vm=wrapper.vm as any;await vm.authorize({id:7,username:'alice'});expect(vm.selected).toEqual([2]);vm.selected=[];await vm.saveAuthorization();expect(api.request).toHaveBeenLastCalledWith('/user/user_role/7',{method:'PUT',body:'{"rights_ids":""}'});wrapper.unmount()
})
test('failed authorization load closes editor and never writes a grant',async()=>{
 const wrapper=mount(Records,{props:{kind:'users'},global});await flushPromises();api.request.mockRejectedValue(new Error('network'));const vm=wrapper.vm as any;await vm.authorize({id:7,username:'alice'});expect(vm.authOpen).toBe(false);expect(api.request.mock.calls.every(call=>!call[1]?.method)).toBe(true);wrapper.unmount()
})
test('backup load and save preserve masked secret and do not execute backup',async()=>{
 const config={mail_server:'smtp.example.com',mail_port:'465',mail_receiver:'a@example.com',mail_pass:'******',backup_time:'01:00',enable_auto_backup:false};api.request.mockResolvedValue({code:0,data:config})
 const wrapper=mount(Backup,{global});await flushPromises();const vm=wrapper.vm as any;expect(vm.form.mail_pass).toBe('');await vm.save();const writes=api.request.mock.calls.filter(call=>call[1]?.method);expect(writes).toHaveLength(1);expect(writes[0][0]).toBe('/system/config/backup');expect(JSON.parse(writes[0][1].body).mail_pass).toBe('******');expect(api.request.mock.calls.some(call=>call[0]==='/system/backup/test')).toBe(false);wrapper.unmount()
})

test('user Cancel keeps draft when discard confirmation is rejected',async()=>{
 const wrapper=mount(Records,{props:{kind:'users'},global});await flushPromises();const vm=wrapper.vm as any;vm.edit({id:7,username:'alice',nickname:'Alice'});expect(vm.dirty).toBe(false);vm.form.nickname='Changed';messages.confirm.mockRejectedValueOnce('cancel');expect(await vm.allowDiscard()).toBe(false);expect(vm.dialog).toBe(true);expect(vm.form.nickname).toBe('Changed');expect(api.request).not.toHaveBeenCalled();wrapper.unmount()
})
test('backup reload cancelled with unsaved form performs no second request',async()=>{
 api.request.mockResolvedValue({code:0,data:{mail_server:'original',mail_port:'465',mail_receiver:'a@example.com',mail_pass:'',backup_time:'01:00',enable_auto_backup:false}});const wrapper=mount(Backup,{global});await flushPromises();const vm=wrapper.vm as any;expect(vm.dirty).toBe(false);vm.form.mail_server='unsaved';messages.confirm.mockRejectedValueOnce('cancel');await vm.reload();expect(vm.form.mail_server).toBe('unsaved');expect(api.request).toHaveBeenCalledTimes(1);wrapper.unmount()
})
test('dictionary detail cancellation preserves selected editor draft',async()=>{
 const wrapper=mount(Dictionary,{global});await flushPromises();const vm=wrapper.vm as any;vm.edit(true,{id:4,code:'unit',value:'株',dic_id:9});expect(vm.dirty).toBe(false);vm.form.value='棵';messages.confirm.mockRejectedValueOnce('cancel');expect(await vm.allowDiscard()).toBe(false);expect(vm.form.value).toBe('棵');expect(vm.dialog).toBe(true);wrapper.unmount()
})
test('profile password draft protects reload and is clean after successful save',async()=>{
 api.request.mockResolvedValue({code:0,data:{username:'alice'}});const wrapper=mount(Profile,{global});await flushPromises();const vm=wrapper.vm as any;expect(vm.dirty).toBe(false);vm.oldPassword='old';vm.newPassword='123456';vm.confirmation='123456';const before=new Event('beforeunload',{cancelable:true});window.dispatchEvent(before);expect(before.defaultPrevented).toBe(true);await vm.save();expect(vm.dirty).toBe(false);const after=new Event('beforeunload',{cancelable:true});window.dispatchEvent(after);expect(after.defaultPrevented).toBe(false);wrapper.unmount()
})
