# ข้อเสนอระบบ Native AI Services และการบริหารส่วนกลาง

สถานะ: แบบออกแบบสำหรับพัฒนารุ่นถัดไป ปัจจุบันมี Python control-plane pilot ใน `versions/python/control/` สำหรับบัญชี สิทธิ์ API token และ desired state แต่ยังไม่มี native installer, authenticated worker transport หรือ Android agent ที่ทำงานจริง โค้ด Docker/UDP เดิมเป็นต้นแบบและไม่ผ่านข้อกำหนดความปลอดภัยของแบบนี้

## ข้อสรุปที่แนะนำ

ใช้ native service แทน Docker สำหรับ agent และใช้ศูนย์กลางที่มีชื่อ DNS คงที่ แยก control plane (บริหารงาน) ออกจาก inference plane (ส่ง prompt/ผลลัพธ์) ไม่ใช้ UDP broadcast หรือ election ของเครื่องพนักงานเป็นฐานของระบบบริหาร

แนะนำ Go สำหรับ agent/controller เพื่อแพ็ก executable ต่อ OS โดยไม่ต้องติดตั้ง Python ที่เครื่องพนักงาน และใช้ Kotlin สำหรับ Android agent การเลือกภาษานี้เป็นข้อเสนอ ยังต้องทำ prototype และ benchmark

เสนอ inference สองโหมดที่ต้องแสดงแยกกันในหน้า admin:

1. Native inference pool: Windows/macOS/Linux แต่ละเครื่องรันโมเดลที่พอดีกับทรัพยากรเครื่อง เช่น backend จาก llama.cpp แล้ว gateway กระจายคำขอไปยังเครื่องที่พร้อม โหมดนี้เพิ่ม throughput แต่ไม่ได้รวม RAM หลายเครื่องให้รันโมเดลเดียวที่ใหญ่เกินทุกเครื่อง
2. Distributed model pool: ใช้ Petals บนกลุ่มเครื่องที่ทดสอบรองรับจริง เริ่มจาก Linux host ที่เชื่อถือได้ โดยใช้ environment ที่ตรึง dependencies ไม่พึ่ง Docker การกระจาย blocks ยังต้องมี network segmentation, สมาชิกที่ยืนยันตัวตน และทดสอบความปลอดภัยของ protocol เพิ่ม ไม่ถือว่า Petals LAN เดิมปลอดภัยเพราะมี agent ใหม่

Android เริ่มต้นเป็น client เรียก inference gateway; การให้เป็น compute worker เป็นงานพัฒนา NDK/backend และตรวจนโยบาย background execution แยกต่างหาก ไม่ใช่ติดตั้ง Petals แล้วรันได้ทันที

## บริการตามระบบปฏิบัติการ

| ระบบ | รูปแบบ | สิทธิ์และ lifecycle | สถานะ inference ที่เสนอ |
|---|---|---|---|
| Windows | Windows Service ผ่าน SCM, MSI ที่เซ็นชื่อ | Automatic delayed start, dedicated service identity, service ACL จำกัดผู้หยุด/แก้ configuration, Job Object ครอบ child processes, ไม่เปิด console | native backend ต้องทดสอบ Windows build; Petals native ยังไม่รับรอง |
| Linux | systemd system service | dedicated account, Restart=on-failure, CPUQuota/MemoryMax, NoNewPrivileges, ProtectSystem, จำกัด directory และอุปกรณ์ตาม GPU | Petals pilot หลัก หรือ native backend |
| macOS | launchd LaunchDaemon ใน /Library/LaunchDaemons | dedicated account, RunAtLoad, restart policy ที่ไม่ทำให้ retry วน, signed/notarized package, child process lifecycle ต้องทดสอบ | native backend/Metal หรือ Petals หลังยืนยันรุ่นและ hardware |
| Android | managed app + foreground service เมื่อเข้าเงื่อนไข OS | ต้องมี notification และใช้ service type ที่ตรงงานจริง; ห้ามอ้าง service type อื่นเพื่อหลบข้อจำกัด | gateway client ก่อน; local compute เป็น optional pilot |

Desktop ไม่มีหน้าต่างที่ผู้ใช้กด X แล้วบริการหยุด การติดตั้งและสิทธิ์หยุดบริการกำหนดโดย IT ผู้ใช้ standard account ไม่ควรเขียน executable/config หรือสั่งหยุดบริการได้ แต่ local administrator/root ยังหยุดหรือถอนบริการได้เสมอ

Android ทั่วไปไม่สามารถรับประกันว่าไม่มี notification, ทำงานตลอดเวลา, เริ่มหลัง boot ได้ทุกกรณี หรือผู้ใช้หยุดไม่ได้ หากเป็นเครื่ององค์กร ให้ IT ใช้ Android Enterprise/MDM แบบ fully managed ตามความสามารถที่ OS และผู้ผลิตรองรับ นโยบายดังกล่าวอยู่นอกช่องทาง AI และไม่รับประกันการทำงานต่อเนื่องเมื่อเครื่องร้อน แบตต่ำ หรือ OS ยุติ process

## รูปแบบการเชื่อมต่อ

Agent → HTTPS 443 → Controller: enrollment, heartbeat, desired state, acknowledgement

User → HTTPS 443 → Inference gateway → authenticated inference worker: prompt และคำตอบ

Admin → SSO/MFA → Admin API → desired-state database + audit log

Agent ไม่เปิด management listener บนเครื่องพนักงาน ใช้ outbound polling/long polling พร้อม jitter และ exponential backoff จึงไม่ต้องมี remote shell, SSH, WinRM, ADB, RDP, VNC หรือ file browser ผ่านระบบนี้ อย่างไรก็ตาม inference แบบ gateway ส่งเข้า worker หรือ P2P ยังต้องมี network path ที่ออกแบบแยก ไม่สามารถอ้างว่าระบบทั้งหมดใช้ outbound-only โดยอัตโนมัติ

สำหรับรุ่นแรกให้ backend bind ที่ loopback แล้ว agent รับงาน inference ผ่าน connection ที่ตนเปิดออกไปยัง gateway ห้ามทำ tunnel แบบส่ง TCP ไปปลายทางใดก็ได้ ต้องมีเพียง protocol รับ prompt/ส่ง tokens ที่กำหนด schema, ขนาด และ timeout ส่วน Petals P2P ต้องอยู่ใน compute VLAN/เครือข่ายสมาชิกที่ผ่านการรับรอง ไม่เปิด P2P ทั่ว LAN พนักงาน

## สิทธิ์ admin ที่ให้ได้

| การกระทำ | พฤติกรรม |
|---|---|
| Run | เริ่ม runtime ที่ติดตั้งไว้ด้วย model ID ที่อนุมัติ |
| Drain | หยุดรับงานใหม่ รอ in-flight ตาม deadline |
| Pause/Stop | หยุด runtime และคืน RAM/VRAM แต่ agent ยังออนไลน์ |
| Disable AI | คง agent ไว้ แต่ปิดการรับงาน AI จน admin เปิดใหม่ |
| Change model | stage → verify → load → health check → route traffic → retire รุ่นเก่า |
| Move assignment | เตรียมปลายทางและตรวจ capacity/health ก่อนย้าย routing หรือ block assignment |
| Resource policy | เลือก profile ภายใน local hard limits เช่น eco/normal |

คำว่า “ปิด” ในระบบนี้หมายถึงปิด AI ไม่ใช่ shutdown/reboot เครื่องพนักงาน หากหยุดตัว agent ด้วยคำสั่งส่วนกลางจะเปิดกลับจากช่องทางเดิมไม่ได้ จึงไม่ให้มีคำสั่งนั้น การ stop/uninstall agent เป็นงาน IT ที่เครื่องหรือผ่าน MDM/software deployment แยกต่างหาก

“ย้ายโมเดล” หมายถึงโหลด weights/blocks ที่ปลายทางใหม่และเปลี่ยน assignment ไม่ใช่ย้าย process memory หรือ KV cache แบบ live การย้าย Petals blocks ต้องใช้ adapter ที่ระบุ blocks ได้และตรวจ coverage/replicas ทุกช่วง ไม่ถือว่า CLI ที่มีอยู่ทำ rolling migration ให้แล้ว

## ขอบเขตที่ลดโอกาสกลายเป็น remote administration

- Agent ใช้บัญชีสิทธิ์ต่ำ อ่าน/เขียนเฉพาะ cache, state, log และ credentials ของตัวเอง ไม่มีสิทธิ์อ่าน home/Documents ของพนักงาน
- Controller ส่งเฉพาะ desired state ที่มี schema version, node ID, revision, expiry, model ID และ resource profile ไม่รับ command, script, executable path, environment, Python expression, arbitrary URL หรือ arbitrary flags
- Agent ตรวจสิทธิ์และ allowlist ซ้ำในเครื่อง แม้ controller ส่งค่าที่ผิดก็ต้องปฏิเสธ ไม่มี eval, shell หรือ plugin loader จากข้อมูลส่วนกลาง
- Runtime executable ถูกติดตั้งโดย IT, hash/version ถูกตรึง, launch ด้วย argument array คงที่ runtime user ไม่มีสิทธิ์แก้ executable
- Model catalog ใช้ artifact แบบข้อมูล เช่น GGUF/safetensors ตาม backend ที่รองรับ ตรึง digest และ config; ไม่เปิด trust_remote_code ไม่โหลด pickle/โค้ดจากโมเดล
- Artifact host อยู่ใน allowlist; ป้องกัน redirects ไป host อื่น, path traversal, symlink escape, archive extraction และ SSRF การมี SHA-256 อย่างเดียวไม่ยืนยันว่าไฟล์ปลอดภัยหรือมาจากผู้มีสิทธิ์ ต้องมี approved/signed manifest ด้วย
- ช่องทาง update executable ไม่รวมกับคำสั่งเปลี่ยนโมเดล ใช้ signed MSI/PKG/package และ release approval แยกจาก Model Operator
- inference process ไม่มี tool execution, browser automation, shell tools หรือสิทธิ์เข้าถึงไฟล์ผู้ใช้ โมเดลตอบข้อความอย่างเดียว
- ไม่มี endpoint ดาวน์โหลดไฟล์ arbitrary จากเครื่อง worker และไม่ส่ง prompt/ข้อมูลส่วนตัวไปใน heartbeat
- ปิด P2P/discovery API ที่ไม่ยืนยันตัวตนของต้นแบบใน deployment ใหม่ การมี mTLS บน control plane ไม่ได้ป้องกัน inference endpoint ที่เปิดเปลือย

สิ่งเหล่านี้ลดความสามารถของช่องทางบริหาร ไม่ใช่คำรับรองว่า remote code execution เป็นไปไม่ได้ ต้องติดตามช่องโหว่ runtime/model parser และแยก process/สิทธิ์/เครือข่ายด้วย

## Identity และส่วนกลาง

- Enrollment token ใช้ครั้งเดียว มีอายุสั้น ผูก organization/node และออก device certificate เฉพาะเครื่อง
- Agent ตรวจ certificate ของ controller; controller ตรวจ device identity ด้วย mTLS มี rotation/revocation และไม่ใช้ shared admin token ในทุกเครื่อง
- Admin ใช้ SSO + MFA; แยก Viewer, Model Operator, Security Admin และ Release Admin
- Model Operator เลือกได้เฉพาะ catalog ที่ Security/Release Admin อนุมัติแล้ว ไม่สามารถเพิ่ม executable หรือ artifact host เอง
- Audit เก็บ actor, target, before/after, revision, timestamp, result และ failure reason ในที่ที่ worker แก้ไม่ได้ ไม่เก็บ secret/prompt โดยปริยาย
- Database เก็บ desired state และ observed state แยกกัน UI ต้องแสดง pending/offline/failed ไม่แสดง success ทันทีที่กดปุ่ม
- Controller ขั้นแรกใช้เครื่องบริหารที่แน่นอนพร้อม backup; ถ้าต้องการ HA ใช้ load balancer และ durable shared database/leader lease ฝั่ง scheduler ไม่ใช้ election จาก desktop

## State และเหตุขัดข้อง

สถานะ worker: OFFLINE, IDLE, STAGING, LOADING, READY, DRAINING, STOPPED, FAILED

READY ต้องผ่าน inference health check และ capacity validation ไม่ใช่เพียงมี process สำหรับ Petals ต้องตรวจ block coverage ของกลุ่มด้วย

Desired state ทุกฉบับมี revision เพิ่มขึ้น, target node, deadline/lease และลายเซ็นตามแบบที่จะเลือก Agent เก็บ revision สูงสุดลง disk แบบ atomic เพื่อปฏิเสธ replay หลัง restart และ acknowledge ซ้ำอย่าง idempotent เวลาต้อง sync และกำหนด tolerance ที่ตรวจได้

Heartbeat ทุก 15 วินาทีโดยประมาณ แสดง offline หลัง 60 วินาที; เป็นค่าตั้งต้นที่ต้องวัด ไม่ใช่ SLA หาก control lease หมดอายุ เช่น 5 นาที ให้ drain งาน AI และหยุด runtime ตาม deadline แทนการทำงานต่อไม่จำกัด หน้า admin ต้องบอกว่าเครื่อง offline จะรับ stop ไม่ได้ทันที

เมื่อ CPU/อุณหภูมิ/แบต/หน่วยความจำเกิน local policy ให้ลดรับงานหรือพักเอง แม้ admin ขอ run ระบบกลางเพิ่ม limit เกินขอบเขตที่ IT ติดตั้งไว้ไม่ได้

เปลี่ยนโมเดลแบบ canary ทีละกลุ่ม ตรวจ disk/RAM/VRAM ก่อน staging ตรวจ hash/manifest ก่อนโหลด ต้องมี capacity สำหรับ rollback ถ้าไม่มี capacity ซ้อน ต้องแจ้ง downtime ไม่รับประกัน zero downtime

## แผนพัฒนาและเกณฑ์รับงาน

1. Controller และ desktop agent ขั้นพื้นฐาน: enrollment/mTLS, typed desired state, persistent revision, stop/run/drain, resource limits และ audit โดยใช้ fake runtime ทดสอบก่อน
2. Native runtime บน Linux/Windows/macOS: ตรึง build/driver/model versions แล้ว benchmark latency, throughput, RAM, CPU, GPU และเวลาที่กระทบงานผู้ใช้ เลือก pool ตาม capability จริง
3. Admin UI + gateway: RBAC, rollout/rollback, offline/pending reporting และ admission control
4. Installer ที่เซ็นชื่อ: MSI, macOS PKG, Linux package พร้อม start-at-boot, upgrade/rollback และถอนผ่าน IT ทดสอบบน clean OS
5. Petals distributed pilot บน Linux compute pool: identity/network isolation, block coverage, worker loss และการย้าย assignments
6. Android client/managed deployment ก่อน หากจำเป็นต้องใช้ compute จึงทำ NDK prototype และยืนยัน service type/policy, heat/battery และ behavior ของ OEM

เกณฑ์ก่อน production: ผู้ใช้ logout แล้ว desktop service ยังทำงาน, standard user ปิด/แก้ executable ไม่ได้, reboot แล้วเริ่มตาม policy, child process ไม่ตกค้าง, control lease หมดแล้วหยุด AI, TLS ผิด/revoked identity ใช้งานไม่ได้, payload มี shell/URL/flags/path ต้องถูกปฏิเสธ, replay หลัง reboot ใช้ไม่ได้, stop รุ่นเก่าถูกแทนด้วย revision ใหม่อย่างถูกต้อง, rollout ล้มเหลวแล้วไม่ตัด traffic ไปปลายทางที่ยังไม่พร้อม, และทดสอบว่าระบบอ่านไฟล์/สั่ง shell/เปิด remote desktop บนเครื่องพนักงานไม่ได้ผ่าน API ที่ให้ไว้

## เอกสารต้นทาง

- Windows SCM: https://learn.microsoft.com/en-us/windows/win32/services/service-control-manager
- macOS launchd: https://support.apple.com/en-euro/guide/terminal/apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/2.15/mac/27
- systemd: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- Android background start: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- Android user stopping: https://developer.android.com/develop/background-work/services/fgs/handle-user-stopping
- Petals platform/backend instructions: https://github.com/bigscience-workshop/petals
- llama.cpp platform/backend options: https://github.com/ggml-org/llama.cpp
