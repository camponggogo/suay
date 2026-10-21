"""Fleet model for the i3 / 8 GB / 120 GB profile, 50-100 machines.

Anchored on two measurements:
  * 11.74 tok/s generation for a 0.63B Q4 model on an i7-8550U (llama.cpp, this repository)
  * heartbeat ceiling ≈ 25 req/s per hub worker (sim/fleet/heartbeat_stress.json)

    python sim/fleet/model.py --out report/fleet
"""
import argparse
import json
from pathlib import Path

BASE_TPS = 11.74          # measured, 0.63B Q4, i7-8550U
BASE_PARAMS = 0.63
I3_FACTOR = 1.8           # 4C/4T at 3.6 GHz sustained vs 4C/8T at 1.8 GHz 15 W
ANSWER_STEPS = 150.0
GATEWAY_RPS = 10.2        # measured inference ceiling, single worker
HEARTBEAT_RPS = 25.0      # measured heartbeat saturation
HEARTBEAT_INTERVAL = 2.0

MODELS = [
    ('qwen2.5-0.5B Q4', 0.63, 0.45),
    ('qwen2.5-1.5B Q4', 1.54, 1.00),
    ('qwen2.5-3B Q4', 3.09, 2.00),
    ('llama-3.1-8B Q4', 8.03, 4.90),
]
CAP_BACKGROUND_GB = 1.5   # container limit while the employee keeps working
CAP_DEDICATED_GB = 4.0    # machine handed over for compute
FLEETS = [50, 60, 70, 80, 90, 100]


def per_node_tps(params):
    return round(BASE_TPS * I3_FACTOR * (BASE_PARAMS / params), 2)


def nodes_per_copy(size_gb, cap_gb):
    usable = cap_gb - 0.35  # runtime overhead measured earlier
    return max(1, int(-(-size_gb // usable)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='report/fleet')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, params, size_gb in MODELS:
        tps = per_node_tps(params)
        for fleet in FLEETS:
            copies_bg = fleet // nodes_per_copy(size_gb, CAP_BACKGROUND_GB)
            copies_ded = fleet // nodes_per_copy(size_gb, CAP_DEDICATED_GB)
            capacity_bg = copies_bg * tps / ANSWER_STEPS
            capacity_ded = copies_ded * tps / ANSWER_STEPS
            rows.append({
                'model': name, 'params_b': params, 'size_gb': size_gb, 'tps_per_stream': tps,
                'nodes_per_copy_background': nodes_per_copy(size_gb, CAP_BACKGROUND_GB),
                'nodes_per_copy_dedicated': nodes_per_copy(size_gb, CAP_DEDICATED_GB),
                'fleet': fleet,
                'copies_background': copies_bg, 'capacity_background_rps': round(capacity_bg, 3),
                'capacity_dedicated_rps': round(capacity_ded, 3),
                'compute_bound_rps': round(capacity_ded, 3),
                'effective_rps': round(min(capacity_ded, GATEWAY_RPS), 3),
                'gateway_bound': capacity_ded > GATEWAY_RPS,
                'heartbeat_bound': fleet > HEARTBEAT_RPS * HEARTBEAT_INTERVAL,
                'disk_fits_120gb': size_gb <= 60,
            })

    stress_path = Path('report/fleet/heartbeat_stress.json')
    stress = json.loads(stress_path.read_text(encoding='utf-8')) if stress_path.exists() else {'sizes': []}

    summary = {
        'profile': {'cpu': 'Intel Core i3 (4C/4T, ~3.6 GHz)', 'ram_gb': 8, 'disk_gb': 120,
                    'container_cap_gb': CAP_BACKGROUND_GB, 'dedicated_cap_gb': CAP_DEDICATED_GB},
        'anchors': {'measured_tps_i7_0.63b': BASE_TPS, 'i3_factor': I3_FACTOR,
                    'gateway_ceiling_rps': GATEWAY_RPS, 'heartbeat_ceiling_rps': HEARTBEAT_RPS},
        'rows': rows,
        'heartbeat_stress': stress['sizes'],
    }
    (out / 'fleet_model.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    for name, params, size_gb in MODELS:
        sample = next(row for row in rows if row['model'] == name and row['fleet'] == 100)
        print(f"{name:20s} tps/stream {sample['tps_per_stream']:6.2f}  "
              f"nodes/copy bg {sample['nodes_per_copy_background']:2d} ded {sample['nodes_per_copy_dedicated']:2d}  "
              f"rps@100 bg {sample['capacity_background_rps']:6.3f} ded {sample['capacity_dedicated_rps']:6.3f}")
    print('written', out / 'fleet_model.json')


if __name__ == '__main__':
    main()
