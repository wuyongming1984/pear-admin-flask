// @vitest-environment jsdom
import {test,expect} from 'vitest';
import {mount} from '@vue/test-utils';
import {h} from 'vue';
import {CardTable,Column,MobileSelect,Option} from './controls';
test('card table preserves row actions and selected record identities',async()=>{
 const rows=[{id:7,name:'苗木',quantity:'12'}];
 const w=mount(CardTable,{props:{data:rows},slots:{default:()=>[h(Column,{type:'selection'}),h(Column,{prop:'name',label:'名称'}),h(Column,{label:'操作'},{default:({row}:any)=>h('button',{'data-id':row.id},'编辑')})]}});
 expect(w.text()).toContain('苗木');expect(w.find('button').attributes('data-id')).toBe('7');
 await w.find('input[type=checkbox]').setValue(true);expect(w.emitted('selection-change')?.[0]).toEqual([rows]);
});
test('choice preserves numeric ID rather than converting it to text',async()=>{
 const w=mount(MobileSelect,{props:{modelValue:null},slots:{default:()=>[h(Option,{value:8,label:'供应商'})]}});
 await w.find('button').trigger('click');await w.find('[data-choice]').trigger('click');
 expect(w.emitted('update:modelValue')?.[0]).toEqual([8]);
});
test('multiple invoice choices preserve all numeric IDs and allow deselection',async()=>{
 const w=mount(MobileSelect,{props:{modelValue:[8],multiple:true},slots:{default:()=>[h(Option,{value:8,label:'发票甲'}),h(Option,{value:9,label:'发票乙'})]}});
 await w.find('button').trigger('click');await w.findAll('[data-choice]')[1].trigger('click');expect(w.emitted('update:modelValue')?.[0]).toEqual([[8,9]]);
 await w.setProps({modelValue:[8,9]});await w.findAll('[data-choice]')[0].trigger('click');expect(w.emitted('update:modelValue')?.[1]).toEqual([[9]]);
});
test('nested department records remain reachable and dictionary cards emit selection',async()=>{
 const child={id:2,name:'子部门'},parent={id:1,name:'总公司',children:[child]};const w=mount(CardTable,{props:{data:[parent]},slots:{default:()=>[h(Column,{prop:'name',label:'部门'})]}});
 expect(w.findAll('article')).toHaveLength(2);await w.findAll('article')[1].trigger('click');expect(w.emitted('row-click')?.[0]).toEqual([child]);
});
