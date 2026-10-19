"""LAN discovery, deterministic election and supervised Petals workers."""
import ipaddress
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = logging.getLogger(__name__)
MODEL = os.getenv('MODEL_NAME', 'bigscience/bloom-560m')
PORT = int(os.getenv('DISCOVERY_PORT', '31338'))
HTTP_PORT = int(os.getenv('DASHBOARD_PORT', '8080'))
TIMEOUT = 8


def local_ip():
    override = os.getenv('NODE_IP')
    if override:
        return str(ipaddress.IPv4Address(override))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(('10.255.255.255', 1))
        return sock.getsockname()[0]


class Registry:
    def __init__(self, own_ip, model=MODEL):
        self.own_ip, self.model = own_ip, model
        self.nodes = {}
        self.lock = threading.RLock()

    def update(self, message, source, now=None):
        if not isinstance(message, dict) or message.get('type') != 'node' or message.get('model') != self.model:
            return False
        ipaddress.IPv4Address(source)
        peers = message.get('peers', [])
        if not isinstance(peers, list) or len(peers) > 16 or not all(isinstance(p, str) and p.startswith('/ip4/' + source + '/') and '/p2p/' in p for p in peers):
            return False
        ram = message.get('ram', 0)
        if isinstance(ram, bool) or not isinstance(ram, (int, float)) or not 0 <= ram <= 1e6:
            return False
        with self.lock:
            self.nodes[source] = dict(message, seen=time.monotonic() if now is None else now)
        return True

    def active(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            return {ip: dict(node) for ip, node in self.nodes.items() if now - node['seen'] < TIMEOUT}

    def leader(self, now=None):
        return min(self.active(now), key=lambda ip: int(ipaddress.IPv4Address(ip)), default=None)


class Agent:
    def __init__(self):
        self.ip = local_ip()
        self.registry = Registry(self.ip)
        self.stop = threading.Event()
        self.process = None
        self.dht = None
        self.peers = []
        self.last_start = 0
        self.http = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', PORT))
        self.sock.settimeout(1)

    def heartbeat(self):
        import psutil
        message = dict(type='node', model=MODEL, peers=self.peers,
                       ram=round(psutil.virtual_memory().total / 1024**3, 2),
                       process_running=self.process is not None and self.process.poll() is None)
        self.registry.update(message, self.ip)
        return message

    def status(self):
        nodes = self.registry.active()
        leader = self.registry.leader()
        return dict(total_nodes=len(nodes), total_ram=round(sum(n['ram'] for n in nodes.values()), 2),
                    coordinator_ip=leader, current_model=MODEL, node_ip=self.ip,
                    role='COORDINATOR' if leader == self.ip else 'WORKER',
                    initial_peers=[p for n in nodes.values() for p in n['peers']],
                    running_processes=sum(bool(n.get('process_running')) for n in nodes.values()),
                    readiness='Process status only; model block coverage is not verified')

    def receive(self):
        while not self.stop.is_set():
            try:
                raw, addr = self.sock.recvfrom(8192)
                message = json.loads(raw)
                if isinstance(message, dict) and message.get('type') == 'discover':
                    self.sock.sendto(json.dumps(dict(type='discovery', api_port=HTTP_PORT)).encode(), addr)
                else:
                    self.registry.update(message, addr[0])
            except socket.timeout:
                continue
            except (ValueError, TypeError, OSError):
                if not self.stop.is_set():
                    LOG.debug('Ignored invalid discovery packet', exc_info=True)

    def start_dht(self):
        from hivemind import DHT
        peers = [p for ip, n in self.registry.active().items() if ip != self.ip for p in n['peers']]
        # A dedicated bootstrap node stays alive across coordinator changes.
        self.dht = DHT(initial_peers=peers, host_maddrs=['/ip4/0.0.0.0/tcp/31337'],
                       announce_maddrs=[f'/ip4/{self.ip}/tcp/31337'], start=True)
        self.peers = [str(p) for p in self.dht.get_visible_maddrs()]

    def supervise(self):
        if self.process is not None and self.process.poll() is None:
            return
        if time.monotonic() - self.last_start < 30:
            return
        self.last_start = time.monotonic()
        if self.process is not None:
            LOG.error('Petals exited with code %s; restarting', self.process.returncode)
        cmd = [sys.executable, '-m', 'petals.cli.run_server', MODEL,
               '--num_blocks', os.getenv('NUM_BLOCKS', '2'), '--port', '31339',
               '--device', os.getenv('PETALS_DEVICE', 'cpu'), '--initial_peers', *self.peers]
        self.process = subprocess.Popen(cmd)

    def run(self):
        agent = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/api/status':
                    payload = json.dumps(agent.status()).encode()
                    content_type = 'application/json'
                elif self.path == '/':
                    payload = Path(__file__).with_name('dashboard.html').read_bytes()
                    content_type = 'text/html; charset=utf-8'
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):
                pass
        self.http = ThreadingHTTPServer(('', HTTP_PORT), Handler)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        threading.Thread(target=self.receive, daemon=True).start()
        started = time.monotonic()
        try:
            while not self.stop.is_set():
                self.sock.sendto(json.dumps(self.heartbeat()).encode(),
                                 (os.getenv('BROADCAST_ADDRESS', '255.255.255.255'), PORT))
                # Lowest live IPv4 starts first; followers wait for a bootstrap address.
                if not self.dht and time.monotonic() - started >= TIMEOUT:
                    nodes = self.registry.active()
                    if self.registry.leader() == self.ip or any(n['peers'] for n in nodes.values()):
                        try:
                            self.start_dht()
                        except Exception:
                            LOG.exception('DHT startup failed; retrying')
                            if self.dht:
                                self.dht.shutdown()
                            self.dht = None
                if self.dht:
                    self.supervise()
                self.stop.wait(2)
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            if self.dht:
                self.dht.shutdown()
            self.http.shutdown()
            self.http.server_close()
            self.sock.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    agent = Agent()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: agent.stop.set())
    agent.run()
