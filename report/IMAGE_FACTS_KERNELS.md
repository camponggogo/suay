# Image facts — kernels and router figures

บันทึกเพิ่มเติมก่อนภาพ `fig10_router_confusion.png` และ `fig01_pasadhi_kernels.png` ถูกแทนที่

## fig10_router_confusion.png — expert router (PASADHI)

- 6 000 คำถาม · ความแม่นรวม **90.15 %**
- clear 100 % · ambiguous 100 % · adversarial **50.75 %** (กับดัก substring)
- confusion matrix (จริง→ทำนาย): legal 2 114/2 043 · chemistry 1 795/1 793 · finance 1 500/1 497
- ที่มา: `report/EXPERTS_WHITEPAPER.md`, `report/experts/results.json`

## fig01_pasadhi_kernels.png — PASADHI M0 kernels (i7-8550U)

- f32 ผ่าน BLAS: **58–74 GFLOP/s** · tiled 128: 7–11 · numpy int8: **1.2**
- int8 relative error 1.0–1.1 %
- thread scaling (n=1024): 1 → 38.1 · 2 → 59.0 · **4 → 83.3** · 8 → 78.4 GFLOP/s
- multi-layer pipeline แพ้ single loop **0.26–0.55×** (payload 256 KB ต่อ hop)
- ที่มา: `pasadhi/docs/ARCHITECTURE.md`, `pasadhi/bench/results/summary.json`
