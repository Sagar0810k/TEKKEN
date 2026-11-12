# Tekken Tag Tournament 2 --- Local Two-Player Gaming System

## Agent Project Brief & Technical Specification

**Project status:** Planning / implementation brief\
**Primary goal:** Build a lightweight local-network gaming system that
lets two smartphones act as independent controllers for Tekken Tag
Tournament 2 running on a Windows laptop, with gameplay displayed on a
TV over HDMI.

------------------------------------------------------------------------

## 1. Product vision

Create a small, self-hosted gaming console experience:

-   A Windows laptop runs the game and hosts the local web server.
-   A TV connected to the laptop through HDMI displays the game.
-   Two smartphones connect to the laptop over the same local Wi-Fi
    network.
-   Each phone opens its own player route and becomes that player's
    touch controller.
-   The laptop translates phone inputs into two independent Windows
    game-controller inputs.
-   The system should work on the local network without cloud services
    or an Internet connection during normal play.

This is a **controller and local session-management system**, not a
game-streaming system. Do not stream gameplay video to the phones.

## 2. Non-negotiable design decisions

1.  **One local server and one configurable port.**
2.  The two player entry routes are:
    -   `/player1`
    -   `/player2`
3.  Do not create separate public routes for settings, templates, or the
    dashboard unless a real requirement emerges. These can be internal
    screens/components inside the two player experiences or the laptop
    launcher.
4.  Both routes use the same server, shared session, input manager, and
    game instance.
5.  Player 1 and Player 2 must have independent controller state and
    independent saved layouts.
6.  First-time users must complete controller setup before playing.
7.  Provide ready-made controller templates first; allow users to
    customize them.
8.  Save controller configurations locally so users do not need to
    repeat setup every time.
9.  Keep the application as lightweight as possible without compromising
    input responsiveness, stable game frame rate, or reliability.
10. Do not begin with a universal game launcher. The first supported
    game is Tekken Tag Tournament 2 only.

## 3. Example local-network experience

When the laptop application starts, it should:

1.  Start the local server on a configurable port.
2.  Determine and display the laptop's reachable LAN IPv4 address.
3.  Display the complete player URLs and QR codes.
4.  Show whether each player slot is connected.
5.  Allow the operator to launch or close the configured game.
6.  Keep the server and game as separate processes.

Example only:

-   Player 1: `http://192.168.1.5:8000/player1`
-   Player 2: `http://192.168.1.5:8000/player2`

The IP address must be discovered at runtime. Do not hardcode the
example address. Handle changing DHCP addresses and multiple network
adapters sensibly. Bind the server to the LAN interface or `0.0.0.0` as
appropriate, and show the actual reachable address to the user.

A QR code should encode each complete player URL. Manual URL entry
should also work.

## 4. User journey

### First-time setup for each player

1.  Player scans their assigned QR code or enters their player URL.
2.  The server validates and reserves the requested player slot.
3.  The phone opens the player setup experience.
4.  The player selects a predefined layout template.
5.  The player previews and customizes the layout.
6.  The player tests buttons and directional inputs.
7.  The player saves the layout.
8.  The phone enters the ready state and waits for the game session to
    start.

### Returning player

1.  Player opens their assigned route.
2.  The application loads that player's saved configuration.
3.  The player can use it immediately or choose to edit it.
4.  The phone connects to the active session and shows ready/connected
    status.

### Starting a match

1.  Both player slots are connected and ready.
2.  The laptop operator starts the configured game.
3.  The controller bridge exposes two independent gamepads.
4.  The game recognizes Player 1 and Player 2.
5.  Gameplay appears on the TV through HDMI.

Do not assume the game is ready merely because both phones have
connected. Include a controller test and a clear ready state.

## 5. Player routes and session model

### Public routes

  -----------------------------------------------------------------------
  Route                               Purpose
  ----------------------------------- -----------------------------------
  `/player1`                          Player 1 setup, saved layout,
                                      connection and controller UI

  `/player2`                          Player 2 setup, saved layout,
                                      connection and controller UI
  -----------------------------------------------------------------------

### Real-time communication

Use one persistent WebSocket connection per phone, associated with its
player slot. The exact WebSocket URL may be an internal implementation
detail; the user-facing entry points remain `/player1` and `/player2`.

The server must:

-   Validate player-slot ownership.
-   Prevent two phones from silently controlling the same slot.
-   Support a deliberate reconnect or takeover flow.
-   Maintain separate input state for each player.
-   Reject malformed or out-of-session messages.
-   Send connection and readiness status to the phone.
-   Release all active inputs if a phone disconnects or becomes stale.

Use a session identifier and short-lived pairing token or equivalent
local-session mechanism. Do not rely solely on the route name as
authorization. Keep the system LAN-only by default and do not expose it
to the public Internet.

## 6. Controller templates and customization

Provide a small number of useful starter templates. Suggested initial
templates:

-   **Classic Arcade:** directional pad and four primary action buttons.
-   **Six-Button:** directional pad and six action buttons.
-   **Minimal:** fewer, larger controls.
-   **Custom:** user-created layout.

These are layout presets, not assumptions about the game's exact button
mapping. Confirm the native port's supported controller mapping and
configure the logical actions accordingly.

### Customization requirements

Users should be able to:

-   Drag buttons to reposition them.
-   Resize buttons.
-   Adjust button opacity.
-   Change button spacing.
-   Choose a left- or right-handed arrangement.
-   Remap a logical action to a supported gamepad control.
-   Hide optional controls.
-   Preview the layout.
-   Test press and release behavior.
-   Restore the selected template.
-   Save the layout locally.

Use touch-friendly controls and support multi-touch. A directional input
and multiple action buttons must be usable simultaneously.

### Configuration persistence

Store configuration on the laptop, keyed by player slot and, where
useful, a device/profile identifier. A phone should not accidentally
overwrite the other player's configuration.

Use a small JSON configuration file or similarly lightweight local store
initially. Do not store every button press in a database. Consider
export/import of layouts as a later feature.

## 7. Input pipeline and latency requirements

Expected input path:

`Phone touch → browser event → WebSocket → laptop input manager → native gamepad bridge → game input sampling → rendered frame → TV`

Optimize the entire path, not just WebSocket performance.

Requirements:

-   Use Pointer Events or an equivalent robust touch-input mechanism.
-   Handle `pointerdown`, `pointerup`, `pointercancel`, and lost-pointer
    cases.
-   Prevent unwanted browser scrolling, zooming, text selection, and
    gesture handling on the controller surface.
-   Support simultaneous touches.
-   Send button-down and button-up transitions promptly.
-   Do not add artificial batching or debounce delays to gameplay
    inputs.
-   Keep messages small. Start with simple compact messages; only adopt
    a binary protocol if profiling demonstrates a meaningful benefit.
-   Avoid excessive polling. Prefer event-driven updates, with a
    sensible heartbeat and optional state reconciliation.
-   Maintain independent pressed-button state per player.
-   Handle repeated, out-of-order, stale, and duplicate messages safely.
-   Add a disconnect watchdog that releases all buttons for the affected
    player.
-   On page hide, disconnect, or connection loss, attempt to release all
    active controls.
-   Never let one player's disconnect or input affect the other player's
    state.

Measure: - Phone-to-server round-trip time. - Server message handling
time. - Native bridge update time. - Disconnect/reconnect behavior. -
End-to-end touch-to-visible-action latency where practical. - Packet
loss and jitter. - Game FPS and frame-time consistency.

Do not promise a fixed end-to-end latency before measurement. Network
latency is only one part of the total input delay.

## 8. Native controller bridge

The browser Gamepad API is not a solution for sending remote phone
inputs to a Windows game. It reads game controllers attached to the
device running the browser; it does not turn a phone browser into a
controller automatically recognized by a separate laptop game.

Implement or integrate a Windows-side native bridge that:

1.  Receives the server's logical input state.
2.  Exposes two independent Xbox-compatible virtual gamepads to Windows.
3.  Maps Player 1 only to virtual controller 1.
4.  Maps Player 2 only to virtual controller 2.
5.  Updates button and directional state promptly.
6.  Releases all controls on disconnect or shutdown.
7.  Starts and stops cleanly with the local application.

Before selecting a driver, verify that it is maintained, compatible with
the target Windows version, and safe to install. Do not assume a
discontinued virtual-controller driver is the default choice. Document
any driver installation and its security implications.

**Critical proof of concept:** Before building the complete UI, prove
that two independent virtual gamepads can be created and that the
selected Tekken build recognizes them as two local players. The native
port's controller assignment behavior must be tested rather than
assumed.

## 9. Game choice and ISO handling

The preferred initial route is the unofficial native Windows
recompilation project:

`https://github.com/shihabal3amri/tekken-tag-tournament-2-pc`

The project is based on the Xbox 360 version and advertises native
Windows execution, DirectX 11, a 60 FPS target, local two-player
support, and low-latency options. These are project claims and must be
independently tested on the target laptop.

The project documentation indicates that it requires:

-   A supported USA or Europe Xbox 360 retail game disc image.
-   The required Xbox 360 Title Update 3.
-   Its installer/build process.

Important distinctions:

-   An ISO is a disc image, not a universal Windows executable.
-   A PS3 ISO is not interchangeable with an Xbox 360 image.
-   The Xbox 360 image is the preferred source only because the chosen
    native recompilation project targets that version.
-   If the native port is unsuitable, the fallback depends on the game
    platform: Xenia for Xbox 360, RPCS3 for PS3, or Cemu for Wii U.
-   Do not download, bundle, redistribute, or provide links to
    unauthorized game ROMs, disc images, or copyrighted game updates.
-   The user must supply game files they are legally entitled to use.
-   Do not silently bypass Windows SmartScreen or other security
    warnings. Review project source, releases, checksums/signatures
    where available, and installation requirements before running
    executables.

The game launcher should initially support a configured native-port
installation. Do not build automatic ISO conversion or a multi-emulator
abstraction until the native-port proof of concept is complete.

## 10. Performance and lightweight implementation

Target machine currently known:

-   Intel Core i3, 11th generation.
-   8 GB RAM.
-   Exact CPU SKU, GPU, storage type, and memory-channel configuration
    are not yet known.

Performance priorities, in order:

1.  Stable game frame pacing and target 60 FPS.
2.  Low and consistent input latency.
3.  Reliable two-player input.
4.  Fast startup and low idle resource use.
5.  Good mobile usability.

Tekken Tag Tournament 2 is designed around 60 FPS gameplay. Do not chase
120/144 FPS at the expense of correct game timing or stability.

### Lightweight stack proposal

Prefer the simplest stack that meets the requirements:

-   Frontend: plain HTML, CSS, and JavaScript.
-   Server: FastAPI with an efficient ASGI server, or another comparably
    lightweight local server if it materially reduces complexity.
-   Real-time transport: WebSockets.
-   State: in-memory input state; local JSON for saved settings.
-   Native integration: small Windows-side bridge.
-   QR code: generate locally.
-   No cloud services, analytics, remote fonts, external CDNs, or
    external runtime dependencies.

Avoid introducing Next.js, a database server, containers, Redis, a
message broker, or a large state-management framework without a
demonstrated need.

### Runtime behavior

-   The controller interface should be visually responsive but
    computationally quiet.
-   During gameplay, disable editor-only logic and unnecessary
    animations.
-   Do not run expensive effects on the phone.
-   Do not stream the game image to the phone.
-   Do not perform disk writes for every input.
-   Keep server processing event-driven.
-   Avoid unnecessary background threads and busy loops.
-   Keep the game process separate from the web server.
-   Do not change process priorities or CPU affinity aggressively
    without measurements.

### Network recommendations

-   Laptop connected to the router by Ethernet where practical.
-   Phones connected to the same 5 GHz Wi-Fi network where available.
-   Router close to the players.
-   No Internet dependency after local setup.
-   Show a useful error if phones are on a guest network or client
    isolation prevents device-to-device communication.

## 11. Game launch and laptop operator experience

The laptop needs a simple operator window or launcher. It should show:

-   Server status.
-   Local IP address and port.
-   QR code for Player 1.
-   QR code for Player 2.
-   Player connection and ready states.
-   Controller test status.
-   Configured game path/status.
-   Start game and stop game controls.
-   Basic FPS/performance information when available.

The operator UI is not a second complex web application. A small local
launcher or simple desktop window is sufficient.

Starting the game should be an explicit action after the operator can
see that both players are ready. Do not launch the game automatically
merely because one phone connects.

The game should render on the laptop and be displayed on the TV over
HDMI. Recommend enabling TV Game Mode if available.

## 12. Reliability and safety

-   Handle laptop IP changes and server restarts.
-   Show clear connection errors.
-   Prevent duplicate player-slot ownership.
-   Release buttons on disconnect, timeout, app shutdown, or session
    reset.
-   Provide a safe stop/cleanup path for the virtual controllers.
-   Validate all incoming WebSocket messages.
-   Restrict the service to the local network by default.
-   Use a session token or equivalent protection against accidental
    control by unknown devices on the LAN.
-   Do not expose the server port to the public Internet.
-   Do not execute arbitrary commands received from a phone.
-   Do not accept arbitrary executable paths from untrusted client
    messages.
-   Do not store sensitive information.

## 13. Suggested implementation phases

### Phase 0 --- Hardware and game feasibility

Before building the full application:

-   Identify exact CPU model, GPU, RAM configuration, and storage.
-   Verify the native port's current installation requirements.
-   Test the game independently.
-   Measure FPS and frame-time stability at 720p and other sensible
    resolutions.
-   Test a local two-player match.
-   Confirm the game recognizes two separate physical or virtual
    controllers.
-   Review the native port's security and project status.

**Exit condition:** The game runs acceptably and two-player input is
proven.

### Phase 1 --- Native controller proof of concept

-   Select a maintained Windows virtual-gamepad approach.
-   Create two independent virtual controllers.
-   Build a tiny local test sender or diagnostic tool.
-   Verify all required buttons and directional inputs.
-   Test simultaneous inputs and disconnect release.

**Exit condition:** Two independent gamepads are recognized correctly
and safely.

### Phase 2 --- Minimal local server

-   Start one local server on one configurable port.
-   Implement `/player1` and `/player2`.
-   Display LAN address and QR codes.
-   Implement one persistent WebSocket per player.
-   Add player-slot reservation and reconnect behavior.
-   Add basic connection status.

**Exit condition:** Two phones can connect simultaneously and remain
correctly assigned.

### Phase 3 --- Controller UI and templates

-   Build touch-first controller screens.
-   Add initial templates.
-   Add drag, resize, opacity, remapping, preview, and reset.
-   Save separate player configurations.
-   Verify multi-touch and button release behavior.

**Exit condition:** Both phones can control separate virtual gamepads
reliably.

### Phase 4 --- Game integration

-   Connect the input manager to the native bridge.
-   Verify both players in the actual game.
-   Add ready states and controller testing.
-   Add game launch/stop controls.
-   Display gameplay on the TV.

**Exit condition:** Two-phone local play works end to end.

### Phase 5 --- Profiling and polish

-   Measure end-to-end input behavior.
-   Measure CPU, memory, FPS, and frame times.
-   Remove unnecessary work.
-   Test Wi-Fi jitter, reconnects, browser backgrounding, and phone
    sleep.
-   Test different phone screen sizes and orientations.
-   Document setup and troubleshooting.

**Exit condition:** Stable, repeatable local play with no stuck inputs
and acceptable performance.

## 14. Acceptance criteria

The project is not complete until all of the following work:

-   [ ] One local server starts on one port.
-   [ ] `/player1` and `/player2` are the only player entry routes.
-   [ ] The laptop displays both QR codes and the LAN URLs.
-   [ ] Two phones can connect at the same time.
-   [ ] Player slots cannot be accidentally duplicated.
-   [ ] First-time setup offers predefined templates.
-   [ ] Users can customize and save their own layouts.
-   [ ] Returning users can load their saved layouts.
-   [ ] Multi-touch works correctly.
-   [ ] Simultaneous directional and action inputs work.
-   [ ] Disconnects never leave stuck buttons.
-   [ ] Two independent virtual gamepads are exposed to Windows.
-   [ ] The selected game build recognizes both players.
-   [ ] The game runs as one instance on the laptop.
-   [ ] Gameplay displays on the HDMI-connected TV.
-   [ ] No game video is streamed to the phones.
-   [ ] Normal gameplay does not require Internet or cloud services.
-   [ ] CPU and memory overhead from the controller system remains
    small.
-   [ ] Performance and input behavior are measured rather than guessed.

## 15. Agent working instructions

1.  Read this document before making architectural decisions.
2.  Do not start by generating the entire application.
3.  Work phase by phase and prove risky dependencies early.
4.  First investigate the native game port and prove two-controller
    compatibility.
5.  Do not assume a particular ISO, title update, driver, or controller
    mapping is compatible without testing.
6.  Keep dependencies and background processes to a minimum.
7.  Prefer readable, maintainable code over unnecessary abstraction.
8.  Do not add cloud infrastructure or external services.
9.  Do not invent performance results. Record measurements from the
    actual target machine.
10. Maintain a `DECISIONS.md` file recording chosen technologies,
    rejected alternatives, reasons, and unresolved questions.
11. Maintain a `TESTING.md` file recording hardware, game version,
    settings, FPS, frame-time observations, controller tests, and
    latency measurements.
12. If a critical dependency cannot be verified, stop and report the
    blocker instead of building on an unproven assumption.

------------------------------------------------------------------------

## Current unresolved information

The agent should request or help the user identify:

-   Exact Intel i3 11th-generation CPU model.
-   Exact GPU (Intel integrated graphics or dedicated NVIDIA/AMD).
-   RAM configuration and whether it is upgradeable.
-   SSD or HDD.
-   Windows version.
-   Whether the user can provide a legally obtained compatible Xbox 360
    game disc image and required update.
-   Whether the native Windows port currently works on this laptop.
-   Which Windows virtual-gamepad solution is maintained and compatible.

**Final guiding principle:** Build the smallest reliable local system
that delivers responsive two-player controls and stable Tekken gameplay.
The game must receive inputs directly through two independent native
gamepads; the web application should do as little work as possible
during a match.
