import { describe,it,expect } from 'vitest';
import { attachmentsOf, payloadFor, validMoney } from './model';
describe('mobile persistence adapters',()=>{
 it('normalizes blank optional monetary fields to null',()=>{
 expect(payloadFor('pay',{invoice_amount:'',current_payment_amount:'10.10'})).toEqual({invoice_amount:null,current_payment_amount:'10.10'});
 });
 it('keeps stable raw attachment URLs and unrecognized metadata',()=>{
 const a=attachmentsOf({attachments:'[{"url":"/uploads/a.pdf","legacy":42}]',attachments_list:[{url:'https://signed.invalid/x'}]});
 expect(a[0]).toMatchObject({url:'/uploads/a.pdf',legacy:42});expect(JSON.parse(payloadFor('order',{},a).attachments)[0]).toEqual({url:'/uploads/a.pdf',legacy:42});
 });
 it('keeps project attachment IDs and original storage path',()=>{
 expect(attachmentsOf({attachments_list:[{id:8,code:'合同',file_path:'/uploads/a.pdf',url:'https://signed.invalid/x'}]})[0]).toMatchObject({id:8,code:'合同',url:'/uploads/a.pdf'});
 });
 it('never sends invoice links or hidden fields during payment edits',()=>{
 const p=payloadFor('pay',{current_payment_amount:'100.20',payment_status:'1',invoices_list:[{id:9}],invoice_ids:[],create_at:'old'},undefined);
 expect(p).toEqual({current_payment_amount:'100.20',payment_status:'1'});
 });
 it('omits unchanged attachments and keeps decimal strings',()=>{
 expect(payloadFor('project',{project_name:'工程',project_amount:'0.10'},undefined)).toEqual({project_name:'工程',project_amount:'0.10'});
 });
 it('rejects invalid or excessive-precision money',()=>{
 expect(validMoney('123.45')).toBe(true); expect(validMoney('0.00')).toBe(true);
 for(const v of ['-1','1e3','12.345','NaN','1,000','']) expect(validMoney(v)).toBe(false);
 });
});
