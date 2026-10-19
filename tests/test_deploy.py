import unittest

from deploy.deploy_landing import INCLUDE, add_include


class DeploymentConfigTests(unittest.TestCase):
    def test_adds_only_to_exact_https_server_and_is_idempotent(self):
        original = '''server {
    listen 80;
    server_name campong.online www.campong.online;
    return 301 https://campong.online$request_uri;
}
server {
    listen 443 ssl;
    server_name www.campong.online;
    return 301 https://campong.online$request_uri;
}
server {
    listen 443 ssl;
    server_name campong.online;
    location / { proxy_pass http://127.0.0.1:9499; }
    location /projects/existing/ { proxy_pass http://127.0.0.1:8500; }
}
'''
        changed = add_include(original)
        self.assertEqual(changed.count(INCLUDE), 1)
        self.assertEqual(changed.replace(INCLUDE+'\n', ''), original)
        self.assertEqual(add_include(changed), changed)
        self.assertGreater(changed.index(INCLUDE), changed.index('server_name campong.online;'))

    def test_rejects_unexpected_or_conflicting_configuration(self):
        for config in ['server { listen 443; server_name other.example; }',
                       'server {\n    server_name campong.online;\n}',
                       'server { listen 443;\n    server_name campong.online;\n location /projects/suay/ {}\n}']:
            with self.assertRaises(ValueError):
                add_include(config)
