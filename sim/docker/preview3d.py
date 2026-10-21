"""Render the 3D layout preview from the live topology, using the same geometry and camera as neural3d.js.

This is a *geometry preview* rendered with matplotlib — not a screenshot of the WebGL page. It exists because
headless Chrome in this environment renders the scene (161 draw calls) but does not composite the WebGL layer
into a screenshot. Open http://127.0.0.1:8080/neural for the real thing.

    python sim/docker/preview3d.py --out sim/docker/results/neural-3d-geometry.png
"""
import argparse
import math
from pathlib import Path

import httpx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np

ZONE_COLORS = ['#7c5cff', '#22d3ee', '#34d399', '#f472b6', '#fbbf24', '#60a5fa']
CAMERA_THETA = 0.65
CAMERA_PHI = 1.15
CAMERA_RADIUS = 12.4
FOV = 50.0


def layout(nodes, zones):
    grouped = {}
    for node in nodes:
        grouped.setdefault(node['zone'], []).append(node)
    placed = []
    for index, node in enumerate(nodes):
        zone_index = zones.index(node['zone']) if node['zone'] in zones else 0
        members = grouped[node['zone']]
        slot = [item['id'] for item in members].index(node['id'])
        count = len(members)
        shell = 2.7 + min(zone_index, 3) * 1.45
        seed = index * 0.618 + 0.17
        angle = (slot / count) * math.pi * 2 + zone_index * 0.7 + (seed % 0.18)
        wobble = (abs(math.sin(seed * 91.7)) % 1 - 0.5) * 0.55
        tilt = 0.5 + zone_index * 0.16
        placed.append({
            **node,
            'zone_index': zone_index,
            'color': ZONE_COLORS[zone_index % len(ZONE_COLORS)] if node['status'] == 'live' else '#fbbf24',
            'p': np.array([
                math.cos(angle) * shell,
                math.sin(angle + zone_index * 1.3) * tilt + (zone_index - 1) * 0.9 + wobble,
                math.sin(angle) * shell,
            ]),
        })
    return placed


def camera_basis():
    position = np.array([
        CAMERA_RADIUS * math.sin(CAMERA_PHI) * math.sin(CAMERA_THETA),
        CAMERA_RADIUS * math.cos(CAMERA_PHI),
        CAMERA_RADIUS * math.sin(CAMERA_PHI) * math.cos(CAMERA_THETA),
    ])
    forward = -position / np.linalg.norm(position)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    up_cam = np.cross(right, forward)
    return position, right, up_cam, forward


def project(points, width, height):
    position, right, up_cam, forward = camera_basis()
    relative = points - position
    depth = relative @ forward
    x = relative @ right
    y = relative @ up_cam
    scale = (height / 2) / math.tan(math.radians(FOV / 2))
    return (x / depth) * scale + width / 2, (y / depth) * scale + height / 2, depth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    parser.add_argument('--out', default='sim/docker/results/neural-3d-geometry.png')
    args = parser.parse_args()

    data = httpx.get(args.base.rstrip('/') + '/api/topology', timeout=20).json()
    zones = [zone['name'] for zone in data['zones']]
    nodes = layout(data['nodes'], zones)

    width, height = 1600, 1000
    figure = plt.figure(figsize=(width / 100, height / 100), dpi=100, facecolor='#05070f')
    axes = figure.add_axes([0, 0, 1, 1])
    axes.set_facecolor('#05070f')
    axes.set_xlim(0, width)
    axes.set_ylim(height, 0)
    axes.axis('off')

    for radius, alpha in ((46, 0.05), (92, 0.04), (138, 0.03), (184, 0.02)):
        circle = plt.Circle((width / 2, height / 2), radius, color='#7c5cff', fill=False,
                            linewidth=1, alpha=alpha)
        axes.add_patch(circle)

    hub_glow = plt.Circle((width / 2, height / 2), 70, color='#7c5cff', alpha=0.10)
    axes.add_patch(hub_glow)
    axes.add_patch(plt.Circle((width / 2, height / 2), 34, color='#7c5cff', alpha=0.20))
    axes.add_patch(plt.Circle((width / 2, height / 2), 9, color='#ded4ff', alpha=0.95))

    segments, colors = [], []
    for node in nodes:
        start = project(np.array([[0.0, 0.0, 0.0]]), width, height)
        end = project(node['p'][None, :], width, height)
        segments.append([(float(start[0][0]), float(start[1][0])), (float(end[0][0]), float(end[1][0]))])
        colors.append(node['color'])
    axes.add_collection(LineCollection(segments, colors=colors, linewidths=1.2,
                                      linestyles=(0, (4, 5)), alpha=0.55))

    order = sorted(nodes, key=lambda item: -project(item['p'][None, :], width, height)[2][0])
    for node in order:
        x, y, depth = project(node['p'][None, :], width, height)
        fade = float(np.clip(1.25 - float(depth[0]) / 22, 0.35, 1.0))
        for size, alpha in ((120, 0.10), (60, 0.20), (20, 0.95)):
            axes.scatter([x[0]], [y[0]], s=size, color=node['color'], alpha=alpha * fade,
                         linewidths=0, zorder=3)
        axes.scatter([x[0]], [y[0]], s=7, color='#f4f0ff', alpha=0.95 * fade, linewidths=0, zorder=4)

    axes.text(width / 2, height / 2 + 62, 'SUAY CORE', color='#e9edff', alpha=0.55,
              ha='center', va='center', fontsize=9)
    for zone, index in zip(zones, range(len(zones))):
        axes.text(60, 60 + index * 22, f'■ {zone}', color=ZONE_COLORS[index % len(ZONE_COLORS)],
                  fontsize=10, ha='left', alpha=0.85)
    axes.text(width - 40, height - 34, f"{data['stats']['nodes_live']}/{len(nodes)} live · geometry preview",
              color='#7f88ad', fontsize=10, ha='right')

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, facecolor='#05070f')
    print('wrote', target)


if __name__ == '__main__':
    main()
