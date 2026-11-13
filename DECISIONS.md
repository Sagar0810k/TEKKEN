# DECISIONS.md

Chosen technologies, rejected alternatives, reasons, unresolved questions.
Updated as work progresses. See `TEKKEN_LOCAL_CONSOLE_AGENT_BRIEF.md` for the full spec.

---

## D1 — Game source: native Windows port (Phase 0)

**Chosen:** `shihabal3amri/tekken-tag-tournament-2-pc` (static recompilation of the
Xbox 360 version, XenonRecomp-based).

**Reason:** Native DX11 executable, no emulator overhead — critical because the
target laptop has only Intel UHD integrated graphics (i3-1115G4, no dedicated GPU).
Supports two XInput-compatible local controllers, which is exactly the interface
our virtual-gamepad bridge will expose.

**Alternatives rejected:**
- Xenia (Xbox 360 emulator) — much heavier CPU/GPU load; poor fit for a 2-core
  i3 with integrated graphics.
- RPCS3 (PS3 emulator) — even heavier; PS3 image not interchangeable anyway.
- Cemu (Wii U) — same reasons.

**Status:** Installer `ttt2_setup.exe` identified from GitHub Releases.
Not yet downloaded/run (network flaky on this machine at time of writing).

## D2 — Game files are user-supplied (legal constraint)

The port ships no game data. It requires a **USA or Europe retail Xbox 360 disc
image (.iso) of TTT2** plus **Title Update 3**. These are copyrighted files; the
system will never download, bundle, or link them. The user places their own
legally obtained copies in `C:\TEKKEN\game_files\`. No automatic ISO conversion
is built until the native-port PoC is proven (per brief §9).

## D3 — Server stack: FastAPI + Uvicorn + WebSockets (Phase 2)

**Chosen:** Python 3.12, FastAPI 0.115, Uvicorn 0.30 (with websockets), qrcode 8.2
for local QR generation.

**Reason:** Matches the brief's lightweight stack proposal. Single process,
event-driven, small dependency count, no frontend build tooling.

**Alternatives rejected:**
- Plain `http.server` + hand-rolled WS — too much hand-written protocol risk.
- Node/Express — equal weight, but Python is already the team's environment.
- Next.js/React — explicitly rejected by brief §10.

## D4 — Frontend: plain HTML/CSS/JS, no build step

Single-file controller page per player served at `/player1` and `/player2`.
Pointer Events for multi-touch. No CDNs, no external fonts (brief §10).

## D5 — Virtual gamepad bridge: stubbed for Phase 1

The skeleton logs/mirrors input state to the operator dashboard. The real
Windows virtual-gamepad driver (candidate: ViGEm / vXbox-style bus — **to be
verified as maintained and compatible before install**) is Phase 1 work.
No driver has been installed on this machine yet.

## D6 — Operator UI served at `/` on the same server

The brief forbids separate public routes for dashboards; the operator screen is
served from the same server root and is only intended to be opened on the laptop
itself. Player entry remains exactly `/player1` and `/player2`.

## D7 — Session/auth model (skeleton level)

Per-slot pairing token generated at server startup, delivered only via the
player page's own `/api/session/{slot}` call. LAN-only binding (0.0.0.0 behind
the local network). This prevents casual slot-hijacking by other LAN devices but
is NOT strong auth — revisit before any use outside a private LAN.

## D8 — Controller skin: PPSSPP-style flat translucent controls

**Chosen:** PSP/PPSSPP on-screen-control look — flat translucent circles, thin light
borders, PS-glyph colors (✕ blue, ○ red, □ pink, △ teal), D-pad as a cross of four
separate rounded keys, single analog nub bottom-left, L/R shoulders, SELECT/START.
A DualSense skin was built first and rejected by the user in favor of this.

Button design uses per-control `--c` CSS variable + `color-mix()` so the pressed
glow matches each button's identity color. Positions in vw/vh, sizes in vmin so
the layout scales across phone screens.

## D9 — Layout editor model (Phase 3)

One layout per player slot, stored as JSON at `console/layouts/{slot}.json`
(memory-cached in the server; written only on explicit SAVE). The editor is a
mode inside the player page itself (EDIT button), not a separate route, per the
brief's route rules. Supports: drag to move, size +/−, hide/show buttons, global
opacity, reset to default template, save. Buttons carry a `hidden` flag; the
D-pad and analog nub are movable/resizable but not hideable. Button remapping is
deferred until the game-side mapping is proven (needs Phase 1/4 testing first).

## D10 — Virtual gamepad bridge (Phase 1)

**Chosen:** ViGEm Bus driver (v1.22.0, kernel service `ViGEmBus`) + Python
`vgamepad` 0.2.0. At server startup one virtual Xbox 360 controller is created
per slot; `bridge_update()` diffs the slot's pressed-button set against the pad's
current flags and pushes press/release, D-pad flags, and the left stick
(phone ly is down-positive, XInput LY is up-positive, so it is negated).
If the driver/library is missing the server still runs, dashboard-only.

Button mapping (phone logical -> Xbox 360 pad):
A -> A (left kick), B -> B (right kick), X -> X (left punch), Y -> Y (right
punch), LB -> LB, RB -> RB, TAG -> RB (alias), START -> START, BACK -> BACK.
This is the port's XInput layout; remapping UI still deferred until proven
in-game.

Open item: in-game slot assignment — "whoever presses a button first is player
1", so the PLAYER 1 phone should press first at the game's start screen; if the
pads come out swapped we swap the pad assignment in the bridge.

## Unresolved questions

- [ ] Does the port run acceptably on Intel UHD Graphics at 720p/60?
- [ ] Will the user legally obtain the USA/EU disc image + TU3?
- [ ] Which Windows virtual-gamepad driver is maintained and Win11-compatible?
- [ ] Does the port assign two virtual pads to two local players reliably?
- [ ] Exact storage type (SSD/HDD) and free space on the target laptop.

## D11 - 4-player support (PAIR PLAY)

**Chosen:** the server now exposes four slots (/player1 .. /player4) and
creates four virtual Xbox 360 pads at startup (one per slot). Evidence from the
port that 4 players is supported:

- kernel_xam.cpp: guest users 0-3 are the host XInput pads; pads claim users
  "by use" (first button press becomes user 0, next user 1, ...). The port has
  built-in scripted P3/P4 presses ("users 2 / 3 ... offline PAIR PLAY tests").
- Port README: offline PAIR = two controllers tag-teaming on one PC; PAIR PLAY
  extends this to 2 players per team (4 controllers / 4 humans on one machine).

How to play 4: at character select pick PAIR, press START on the second
controller when asked, and use the game's PAIR PLAY team screen. Players 3 and 4
scan their own QR from the operator dashboard (/player3, /player4).

Note: XInput caps at 4 pads, so 4 phone slots is the hard local maximum.

## D12 - Landscape + fullscreen controller

**Chosen:** the controller page stores separate portrait (x, y) and landscape
(xL, yL) coordinates per control. The layout editor edits whichever orientation
the phone is currently in; old saved layouts without landscape coords are filled
with LAND_DEFAULTS client-side (ensureLandscape() also materialises a 
ub
entry so the analog nub honours landscape coords). Rotation triggers a rebuild.
Fullscreen: a ⛶ button plus auto-fullscreen on the first touch, with a best
effort screen.orientation.lock("landscape").

**Result of the live fight proof:** phone A press made the in-fight character
attack (screenshot 	ools/game_window4.png). The "Press START button of
controller in use" screens ignore every button except START - the START pill is
the only way past them (hint shown on first connect).

## D13 - Controller input reliability

**Chosen:** 	ouch-action: none is set on every element (the property is not
inherited - leaving it only on body let the browser intercept gestures and
cancel two-finger presses, which showed up as "clicks don't register"). Presses
also get: a fat-finger fallback that resolves a tap to the nearest control
within a 16 px margin, per-finger state keyed by pointerId (independent
multi-touch), instant release over WS with a short visual flash on very quick
taps, haptic feedback, and a screen Wake Lock so the phone cannot sleep
mid-fight.

Editor: the bottom panel no longer eats taps for controls it overlaps
(rect-based hit detection; the panel can also be collapsed via "panel"), the
selected control's size is displayed, and Size +/- / Hide / drag apply to all
controls including START/BACK pills.

## D14 - Nearest-control hit testing and combo buttons

**Chosen:** taps resolve to the control whose rect (+14 px margin) contains the
touch and whose CENTER is nearest - not to the topmost painted element. This
makes overlapping face buttons (A/B, X/Y rings overlap by design) press
independently per finger, which the old elementFromPoint approach could not do.
The editor keeps the selection across rebuilds (resize no longer deselects), the
EDIT button moves to top-centre in edit mode so it stops covering RB, and
PPSSPP-style combo pills are added: "COMBO n" entries in the layout carry a
member list and a label; pressing one sends a press/release for every member
from the phone, so the server protocol is unchanged.

## D15 - PPSSPP-style custom buttons

**Chosen:** the editor gains PPSSPP-parity custom controls. "+ BUTTON" starts a
bind-pick flow: tap any of the game buttons (single or several), then Finish; a
new pill (label = member names, e.g. "A+B") is created at the screen centre and
can be dragged, resized, renamed (name field + Set name), made a toggle
(first tap holds, second tap releases - state tracked client-side in
toggleState, released on hide/reconnect), or deleted. Everything persists in the
slot layout JSON via SAVE. Pressing a custom pill expands to per-member press/
release messages on the phone, so the server protocol stays unchanged and any
combination of A/B/X/Y/LB/RB/START/BACK/TAG is possible.

## D16 - Source-counted input model (spec 4.4)

**Chosen:** per-slot, per-output source counting on the phone. Map
output name -> Set of source tokens; every control activation (plain button
press, combo press, toggle-on) registers one token per affected output; a
press message goes out only when the first source appears and a release only
when the last source disappears. releaseAllLocal (edit entry, page hide,
unload, WS close) clears all sources and sends the slot-wide release message
("rel"); the server additionally clears slot state on disconnect/timeout, so
stuck buttons cannot survive a lost phone. This guarantees that two controls
mapped to the same output (e.g. a combo A+B and the plain A button held by
different fingers) release independently, per the two-player touch-controller
spec. lostpointercapture joins pointerup/pointercancel on the same idempotent
release path. Combo mapping (one contact -> many outputs) and multi-touch
(one finger -> one control, many fingers in parallel) remain separate
mechanisms that compose freely.

## D17 - Overlap tap presses all covered buttons (multi-hit hit testing)

**Chosen:** hitAll(e, single) replaces the single nearest-centre hit in play
mode. Every button whose rect strictly contains the touch point is pressed
(margin 0 for multi-inclusion, so non-overlapping neighbours like START/BACK
never double-fire); a touch in the lens of two overlapping buttons activates
both, sharing one source token per output so release stays source-counted
(D16). D-pad/stick remain single-hit and yield to buttons; the nearest-within-
14px fallback (fat-finger) is unchanged. Edit mode keeps single nearest-centre
selection via hitControl (thin wrapper), so dragging/resizing stays
predictable. onDown stores a btns entry {entries:[{el,name}], token} and onUp
releases the token and clears .pressed on every covered button (quick-tap
flash preserved).

## D18 - Auto-save, hold-to-repeat resize, dpad arm gap

**Auto-save:** every layout change (drag move, Size +/-, Opacity, Hide, custom
button create/rename/toggle/delete, Reset) schedules a debounced save 800ms
after the last change; exiting edit mode flushes any pending save. Saves go
both to the laptop's per-slot JSON (shared, authoritative) and to the phone's
localStorage (ttt2-layout-<slot>), which is used as a fallback at load when
the laptop has no usable layout for the slot. The SAVE button still forces an
immediate save and the status bar shows "saved".

**Continuous Size +/-:** Size and Gap buttons now use pointerdown + hold:
single tap = one step, hold = repeats every 140ms after a 380ms delay, and the
selection is kept so every repeat applies to the same control until another
control is chosen. Fixed the old single-click-only behaviour.

**D-pad gap:** new per-slot dpad.gap (0-12, default 0) spreads the four arms
apart from the centre (Gap +/- shown in the editor only while the dpad is
selected). Direction logic is unchanged - arms are visual; hit zones still use
the dpad rect and centre deadzone.

## D19 - Landscape + fullscreen gate

**Chosen:** the controller is unusable until the phone is landscape AND
fullscreen. A #gate overlay (z 90, above everything) shows on load and on ws
open whenever a condition is missing; it covers all controls, and onDown also
refuses touches while gated. It listens to resize/orientationchange/
fullscreenchange/visibilitychange, so rotating to portrait or leaving
fullscreen mid-play re-locks the screen and sends the slot-wide release (spec
12: release-all on condition loss). The gate defers to the server messages
(connecting / unreachable / slot busy). If requestFullscreen is rejected
(iOS Safari), a "Continue without fullscreen" bypass link appears after the
failed attempt; the landscape requirement is never bypassable.

## 2026-11-12 — Stage C1 live experiment (4 virtual pads, one process)
- Offline OFFLINE MODE > PAIR PLAY (console 4-player mode): **all four virtual pads joined the stones** in player order (START each, LEFT/RIGHT to a stone, A to confirm; the "Exiting player select. Continue anyway?" dialog's OK = advance). Red = P1+P2, blue = P3+P4 confirmed on screen (pair_play_four_seated.png).
- Pair Play character select: **one picker cursor per side** (P2 drove red, P3 drove blue; P1/P4 had no cursor). 2 fighters per side confirmed; match start reached in earlier runs.
- TEAM BATTLE: LEFT/RIGHT sets team size 1..8 characters per side ("2 PLAYERS ON TEAM"); extra local pads' START ignored -> one human per side, other side CPU.
- Online room (PAIR PLAY > QUICK MATCH > BEGIN SEARCH, Steam-less loopback fallback): **P2 joined the host's red side locally** with own cursor and picked their own fighter (Nina); the blue side is hard-wired to a remote PC ("each on their own PC" - the game's own help text). P3/P4 START presses ignored in the room. True per-fighter 4-human 2v2 needs the second loopback instance (fallback plan).
- Game window was closed externally once and exited once without the clean-quit log line; relaunches were clean. Server restarted fresh before the session (4 pads ready).
- Deliverable: README.md (root) rewritten with full setup + 2v2 guide; screenshots in images/.

## 2026-11-12 — Server startup UX + operator dashboard redesign
- Server banner added at startup (flush=True): prints the localhost dashboard URL, the four per-phone LAN URLs, and explains that 0.0.0.0 just means "all interfaces" (localhost works on the laptop). Verified in a redirected log.
- start_server.bat now auto-opens http://localhost:8000/ on the laptop 3 s after launch.
- Operator dashboard (console/static/operator.html) redesigned per the ai-design-skills system (landing-page-design + figma-designer): Manrope + Geist Mono vendored locally (console/static/fonts, OFL, offline-safe), flat #181818-family surfaces only, Tailwind type scale, radius 16/8, heading gradient white->#9B9B9B as the only gradient, team identity via labeled chips (no border-top stripes), full button states (hover/active scale(0.98)/focus ring/disabled), inline error instead of alert(), skeleton loading state, inline SVG icons, motion cubic-bezier(0.22,1,0.36,1) with prefers-reduced-motion respected.
- Verified: server boots, / and /static/fonts/f12.woff2 and /api/status all return 200; API contract unchanged (/api/status, /api/game/start|stop).
- The ai-design-skills repo clone (temp dir) was deleted after use; only the vendored fonts remain in the repo.
- Server left STOPPED after testing; game window parked at main menu.

## 2026-11-13 — License system added (sellable product)
- Model decided: lifetime, single-seat — one key activates ONE laptop, then works forever. Without a valid license EVERYTHING is locked: no virtual pads (init_bridge skipped), phones redirected 302 to /, /api/game/start|stop return 403, dashboard shows only the activation gate.
- console/ttt2_license.py: machine fingerprint (hostname+MachineGuid SHA256, shown as FP-XXXX-XXXX-XXXX-XXXX), key format TTT2-SERIAL-SIG where SIG = HMAC-SHA256(SERIAL, embedded secret) truncated 8 hex. Activation writes hidden license.json (key, fingerprint, timestamp, HMAC record-mac) - tamper-tested: edited key -> "license key in file is invalid", swapped fingerprint -> "license record was modified".
- console/keygen.py: SELLER-ONLY tool. `python keygen.py 3 "buyer name"` mints keys, validates them, appends to licenses_issued.csv (issued_at, buyer, key). Buyers never get keygen.py or licenses_issued.csv.
- server.py: startup banner splits licensed (pads ready + full URL banner) vs locked (LICENSE REQUIRED banner with fingerprint); /api/status carries licensed + license fields; POST /api/license/activate validates + binds + init_bridge() immediately (no restart); operator.html shows a full-screen activation gate when licensed=false (design-system styled, inline errors).
- Verified live: locked boot banner, /api/status licensed:false, /player1 302, /api/game/start 403 with message, activation gate renders (tools/gate_ui.png), keygen output + CSV, invalid-key rejection, tamper detection both ways.
- Caveat recorded (offline model): enforcement = one key binds one laptop; a key-holder could still activate the same raw key on a second PC since there is no online activation server. Acceptable for small-scale direct sales; online activation is the future hardening step.
- 3 test keys generated for owner/stock (TTT2-73AE9862-C3D4E199, TTT2-90BE4972-DA569412, TTT2-B9775DBA-247AF9FB) - none consumed on the owner's laptop yet; machine currently UNLICENSED.

## 2026-11-13 — License system added (sellable product) [append pending from earlier]
- Model: lifetime, single-seat, everything locked without a license. Keys are FINGERPRINT-BOUND: buyer sends the fingerprint shown on their activation screen; seller mints with keygen.py (key = TTT2-SERIAL-SIG, SIG = HMAC-SHA256(serial|fingerprint)). Verified: key minted for laptop A validates on A, INVALID on B, even with the raw key text shared. Activation writes a hidden, HMAC-tamper-checked license.json bound to the machine (tested: edited key -> invalid, swapped fingerprint -> record modified).
- Locked mode verified live: no pads, phones 302 to /, game start 403, dashboard shows only the activation gate (tools/gate_ui.png).

## 2026-11-13 — Buyer package: self-extracting, self-deleting installer
- console/build_package.py (SELLER-ONLY) builds dist/TTT2_Local_Lounge_SETUP.bat: a single ~106 KB file with the lounge system embedded as base64. No key, no keygen.py, no licenses_issued.csv, no README/docs, no seller settings.json (fresh empty one included).
- Flow: buyer double-clicks -> extracts TTT2_Local_Lounge/ next to itself -> prints instructions -> DELETES ITSELF. Verified in a buyer simulation: folder extracted (server, ttt2_license.py, start_server.bat, INSTALL.bat, requirements.txt, static + 2 fonts, settings.json template, START_HERE.txt, package_id.txt), installer file gone after run.
- Bugs fixed during testing: (1) the payload marker also appeared inside the extraction command - IndexOf grabbed the wrong text; fixed by splitting the string in the command. (2) %RANDOM% + Expand-Archive path concat broke - replaced with pre-composed env vars + .NET ZipFile::ExtractToDirectory. (3) zip nested a second TTT2_Local_Lounge folder - flattened.
- Buyer boot test (extracted copy, port 8123): starts LOCKED, correct fingerprint, /api/status licensed:false. The system refuses to work on any laptop until the seller mints a fingerprint-bound key.
- Honest limitation recorded: no file can literally self-corrupt when copied; the installer self-deletes after first extraction and the software is fingerprint-locked, which is the enforceable equivalent - a forwarded package or extracted folder is a locked brick without a key for THAT laptop.
- Dashboard button/share route requested then cancelled by user - server.py reverted to clean state (no seller/package endpoints; py_compile OK).
