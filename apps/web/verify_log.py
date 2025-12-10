import unittest
import os
import json
import shutil
import uuid
from app import app

class LogTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    def setUp(self):
        self.app = app.test_client()
        self.log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        self.log_file = os.path.join(self.log_dir, 'app.log')
        # ログファイルが存在しない場合は作成
        if not os.path.exists(self.log_file):
            open(self.log_file, 'a').close()

    def test_log_action(self):
        unique_action = f"test_action_{uuid.uuid4()}"
        response = self.app.post('/api/log_action', 
                                 data=json.dumps({'action': unique_action, 'details': {'foo': 'bar'}}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn('ACTION_LOG', content)
            self.assertIn(unique_action, content)

    def test_search_log(self):
        unique_query = f"test_query_{uuid.uuid4()}"
        # 検索リクエスト
        response = self.app.post('/search', data={'query': unique_query, 'search_mode': 'or'})
        self.assertEqual(response.status_code, 200)

        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn('ACCESS_LOG', content)
            self.assertIn(unique_query, content)
            self.assertIn('cpu_percent', content)

    def test_ip_address(self):
        # プロキシ経由のリクエストをシミュレーション
        headers = {'X-Forwarded-For': '192.168.1.100'}
        response = self.app.post('/api/log_action', 
                                 data=json.dumps({'action': 'ip_test'}),
                                 content_type='application/json',
                                 headers=headers)
        self.assertEqual(response.status_code, 200)

        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn('192.168.1.100', content)

    def test_cookie_identification(self):
        # 1. 初回リクエスト：Cookieなし -> Set-Cookieされるはず
        response1 = self.app.get('/')
        self.assertEqual(response1.status_code, 200)
        
        cookies = response1.headers.getlist('Set-Cookie')
        print(f"DEBUG: Set-Cookie headers: {cookies}")
        
        # user_id が設定されているか確認
        user_id_cookie = None
        for cookie in cookies:
            if 'user_id=' in cookie:
                user_id_cookie = cookie.split(';')[0].split('=')[1]
                break
        
        self.assertIsNotNone(user_id_cookie)
        
        # 2. 2回目リクエスト：Cookieあり -> 同じIDが維持され、Set-Cookieされない（または同じID）はず
        # test_clientでcookieを送信する
        self.app.set_cookie('localhost', 'user_id', user_id_cookie)
        response2 = self.app.get('/')
        self.assertEqual(response2.status_code, 200)
        
        # ログにこのUIDが記録されているか確認
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn(user_id_cookie, content)


if __name__ == '__main__':
    unittest.main()
