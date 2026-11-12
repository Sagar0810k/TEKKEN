# TTT2 Local 4-Player 2v2 — IMPLEMENTATION PLAN

Date: 2026-11-12 · Companion to `ARCHITECTURE_REPORT.md` (read that first)
Chosen architecture: **Approach C, staged** — one game process, four
independent pad users, existing combat/tag systems untouched; the port's
own online-2v2 hooks are the model if offline wiring is missing.
Approach B (4 game instances + `TTT2_NET=loopback`) is documented as the
fallback, not the plan.

Ground rules honoured: the existing controller/server system is kept; no
Steam account; no internet; no second PC; no copyrighted files handled;
original single-player/2-player modes must keep working.

---

## Phase 0 — Housekeeping (before any code change)

| Step | Detail |
|---|---|
| 0.1 Restore version control | The local repo copy has no `.git`. Re-clone from GitHub into a fresh folder (or `git init` + add remote), then create branch `local-4p-2v2`. The installed game at `C:\Program Files\Tekken Tag Tournament 2\` stays untouched. |
| 0.2 Baseline build ability check | Verify the machine can at least run the installed build; full source builds only needed if Stage C3/B is reached. |
| Deliverable | Branched repo + baseline notes in `TESTING.md`. |

## Phase 1 — Repository analysis (complete → this report)

- Done: `ARCHITECTURE_REPORT.md` (this plan's companion).
- Remaining open items that do not block Phases 2-3: profile/save
  isolation env-vars for multi-instance fallback (only relevant to B).

## Phase 2 — Existing controller analysis (largely complete)

Already verified in earlier sessions [C]:
- 4 routes `/player1..4`, one WebSocket per phone, per-slot auth & state.
- 4 virtual Xbox pads (ViGEm), game sees XInput users 0-3 CONNECTED.
- Source-counted release, layout editor, per-phone identity.
Remaining:
| Step | Detail |
|---|---|
| 2.1 Real-device 4-phone soak test | All four phones connected simultaneously for ≥30 min; forced Wi-Fi drop on each phone in turn; verify slot takeover and zero stuck buttons (server slot-wide release). |
| 2.2 Latency baseline | Measure phone-press → ViGEm pad change (server-side timestamp) and pad → game reaction (screen capture timing), per phone. |
| Deliverable | Four-phone demo + measured latency numbers in `TESTING.md`. |

## Phase 3 — Input integration proof of concept (mostly exists)

| Step | Detail |
|---|---|
| 3.1 Four-state display | Operator dashboard: live per-slot button/dpad/nub state (extend `/api/status` consumers). |
| 3.2 Simultaneity test | Four phones, same-frame presses on all four pads; confirm four independent `XamInputGetState` users in the game (use the port's own `TTT2_2V2_DIAG`/pad debug if enabled). |
| 3.3 Disconnect storm | Kill all four WS connections at once while buttons held; verify all four pads release within one frame and the game never sees a stuck button. |
| Deliverable | `TESTING.md` section "Phase 3". |

## Phase 4 — **Stage C1: the decisive live experiment** (no code changes)

Goal: answer **"does the game's offline pairing flow accept four humans?"**
Choreography (driven by the operator dashboard + phones):
1. Start the game (installed build). All four virtual pads connected.
2. Versus mode → character select → `PAIR`.
3. Join screen 1: pad 0 (phone 1) presses START → Player 1 signs in.
4. Join screen 2 ("Press START of controller in use"): pads 1 (phone 2)
   presses START → user 1 joins (this is the documented offline PAIR path).
5. **Then attempt pads 2 and 3 (phones 3/4) pressing START** on subsequent
   "Press START" prompts, or select a mode variant that shows further join
   prompts. Record exactly what happens at each step (screen text, whether
   users 2/3 are accepted, whether character select shows 4 pickers).
6. If a 4-seat assignment screen appears (PADASSIGN mode 22, the stones
   screen), walk all four phones onto seats and start the match.
7. In-match: each phone attacks; verify four independent fighters; verify
   tag: inactive teammate's phone controls the tagged-in fighter.

| Outcome | Consequence |
|---|---|
| Full 4-human offline 2v2 works | Approach C confirmed → Phase 5 polish only. |
| Works up to 2 humans, users 2/3 ignored | Stage C3 kernel work needed (Phase 5a). |
| Works but tag/ownership misroutes | Stage C3 targeted routing fixes. |
| Recording | Screenshots + step log into `TESTING.md` + `DECISIONS.md`. |

## Phase 5 — Four-player team architecture

### 5a. If Stage C1 fully works (likely-ish given the scripted P3/P4 test hooks)
- No gameplay code changes. Port-side work only:
  - Dashboard lobby UI: per-player connection, ready, team (blue/red),
    fighter name; START MATCH gate when all four ready.
  - Join choreography automation from the dashboard (safe sequenced START
    presses via our server's ViGEm pads).
  - Map phones → users 0-3 → seats/fighters; display the mapping live.

### 5b. If Stage C1 fails (users 2/3 not accepted offline)
New hand-written kernel module `offline_2v2.cpp` (+ `.h`), modelled on the
proven `online_2v2_*` modules but **fully local** (no transport):
| Step | Detail |
|---|---|
| 5b.1 | Reuse `online_2v2_places.cpp` mechanics for the 4-seat stones screen, but with local pads: each user 0-3 = one seat; no network authority split needed (all presses already local). |
| 5b.2 | Reuse team/slot mapping (`mySlot & 1`, slots 9-12) from `online_2v2_team.cpp`. |
| 5b.3 | Remove the online code's pad-forwarding path: partner inputs are already local users; only seat/role assignment remains. |
| 5b.4 | Gate behind an env var (e.g. `TTT2_LOCAL_2V2=1`) so normal offline modes are untouched. |
| 5b.5 | Build via `tools\build_port.cmd` (requires re-generated recompiled code from the operator's disc image — **the ISO was deleted; if a source rebuild is ever needed, the disc image must be re-supplied**). |
| Deliverable | 4-human offline pairing in one process; normal modes unaffected (`TTT2_LOCAL_2V2` unset = stock behaviour). |

## Phase 6 — Match integration & lobby

| Step | Detail |
|---|---|
| 6.1 | Lobby: dashboard shows BLUE (P1/P2) and RED (P3/P4) with connection/ready/fighter status; match cannot start until 4/4 ready (host override toggle). |
| 6.2 | Character selection: each phone picks its own fighter via its own pad (offline PAIR supports per-controller selection; partner-select remap exists in the online path if needed). |
| 6.3 | Full match test: start → 2v2 fight → tags in both directions → round end → restart → second match. |
| 6.4 | Disconnection handling: phone drops mid-match → its pad releases; the game continues; phone reconnects → same slot resumes. |
| Deliverable | A working local 2v2 match, four phones. |

## Phase 7 — Performance & reliability

| Measurement | Method |
|---|---|
| Controller latency (press→game) | Server-side timestamp at WS receive vs ViGEm pad write; game-side via frame-stepped screen capture (existing `tools\snap_game.ps1`). |
| FPS | Game's built-in FPS counter (GRAPHICS SETTINGS) during 2v2 fights, tag-heavy sequences. |
| CPU/GPU/RAM | Task Manager / `typeperf` during matches. |
| Stability | 3 consecutive full matches; 30+ min soak; disconnect storms; simultaneous input bursts. |
| Claim rule | **No 60 FPS claim until the FPS counter confirms it** (spec §14). |

## Fallback plan — Approach B (4 instances + loopback)

Only if single-process proves impossible:
1. Kernel change: env-var host-slot filter (`TTT2_PADS=0|1|2|3`) so each
   instance claims exactly one virtual pad.
2. Profile/save isolation per instance (needs `profiles.cpp`/
   `save_store.cpp` env redirect investigation).
3. Room flow via `TTT2_NET=loopback`: instance 1 hosts, 2-4 join; the
   online PAIR PLAY code handles the rest (proven 4-human logic).
4. Display: show one window on the TV; measure 4× GPU/CPU load; if it
   cannot hold 60 FPS, Approach B is rejected and C3 becomes mandatory.

## Deliverables checklist (spec §13)

| Item | Where |
|---|---|
| ARCHITECTURE_REPORT.md | Done (this session) |
| IMPLEMENTATION_PLAN.md | This file |
| Controller integration | Exists; Phases 2-3 verify |
| Local multiplayer lobby | Phase 6.1 (dashboard UI) |
| Player/team management | Phase 5 |
| Tag integration | Phase 4 step 7 + Phase 6.3 |
| Local networking | None needed for C (all local); loopback documented for B |
| Test results | `TESTING.md` per phase |
| Build instructions | `BUILDING.md` (repo) + Phase 5b.5 caveats |

## Open risks

1. Stage C1 outcome unknown (the plan branches on it).
2. If Stage C3 or B requires a **source build**, the disc image + TU3 must
   be re-supplied (ISO deleted from `game_files\` on 2026-11-12). The
   installed release build does NOT need it.
3. `.git` absence (dev-rule 6) — Phase 0.1 resolves it.
4. Guest users 1-3 cannot save profiles — acceptable for match play;
   progression saving stays on user 0's profile (as on console).
