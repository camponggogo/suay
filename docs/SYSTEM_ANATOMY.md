# SUAY system anatomy

The landing page uses an editable isometric workbench instead of the promotional
video. Five steps explain the **implemented organization inference gateway**:

1. A developer app sends a prompt using a scoped API key.
2. The gateway checks inference scope, expiry and revocation.
3. Model allowlist and atomic request-budget checks control accepted submissions.
4. The gateway forwards to the operator's fixed, approved inference endpoint.
5. The backend result returns to the app; accepted submissions are audited.

The physical drawing includes an old workstation, two laptops, two phones,
two Raspberry Pi-style boards, an edge computer, a gateway appliance with a key
slot and policy indicators, and an approved backend rack. A demonstration AI Agent
web window shows prompt, access/policy checks, processing and response states.
It is an illustrative UI, not a live browser session. Moving dots
illustrate a request and response, not measured traffic or processing speed.
The three-second step duration is editorial timing, not an inference benchmark.
The picture shows the accepted-request path; errors and rejections are handled
by the API but not animated. The request quota is not a model-token budget.

Petals LAN model-block sharing and the Rust process/memory supervisor are separate
experiments. The gateway does not automatically route into Petals; fleet commands
remain pending. The figure does not assert that legacy machines support every model.

## Assets

`landing/assets/anatomy/` contains:

- `suay-system-steps.gif`: 1440×896, five steps, 15-second loop.
- `suay-system.svg`: editable vector source, dark theme.
- `suay-system-light.svg`: the same geometry with paper framing.
- `step-1` through `step-5`, each in SVG and PNG formats (1800×1120).
- `steps.json`: English step titles and descriptions.

Run `python scripts/build_anatomy.py` with Pillow installed to rebuild all assets.
The script uses a shared isometric model for SVG and raster output, with 249
physical parts including CRT casing, keyboard keys, ventilation, mounting feet,
key slot, ports, policy display, rack uprights, disk caddies, phone cradles,
Pi GPIO pins and laptop hinges. Strengths are called out above the mechanism:
evaluate existing capacity, control AI access, and manage users/policies/audit centrally.
The data-exchanging mixed-device pool remains a concept and compatibility must
be checked; the current gateway request path is described independently.

The installed Anatomy skill has no accompanying kit, audit or capture files.
This drawing therefore uses local geometry and simple bounds checks; it does
not claim to pass that missing kit's full clearance/depth/line-end audit.

## Landing behavior

The initial view is a still PNG. The GIF automatically plays when the figure
enters view, unless reduced motion is requested. Pause or selecting a step
restores a still and prevents automatic restarting until Play is pressed.
Playback stops outside the viewport or when the page is hidden, and resumes
when visible if the visitor has not paused it. A change to reduced-motion
preference stops playback; explicit Play remains available. No audio, video player or external
media service is required. Step descriptions remain available as HTML text.

The existing promotional video exports are retained as earlier project assets,
but are no longer embedded in the landing page.
