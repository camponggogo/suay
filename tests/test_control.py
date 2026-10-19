import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'versions' / 'python'))
from control.app import create_app


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db = Path(self.temp.name) / 'test.db'
        self.app = create_app(self.db, upstream='', models=['test-model'])
        self.client = TestClient(self.app, headers={'X-SUAY-Request': '1'})
        self.password = 'ChangedPassword!123'

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def admin(self):
        self.assertEqual(self.client.post('/api/login', json={'username':'admin','password':'suay1234'}).status_code, 200)
        self.assertEqual(self.client.post('/api/password', json={'current_password':'suay1234','new_password':self.password}).status_code, 200)
        self.client.post('/api/login', json={'username':'admin','password':self.password})

    def add_user(self, name, role, zones=None, nodes=None):
        result = self.client.post('/api/users', json={'username':name,'password':'TemporaryPass!123','role':role,'zones':zones or [],'nodes':nodes or []})
        self.assertEqual(result.status_code, 200, result.text)
        c = TestClient(self.app, headers={'X-SUAY-Request':'1'})
        c.post('/api/login', json={'username':name,'password':'TemporaryPass!123'})
        c.post('/api/password', json={'current_password':'TemporaryPass!123','new_password':self.password})
        c.post('/api/login', json={'username':name,'password':self.password})
        return c

    def test_bootstrap_cannot_access_data_or_tokens_until_password_changed(self):
        self.client.post('/api/login', json={'username':'admin','password':'suay1234'})
        self.assertEqual(self.client.get('/api/nodes').status_code,403)
        self.assertEqual(self.client.post('/api/tokens', json={'name':'x','scopes':['inference']}).status_code,403)
        result = self.client.post('/api/password', json={'current_password':'suay1234','new_password':self.password})
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.client.get('/api/users').status_code,401)
        with sqlite3.connect(self.db) as conn:
            stored = conn.execute('SELECT password FROM users').fetchone()[0]
            self.assertNotIn('suay1234', stored)
        conn.close()

    def test_zone_node_filters_readonly_and_no_shell(self):
        self.admin()
        for nid,zone in [('n1','dev'),('n2','finance')]:
            self.client.post('/api/nodes', json={'id':nid,'zone':zone})
        viewer = self.add_user('viewer','view_only',['dev'])
        self.assertEqual([n['id'] for n in viewer.get('/api/nodes').json()],['n1'])
        self.assertEqual(viewer.post('/api/nodes/n1/command', json={'action':'stop'}).status_code,403)
        monitor = self.add_user('monitor','agent_monitor',['*'],['n2'])
        self.assertEqual([n['id'] for n in monitor.get('/api/nodes').json()],['n2'])
        dev = self.add_user('developer','command_line',['dev'])
        self.assertEqual(dev.post('/api/nodes/n2/command', json={'action':'stop'}).status_code,404)
        for body in [{'action':'shell'}, {'action':'run','model':'not-approved'}, {'action':'stop','command':'whoami'}]:
            self.assertEqual(dev.post('/api/nodes/n1/command', json=body).status_code,422)
        response = dev.post('/api/nodes/n1/command', json={'action':'run','model':'test-model'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['applied'])
        self.assertEqual(response.json()['status'],'pending')

    def test_token_scopes_revocation_and_grant_changes(self):
        self.admin()
        dev = self.add_user('developer','command_line',['dev'])
        key = dev.post('/api/tokens', json={'name':'build','scopes':['observe']}).json()
        raw = key['token']
        with sqlite3.connect(self.db) as conn:
            self.assertNotEqual(conn.execute('SELECT hash FROM tokens').fetchone()[0],raw)
        conn.close()
        api = TestClient(self.app, headers={'X-SUAY-Request':'1','Authorization':'Bearer '+raw})
        self.assertEqual(api.get('/api/nodes').status_code,200)
        self.assertEqual(api.get('/api/users').status_code,403)
        self.assertEqual(api.post('/v1/chat/completions', json={'model':'test-model','messages':[{'role':'user','content':'hi'}]}).status_code,403)
        uid = next(u['id'] for u in self.client.get('/api/users').json() if u['username']=='developer')
        self.client.put(f'/api/users/{uid}', json={'role':'view_only','zones':[],'nodes':[]})
        self.assertEqual(api.get('/api/nodes').status_code,401)
        self.assertEqual(dev.get('/api/nodes').status_code,401)

    def test_expiry_revocation_and_password_reset(self):
        self.admin()
        key = self.client.post('/api/tokens', json={'name':'build','scopes':['observe']}).json()
        api = TestClient(self.app, headers={'Authorization':'Bearer '+key['token']})
        self.assertEqual(api.get('/api/nodes').status_code,200)
        self.client.delete('/api/tokens/'+str(key['id']))
        self.assertEqual(api.get('/api/nodes').status_code,401)
        key = self.client.post('/api/tokens', json={'name':'expired','scopes':['observe']}).json()
        with sqlite3.connect(self.db) as conn:
            conn.execute('UPDATE tokens SET expires=0 WHERE id=?',(key['id'],))
        conn.close()
        api.headers['Authorization']='Bearer '+key['token']
        self.assertEqual(api.get('/api/nodes').status_code,401)
        dev = self.add_user('developer','command_line')
        uid = next(u['id'] for u in self.client.get('/api/users').json() if u['username']=='developer')
        self.assertEqual(self.client.post(f'/api/users/{uid}/reset-password', json={'password':'AnotherTemp!123'}).status_code,200)
        self.assertEqual(dev.get('/api/nodes').status_code,401)
        dev.post('/api/login',json={'username':'developer','password':'AnotherTemp!123'})
        self.assertEqual(dev.get('/api/nodes').status_code,403)

    def test_inference_proxy_uses_configured_url_and_atomic_request_budget(self):
        self.admin()
        app = create_app(self.db, upstream='http://127.0.0.1:9000/v1/chat/completions', models=['test-model'])
        token = self.client.post('/api/tokens',json={'name':'ci','scopes':['inference'],'max_requests':1}).json()['token']
        api = TestClient(app,headers={'X-SUAY-Request':'1','Authorization':'Bearer '+token})
        async def fake_post(client, url, **kwargs):
            self.assertEqual(url,'http://127.0.0.1:9000/v1/chat/completions')
            self.assertNotIn('Authorization',kwargs['headers'])
            return httpx.Response(200,json={'choices':[{'message':{'content':'ok'}}], 'usage':{'total_tokens':7}})
        body = {'model':'test-model','messages':[{'role':'user','content':'hi'}]}
        with patch.object(httpx.AsyncClient,'post',new=fake_post):
            self.assertEqual(api.post('/v1/chat/completions',json=body).status_code,200)
            self.assertEqual(api.post('/v1/chat/completions',json=body).status_code,429)
        entry = self.client.get('/api/tokens').json()[0]
        self.assertEqual((entry['used'],entry['inference_tokens']),(1,7))

    def test_csrf_payload_size_and_login_throttle(self):
        self.assertEqual(TestClient(self.app).post('/api/login',json={'username':'admin','password':'x'}).status_code,403)
        self.assertEqual(self.client.post('/api/login',headers={'Origin':'https://evil.invalid'},json={'username':'admin','password':'x'}).status_code,403)
        self.assertEqual(self.client.post('/api/login',content='x'*65537).status_code,413)
        for _ in range(5):
            self.assertEqual(self.client.post('/api/login',json={'username':'admin','password':'bad'}).status_code,401)
        self.assertEqual(self.client.post('/api/login',json={'username':'admin','password':'suay1234'}).status_code,429)


if __name__ == '__main__':
    unittest.main()
