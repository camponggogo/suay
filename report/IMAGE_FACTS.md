# ข้อเท็จจริงของภาพที่ถูกแทนที่ (image facts ledger)

บันทึกไว้ก่อนภาพชุด fig37–fig41 และหน้า proof ของ white paper จะถูกแทนที่ด้วย placeholder
ข้อมูลดิบยังอยู่ที่ `report/**/*.json`, `report/*.md` และ `paper/SUAY-whitepaper.pdf`

## fig37_growth_laws.png — growth laws

- N+1 กับ N·log₂N ตันที่เพดานเดียวกัน **15.7 req/s**
- base 100: N+1 = 101 เครื่อง (7.78 rps) · N·log₂N = 664 เครื่อง (15.70 rps)
- base 500: 501 เครื่อง (15.70) · 4,483 เครื่อง (15.70)
- dispatch RTT: 48 ms (N+1 @100) เทียบ 274 ms (N·log₂N @100)
- ที่มา: `report/GROWTH_MODEL.md`, `report/growth/growth.json`

## fig38_complexity_classes.png — 8 complexity classes

- class: O(1), O(log n), O(n), O(2n), O(n log n), O(n²), O(cⁿ), O(nⁿ) — normalize ที่ 50 เครื่องตอน n=50
- **319 เครื่อง** คือจำนวนที่ถึงเพดาน 15.70 rps
- ต้นทุนต่อ 1M token: **฿1.77 → ฿88.66**; dispatch 160 → 8,008 ms
- O(1) 5.94 rps · O(log n) 7.34 rps (ไปไม่ถึงเพดาน)
- ที่มา: `report/GROWTH_MODEL.md`, `report/growth/complexity_classes.json`

## fig39_rps_ceiling.png — gateway throughput

- 1 worker: 15.0 (C=8) / 15.7 (C=16)
- 2 workers: **22.3 / 24.8**
- 4 workers: 29.1 (C=8) / 23.7 (C=16) / 20.5 (C=32)
- raw loop (health/models): **58.7–71.2 rps** — เพดานของ loop เปล่า
- ที่มา: `report/RPS_LIMIT.md`, `sim/docker/results/{best2,w2b,w4b}`

## fig40_multiport.png — multi-port transport

- 1 port 1 worker 15.7 · 1 port 2 workers 24.8
- 2 ports direct: **26.5 (C=16) / 28.8 (C=32)**
- 2 ports ผ่าน L4 proxy: 20.8 / 19.2 (**−25%**)
- ที่มา: `report/MULTIPORT.md`

## fig41_many_ports.png — scaling to 100 ports

- 1 port 15.7 · 2 ports 26.5 · 4 ports 20.8 · 8 ports 23.5 (C=64: 25.5 พร้อม error 1 ครั้ง)
- rps ต่อพอร์ต: 15.7 → 13.25 → 5.20 → 2.94
- memory: **45 MiB ต่อพอร์ต** → 100 ports = **4.4 GiB** (host 7.7 GiB, fleet ใช้อยู่ 1.3 GiB)
- ที่มา: `report/MULTIPORT_100.md`

## paper/_build/page1.png, page2.png, v2_*, v3_*, v4_p9.png — หน้า proof ของ white paper

- เอกสาร 20 หน้า A4 · 3.18 MB · `paper/SUAY-whitepaper.pdf`
- หน้า 1: ปก + abstract + keywords + meta (v1.1 · 22 Oct 2026)
- หน้า 2: สารบัญ 9 หัวข้อ พร้อมเลขหน้า **3, 4, 5, 6, 17, 19, 20, 21, 22**
- หน้า 8: §4.4 CPU quota table (1% 3.0/3.7 · 10% 11.0/13.4 · 40% 11.2/10.7 · 80% 8.2/8.3) + fig31/fig32
- หน้า 9: fig28 (TTFT vs reuse) + §4.6 expert routing tables (90.15%, MoE 86 เครื่อง, experts 32 เครื่อง/0.64 rps)
- หน้า 16: fig38 (complexity classes) + ข้อสรุป 4 ข้อ
- หน้า 20: Appendix A figure index (fig19–fig41)

> ภาพ proof เหล่านี้เป็นเพียงหน้าเรนเดอร์ของ PDF; ตัวจริงคือ `paper/SUAY-whitepaper.pdf` ซึ่งยังอยู่ครบ
