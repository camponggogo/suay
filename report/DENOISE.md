# Denoising the latency measurements: four methods compared

**Method note · 2026-10-21** · figures: `report/denoise/figures/` (white, 300 dpi)
Code: `sim/denoise/bench.py`, `sim/denoise/plots.py` · data: `report/denoise/{series.npz,metrics.json}`

## 1. Signal and reference

Input: **963 request latencies** from the 50-machine run (`sim/docker/results/paper/latency.csv`), in acquisition
order, grouped into ten load steps (C = 1 … 50). The signal is heavy-tailed and non-stationary *inside* each
step — the queue warms up, so latency ramps before it plateaus.

Reference: the **per-step median**, repeated. It is the blunt but honest "true level" a stationary system would
show. The gap between raw data and reference inside a step is therefore partly real drift, not noise — which
matters for interpreting every score below.

## 2. Methods (as requested)

| Method | Implementation | Hyper-parameters |
|---|---|---|
| **Savitzky–Golay** | `scipy.signal.savgol_filter` | window 31, polynomial order 3 |
| **Savitzky–Golay in log space** | filter `log(y)`, exponentiate | same |
| **PyWavelets** | `pywt.wavedec` + soft threshold, universal threshold `σ√(2 ln n)`, σ from MAD | db4, level 3 |
| **TabDAE** | PyTorch denoising autoencoder over sliding windows (9 → 24 → 12 → 24 → 9), trained 400 epochs on noisy copies (σ = 0.35 of robust scale), overlapping windows averaged back | window 9, Adam 0.02 |
| **DeepFilterNet-style gate** | STFT magnitude, per-band noise floor at the 20th percentile, Wiener gain `SNR/(1+SNR)`, inverse STFT — the *idea* of DeepFilterNet applied to a 1-D series; **no pretrained weights**, since DeepFilterNet is a 48 kHz speech model | nperseg 63, 87.5 % overlap |

DeepFilterNet is included for completeness of the comparison, not because an audio model is expected to win on
tabular latency. The equivalent tabular idea is the autoencoder, and the equivalent 1-D frequency idea is the
spectral gate; both are measured honestly.

## 3. Results

| Method | RMSE (ms) | SNR gain (dB) | Edge RMSE (ms) | Smoothness |
|---|---:|---:|---:|---:|
| raw (no filter) | 629.0 | 0.00 | 605.3 | 61.5 |
| **Savitzky–Golay** | **551.0** | **+1.15** | 542.2 | **35.5** |
| Savitzky–Golay (log) | 549.7 | +1.17 | 650.0 | 35.7 |
| Median filter (15) | 612.8 | +0.23 | **557.1** | 38.7 |
| Wavelet (db4, soft) | 619.6 | +0.13 | 599.7 | 54.5 |
| TabDAE (window 9) | 592.7 | +0.52 | 558.6 | 42.6 |
| DeepFilterNet-style gate | 642.8 | −0.19 | 674.1 | 58.0 |

![Overlay](figures/fig34_denoise_overlay.png)

**Figure 34.** Raw series, the per-step reference, and four denoisers. All methods follow the ramp inside a step
and lag the step edges; the reference itself is a step, so part of every residual is genuine drift, not noise.

![Metrics](figures/fig35_denoise_metrics.png)

**Figure 35.** RMSE, SNR gain and edge RMSE per method (dashed red line = raw RMSE in the first panel).

## 4. What the numbers say

1. **Savitzky–Golay wins on RMSE and smoothness** (551 ms vs 629 raw, +1.15 dB). It is the right choice for a
   *visualisation* of the trend.
2. **Log-space helps RMSE a hair but hurts edges** (650 ms at step boundaries vs 542). Log compresses peaks, so
   a sudden jump becomes a longer, softer ramp — bad if the step itself is the finding.
3. **Median filtering is the edge-preserving option** (edge 557, best of all) at the cost of RMSE.
4. **TabDAE lands in the middle** (+0.52 dB). Trained on 963 windows it cannot learn much; it is a proof of
   method, not a tuned model.
5. **Wavelet soft-thresholding barely moves** (+0.13 dB): the noise is not Gaussian and not spread across
   scales, so thresholding small coefficients removes signal detail as often as noise.
6. **The spectral gate makes it worse** (−0.19 dB). A latency series has no meaningful stationary spectrum;
   Wiener gains computed on non-stationary bands inject ringing around edges.

**Why every gain is small:** 1.15 dB is roughly a 12 % RMSE reduction. Denoising cannot remove the largest
component of the variance — queue growth within a 10 s step — because that component is signal, not noise. The
honest fix for a paper is not filtering: it is **more samples per load level and robust statistics** (median +
bootstrap CI), which we already do when reporting p50/p95.

## 5. Recommendation for the white paper

| Purpose | Use | Do not use |
|---|---|---|
| Plotting the trend | Savitzky–Golay (31, 3) on the raw series, stated in the caption | the filtered series as a metric |
| Reported percentiles | raw samples, per-step median + bootstrap CI | any filter |
| Step-change detection | median filter or SG with a narrow window | log-space SG, spectral gate |
| Learned denoising | only with ≥10⁴ samples per level | TabDAE at 963 samples |

## 6. Threats

- The reference is a per-step median; it penalises filters for tracking real within-step drift.
- Only one acquisition order; a shuffled order would change the edge scores.
- TabDAE was not tuned (architecture, noise level, epochs) and was trained on the same series it filters, so it
  is optimistically biased, not conservative.
- The spectral gate uses no pretrained model; DeepFilterNet proper would need audio, which this signal is not.
