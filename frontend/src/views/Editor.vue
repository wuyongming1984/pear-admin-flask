<script setup lang="ts">
import {computed,onMounted,reactive,ref,onBeforeUnmount} from 'vue';import {useRoute,useRouter,onBeforeRouteLeave} from 'vue-router';import {showConfirmDialog,showSuccessToast} from 'vant';
import {request,ApiError} from '../api';import {session,label,can,invalidate} from '../store';import {config,attachmentsOf,payloadFor,validMoney,relationName,type Kind,type RecordData,type Field,type Attachment} from '../model';import SearchPicker from '../components/SearchPicker.vue';import AttachmentPanel from '../components/AttachmentPanel.vue';
const route=useRoute();const router=useRouter();const kind=route.params.kind as Kind;const id=route.params.id;const meta=config[kind];const form=reactive<RecordData>({});const names=reactive<Record<string,string>>({});const original=ref<RecordData>({});const attachments=ref<Attachment[]>([]);const initialAttachments=ref('[]');const baseline=ref('');const loading=ref(true);const loaded=ref(false);const saving=ref(false);const error=ref('');const uploadBusy=ref(false);const blocked=ref(false);const uncertain=ref(false);const completed=ref(false);const picker=ref(false);const field=ref<Field|null>(null);
const relationLabels:Record<string,string>={project_id:'project_name',supplier_id:'supplier_name',order_id:'order_number',payer_supplier_id:'payer_supplier_name',payee_supplier_id:'payee_supplier_name'};
const dirty=computed(()=>loaded.value&&(JSON.stringify(form)!==baseline.value||JSON.stringify(attachments.value)!==initialAttachments.value||blocked.value||uploadBusy.value));
function beforeUnload(e:BeforeUnloadEvent){if(dirty.value&&!completed.value){e.preventDefault();e.returnValue=''}}
onBeforeRouteLeave(async()=>{if(completed.value)return true;if(saving.value||uploadBusy.value)return false;if(!dirty.value)return true;try{await showConfirmDialog({title:'离开编辑页？',message:'尚未保存的填写内容将丢失。',confirmButtonText:'离开',cancelButtonText:'继续编辑'});return true}catch{return false}});
onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload));
async function load(){if(!can(kind)){loading.value=false;return}loading.value=true;error.value='';loaded.value=false;try{
 let data:RecordData={};if(id)data=(await request(`/${kind}/${id}`)).data;
 original.value=data;for(const f of meta.fields){form[f.key]=data[f.key]??'';if(f.type==='money')form[f.key]=String(form[f.key]);if(f.type==='relation')names[f.key]=data[relationLabels[f.key]]||''}
 attachments.value=attachmentsOf(data);initialAttachments.value=JSON.stringify(attachments.value);
 if(!id){if(kind==='pay'){form.pay_number=`P${new Date().toISOString().slice(0,10).replace(/-/g,'')}${crypto.randomUUID().replace(/-/g,'').slice(0,12)}`;form.handler=session.user.nickname||session.user.username;}
  if(kind==='order'&&route.query.project_id){const p=(await request(`/project/${route.query.project_id}`)).data;form.project_id=p.id;names.project_id=p.project_name;}
  if(kind==='pay'&&route.query.order_id){const o=(await request(`/order/${route.query.order_id}`)).data;await selectRelation({key:'order_id',source:'order'} as Field,o)}
 }
 baseline.value=JSON.stringify(form);loaded.value=true;
}catch(e){error.value=(e as Error).message}finally{loading.value=false}}
async function selectRelation(f:Field,row:RecordData){form[f.key]=row.id;names[f.key]=relationName(f.source!,row);
 if(f.key==='supplier_id'){form.supplier_contact_person=row.contact_person||'';form.contact_phone=row.phone||''}
 if(f.key==='order_id'&&row.supplier_id){form.payee_supplier_id=row.supplier_id;names.payee_supplier_id=row.supplier_name||String(row.supplier_id)}
}
function choose(row:RecordData){if(!field.value)return;if(field.value.type==='select')form[field.value.key]=row.value;else selectRelation(field.value,row)}
function open(f:Field){field.value=f;picker.value=true}
function validate(){for(const f of meta.fields){const value=form[f.key];if(f.required&&(value===null||value===undefined||String(value).trim()===''))throw new Error(`请填写${f.label}`);if(f.type==='money'&&value!==''&&!validMoney(String(value)))throw new Error(`${f.label}应为最多两位小数的非负金额`)}
 if(kind!=='project'&&Number(form[meta.amount])<=0)throw new Error('金额必须大于零');if(kind==='project'&&form.start_date&&form.end_date&&form.end_date<form.start_date)throw new Error('结束日期不能早于开始日期');}
async function save(){if(saving.value||uploadBusy.value||blocked.value||uncertain.value)return;error.value='';try{validate()}catch(e){error.value=(e as Error).message;return}saving.value=true;try{
 const changed=JSON.stringify(attachments.value)!==initialAttachments.value;const data=payloadFor(kind,form,changed?attachments.value:undefined);
 const r=await request(`/${kind}/${id||''}`,{method:id?'PUT':'POST',body:JSON.stringify(data)});
 completed.value=true;invalidate(kind);showSuccessToast('保存成功');await router.replace({path:`/${kind}/${id||r.data?.id}`,query:route.query});
}catch(e){error.value=(e as Error).message;if(e instanceof ApiError&&e.uncertain){uncertain.value=true;invalidate(kind)}}finally{saving.value=false}}
onMounted(()=>{window.addEventListener('beforeunload',beforeUnload);load()});
</script><template><main class="page editor-page"><van-nav-bar :title="`${id?'编辑':'新增'}${meta.title}`" left-text="取消" left-arrow @click-left="router.push({path:id?`/${kind}/${id}`:`/${kind}`,query:route.query})"/><van-empty v-if="!can(kind)" description="当前账号无此业务菜单"/><van-loading v-else-if="loading" class="center-loading"/><div v-else-if="!loaded" class="error-panel" role="alert">{{error}}<van-button @click="load">重新加载</van-button></div><template v-else>
 <div class="editor-intro"><span class="eyebrow">{{id?'UPDATE':'CREATE'}} / {{kind.toUpperCase()}}</span><h2>{{id?'更新业务信息':'填写'+meta.title+'信息'}}</h2><p>带 * 的项目为必填项</p></div>
 <van-form @submit="save"><van-cell-group inset>
 <template v-for="f in meta.fields" :key="f.key">
 <van-field v-if="f.type==='select'||f.type==='relation'" :model-value="f.type==='select'?(form[f.key]?label(f.dict,form[f.key]):''):(names[f.key]||String(form[f.key]||''))" :label="f.label" :placeholder="'请选择'+f.label" :required="f.required" readonly is-link @click="open(f)"/>
 <van-field v-else-if="f.type==='date'" :label="f.label"><template #input><input v-model="form[f.key]" type="date" :aria-label="f.label" class="date-input"/></template></van-field>
 <van-field v-else v-model="form[f.key]" :label="f.label" :name="f.key" :required="f.required" :type="f.type==='textarea'?'textarea':f.type==='money'?'number':'text'" :inputmode="f.type==='money'?'decimal':'text'" :placeholder="f.hint||'请输入'+f.label" :rows="f.type==='textarea'?3:undefined" :maxlength="f.type==='textarea'?2000:f.type==='money'?19:128" :rules="f.required?[{required:true,message:'请填写'+f.label}]:[]"/>
 </template></van-cell-group>
 <p v-if="kind==='pay'&&original.invoices_list?.length" class="empty-hint">已关联 {{original.invoices_list.length}} 张发票，本次编辑将保留原关联。</p>
 <AttachmentPanel v-model="attachments" :kind="kind" @busy="uploadBusy=$event" @blocked="blocked=$event"/>
 <p v-if="error" class="form-error" role="alert">{{error}}</p><p v-if="blocked" class="form-error">请先重试失败的附件，或移除失败任务，再保存。</p><div class="form-actions"><van-button block round type="primary" native-type="submit" :loading="saving" :disabled="uploadBusy||blocked||uncertain">{{uploadBusy?'等待附件上传':uncertain?'请先核对提交结果':'保存'+meta.title}}</van-button><van-button v-if="uncertain" block plain class="section-button" @click="router.push(`/${kind}`)">返回列表核对</van-button></div></van-form>
 <SearchPicker v-if="field" v-model:show="picker" :title="field.label" :source="field.type==='relation'?field.source:undefined" :items="session.dicts[field.dict||'']||[]" @select="choose"/>
 </template></main></template>
