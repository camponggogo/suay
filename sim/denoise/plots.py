"""White-background figures for the denoising comparison."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

INK = '#1a1a1a'
MUTED = '#5a5a5a'
GRID = '#e3e3e3'
BLUE = '#1f4e79'
ORANGE = '#c55a11'
GREEN = '#2e7d32'
RED = '#b00020'
GREY = '#9a9a9a'


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor('white')
    ax.figure.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_color('#999999')
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_title(title, color=INK, fontsize=10.5, pad=10)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='report/denoise')
    parser.add_argument('--out', default='report/denoise/figures')
    args = parser.parse_args()
    data = np.load(Path(args.data) / 'series.npz')
    metrics = json.loads((Path(args.data) / 'metrics.json').read_text(encoding='utf-8'))['results']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    values = data['values']
    reference = data['reference']
    index = np.arange(len(values))

    # 1 — overlay
    fig, ax = plt.subplots(figsize=(11.0, 4.6), facecolor='white')
    style(ax, 'Measured latency per request and four denoisers (log scale)', 'request index (grouped by load step)',
          'latency (ms, log)')
    ax.plot(index, values, color=GREY, linewidth=0.7, alpha=0.75, label='raw measurements')
    ax.plot(index, reference, color=INK, linewidth=1.6, linestyle='--', label='reference (per-step median)')
    ax.plot(index, data['Savitzky–Golay'], color=BLUE, linewidth=1.5, label='Savitzky–Golay (31, 3)')
    ax.plot(index, data['TabDAE_(window_9)'], color=GREEN, linewidth=1.5, label='TabDAE (window 9)')
    ax.plot(index, data['Median_filter_(15)'], color=ORANGE, linewidth=1.5, label='Median filter (15)')
    ax.plot(index, data['Wavelet_(db4,_soft)'], color=RED, linewidth=1.2, linestyle=':', label='Wavelet (db4, soft)')
    ax.set_yscale('log')
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED, ncol=2)
    fig.tight_layout()
    fig.savefig(out / 'fig34_denoise_overlay.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 2 — metrics
    names = [name for name in metrics if name != 'raw (no filter)']
    short = {'Savitzky–Golay': 'S-G', 'Savitzky–Golay (log-space)': 'S-G log', 'Median filter (15)': 'Median',
             'Wavelet (db4, soft)': 'Wavelet', 'TabDAE (window 9)': 'TabDAE',
             'DeepFilterNet-style gate': 'DFN gate'}
    labels = [short.get(name, name) for name in names]
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.9), facecolor='white')
    for ax, key, title, unit in zip(axes, ('rmse', 'snr_gain_db', 'edge_rmse'),
                                    ('RMSE against reference', 'SNR gain', 'RMSE at step edges'),
                                    ('ms', 'dB', 'ms')):
        style(ax, title, 'method', unit)
        vals = [metrics[name][key] for name in names]
        colors = [GREEN if value == max(vals) and key == 'snr_gain_db' else BLUE for value in vals]
        bars = ax.bar(labels, vals, color=colors, width=0.6)
        for bar, value in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, value + (max(vals) * 0.02 if max(vals) > 0 else 0.05),
                    f'{value:.2f}', ha='center', fontsize=7, color=INK)
        ax.tick_params(axis='x', labelrotation=35)
        for tick in ax.get_xticklabels():
            tick.set_fontsize(7.5)
    axes[0].axhline(metrics['raw (no filter)']['rmse'], color=RED, linestyle='--', linewidth=1, label='raw')
    axes[0].legend(frameon=False, fontsize=7, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig35_denoise_metrics.png', facecolor='white', dpi=300)
    plt.close(fig)
    print('figures ->', out)


if __name__ == '__main__':
    main()
