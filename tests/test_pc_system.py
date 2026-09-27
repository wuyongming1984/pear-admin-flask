"""PC system regressions; ephemeral SQLite only, no scheduler or network."""
import json
import sys
import types
import unittest
from unittest.mock import patch, Mock
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask
from flask_jwt_extended import create_access_token
from pear_admin.apis import register_apis
from pear_admin.extensions import db, jwt
from pear_admin.orms import UserORM, RoleORM, DepartmentORM, RightsORM
from pear_admin.orms.dictionary import DictionaryORM, DictionaryDetailORM
from pear_admin.orms.sys_config import SysConfigORM


class PCSystemTest(unittest.TestCase):
    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network prohibited'))
        self.network.start()
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://', JWT_SECRET_KEY='system-offline-secret-at-least-32-characters', JWT_VERIFY_SUB=False)
        db.init_app(self.app)
        jwt.init_app(self.app)
        register_apis(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = UserORM(username='admin', nickname='Admin', password='old password ', mobile='', email='', department_id=None)
        db.session.add(self.user)
        db.session.commit()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=self.user)}
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.network.stop()

    def call(self, method, path, data=None):
        response = self.client.open('/api/v1/' + path, method=method, json=data, headers=self.headers)
        self.assertTrue(response.is_json, response.get_data(as_text=True))
        return response.get_json()

    def test_management_requires_login(self):
        for resource in ('user', 'role', 'department'):
            for method, suffix in [('GET','/'),('POST','/'),('PUT','/1'),('DELETE','/1')]:
                with self.subTest(resource=resource, method=method):
                    response=self.client.open('/api/v1/'+resource+suffix, method=method, json={})
                    self.assertIn(response.status_code, (401,403))
        for path in ('user/user_role/1','role/role_rights/1'):
            for method in ('GET','PUT'):
                self.assertIn(self.client.open('/api/v1/'+path, method=method, json={}).status_code,(401,403))

    def test_user_create_defaults_update_url_and_empty_password(self):
        self.assertEqual(self.call('POST','user/',{'username':'other','nickname':'Other','create_at':''})['code'],0)
        user=db.session.scalar(db.select(UserORM).where(UserORM.username=='other'))
        self.assertTrue(user.check_password('123456'))
        self.assertEqual(self.call('PUT',f'user/{user.id}',{'nickname':'Changed','password':'','create_at':''})['code'],0)
        self.assertTrue(user.check_password('123456'))
        self.assertEqual(user.nickname,'Changed')
        self.assertEqual(self.call('POST','user/',{'username':'other','nickname':'Other'})['code'],-1)
        self.assertEqual(self.call('PUT',f'user/{user.id}',{'username':'admin'})['code'],-1)
        self.assertEqual(user.username,'other')

    def test_missing_and_empty_records_return_errors(self):
        for resource in ('user','role','department','rights'):
            for method,path,data in [('POST',resource+'/',{}),('PUT',resource+'/999',{}),('DELETE',resource+'/999',None)]:
                with self.subTest(path=path,method=method):
                    self.assertEqual(self.call(method,path,data)['code'],-1)
        for resource in ('user','role','department'):
            self.assertEqual(self.call('GET',resource+'/?page=999')['data'],[])

    def test_role_picker_returns_all_roles(self):
        db.session.add_all([RoleORM(name=f'Role{i}',code=f'R{i}') for i in range(14)])
        db.session.commit()
        self.assertEqual(len(self.call('GET','role/?type=tree')['data']),14)
        self.assertEqual(len(self.call('GET','role/?page=2&limit=10')['data']),4)
        self.assertEqual(self.call('POST','role/',{'name':'New','code':'new'})['code'],0)

    def test_department_root_deep_tree_and_cycle(self):
        self.assertEqual(self.call('POST','department/',{'name':'Root','pid':''})['code'],0)
        root=db.session.scalar(db.select(DepartmentORM))
        child=DepartmentORM(name='Child',pid=root.id)
        db.session.add(child);db.session.commit()
        grand=DepartmentORM(name='Grandchild',pid=child.id)
        db.session.add(grand);db.session.commit()
        tree=self.call('GET','department/treetable')
        self.assertEqual(tree['count'],1)
        self.assertEqual(tree['data'][0]['children'][0]['children'][0]['name'],'Grandchild')
        self.assertEqual(self.call('PUT',f'department/{root.id}',{'pid':grand.id})['code'],-1)
        self.assertEqual(self.call('DELETE',f'department/{root.id}')['code'],-1)
        self.assertEqual(root.pid,0)

    def test_rights_tree_non_topological_ids_and_pagination(self):
        db.session.add_all([RightsORM(id=30,name='Root',pid=0,sort=0),RightsORM(id=20,name='Child',pid=30,sort=0),RightsORM(id=10,name='Grand',pid=20,sort=0),RightsORM(id=5,name='Leaf',pid=10,sort=0)])
        db.session.commit()
        tree=self.call('GET','rights/tree')['data']
        self.assertEqual(tree[0]['children'][0]['children'][0]['children'][0]['id'],5)
        table=self.call('GET','rights/treetable?limit=1')['data']
        self.assertEqual(table[0]['children'][0]['children'][0]['children'][0]['id'],5)
        self.assertEqual(self.call('PUT','rights/30',{'pid':5})['code'],-1)
        self.assertEqual(self.call('PUT','rights/5',{'status':False,'sort':''})['code'],0)
        self.assertFalse(db.session.get(RightsORM,5).status)

    def test_invalid_grants_preserve_previous_assignments(self):
        role=RoleORM(name='Test',code='test');db.session.add(role);db.session.commit()
        self.assertEqual(self.call('PUT',f'user/user_role/{self.user.id}',{'rights_ids':str(role.id)})['code'],0)
        self.assertEqual(self.call('PUT',f'user/user_role/{self.user.id}',{'rights_ids':'9999'})['code'],-1)
        self.assertEqual([r.id for r in self.user.role_list],[role.id])
        self.assertEqual(self.call('PUT',f'user/user_role/{self.user.id}',{'rights_ids':''})['code'],0)
        self.assertEqual(list(self.user.role_list),[])

    def test_dictionary_invalid_data_and_duplicate_rollback(self):
        self.assertFalse(self.call('POST','dictionary/',{'code':'  ','name':'X'})['success'])
        self.assertTrue(self.call('POST','dictionary/',{'code':'A','name':'A'})['success'])
        self.assertTrue(self.call('POST','dictionary/',{'code':'B','name':'B'})['success'])
        item=db.session.scalar(db.select(DictionaryORM).where(DictionaryORM.code=='B'))
        self.assertFalse(self.call('PUT',f'dictionary/{item.id}',{'code':'A'})['success'])
        self.assertEqual(item.code,'B')
        self.assertFalse(self.call('POST','dictionary/detail',{'dic_id':999,'code':'x','value':'X'})['success'])
        self.assertTrue(self.call('POST','dictionary/detail',{'dic_id':item.id,'code':'x','value':'X','order_no':''})['success'])
        self.assertFalse(self.call('POST','dictionary/detail',{'dic_id':item.id,'code':'x','value':'X'})['success'])
        self.assertFalse(self.call('DELETE',f'dictionary/{item.id}')['success'])
        self.assertEqual(self.call('GET','dictionary/list?page=bad&limit=bad')['code'],0)

    def test_backup_mask_does_not_overwrite_secret_or_start_scheduler(self):
        db.session.add(SysConfigORM(key='backup_email_config',value=json.dumps({'mail_pass':'saved-secret'})))
        db.session.commit()
        scheduler=types.ModuleType('pear_admin.extensions.init_scheduler')
        scheduler.refresh_backup_scheduler_job=Mock()
        with patch.dict(sys.modules,{'pear_admin.extensions.init_scheduler':scheduler}):
            result=self.call('POST','system/config/backup',{'mail_server':'example.test','mail_port':'465','mail_receiver':'test@example.test','mail_pass':'******','backup_time':'01:00'})
        self.assertEqual(result['code'],0)
        config=db.session.scalar(db.select(SysConfigORM))
        self.assertEqual(json.loads(config.value)['mail_pass'],'saved-secret')
        self.assertEqual(self.call('GET','system/config/backup')['data']['mail_pass'],'******')

    def test_role_rights_cache_and_menu_preserve_reparented_hierarchy(self):
        role=RoleORM(name='Menu',code='menu')
        root=RightsORM(id=30,name='Root',pid=0,sort=1,type='menu')
        child=RightsORM(id=20,name='Child',pid=30,sort=1,type='path')
        leaf=RightsORM(id=10,name='Leaf',pid=20,sort=1,type='path')
        db.session.add_all([role,root,child,leaf]);db.session.commit()
        self.assertEqual(self.call('PUT',f'role/role_rights/{role.id}',{'rights_ids':'30,20,10'})['code'],0)
        self.assertEqual(set(role.rights_ids.split(',')),{'30','20','10'})
        self.user.role_list.append(role);db.session.commit()
        menu=self.call('GET','menu')
        self.assertEqual(menu[0]['children'][0]['children'][0]['id'],10)
        self.assertEqual(self.call('PUT',f'role/role_rights/{role.id}',{'rights_ids':'999'})['code'],-1)
        self.assertEqual(len(role.rights_list),3)

    def test_commit_failure_rolls_back_system_changes(self):
        with patch.object(db.session,'commit',side_effect=SQLAlchemyError('offline simulated failure')):
            self.assertEqual(self.call('POST','role/',{'name':'Unsaved','code':'unsaved'})['code'],-1)
        self.assertEqual(db.session.query(RoleORM).count(),0)
        self.assertEqual(self.call('POST','role/',{'name':'Saved','code':'saved'})['code'],0)

    def test_backup_uses_saved_credentials_without_running_subprocess(self):
        from pear_admin.extensions import init_scheduler
        config=SysConfigORM(key='backup_email_config',value=json.dumps({'mail_user':'saved-user','mail_pass':'saved-pass','mail_server':'example.test','mail_port':'465','mail_receiver':'test@example.test'}))
        db.session.add(config);db.session.commit()
        result=types.SimpleNamespace(returncode=0,stdout='mocked',stderr='')
        with patch('pear_admin.apis.system.subprocess.run',return_value=result) as run:
            self.assertEqual(self.call('POST','system/backup/test')['code'],0)
            self.assertEqual(run.call_args.kwargs['env']['MAIL_USERNAME'],'saved-user')
            self.assertEqual(run.call_args.kwargs['env']['MAIL_PASSWORD'],'saved-pass')
        with patch.object(init_scheduler,'scheduler',types.SimpleNamespace(app=self.app)), patch.object(init_scheduler.subprocess,'run',return_value=result) as run:
            init_scheduler.run_backup_job()
            self.assertEqual(run.call_args.kwargs['env']['MAIL_USERNAME'],'saved-user')
            self.assertEqual(run.call_args.kwargs['env']['MAIL_PASSWORD'],'saved-pass')
        config.value=json.dumps({'mail_user':'','mail_pass':'','mail_server':'example.test','mail_port':'465','mail_receiver':'test@example.test'})
        db.session.commit()
        with patch.dict('os.environ',{'MAIL_USERNAME':'env-user','MAIL_PASSWORD':'env-pass'}), patch('pear_admin.apis.system.subprocess.run',return_value=result) as run:
            self.assertEqual(self.call('POST','system/backup/test')['code'],0)
            self.assertEqual(run.call_args.kwargs['env']['MAIL_USERNAME'],'env-user')
            self.assertEqual(run.call_args.kwargs['env']['MAIL_PASSWORD'],'env-pass')

    def test_login_missing_input_and_password_spaces(self):
        for data in ({},[],{'username':'admin','password':None}):
            self.assertEqual(self.client.post('/api/v1/login',json=data).status_code,400)
        self.assertEqual(self.call('POST','user/change-password',{'old_password':'old password ','new_password':'new password '})['code'],0)
        self.assertTrue(self.user.check_password('new password '))


if __name__=='__main__':
    unittest.main()
