# TTT2 Local 4-Player 2v2 — ARCHITECTURE REPORT

Date: 2026-11-12 · Status: investigation only, no gameplay code changed
Scope: `C:\TEKKEN\tekken-tag-tournament-2-pc` (local copy of
github.com/shihabal3amri/tekken-tag-tournament-2-pc), plus the existing
controller/server system in `C:\TEKKEN\console`.

Every finding below is tagged **[C]** = confirmed against files on disk,
**[I]** = inferred, **[U]** = unknown / needs live verification.

---

## 1. Repository architecture

- **Two kinds of code live side by side** [C]:
  1. **Recompiled game code** — the original Xbox 360 PowerPC program of TTT2
     (retail + Title Update 3) translated to x64 C++ by XenonRecomp. It is
     **generated on the build machine and is NOT in the repo**
     (`BUILDING.md:6-8`); it lands in `re\ppc\` and is produced from the
     user's own disc image. Gameplay logic (modes, menus, fights, pairing
     screens) lives here.
  2. **Hand-written port code** (`port\src\runtime\...`) — the "kernel" the
     recompiled game calls: XAM imports, input, GPU (Xenos→D3D11), audio
     (XMA→FFmpeg), file I/O, profiles, networking, and a large set of
     `online_2v2_*` modules that implement online PAIR PLAY by *hooking*
     recompiled functions (e.g. `online_2v2_team.cpp:526-541` overrides
     `sub_825FE600`, the game's state machine).
- Key consequence: **"modifying the game" = writing more kernel-side hook
  code (or patching specific recompiled functions), never editing a game
  logic source file that doesn't exist.**
- Build: MSVC x64 + clang-cl + CMake/Ninja; needs the user's own
  `Default.xex` + TU3 (`BUILDING.md:10-41`).
- Installed layout (`port/INSTALLER.md:35-39`): runtime reads
  `<exe dir>\game` (`TTT2_VFS_ROOT`), writes only to
  `%LOCALAPPDATA%\TTT2Recomp` (saves, settings.ini, shader cache, net).
  Our install: `C:\Program Files\Tekken Tag Tournament 2\` [C].
- **Repository state** [C]: the local copy has **no `.git`** (plain file
  copy; the workspace root `.git` at `C:\TEKKEN\.git` was removed on
  2026-11-12 at the operator's request). Dev-rule 6 (work on a branch)
  requires re-initializing/re-cloning before gameplay code changes.

## 2. How normal offline PAIR works

- Offline PAIR = **two humans on one PC, each human controlling one whole
  tag team** (`dist_README.txt:81-83`, root `README.md:211-214`) [C].
- Flow: at character select pick `PAIR` → the game shows the join screen
  "Press START button of controller in use" → the second controller's first
  button press makes it **user 1** → the game accepts START on it. The
  second controller plays as a **guest of user 0's profile**
  (`kernel_xam.cpp:96-103`, `123-128`) [C].
- "Offline pair play takes any controller" — no sign-in requirement
  (`kernel_xam.cpp:99-100`) [C].
- The game flow itself is the recompiled game's own; the port only feeds it
  a second controller. **Offline PAIR is documented and wired for exactly 2
  humans.** No shipped offline 4-human mode exists in the docs [C].

## 3. How online PAIR PLAY works (the port's own 4-human architecture)

All hand-written kernel modules: `online_2v2.{h,cpp}`,
`online_2v2_{team,pair,places,pick,select,rewards}.cpp`,
`online_pair_room.cpp`, `diag_2v2.cpp` [C].

- **Unit of participation = one PC = one participant.** Four PCs meet in a
  room; the PAIR PLAY screen ("stones") is the **game's own PADASSIGN mode
  22 with its PAIR sequence** — the same screen offline PAIR uses — which
  has **four seats / four controllers** ("the game's controllers 1-4 are
  the room's members", `online_2v2.h:76-78`; places 1 red-lower, 2
  blue-lower, 3 red-upper, 4 blue-upper, `online_2v2.h:84-89`) [C].
- Teams: side = `mySlot & 1` (red 0 / blue 1); fighter slots **9/10** are a
  side's first player (lower stone, fights), **11/12** the partner
  (`online_2v2_team.cpp:256-302`) [C].
- Partner input is forwarded over the network to the teammate's PC and
  surfaced as that PC's **user 1** (`RemotePad`, `kernel_xam.cpp:958-968`;
  sent on change / ≥16 ms, `online_2v2.cpp:442-455`) [C].
- The seat-0 PC is the authority that collects everyone's presses on the
  stones screen and replays them (`online_2v2_places.cpp:5-16`) [C].
- The match itself uses the **game's own NACE sync/rollback engine**
  (`rollback_session.cpp:1-9`) — the port reuses it, it does not replace
  the fight simulation [C].
- "A room of two members plays the game's own 1-on-1"
  (`online_pair_room.cpp:13`) [C] — **2 participants can never make a 2v2.**

## 4. Steam and networking as they exist today

- Steam App **480 (Spacewar)** is hardcoded; Steam runs in a **helper
  process** (`steam_bridge.cpp`); the game process never loads Steam
  (`steam_net.h:44-51`) [C].
- Steam provides: identity (SteamID/XUID), matchmaking lobbies, invites,
  auth tickets for community servers, and the default **packet transport**
  (SteamNetworkingMessages) [C].
- **The netcode already runs without Steam**: transport backend
  `net_transport.{h,cpp}` has selectable backends via `TTT2_NET`:
  `steam` (default), **`loopback`** (UDP on 127.0.0.1:28100+n, peer id
  `0x4C4F4F50'0000xxxx`, no Steam, no internet — `net_transport.h:5-7`,
  `net_transport.cpp:447-476`), and silent fallback to loopback when Steam
  is unavailable [C].
- `TTT2_NET=loopback` is the documented two-instances-on-one-PC offline
  path (`BUILDING.md:54-55`) [C].
- Community server (`server\`, Go) = discovery/rank/replay services only;
  **matches never pass through it** (`PROTOCOL.md:5-8`) [C].

## 5. How controller inputs are processed (game side)

- The recompiled game calls XAM imports
  (`XamInputGetState`, `XamInputGetCapabilities`); the port reimplements
  them and writes results into guest memory
  (`kernel_xam.cpp:1263-1321`) [C].
- A dedicated poll thread (`PadPollThread`, ~1 ms loop) samples host
  **XInput slots 0-3** (`XInputGetState`), merges the keyboard pad into
  user 0, merges scripted/synthesized presses, applies online-2v2
  routing/masking, and publishes `g_pads[4]` [C].
- **Four pad users are structurally supported** (`g_pads[4]`, users >3
  rejected) [C]. Pads are assigned "by first use" to users 0-3
  (`kernel_xam.cpp:643-647, 713-718`) [C]. Users 1-3 are guests of user 0;
  they cannot save [C].
- Game-side, the fight reads **pad slots 9/10/11/12**; the active
  character's controller slot can switch to the partner's slot on tag
  (fighter field +7792; TAG bit gating in state +48 — `diag_2v2.cpp:7-9`)
  [C]. The port observes/hooks this layer rather than reimplementing it.
- **No rumble path exists** — no `XInputSetState` anywhere in the repo [C].

## 6. The existing controller system (ours — kept per dev-rule 1)

- FastAPI/uvicorn server, port 8000 (`console/server.py`): routes
  `/player1..4` + operator dashboard at `/`, one WebSocket per phone,
  per-slot token auth, per-slot input state, slot-wide release on
  disconnect/timeout [C].
- Four **virtual Xbox pads via ViGEm Bus + vgamepad**, created at startup;
  verified XInput users 0-3 CONNECTED in the game [C].
- Phone controller (`console/static/controller.html`): source-counted
  input model (overlap-safe release), combo pills, toggles, layout editor
  with auto-save, landscape+fullscreen gate [C].
- **Input path today:** phone → WS → server → ViGEm pad N → port's poll
  thread (host XInput) → `XamInputGetState(user)` → game. All four phones
  stay separate end-to-end; the game already sees four independent pads.
- End-to-end control was proven in a live fight (a phone press attacked)
  [C from prior session records].

## 7. Feasibility: Approach B vs Approach C

### Approach B — multiple game instances on one laptop

- The port's own 4-human architecture maps **one participant per
  instance**. Therefore:
  - **2 instances ≠ 2v2** — a two-member room plays plain 1v1 [C].
  - **4 instances = exactly the online PAIR PLAY topology**, connected via
    `TTT2_NET=loopback` (no Steam, no internet, transport already exists).
- Required work for B [I]:
  1. Per-instance pad separation: today every instance samples host XInput
     slots 0-3 and self-assigns users "by first use" — two instances would
     fight over the same four virtual pads. Needs a small kernel change
     (env-var filter like `TTT2_PADS=0` / `1` / `2` / `3` masking which
     host slots an instance samples).
  2. Per-instance profile/save isolation: all instances share
     `%LOCALAPPDATA%\TTT2Recomp` [U — needs investigation of
     env-var redirect support in `profiles.cpp`/`save_store.cpp`].
  3. Window/display management: only one window is shown on the TV; the
     other three instances must still run (rendering cost ×4) [U perf].
  4. CPU/GPU load of 4 native D3D11 instances on one laptop [U — biggest
     risk; unmeasured].
- Verdict: **architecturally supported by the existing source** (loopback
  netcode is already there), but heavy: 4 processes, per-instance input
  masking, profile isolation, and unproven 4× performance.

### Approach C — one game process with four logical players

- Facts in favour [C]:
  - The kernel already supports **4 pad users simultaneously**; our four
    virtual pads already appear as users 0-3.
  - The game's own pairing screen (PADASSIGN mode 22, PAIR sequence) has
    **four seats**, and the online code proves the game-side structures
    (slots 9-12, roles, tag-to-partner-slot) accept four controllers.
  - The port authors wrote **scripted P3/P4 press hooks labelled
    "(offline PAIR PLAY tests)"** (`kernel_xam.cpp:728-736`) — evidence
    that 4 pads were driven through an offline pairing flow in tests [I].
- Facts against [C]:
  - Offline PAIR is documented for 2 humans only; no shipped offline
    4-human wiring exists.
  - The online implementation's team/partner hooks assume the partner is
    on **another PC** (pad forwarding over the network); they do not work
    as-is with everything local.
- What C needs [I]:
  - **Verify live** whether the game's offline pairing flow already
    accepts users 2/3 as fighters 3/4 when four pads press START at the
    join screens. Prior sessions reached the 4-pad claim stage; a full
    4-human offline 2v2 match has not been confirmed end-to-end.
  - If it does: Approach C is mostly **input integration + lobby UI**
    (our server/dashboard), the cheapest path by far.
  - If it does not: port the online `online_2v2_places/team` mechanics
    into the offline flow (single process, all inputs local, no netcode
    needed) — moderate hook work in `kernel_xam.cpp` + a new offline
    module; no recompiled-code regeneration required if we only hook
    existing functions (as online_2v2 does).

### Recommendation

**Staged hybrid, C-first:**

1. **Stage C1 (verify):** run the installed game with 4 virtual pads and
   attempt a full offline 4-human pairing (PAIR + both join screens with
   users 2/3). This decides everything and costs one test session.
2. **Stage C2 (integrate):** if C1 succeeds — operator-dashboard lobby
   (connection/ready/team/fighter state), controlled join choreography
   (who presses START when), per-phone tag/mapping docs. Done via our
   existing server; no game code changes.
3. **Stage C3 (patch if needed):** if C1 fails at any step, add the
   missing offline 4-seat support as a new kernel module modelled on
   `online_2v2_*` (all-local, no transport).
4. **Stage B (fallback only):** if single-process 4-player proves
   impossible, fall back to 4 instances + `TTT2_NET=loopback`, accepting
   the performance investigation risk.

## 8. Major technical challenges

1. **The decisive unknown:** does offline pairing accept 4 humans? [U]
2. Recompiled gameplay code can only be changed via hooks/patches — every
   gameplay change is reverse-engineering work against generated code [C].
3. Approach B: 4× render/CPU load on one laptop; per-instance pad
   filtering and profile isolation are mandatory kernel changes [I].
4. Join choreography: the "Press START of controller in use" screens only
   react to START — the four phones must press in a controlled sequence,
   or the flow must be driven for them (synth presses exist in the port)
   [C].
5. Guest users 1-3 cannot save; per-player profiles/progress need care [C].
6. Input latency budget: phone→WS→server→ViGEm→game chain must be measured
   (Phase 7); source-counted release already prevents stuck buttons [C].
7. No git history in the local copy; the dev-rule "work on a branch"
   requires re-initializing the repo first [C].
8. Repo root `README.md` and some docs exist only in the local copy — the
   GitHub source of truth may differ; keep the local copy as reference [I].

## 9. Confirmed vs assumed (summary table)

| Question (spec §10) | Answer |
|---|---|
| Does online PAIR PLAY support 4 independent player identities? | **Yes** [C] — 4 seats, 4 controllers, per-participant pads |
| Is player ownership separated from team ownership? | **Yes** — roles (host/partner) vs side (red/blue), fighter slots 9-12 [C] |
| Can the game instantiate four logical player controllers? | Kernel layer: **yes** (users 0-3) [C]; offline game flow: **unverified** [U] |
| Does the match simulation expect exactly two player objects? | The fight has two **sides**, each with fighter+partner (4 fighters, slots 9-12) [C] |
| Is Steam only matchmaking or essential to gameplay? | Not essential: transport is pluggable, `loopback` works with no Steam [C]; Steam adds identity/discovery [C] |
| Can the networking layer be replaced with local communication? | **Already done by the port**: `TTT2_NET=loopback` [C]; a LAN-across-machines backend would be new [I] |
| Can the game run entirely offline after modification? | Offline play already runs with no Steam/internet today [C] |
| Is the source complete enough to implement the behavior? | Hand-written port code: yes; recompiled game code must be regenerated from the user's disc to rebuild [C] |

## 10. Information needed from the operator

1. **Approval of the staged C-first plan** (§7) before any gameplay code
   is touched.
2. **A live test session** (Stage C1): the laptop, the game, and four
   phones (or the agent driving synthetic pads) to answer the decisive
   unknown.
3. Confirmation whether the ISO copy of the game was archived somewhere
   before deletion (needed only if the port must ever be rebuilt from
   source; not needed for any planned phase).
4. Optional: laptop CPU/GPU model — only relevant if Approach B (4
   instances) has to be evaluated seriously.
