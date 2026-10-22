# Image facts — UI, story and anatomy figures

บันทึกก่อนภาพชุดต่อไปนี้ถูกแทนที่ด้วย placeholder

## pasadhi/app/ui-screenshot.png — หน้าตั้งค่า PASADHI

- role ที่ระบบเลือกให้เครื่องทดสอบ: **worker · score 18.2** (8 threads, 15.9 GB, uptime 88 ชม.)
- ค่าเริ่มต้น 30 % CPU / 0 % GPU / 20 % RAM → **฿711/เดือน** (0.99 ฿/ชม.)
- ตั้ง 35 % CPU / 20 % RAM → **฿1,189/เดือน** (1.65 ฿/ชม.)
- แสดงเพดานจริง: 2.8 cores · 3.18 GB RAM · 2.3 GB disk
- หน้าจอมี: สไลเดอร์ 5 ตัว, ตัวเลขรายได้, device id `psd_40195289c3c08006`, ปุ่ม rotate, สวิตช์ autostart
- ที่มา: `pasadhi/docs/APP_SERVICE.th.md`

## landing-pasadhi/story-preview.png — หน้า story 6 บท

| บท | วันที่ | ตัวเลข |
|---|---|---|
| 1 | 19 ต.ค. | 12.0 req/s · p50 3 811 ms · 96.5 % queueing |
| 2 | 20 ต.ค. | 44 → **161 req/s**/shard |
| 3 | 21 ต.ค. | 15.7 → **22.3 / 24.8 req/s** |
| 4 | 21 ต.ค. | 111.4 s → **0.71 s (157×)** |
| 5 | 21 ต.ค. | **90.15 %** · 31.5 µs |
| 6 | 22–23 ต.ค. | **3 564 GFLOP/s** · 30 links |

- ที่มา: `landing-pasadhi/story.html`, `scripts/build_story.py`

## pasadhi-mesh.png / pasadhi-pool.png — ฉาก isometric

- pool: 4 อุปกรณ์ · bus + dial + counter · 4 เส้นทาง packet · 533 GFLOP/s ที่ 30 %
- mesh: 12 อุปกรณ์ (desktop 3, laptop 2, server 2, phone 2, GPU 3 เครื่อง = 7 การ์ด) · **30 links** · 10 เส้นทาง animated · **266 GFLOP/s** ที่ 30 %
- ที่มา: `pasadhi/web/anatomy/*.html`, `scripts/build_{pool,mesh}_scene.py`

## landing-pasadhi/preview-en.png · preview-th.png — หน้าแรก

- EN 13,487 bytes · TH 19,041 bytes (หลังเพิ่มส่วน download)
- ราคาบนหน้า: Shared ฟรี · Monthly 1,490 · Yearly 1,242 · Premium 3,490 · On-prem เริ่ม 18,900/กลุ่ม/เดือน
- ที่มา: `landing-pasadhi/{index.html,th/index.html}`
