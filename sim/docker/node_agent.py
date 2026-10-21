"""One simulated machine.

Two jobs, standard library only:

1. Heartbeat to the hub every SUAY_HEARTBEAT_S seconds (with jitter) and report its own IP so the hub can
   address it directly.
2. Serve a tiny work endpoint on SUAY_WORK_PORT. The hub calls it on every inference request, so the
   visualisation sees a real dispatch and a real round-trip instead of decorative animation.
"""
import json
import os
import random
import socket
import threading
import time
import urllib.error
import urllib.request
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HUB = os.getenv('SUAY_HUB', 'http://hub:8080')
PLANE = os.getenv('SUAY_PLANE', '')          # e.g. http://nodeplane:8081 — preferred when set
KEY = os.getenv('SUAY_SWARM_KEY', 'sim-swarm-key')
ZONE = os.getenv('SUAY_ZONE', 'sim-zone')
NODE = os.getenv('SUAY_NODE_ID') or socket.gethostname()
INTERVAL = float(os.getenv('SUAY_HEARTBEAT_S', '10' if PLANE else '2'))
WORK_PORT = int(os.getenv('SUAY_WORK_PORT', '9100'))


def local_ip():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(('10.255.255.255', 1))
        return probe.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        probe.close()


IP = local_ip()


def process_chunk(text, rounds):
    """Deterministic, verifiable work: tokenise, count, then mix the digest `rounds` times."""
    words = text.split()
    digest = hashlib.sha256(text.encode()).digest()
    for _ in range(max(0, rounds)):
        digest = hashlib.sha256(digest).digest()
    return {'words': len(words), 'chars': len(text), 'sum_len': sum(len(word) for word in words),
            'digest': digest.hex()}


class WorkHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _reply(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get('content-length', '0') or 0)
        raw = self.rfile.read(length) if length else b'{}'
        try:
            payload = json.loads(raw or b'{}')
        except ValueError:
            payload = {}
        text = payload.get('text')
        if isinstance(text, str):
            result = process_chunk(text, int(payload.get('rounds', 200)))
            result.update({'ok': True, 'node': NODE, 'job': payload.get('job')})
            self._reply(result)
            return
        # Legacy warm-up path: a tiny fixed delay keeps old benchmarks comparable.
        time.sleep(0.004 + random.random() * 0.006)
        self._reply({'ok': True, 'node': NODE, 'job': payload.get('job')})

    def do_GET(self):
        self._reply({'ok': True, 'node': NODE, 'zone': ZONE})

    def log_message(self, *args):
        return


def serve():
    server = ThreadingHTTPServer(('0.0.0.0', WORK_PORT), WorkHandler)
    server.daemon_threads = True
    server.serve_forever()


def beat():
    body = json.dumps({'node_id': NODE, 'zone': ZONE, 'hostname': socket.gethostname(), 'ip': IP}).encode()
    if PLANE:
        url = PLANE.rstrip('/') + '/hb'
    else:
        url = HUB.rstrip('/') + '/api/node/heartbeat'
    request = urllib.request.Request(
        url, data=body, method='POST',
        headers={'Content-Type': 'application/json', 'X-SUAY-Request': '1', 'X-Swarm-Key': KEY})
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status


def main():
    threading.Thread(target=serve, daemon=True).start()
    print(f'node {NODE} ip {IP} -> {PLANE or HUB} every {INTERVAL}s, work on :{WORK_PORT}', flush=True)
    failures = 0
    while True:
        try:
            beat()
            failures = 0
        except (urllib.error.URLError, OSError) as exc:
            failures += 1
            if failures in (1, 10, 100):
                print(f'node {NODE} heartbeat failed ({failures}): {exc}', flush=True)
        time.sleep(INTERVAL * (0.85 + random.random() * 0.3))


if __name__ == '__main__':
    main()
