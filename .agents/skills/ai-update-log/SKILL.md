---
name: ai-update-log
description: Keep ai_update_log.md at the project root current after every change. Read it first when picking up this repository; append a 4-field entry before finishing.
---

# ai-update-log

## When to use

- **Reading:** at the start of any task in this repository, read `ai_update_log.md` (top entry first) before
  exploring the codebase. It is the cheapest way to learn what changed, why, and what is still open.
- **Writing:** at the end of any change — code, docs, deployment, licence — append one entry. No exceptions
  for "small" changes.

## File contract

- Location: `ai_update_log.md` at the repository root.
- Ordering: newest entry on top. Never delete or rewrite history.
- Language: Thai (the maintainer's working language); keep code identifiers and commands in English.

Each entry has exactly four fields:

```markdown
## <หัวข้อการแก้ไข>

- **วิธีแก้ไข:** <what was changed, file paths, key decisions>
- **วันเวลา:** YYYY-MM-DD HH:mm (Asia/Bangkok)
- **ผลของการแก้ไข:** <verified outcome + evidence: test output, command, screenshot path, commit hash>
- **ไฟล์/หลักฐาน:** <paths touched, logs, links>
```

## Rules

1. `ผลของการแก้ไข` must state what was actually executed. "ควรจะผ่าน" is not a result; write
   `ยังไม่ได้รัน` together with the reason if verification was impossible.
2. If a change was attempted and blocked or reverted, log it too — with the blocking reason. A blocked
   attempt is information the next agent needs.
3. Reference only paths that exist in the repository. Do not paste secrets, tokens, passwords or `.env`
   values into the log.
4. When seeding history from an older file (`agent_update.md`), copy the entries verbatim, mark the old file
   as archived, and note the seed in the newest entry.
