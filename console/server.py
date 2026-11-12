"""Tekken Tag Tournament 2 - local two-player console server (Phase 2 skeleton).

One server, one configurable port. Player entry routes are exactly
/player1 through /player4. The laptop operator dashboard is served at /.

Input path: phone touch -> browser -> WebSocket -> this input manager.
The virtual-gamepad bridge is a stub for now (Phase 1); the operator
dashboard mirrors live input state so the pipeline can be tested.
"""

import asyncio
import base64
import io
import json
import socket
import subprocess
import time
import uuid
from pathlib import Path

import qrcode
import uvicorn
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
LAYOUTS = ROOT / "layouts"
LAYOUTS.mkdir(exist_ok=True)
GAME_FILES = ROOT.parent / "game_files"
SETTINGS_PATH = ROOT / "settings.json"

PORT = int(Path("port.txt").exists() and Path("port.txt").read_text().strip() or 8000)
HEARTBEAT_TIMEOUT = 6.0  # seconds without any message before a slot is force-released
SLOTS = ("player1", "player2", "player3", "player4")

# ---------------------------------------------------------------------------
# Input state
# ---------------------------------------------------------------------------

class PlayerState:
    def __init__(self):
        self.ws: WebSocket | None = None
        self.token = uuid.uuid4().hex[:12]
        self.connected = False
        self.ready = False
        self.last_seen = 0.0
        self.buttons: set[str] = set()
        self.dpad = {"x": 0, "y": 0}
        self.sticks = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}

    def release_all(self):
        self.buttons.clear()
        self.dpad = {"x": 0, "y": 0}
        self.sticks = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}

    def snapshot(self):
        return {
            "connected": self.connected,
            "ready": self.ready,
            "buttons": sorted(self.buttons),
            "dpad": self.dpad,
            "sticks": self.sticks,
        }


players = {slot: PlayerState() for slot in SLOTS}
game_process: subprocess.Popen | None = None

# ---------------------------------------------------------------------------
# Virtual gamepad bridge (Phase 1)
#
# The game polls pads over XInput (XamInputSetState), so each phone slot gets
# one ViGEm virtual Xbox 360 controller. Whoever presses a button first in-game
# is player 1; press a button on the PLAYER 1 phone first.
# ---------------------------------------------------------------------------

try:
    import vgamepad as vg
except Exception:  # driver or library missing -> dashboard still works
    vg = None

XUSB_MAP: dict[str, int] = {}
XUSB_DPAD_UP = XUSB_DPAD_DOWN = XUSB_DPAD_LEFT = XUSB_DPAD_RIGHT = 0
_pads: dict[str, object] = {}
_pad_buttons: dict[str, set[int]] = {s: set() for s in SLOTS}
_bridge_ready = False


def init_bridge():
    """Create the two virtual pads once, at startup."""
    global _bridge_ready
    if _bridge_ready or vg is None:
        return
    try:
        global XUSB_DPAD_UP, XUSB_DPAD_DOWN, XUSB_DPAD_LEFT, XUSB_DPAD_RIGHT
        XUSB_DPAD_UP = vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP
        XUSB_DPAD_DOWN = vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN
        XUSB_DPAD_LEFT = vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT
        XUSB_DPAD_RIGHT = vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
        for name, xb in (
            ("A", "XUSB_GAMEPAD_A"),           # left kick
            ("B", "XUSB_GAMEPAD_B"),           # right kick
            ("X", "XUSB_GAMEPAD_X"),           # left punch
            ("Y", "XUSB_GAMEPAD_Y"),           # right punch
            ("LB", "XUSB_GAMEPAD_LEFT_SHOULDER"),   # tag
            ("RB", "XUSB_GAMEPAD_RIGHT_SHOULDER"),  # tag
            ("TAG", "XUSB_GAMEPAD_RIGHT_SHOULDER"),  # alias of RB
            ("START", "XUSB_GAMEPAD_START"),
            ("BACK", "XUSB_GAMEPAD_BACK"),
        ):
            XUSB_MAP[name] = getattr(vg.XUSB_BUTTON, xb)
        for slot in SLOTS:
            _pads[slot] = vg.VX360Gamepad()
        _bridge_ready = True
        print(f"bridge: {len(SLOTS)} virtual Xbox 360 pads ready")
    except Exception as e:
        print(f"bridge: vgamepad unavailable ({e}) - inputs stay dashboard-only")


def bridge_update(slot: str):
    """Feed this slot's state into its virtual XInput pad (phone -> game).

    Each slot owns one ViGEm virtual Xbox 360 controller, created at startup.
    State is per-slot: one phone disconnecting never touches the other pad.
    """
    if not _bridge_ready:
        return
    pad = _pads.get(slot)
    if pad is None:
        return
    p = players[slot]

    # Target set of pressed XInput flags from the phone's logical buttons.
    target: set[int] = set()
    for name in p.buttons:
        xb = XUSB_MAP.get(name)
        if xb is not None:
            target.add(xb)

    # D-pad directions from the phone (x: -1 left / +1 right, y: -1 up / +1 down).
    x, y = p.dpad.get("x", 0), p.dpad.get("y", 0)
    if y < 0: target.add(XUSB_DPAD_UP)
    if y > 0: target.add(XUSB_DPAD_DOWN)
    if x < 0: target.add(XUSB_DPAD_LEFT)
    if x > 0: target.add(XUSB_DPAD_RIGHT)

    cur = _pad_buttons[slot]
    for flag in target - cur:
        pad.press_button(flag)
    for flag in cur - target:
        pad.release_button(flag)
    _pad_buttons[slot] = target

    # Left stick. Phone ly is down-positive; XInput LY is up-positive.
    pad.left_joystick_float(p.sticks.get("lx", 0.0), -p.sticks.get("ly", 0.0))
    pad.update()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def lan_ip() -> str:
    """Best-effort reachable LAN IPv4, without sending any packets."""
    for probe in ("8.8.8.8", "10.255.255.255", "192.168.255.255"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 1))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            continue
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def qr_data_url(text: str) -> str:
    img = qrcode.make(text, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def template_default() -> dict:
    """Starter template: Classic Arcade. Portrait (x, y) + landscape (xL, yL)."""
    return {
        "name": "Classic Arcade",
        "buttons": [
            {"b": "A", "x": 76, "y": 62, "size": 16, "xL": 86, "yL": 74},
            {"b": "B", "x": 88, "y": 51, "size": 16, "xL": 93, "yL": 64},
            {"b": "X", "x": 64, "y": 51, "size": 16, "xL": 79, "yL": 64},
            {"b": "Y", "x": 76, "y": 40, "size": 16, "xL": 86, "yL": 54},
            {"b": "LB", "x": 14, "y": 10, "size": 12, "xL": 10, "yL": 12},
            {"b": "RB", "x": 86, "y": 10, "size": 12, "xL": 90, "yL": 12},
            {"b": "START", "x": 58, "y": 94, "size": 9, "xL": 56, "yL": 92},
            {"b": "BACK", "x": 46, "y": 94, "size": 9, "xL": 43, "yL": 92},
            {"b": "TAG", "x": 95, "y": 78, "size": 11, "xL": 70, "yL": 92},
        ],
        "dpad": {"x": 25, "y": 55, "size": 34, "xL": 17, "yL": 73},
        "nub": {"x": 25, "y": 88, "size": 16, "xL": 15, "yL": 42},
        "opacity": 0.5,
    }


_layout_cache: dict[str, dict] = {}


def load_layout(slot: str) -> dict:
    if slot not in _layout_cache:
        path = LAYOUTS / f"{slot}.json"
        if path.exists():
            try:
                _layout_cache[slot] = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                _layout_cache[slot] = template_default()
        else:
            _layout_cache[slot] = template_default()
    return _layout_cache[slot]


def save_layout(slot: str, cfg: dict) -> None:
    _layout_cache[slot] = cfg  # writes happen only on explicit layout saves
    (LAYOUTS / f"{slot}.json").write_text(json.dumps(cfg, indent=2))


def valid_button(slot: str, name) -> bool:
    return isinstance(name, str) and any(btn["b"] == name for btn in load_layout(slot)["buttons"])


def game_files_status() -> list[dict]:
    found = []
    if GAME_FILES.exists():
        for p in sorted(GAME_FILES.iterdir()):
            if p.is_file() and not p.name.upper().startswith("README"):
                found.append({"name": p.name, "bytes": p.stat().st_size})
    return found


def game_exe() -> str:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text()).get("game_exe", "")
        except (json.JSONDecodeError, OSError):
            pass
    return ""


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

app = FastAPI(title="TTT2 Local Console", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", response_class=HTMLResponse)
async def operator():
    return (STATIC / "operator.html").read_text(encoding="utf-8")


@app.get("/player1", response_class=HTMLResponse)
@app.get("/player2", response_class=HTMLResponse)
@app.get("/player3", response_class=HTMLResponse)
@app.get("/player4", response_class=HTMLResponse)
async def player_page():
    return (STATIC / "controller.html").read_text(encoding="utf-8")


@app.get("/api/session/{slot}")
async def session_info(slot: str):
    if slot not in SLOTS:
        return JSONResponse({"error": "unknown slot"}, status_code=404)
    return {"slot": slot, "token": players[slot].token, "layout": load_layout(slot)}


@app.get("/api/template")
async def template_info():
    """Default layout, used by the editor's 'Reset to default'."""
    return template_default()


@app.post("/api/config/{slot}")
async def config_save(slot: str, body: dict):
    if slot not in SLOTS:
        return JSONResponse({"error": "unknown slot"}, status_code=404)
    save_layout(slot, body)
    return {"ok": True}


@app.get("/api/status")
async def status():
    ip = lan_ip()
    base = f"http://{ip}:{PORT}"
    return {
        "ip": ip,
        "port": PORT,
        "url": base,
        "players": {s: players[s].snapshot() for s in SLOTS},
        "qr": {s: qr_data_url(f"{base}/{s}") for s in SLOTS},
        "game_files": game_files_status(),
        "game_exe": game_exe(),
        "game_running": game_process is not None and game_process.poll() is None,
    }


@app.post("/api/game/start")
async def game_start():
    """Launch the configured game executable (path set locally in settings.json)."""
    global game_process
    exe = game_exe()
    if not exe or not Path(exe).exists():
        return JSONResponse({"error": "game path not configured or missing"}, status_code=400)
    if game_process is not None and game_process.poll() is None:
        return {"ok": True, "already_running": True}
    game_process = subprocess.Popen([exe])
    return {"ok": True}


@app.post("/api/game/stop")
async def game_stop():
    global game_process
    if game_process is not None and game_process.poll() is None:
        game_process.terminate()
    game_process = None
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket: one persistent connection per player slot
# ---------------------------------------------------------------------------

async def ws_send(ws: WebSocket, msg: dict):
    try:
        await ws.send_text(json.dumps(msg))
    except Exception:
        pass


@app.websocket("/ws/{slot}")
async def player_ws(ws: WebSocket, slot: str, token: str = Query("")):
    if slot not in SLOTS:
        await ws.close(code=1008)
        return
    await ws.accept()
    await handle_player_ws(slot, ws, token)


async def handle_player_ws(slot: str, ws: WebSocket, token: str):
    p = players[slot]

    if p.connected and p.token != token:
        # Slot is owned by another session; refuse silently hijacking.
        await ws_send(ws, {"t": "denied", "reason": "slot in use; request takeover"})
        return

    takeover = p.connected
    p.ws = ws
    p.connected = True
    p.last_seen = time.monotonic()
    bridge_update(slot)
    await ws_send(ws, {"t": "init", "slot": slot, "took_over": takeover,
                       "layout": load_layout(slot)})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue  # reject malformed, keep the connection
            mtype = msg.get("t")
            p.last_seen = time.monotonic()

            if mtype == "b":
                b = msg.get("b")
                if valid_button(slot, b):
                    if msg.get("s"):
                        p.buttons.add(b)
                    else:
                        p.buttons.discard(b)
                bridge_update(slot)
            elif mtype == "d":
                x, y = msg.get("x", 0), msg.get("y", 0)
                if isinstance(x, int) and isinstance(y, int) and -1 <= x <= 1 and -1 <= y <= 1:
                    p.dpad = {"x": x, "y": y}
                bridge_update(slot)
            elif mtype == "s":
                sticks = msg.get("v", {})
                if isinstance(sticks, dict):
                    p.sticks = {k: float(sticks.get(k, 0.0)) for k in p.sticks}
                bridge_update(slot)
            elif mtype == "hb":
                pass
            elif mtype == "rel":
                p.release_all()
                bridge_update(slot)
            elif mtype == "ready":
                p.ready = bool(msg.get("v"))
            elif mtype == "cfg":
                cfg = msg.get("cfg")
                if isinstance(cfg, dict):
                    save_layout(slot, cfg)
            else:
                continue  # unknown message types ignored
    except WebSocketDisconnect:
        pass
    finally:
        # Disconnect must never leave stuck buttons and must not affect
        # the other player's state (state is per-slot).
        if p.ws is ws:
            p.connected = False
            p.ready = False
            p.ws = None
            p.release_all()
            bridge_update(slot)


async def watchdog():
    """Force-release any player whose phone went stale without a disconnect."""
    while True:
        await asyncio.sleep(2.0)
        now = time.monotonic()
        for slot, p in players.items():
            if p.connected and p.ws is not None and now - p.last_seen > HEARTBEAT_TIMEOUT:
                try:
                    await p.ws.close()
                except Exception:
                    pass
                p.connected = False
                p.ready = False
                p.ws = None
                p.release_all()
                bridge_update(slot)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(watchdog())
    init_bridge()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
