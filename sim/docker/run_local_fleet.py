"""Process-level fallback for the 50-machine simulation when Docker is unavailable.

Same topology as docker-compose.yml — one hub, one mock upstream, N node agents — but as local processes.

    python sim/docker/run_local_fleet.py --nodes 50 --port 8080
    python sim/docker/run_local_fleet.py --nodes 50 --benchmark      # runs loadgen + plot, then stops
    python sim/docker/run_local_fleet.py --nodes 50 --keep           # leaves the fleet running
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / 'results'


def wait_for(url, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.3)
    return False


def env_for(extra):
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([str(ROOT / 'versions' / 'python'), str(ROOT / 'sim'), str(HERE)])
    env.update(extra)
    return env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes', type=int, default=50)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--steps', default='1,5,10,25,50')
    parser.add_argument('--benchmark', action='store_true', help='run loadgen + plot before stopping')
    parser.add_argument('--keep', action='store_true', help='leave the fleet running')
    args = parser.parse_args()

    upstream_port = args.port + 1
    RESULTS.mkdir(parents=True, exist_ok=True)
    processes = []
    python = sys.executable

    upstream = subprocess.Popen(
        [python, '-m', 'uvicorn', 'mock_upstream:app', '--host', '127.0.0.1', '--port', str(upstream_port),
         '--log-level', 'warning'], cwd=HERE, env=env_for({}), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    processes.append(upstream)
    if not wait_for(f'http://127.0.0.1:{upstream_port}/healthz'):
        raise SystemExit('mock upstream did not start')

    hub = subprocess.Popen(
        [python, '-m', 'uvicorn', 'hub_app:app', '--host', '127.0.0.1', '--port', str(args.port),
         '--log-level', 'warning'], cwd=HERE,
        env=env_for({
            'SUAY_UPSTREAM': f'http://127.0.0.1:{upstream_port}/v1/chat/completions',
            'SUAY_SIM_DB': str(RESULTS / 'sim.sqlite3'),
        }), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    processes.append(hub)
    if not wait_for(f'http://127.0.0.1:{args.port}/logo.svg'):
        raise SystemExit('hub did not start')

    zones = ['floor-1', 'floor-2', 'floor-3']
    for index in range(args.nodes):
        processes.append(subprocess.Popen(
            [python, str(HERE / 'node_agent.py')], cwd=HERE,
            env=env_for({
                'SUAY_HUB': f'http://127.0.0.1:{args.port}',
                'SUAY_NODE_ID': f'node-{index:02d}',
                'SUAY_ZONE': zones[index % len(zones)],
                'SUAY_HEARTBEAT_S': '2',
            }), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))

    print(f'fleet: {args.nodes} node processes against http://127.0.0.1:{args.port}', flush=True)
    deadline = time.time() + 40
    live = 0
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/sim/stats', timeout=3) as response:
                live = json.loads(response.read())['nodes_live']
            if live >= args.nodes:
                break
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(0.5)
    print(f'nodes_live={live}', flush=True)

    try:
        if args.benchmark:
            subprocess.run([python, str(HERE / 'loadgen.py'), '--base', f'http://127.0.0.1:{args.port}',
                            '--key', 'suay_sim_loadgen_key', '--steps', args.steps,
                            '--seconds', str(args.seconds), '--out', str(RESULTS)], check=True)
            subprocess.run([python, str(HERE / 'plot.py'), '--results', str(RESULTS)], check=True)
        if args.keep:
            print('fleet running; press Ctrl+C to stop', flush=True)
            while True:
                time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        print('fleet stopped', flush=True)


if __name__ == '__main__':
    main()
