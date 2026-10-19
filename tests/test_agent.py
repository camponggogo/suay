import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('agent', ROOT / 'versions' / 'python' / 'compute' / 'agent' / 'auto_agent.py')
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

class ElectionTests(unittest.TestCase):
    def message(self, **kwargs):
        return dict(type='node', model='test', peers=[], ram=4, **kwargs)

    def test_simultaneous_start_converges_regardless_of_arrival_order(self):
        for ips in [('10.0.0.10','10.0.0.2'), ('10.0.0.2','10.0.0.10')]:
            registry = agent.Registry(ips[0], 'test')
            for ip in ips:
                registry.update(self.message(), ip, now=0)
            self.assertEqual(registry.leader(now=1), '10.0.0.2')

    def test_expired_leader_fails_over_and_self_is_not_demoted(self):
        registry = agent.Registry('10.0.0.2', 'test')
        registry.update(self.message(), '10.0.0.1', now=0)
        registry.update(self.message(), '10.0.0.2', now=7)
        self.assertEqual(registry.leader(now=8), '10.0.0.2')
        self.assertEqual(len(registry.active(now=8)), 1)

    def test_rejects_other_model_and_malformed_peer(self):
        registry = agent.Registry('10.0.0.1', 'test')
        self.assertFalse(registry.update(dict(type='node', model='other'), '10.0.0.2'))
        message = self.message()
        message['peers'] = ['/ip4/10.0.0.3/tcp/31337/p2p/x']
        self.assertFalse(registry.update(message, '10.0.0.2'))
        self.assertFalse(registry.update([], '10.0.0.2'))

if __name__ == '__main__':
    unittest.main()
