# Image facts — model figures (cost, GPU fleet, hetero, tokens, orbit)

บันทึกก่อนภาพชุดนี้ถูกแทนที่ด้วย placeholder ตัวเลขทั้งหมดมาจาก script ที่ยังอยู่ใน repo

## fig01_cost_per_tflop.png — ต้นทุนต่อ TFLOP

- PASADHI node (duty 60 %) **฿0.016** · cloud CPU (4 vCPU) ฿0.028 · cloud GPU (1× A100) ฿0.001
- สรุป: ชนะ cloud CPU **1.8×** แต่แพ้ A100 **17×**
- สมมติฐาน: เครื่อง ฿12,000 / 36 เดือน · 45 W · ฿4.2/kWh · 74 GFLOP/s · FX 36
- ที่มา: `pasadhi/commercial/pricing.py`, `commercial/results/pricing.json`

## fig02_gpu_fleet.png — 1 000 × GTX 1050 2 GB

- independent: **1.30 PFLOPS f32** · **2.60 POPS int8**
- sharded 1 GbE: 0.16 PFLOPS (8.5 %) · 10 GbE: 0.89 PFLOPS (48 %) · int8 10 GbE: 2.41 POPS (64.9 %)
- crossover n: f32 1 GbE ≈ 177 484 · f32 10 GbE 17 748 · int8 1 GbE 88 647 · int8 10 GbE 8 865
- VRAM: f32 square 15 543 · int8 31 086
- ต้นทุน **฿0.0003/TFLOP-ชม.** → ฿0.0010 ที่ margin 70 %
- ที่มา: `pasadhi/core/gpu.py`, `bench/results/gpu_model.json`

## fig03_hetero_fleet.png — 1 450 การ์ด 5 รุ่น

- คลัง: 1 000 × 1050, 200 × T4, 200 × 3060, 40 × 4090, 10 × A100
- **9.54 PFLOPS f32 · 47.7 POPS int8 · 143.5 kW · 8.9 TB VRAM · 66.5 GFLOP/W**
- mixed makespan **13.19 s** เท่ากันทุก policy (งาน 35 GB 2 % ทำให้ A100 ทำงาน 92 %)
- no_huge: best_fit **0.38 s** · fastest 0.45 · worst_fit **7.31 s**
- ทุน ฿22.6 M · **฿0.00007/TFLOP**
- ที่มา: `pasadhi/core/hetero.py`, `bench/results/hetero_model.json`

## fig04_token_economy.png — layer 10/40/50

- รายได้รวม **฿3,394,450/เดือน** (standard 864,200 + premium 2,530,250)
- credit ออก 391,500 (11.5 %) · ต้นทุนเครื่อง 798,950 · opex 160,000
- กำไร **฿2,044,000 (68.1 %)** · reserve 10 % = 204,400
- stress 720 ชม./เครื่อง → credit 2,349,000 ติดเพดาน 1,697,225 → margin **43.5 %**
- ที่มา: `pasadhi/commercial/token_model.py`, `commercial/results/token_model.json`

## fig05_orbit.png — link budget

| link | RTT | GEMM 4096³ | batch 10 นาที | งานสั้นสุดที่ 90 % |
|---|---:|---:|---:|---:|
| Earth fibre | 196 ms | 6.9 % | 100 % | 2 s |
| LEO 550 km | 31 ms | 32.3 % | 100 % | <1 s |
| GEO | 518 ms | 2.8 % | 99.9 % | 5 s |
| Moon | 2.56 s | 0.57 % | 99.6 % | 23 s |
| Mars ใกล้ | 364 s | 0.004 % | 62.2 % | 3 278 s |
| Mars ไกล | 2 675 s | 0.0005 % | 18.3 % | 24 077 s |

- ที่มา: `pasadhi/core/orbit.py`, `bench/results/orbit_model.json`

## ภาพที่ไม่มี path (1 ภาพ)

เป็นภาพหน้าจอจากแชท ไม่ได้เก็บไฟล์ไว้ — ถ้าเป็นภาพสรุปยอด จะตรงกับ `pasadhi/web/anatomy/pasadhi-system.png`
(4 platform: app/gateway/pool/storage + % แดง 30/88.7/96.5/98/42) หรือ `pasadhi/app/ui-screenshot.png`
(worker score 18.2, ฿711→1,189/เดือน) ซึ่งบันทึกไว้ใน `report/IMAGE_FACTS_UI.md` แล้ว
