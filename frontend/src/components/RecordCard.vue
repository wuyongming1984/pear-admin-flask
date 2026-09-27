<script setup lang="ts">
import {config,money,type Kind,type RecordData} from '../model';import {useRoute} from 'vue-router';const route=useRoute();
import {label} from '../store';
defineProps<{kind:Kind;row:RecordData}>();
</script><template><router-link :to="{path:`/${kind}/${row.id}`,query:route.query}" class="record-card">
 <div class="card-top"><span class="record-index">{{kind==='project'?'PROJECT':kind==='order'?'ORDER':'PAYMENT'}} · {{String(row.id).padStart(3,'0')}}</span><span v-if="config[kind].status" class="status-pill">{{label(config[kind].dict,row[config[kind].status!])}}</span><van-icon v-else name="arrow" color="#a1afb2"/></div>
 <h3>{{row[config[kind].name]||'未命名'}}</h3><p class="card-subtitle">{{kind==='project'?row.project_full_name:row.project_name||'未关联项目'}}</p>
 <div class="card-bottom"><div><small>{{kind==='project'?'合同金额':kind==='order'?'订单金额':'本次付款'}}</small><strong><span>¥ </span>{{money(row[config[kind].amount])}}</strong></div><span class="card-note">{{kind==='order'?row.supplier_contact_person||'':kind==='pay'?row.payee_supplier_name||'':row.start_date||'待安排'}}</span></div>
</router-link></template>
