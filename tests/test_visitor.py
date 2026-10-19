from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'versions/python'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from visitor_analytics.app import create_app
from visitor_analytics.credentials import load, save


class VisitorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.directory=Path(self.temp.name)
        save(self.directory/'private','admin','Initial-test-password',must_change=False)
        root=FastAPI();root.mount('/projects/suay/visitor-api',create_app(self.directory))
        self.client=TestClient(root,base_url='https://campong.online',headers={'Origin':'https://campong.online','X-SUAY-Metrics':'1'})
        self.base='/projects/suay/visitor-api/'
    def tearDown(self):
        self.client.close();self.temp.cleanup()
    def login(self):
        self.assertEqual(self.client.post(self.base+'login',json={'username':'admin','password':'Initial-test-password'}).status_code,200)
    def batch(self,events,view='00000000-0000-4000-8000-000000000001',**changes):
        data=dict(consent=True,view=view,page='en',device='desktop',events=events);data.update(changes)
        return self.client.post(self.base+'events',json=data)
    def test_no_consent_no_report_and_no_arbitrary_fields(self):
        self.assertEqual(self.client.get(self.base+'report').status_code,401)
        self.assertEqual(self.batch([{'kind':'view'}],consent=False).status_code,422)
        self.assertEqual(self.batch([{'kind':'keypress','target':'secret'}]).status_code,422)
        self.assertEqual(self.batch([{'kind':'click','x':20}]).status_code,422)
        self.assertEqual(self.client.post(self.base+'events',json={},headers={'Origin':'https://evil.invalid'}).status_code,403)
    def test_ctr_deduplicates_loads_and_heat_is_quantized(self):
        self.login()
        for _ in range(2):self.assertEqual(self.batch([{'kind':'link','target':'star'},{'kind':'scroll','value':76},{'kind':'click','x':3,'y':7}]).status_code,200)
        self.batch([{'kind':'view'}],view='00000000-0000-4000-8000-000000000002')
        report=self.client.get(self.base+'report').json()
        self.assertEqual(report['views'],2)
        self.assertEqual(report['links'][0]['clicks'],2)
        self.assertEqual(report['links'][0]['ctr'],50)
        self.assertEqual(report['scroll']['75'],1)
        self.assertEqual(report['scroll']['100'],0)
        self.assertEqual(report['heat'][0]['n'],2)
    def test_encrypted_username_rotation_and_feedback_once(self):
        self.assertNotIn('admin',(self.directory/'private/.env').read_text())
        self.assertEqual(load(self.directory/'private')[0],'admin')
        self.login()
        self.batch([{'kind':'feedback','value':5,'intent':'try'}])
        self.batch([{'kind':'feedback','value':1,'intent':'read'}])
        self.assertEqual(self.client.get(self.base+'report').json()['feedback']['responses'],1)
        self.assertEqual(self.client.post(self.base+'password',json={'current_password':'Initial-test-password','new_password':'New-password-for-test'}).status_code,200)
        self.assertEqual(self.client.get(self.base+'report').status_code,401)
    def test_filters_and_retention(self):
        self.login();self.batch([{'kind':'view'}],page='ja',device='mobile')
        self.assertEqual(self.client.get(self.base+'report?page=en').json()['views'],0)
        self.assertEqual(self.client.get(self.base+'report?page=ja&device=mobile').json()['views'],1)
        conn=sqlite3.connect(self.directory/'metrics.sqlite3');conn.execute("UPDATE views SET day='2000-01-01'");conn.commit();conn.close()
        self.batch([{'kind':'view'}],view='00000000-0000-4000-8000-000000000002')
        self.assertEqual(self.client.get(self.base+'report?days=90').json()['views'],1)

if __name__=='__main__':unittest.main()
