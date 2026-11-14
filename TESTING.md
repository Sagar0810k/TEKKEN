# TESTING.md

Hardware, versions, settings, and measurements recorded from the actual machine.
Nothing here is guessed — empty rows mean "not yet measured".

---

## Hardware inventory (recorded 2026-11-11 via systeminfo/wmic)

| Item | Value |
|---|---|
| Model | ASUS VivoBook X515EA |
| CPU | Intel Core i3-1115G4, 11th gen, 2C/4T, 3.00 GHz |
| GPU | Intel UHD Graphics (integrated only) |
| RAM | 8 GB (2×4 GB, DDR4-3200) |
| OS | Windows 11 Home 64-bit, build 22621 (22H2) |
| Storage | not yet recorded |
| Toolchain | Git 2.52, Python 3.12.6, Node 24.22 |

## Game tests

| Test | Result |
|---|---|
| Port installer runs | not yet |
| Game builds from disc image + TU3 | not yet (game files pending) |
| 720p FPS / frame time | not yet |
| Two controllers recognized | not yet |

## Controller / input tests (Phase 2 skeleton, recorded 2026-11-11)

| Test | Result |
|---|---|
| Two independent slots, separate state (P1: A / P2: B+dpad) | PASS |
| Browser pointerdown on A → server state `["A"]` | PASS |
| Browser pointerup → server state cleared | PASS |
| D-pad diagonal right-up → `{x:1, y:-1}` | PASS |
| pointercancel → dpad released to `{0,0}` | PASS |
| Malformed JSON / unknown type / unknown button rejected | PASS |
| Disconnect releases all buttons of that slot only | PASS |
| Wrong-token takeover attempt → denied, owner state intact | PASS |
| Watchdog stale-client force-release | implemented, not yet measured |
| Two real phones simultaneously | not yet |

## Virtual gamepad bridge (Phase 1, recorded 2026-11-11)

| Test | Result |
|---|---|
| ViGEm Bus driver installed (v1.22.0, service RUNNING) | PASS |
| `vgamepad` PoC: two independent virtual Xbox 360 pads, press/release A | PASS |
| Server startup creates both pads ("bridge: two virtual Xbox 360 pads ready") | PASS |
| Windows PnP shows 2x "Xbox 360 Controller for Windows", Status OK | PASS |
| Phone page press A -> WS -> server -> bridge (no exceptions) | PASS |
| Analog nub tilt -> lx=1.0 -> bridge left stick | PASS |
| D-pad right -> dpad x=1 -> bridge D-pad flag | PASS |
| Release/pointerup clears buttons, sticks, dpad | PASS |
| In-game: pads visible and usable | pending user test |

## Layout editor (Phase 3, recorded 2026-11-11)

| Test | Result |
|---|---|
| Play-mode input still works (✕ → A) | PASS |
| EDIT enters edit mode, DONE/✎ exits | PASS |
| Drag control → position updates (Y moved 76vw → 63vw) | PASS |
| Size +/− resizes control | PASS |
| Opacity slider updates live | PASS |
| Hide button (TAG) → ghosted, hidden in play mode | PASS |
| SAVE persists layout via POST /api/config/{slot} | PASS (verified from /api/session) |
| Reset-to-default via /api/template | implemented, smoke-tested |
| Two phones editing at once | not yet |

## Server tests

| Test | Result |
|---|---|
| `/`, `/player1`, `/player2` return 200 HTML | PASS |
| `/api/status` returns LAN IP + QR data URLs | PASS (IP 10.136.37.217 at test time) |
| QR codes render on operator dashboard | PASS (screenshot) |
| Operator dashboard live input mirror | PASS (screenshot) |

## Bugs found and fixed during testing

1. `websockets` 16.0 incompatible with uvicorn 0.30.6 → pinned `websockets==12.0`.
2. WebSocket route was defined but never registered → 403; added `@app.websocket("/ws/{slot}")`.
3. Missing `await ws.accept()` before first receive → HTTP 500; added.
4. `/player1`, `/player2` returned JSON-encoded HTML → added `response_class=HTMLResponse`.

## Latency / performance measurements

| Metric | Value |
|---|---|
| Phone → server RTT | not yet |
| End-to-end touch → action | not yet |
| Game FPS | not yet |

## Network notes

- Server binds `0.0.0.0`, port configurable (default 8000).
- LAN IPv4 discovered at runtime and shown on the operator dashboard.
- Phones must be on the same Wi-Fi; guest networks/client isolation will break
  connectivity (error surfaced to the user).

## Phase 3+1 follow-up: controller UX and 4-player

| Check | Result |
|---|---|
| End-to-end: phone A press attacks in a live fight | PASS (screenshot 	ools/game_window4.png) |
| "Press START" screens ignore all buttons except START | CONFIRMED (not a bug in our chain; START pill passes them) |
| Landscape coords used when window is landscape | PASS (START 56/92, A 86/74, circle 93/64, dpad 17/73) |
| Analog nub honours landscape coords | FIXED (ensureLandscape now creates layout.nub; nub 15/42) |
| D-pad left arm visible in landscape | PARTIAL (xL 17 still clips slightly on 912x670 window; needs xL ~= 22 - to verify on a real phone) |
| Fullscreen button (opens in Review pane) | PRESENT, auto-fullscreen on first touch added |
| /player3 and /player4 routes | PASS (200, session API returns slots) |
| Four virtual pads created at startup | PASS ("bridge: 4 virtual Xbox 360 pads ready") |
| XInput sees 4 connected users | PASS (user0..user3 CONNECTED via xinput9_1_0 read-back) |
| Operator dashboard shows 4 QR cards | PASS (rendered dynamically from /api/status) |

Notes:

- Pads assign "by use": whoever presses first at the game's start screens is
  player 1. In Team Battle the pad was claimed by the Player2 side; players
  should press in the order the game lists them, or we swap in the bridge.
- Mystery drift: idle pads report lx=-3356 ly=-1869 on some users; magnitude
  ~10%, under the game's deadzone, and control was proven - benign so far.
- Same-token connections (phone + browser tab) share one PlayerState and take
  over each other; harmless for input, noisy in logs.
- Port test hook: writing C:\ttt2\port\pad_inject.txt ("START 400", "P2+START
  150", "P3", "P4" supported) injects presses - consumed then deleted by the game.

## Controller reliability + editor fixes (round 2)

| Check | Result |
|---|---|
| Two buttons pressed together both reach the server | PASS (server held [A, B], both released cleanly) |
| Fat-finger tap 10px outside a button still registers | PASS (nearest-control fallback, 16px margin) |
| START pill selectable in editor | FIXED (edit panel was covering it; panel no longer blocks, rect fallback finds controls under it) |
| START pill size change in editor | PASS (72px to 80px via Size +; size number shown) |
| Pill drag in editor | PASS (56vw to 66vw) |
| touch-action:none on all elements | FIXED (was only on body - not inherited; browser gesture handling cancelled multi-finger presses) |
| Panel collapse button ("panel \u25BE") | ADDED |
| Tap flash on very quick taps | ADDED (release sent instantly; visual lingers 90ms) |
| Haptic buzz on press | ADDED (navigator.vibrate) |
| Wake Lock on first touch | ADDED (phone screen stays on during play) |

Notes:
- If presses still occasionally miss on a real phone, the takeover cycle when
  the same slot is opened twice (phone + browser tab) looks similar in logs -
  close duplicate tabs.

## Editor + overlap + combo fixes (round 3)

| Check | Result |
|---|---|
| Selection outline no longer vanishes after Size +/- (build() kept selection) | FIXED + PASS (A stayed selected, size grew, outline stayed) |
| RB selectable in editor | FIXED (EDIT button moved to top-centre in edit mode; was sitting on RB) |
| Overlapping buttons: touch inside two circles presses the NEAREST one | PASS (touch between A and B but closer to A pressed exactly A; old code pressed the topmost) |
| Two fingers on two overlapping buttons press both | PASS (per-finger nearest-control resolution) |
| Combo creation: tap "+ COMBO", pick A and B, Finish | PASS (pill "A+B" created) |
| Combo pill press | PASS (server held [A, B] together, clean release) |
| Delete combo button | ADDED (shows only when a combo is selected) |

Notes:
- Combos are phone-side expansions: the combo pill sends one press message per
  member button, so the server and game need no changes.
- Combos persist in the slot layout JSON after SAVE; they are deleted with
  "Delete combo" + SAVE.

## PPSSPP-parity custom controls (round 4)

| Check | Result |
|---|---|
| "+ BUTTON" creates a custom pill bound to a picked action | PASS (Y-only pill) |
| Custom pill rename via name field | PASS (renamed to "WALL") |
| Toggle mode on a custom pill | PASS (first tap held Y on the server, second tap released) |
| Delete custom pill | PASS (removed; face/system buttons offer no delete) |
| Custom buttons are entries in the slot layout JSON | BY DESIGN (persist on SAVE; server protocol unchanged - phone expands to member presses) |

Editor controls now shown when a custom button is selected: Size +/-, Hide,
Delete, name field + "Set name", "Toggle: ON/off". System buttons (A/B/X/Y/LB/
RB/START/BACK/TAG) can be hidden or resized but not deleted.

## Spec compliance round: source-counted release (PPSSPP spec 4.4/4.3/12)

Input model change: the phone now keeps output name -> Set(source token).
Each finger press (plain or combo) registers a token per affected output; a
release only sends "release" when that token was the output's last source.
Releasing everything (edit entry, hide, unload, WS close) clears all sources
and sends the slot-wide release message.

| Test (spec ref) | Result |
|---|---|
| 4.4 Two controls mapped to same output (combo A+B + plain A), releasing one | PASS (A stayed held by the other finger, B released) |
| 4.3 Three fingers: dpad RIGHT + combo A+B + plain A | PASS (RIGHT + A + B held) |
| 4.3 Combo finger releases while others hold | PASS (RIGHT + A remain, B gone) |
| 12 Full release after all fingers up | PASS (empty buttons, dpad 0,0) |
| 7 lostpointercapture wired to release path | DONE (idempotent with pointerup) |
| Toggle buttons now source-counted too | DONE (toggle holds a token until second tap or release-all) |

## Overlap tap presses BOTH buttons (multi-hit)

Layout change for the test: A moved 3vw left over B (memory-only, not saved).
Tap points measured with getBoundingClientRect.

| Check | Result |
|---|---|
| Tap in the lens where A and B overlap | PASS (server held A + B) |
| Release after overlap tap | PASS (clean zero) |
| Tap on B's exclusive area (not inside A) | PASS (only B) |
| Tap on A's exclusive area (not inside B) | PASS (only A) |
| Tap 10px outside B (fat-finger fallback) | PASS (nearest = B) |
| Edit-mode tap in the same lens | PASS (selects exactly 1 control, nearest center) |

Note: B's *centre* still sits inside A's rect in this test layout, so a centre
tap pressing both is correct behaviour, not a bug - only the 3vw strip on
B's right side is exclusive.

## Auto-save, continuous Size +/-, D-pad gap (round 5)

| Check | Result |
|---|---|
| Edit change auto-saves to server (no SAVE press) | PASS (dpad gap 0->1.5 and button size 23 persisted in /api/session layout ~1s after the change) |
| Layout mirrored to phone localStorage | PASS (ttt2-layout-player3 written on every save) |
| Reset to default auto-saves | PASS (saved layout == template afterwards) |
| Size + held: continuous repeat | PASS (16 -> 22 in ~1.2s hold, 140ms steps) |
| Size + single tap: exactly one step | PASS (+1) |
| Gap + hold spreads dpad arms | PASS (up arm top 2% -> 3.5%) |
| Gap controls only visible when dpad selected | PASS |
| Gap readout updates while changing | PASS (after fix: gapVal refreshes in gapSelected) |

Notes: browser drag test ran in landscape (updates xL/yL), so portrait x
stayed 76 = template default; gap/size saves prove the auto-save path.

## Landscape + fullscreen play gate (round 6)

A full-screen gate now blocks the controller until the phone is landscape AND
fullscreen (a "Continue without fullscreen" link appears only if the browser
refuses the fullscreen request, e.g. iOS Safari).

| Check | Result |
|---|---|
| Landscape but not fullscreen: gate shown ("One more step: fullscreen") | PASS |
| Portrait viewport (420x880 iframe): gate shown ("Turn your phone sideways") | PASS |
| Touches blocked while gated (server buttons stay empty) | PASS (both cases) |
| Unlock (fullscreen granted / bypass link) -> input works | PASS (A reached server) |
| Gating does not appear while the connecting/unreachable overlay is up | BY DESIGN (gate defers, then shows on ws open) |

Untested here (no way to resize the desktop window): rotating to portrait
mid-play re-locks the gate and releases all held outputs (code path
checkGate -> releaseAllLocal on ungated->gated transition). To verify on a
real phone: hold a button, rotate to portrait, gate must appear and the game
must see the button released; rotate back to resume.

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

## 2026-11-13 — Automatic environment setup (requirements.txt + INSTALL.bat upgrade)
- requirements.txt now covers every pip dependency the server actually imports: fastapi, uvicorn[standard] (websockets for the phone links were previously missing), qrcode[pillow], and vgamepad (the ViGEm client - previously assumed present).
- console/INSTALL.bat upgraded to a 5-step automatic setup: (1) detects Python, opens the download page and instructs "Add to PATH" if missing; (2) pip installs requirements; (3) detects the ViGEm Bus driver via sc query, downloads ViGEmBusSetup_x64.exe v1.22.0 from GitHub releases, self-elevates and installs silently; (4) detects an empty settings.json game_exe and prompts drag-and-drop of the game exe, validating the path and writing settings.json via python; (5) verifies all imports + driver, prints SETUP COMPLETE.
- Tested live on the seller machine: all 5 steps pass (Python 3.12.6, libs, driver already installed -> skipped, settings already set -> skipped, verification OK).
- START_HERE.txt simplified to match: Python -> INSTALL.bat (does everything) -> start_server.bat -> activate.
- Buyer package rebuilt (107,175 bytes) and Desktop copy refreshed. Buyer re-extract verified: INSTALL.bat + new requirements included, installer self-deletes.
- The buyer's total setup is now: install Python -> run INSTALL.bat -> run start_server.bat -> send fingerprint -> enter key.

## 2026-11-13 — Buyer guide PDF added to the package
- guide.html (C:\TEKKEN\) renders the complete illustrated guide with a print-friendly light theme (Manrope/Geist Mono vendored): cover, requirements table, Part A install (installer self-extract explained, Python with Add-to-PATH, INSTALL.bat's 5 steps detailed, license activation), Part B phones (links table, QRs, layout editor, first-press golden rule, controller table), Part C the 4-player 2v2 PAIR PLAY choreography per player with screenshots (stones dialog quirk, one picker per side, tag fight), Part D other modes (VS 1v1, TEAM BATTLE 1-8, single-player), Part E troubleshooting, Part F seller appendix (build_package, keygen, fingerprint-bound keys).
- Rendered to dist/TTT2_Local_Lounge_Guide.pdf via headless Edge --print-to-pdf (11.7 MB, screenshots embedded).
- build_package.py now embeds the PDF at the package root as TTT2_Guide.pdf (when present) and START_HERE.txt points buyers to it.
- Rebuilt SETUP.bat is 15.5 MB (PDF included); Desktop copy refreshed. Buyer re-extract verified: guide PDF at root, installer still self-deletes.

## 2026-11-13 — Guide PDF: seller appendix removed
- Part F (For the seller - keys & packages) removed from guide.html; PDF re-rendered (11.2 MB) and the buyer SETUP.bat rebuilt (15.5 MB) + Desktop copy refreshed.
- Verified in a fresh buyer extraction: no build_package.py, no keygen.py, no licenses_issued.csv, no license.json, no demo_keygen.bat anywhere in the extracted tree (they were already excluded by the FILES whitelist; the PDF no longer mentions them either). Guide PDF present at package root. Installer self-deletes.
- The buyer guide now ends after Troubleshooting with the closing line - it contains nothing about how packages or keys are made.

## 2026-11-13 — Final Drive-distribution build verified
- START_HERE.txt numbering fixed (was 1,2,3,3,4,5 -> now 1..6) and wording confirms the Drive flow: extract the ISO zip and TU3 zip, then give ttt2_setup.exe the extracted locations.
- Final SETUP.bat rebuilt (107,187 bytes, NO PDF inside) and Desktop copy refreshed.
- Fresh buyer sim (buyer_sim6): extracts cleanly, START_HERE steps correct, installer self-deletes, tree contains no seller tools (build_package.py/keygen.py/licenses_issued.csv/license.json) and no PDF.
- dist/Game Install.pdf (11.3 MB) is the buyer guide to upload to Drive; it has no seller appendix and teaches the ISO/TU3 zip extraction + ttt2_setup.exe location flow. Old TTT2_Local_Lounge_Guide.pdf superseded.
- Seller Drive upload list: SETUP.bat, Game Install.pdf, ISO as zip, TU3 as zip, ttt2_setup.exe (port's GitHub releases).
