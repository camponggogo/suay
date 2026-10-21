"""Start (or stop) N single-worker gateways on consecutive ports for the multi-port scaling study.

    python sim/gateway/scale_ports.py up --count 8 --base-port 8100
    python sim/gateway/scale_ports.py down --count 8 --base-port 8100
"""
import argparse
import subprocess

IMAGE = 'suay-sim-hub:latest'
NETWORK = 'suay-sim_default'
ENV = [
    'SUAY_UPSTREAM=http://upstream:9000/v1/chat/completions',
    'SUAY_SIM_MODELS=sim-model',
    'SUAY_SWARM_KEY=sim-swarm-key',
    'SUAY_SIM_KEY=suay_sim_loadgen_key',
    'SUAY_SIM_DB=/data/sim.sqlite3',
    'SUAY_NODE_PLANE=http://nodeplane:8081',
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['up', 'down'])
    parser.add_argument('--count', type=int, default=8)
    parser.add_argument('--base-port', type=int, default=8100)
    args = parser.parse_args()

    for index in range(args.count):
        name = f'suay-gw-{index}'
        if args.action == 'down':
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True)
            continue
        command = ['docker', 'run', '-d', '--name', name,
                   '--network', NETWORK,
                   '-p', f'{args.base_port + index}:8080']
        for item in ENV:
            command += ['-e', item]
        command += ['-v', 'suay-sim_hub-data:/data', IMAGE,
                    'uvicorn', 'hub_app:app', '--host', '0.0.0.0', '--port', '8080',
                    '--log-level', 'warning', '--workers', '1']
        result = subprocess.run(command, capture_output=True, text=True)
        status = 'ok' if result.returncode == 0 else result.stderr.strip()[:120]
        print(name, args.base_port + index, status)


if __name__ == '__main__':
    main()
