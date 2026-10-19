import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('client', Path(__file__).resolve().parents[1] / 'versions' / 'python' / 'compute' / 'client' / 'app.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)

class ClientTests(unittest.TestCase):
    def test_reads_status_endpoint_and_rejects_unready_swarm(self):
        payload = {'current_model': 'test', 'initial_peers': ['peer']}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/api/status':
                    self.send_error(404)
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/'
            self.assertEqual(client.fetch_status(url), payload)
            payload['initial_peers'] = []
            with self.assertRaises(RuntimeError):
                client.fetch_status(url)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
