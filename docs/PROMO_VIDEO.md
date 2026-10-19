# SUAY promotional video

24 seconds, silent by design. English titles are burned in so the story works
without audio. Artwork: the project owner's approved SUAY device illustration.
The export is authored motion graphics, not footage from a generative video model.
No third-party music, voices or stock footage are included.

## Generation prompt

Use the supplied SUAY illustration as the exact visual reference. Produce a
24-second premium technology brand film on a near-black forest-green background,
with restrained lime-green illumination. Show branching neural fibers linking
more than fifty varied devices: old desktop computers, laptops, phones, servers,
Raspberry Pi boards and edge computers. Preserve the original SUAY identity.
Animate small coordinated pulses travelling along the fibers toward the central
SUAY node; use slow, deliberate camera movement, subtle depth and generous negative
space. No frantic flashing, invented benchmark numbers, holographic people or
unreadable generated text. Do not imply every depicted device is certified.
Leave typography to post-production. Finish on the SUAY mark with space for a
GitHub call to action. Deliver 16:9 and 9:16 versions. No copyrighted soundtrack.

## Edit / title sequence

| Time | Title | Supporting line |
| --- | --- | --- |
| 0–4s | Your next AI resource | is already here. |
| 4–9s | Wake old machines. | Run AI together. |
| 9–14s | Explore Python + Rust | Different tools. Shared ambition. |
| 14–19s | Start with your local network. | Build with your community. |
| 19–24s | SUAY / Open source | github.com/camponggogo/suay |

Persistent credit: campong.online. The current reproducible export uses the
reference illustration with timed typography and fades; the generative prompt
above is provided for a future animated neural-pulse variant.

## Files and reproduction

- Web: `landing/assets/suay-promote.mp4` — 1920×1080, H.264, 24 fps.
- Social: `.local/promote/suay-promote-vertical.mp4` — 1080×1920, H.264, 24 fps.
- Captions: `landing/assets/suay-promote.en.vtt`.
- Render: `python scripts/render_promote.py`; add `--portrait` for social.

The renderer currently uses Windows Segoe UI fonts; adapt the font path when
rendering on another OS. Social exports stay outside Git. No social upload is
performed by these scripts.

## Suggested social caption

Wake old machines. Run AI together.

Meet SUAY: an open-source project exploring local AI resource sharing, a Python
organization gateway and an experimental Rust resource supervisor. Explore the
source, understand the pilot's limits, and help build the next step.

Explore: https://campong.online/projects/suay/
Code / star / contribute: https://github.com/camponggogo/suay
Support: https://github.com/sponsors/camponggogo (availability depends on account setup)

#SUAY #LocalAI #OpenSource #DistributedAI #EdgeComputing

Before publishing, preview the actual crop and captions in each social app.
Hardware compatibility depends on the runtime and device. This is a concept
illustration, not live telemetry; no speed or budget savings are guaranteed.
