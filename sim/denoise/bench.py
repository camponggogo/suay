"""Denoise the measured latency series with four methods and score them against a piecewise-constant reference.

Reference: the per-concurrency median, repeated — i.e. the "true level" each request should have shown if the
system were stationary inside a load step. Metrics: RMSE, SNR improvement, edge error (samples within ±2 of a
step boundary) and smoothness (mean |first difference|).

    python sim/denoise/bench.py --csv sim/docker/results/paper/latency.csv --out report/denoise
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter, stft, istft
import pywt
import torch
import torch.nn as nn
from scipy.ndimage import median_filter

LEVELS = [1, 2, 4, 8, 12, 16, 24, 32, 40, 50]


def load_series(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    rows = [row for row in rows if row['status'] == '200']
    values = np.array([float(row['latency_ms']) for row in rows])
    levels = np.array([int(row['concurrency']) for row in rows])
    reference = np.zeros_like(values)
    for level in np.unique(levels):
        mask = levels == level
        reference[mask] = np.median(values[mask])
    boundaries = np.where(np.diff(levels) != 0)[0] + 1
    return values, levels, reference, boundaries


def savgol(values, window=31, order=3):
    if window % 2 == 0:
        window += 1
    return savgol_filter(values, window_length=window, polyorder=order, mode='interp')


def wavelet(values, wavelet='db4', level=3):
    coeffs = pywt.wavedec(values, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1] - np.median(coeffs[-1]))) / 0.6745
    threshold = sigma * math.sqrt(2 * math.log(len(values)))
    cleaned = [coeffs[0]] + [pywt.threshold(c, threshold, mode='soft') for c in coeffs[1:]]
    return pywt.waverec(cleaned, wavelet)[: len(values)]


class TabDAE(nn.Module):
    """Small denoising autoencoder over sliding windows of the tabular series."""

    def __init__(self, window=9, hidden=24):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(window, hidden), nn.ReLU(), nn.Linear(hidden, hidden // 2), nn.ReLU())
        self.decoder = nn.Sequential(nn.Linear(hidden // 2, hidden), nn.ReLU(), nn.Linear(hidden, window))

    def forward(self, x):
        return self.decoder(self.encoder(x))


def tabdae(values, window=9, epochs=400, noise=0.35, seed=0):
    torch.manual_seed(seed)
    scale = np.median(np.abs(values - np.median(values))) or 1.0
    series = (values - np.median(values)) / scale
    windows = np.stack([series[i:i + window] for i in range(len(series) - window + 1)])
    x = torch.tensor(windows, dtype=torch.float32)
    model = TabDAE(window=window)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.02)
    loss_fn = nn.MSELoss()
    for _ in range(epochs):
        noisy = x + noise * torch.randn_like(x)
        loss = loss_fn(model(noisy), x)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    model.eval()
    with torch.no_grad():
        out = model(x).numpy()
    # average overlapping windows back onto the timeline
    rebuilt = np.zeros(len(series))
    weight = np.zeros(len(series))
    for index in range(out.shape[0]):
        rebuilt[index:index + window] += out[index]
        weight[index:index + window] += 1
    rebuilt = rebuilt / np.maximum(weight, 1)
    return rebuilt * scale + np.median(values)


def spectral_gate(values, nperseg=63, floor_percentile=20):
    """DeepFilterNet-style idea (STFT magnitude, per-band noise floor, Wiener gain) without pretrained weights."""
    frequencies, times, spectrum = stft(values, nperseg=nperseg, noverlap=nperseg - 8)
    magnitude = np.abs(spectrum)
    noise = np.percentile(magnitude, floor_percentile, axis=1, keepdims=True)
    snr = (magnitude ** 2) / np.maximum(noise ** 2, 1e-9)
    gain = snr / (1.0 + snr)
    _, rebuilt = istft(spectrum * gain, nperseg=nperseg, noverlap=nperseg - 8)
    return np.real(rebuilt[: len(values)])


def score(estimate, reference, values, boundaries):
    error = estimate - reference
    rmse = float(np.sqrt(np.mean(error ** 2)))
    signal_power = float(np.mean(reference ** 2))
    noise_power = float(np.mean((values - reference) ** 2))
    residual_power = float(np.mean(error ** 2))
    snr_before = 10 * math.log10(signal_power / max(noise_power, 1e-9))
    snr_after = 10 * math.log10(signal_power / max(residual_power, 1e-9))
    mask = np.ones(len(values), dtype=bool)
    for boundary in boundaries:
        mask[max(0, boundary - 2): boundary + 2] = False
    edge = float(np.sqrt(np.mean(error[~mask] ** 2))) if (~mask).any() else 0.0
    inner = float(np.sqrt(np.mean(error[mask] ** 2))) if mask.any() else 0.0
    return {'rmse': round(rmse, 2), 'snr_before_db': round(snr_before, 2), 'snr_after_db': round(snr_after, 2),
            'snr_gain_db': round(snr_after - snr_before, 2), 'edge_rmse': round(edge, 2),
            'inner_rmse': round(inner, 2),
            'smoothness': round(float(np.mean(np.abs(np.diff(estimate)))), 2)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='sim/docker/results/paper/latency.csv')
    parser.add_argument('--out', default='report/denoise')
    args = parser.parse_args()
    values, levels, reference, boundaries = load_series(args.csv)

    estimates = {
        'raw (no filter)': values,
        'Savitzky–Golay': savgol(values),
        'Savitzky–Golay (log-space)': np.exp(savgol(np.log(values))),
        'Median filter (15)': median_filter(values, size=15),
        'Wavelet (db4, soft)': wavelet(values),
        'TabDAE (window 9)': tabdae(values),
        'DeepFilterNet-style gate': spectral_gate(values),
    }
    results = {name: score(est, reference, values, boundaries) for name, est in estimates.items()}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'series.npz', values=values, reference=reference,
                        **{name.replace(' ', '_'): est for name, est in estimates.items()})
    (out / 'metrics.json').write_text(json.dumps({'samples': len(values), 'results': results}, indent=2),
                                      encoding='utf-8')
    for name, row in results.items():
        print(f"{name:26s} rmse {row['rmse']:8.2f}  snr_gain {row['snr_gain_db']:6.2f} dB  "
              f"edge {row['edge_rmse']:8.2f}  smooth {row['smoothness']:7.2f}")


if __name__ == '__main__':
    main()
