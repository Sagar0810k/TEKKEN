"""Stage C1 driver: scripted presses on the four virtual pads, in
first-press order, to walk the game's offline pairing flow.

Usage:
  python c1_driver.py 1:START            press START on player 1 (120 ms)
  python c1_driver.py 1:A:400            hold A 400 ms
  python c1_driver.py 2:dpad:1:0:300     hold dpad right 300 ms
  python c1_driver.py 1:LB:150 2:A:200   several actions in order
Actions: <player>:<BUTTON>[:ms] | <player>:dpad:x:y[:ms]
"""
import asyncio, json, sys, urllib.request
import websockets

BASE = "http://localhost:8000"

def token(slot):
    with urllib.request.urlopen(f"{BASE}/api/session/player{slot}") as r:
        return json.load(r)["token"]

async def run(actions):
    conns = {}
    for a in actions:
        parts = a.split(":")
        slot = int(parts[0])
        if slot not in conns:
            conns[slot] = await websockets.connect(
                f"ws://localhost:8000/ws/player{slot}?token={token(slot)}")
            # absorb init message
            try: await asyncio.wait_for(conns[slot].recv(), timeout=2)
            except Exception: pass
        ws = conns[slot]
        if parts[1] == "dpad":
            x, y = int(parts[2]), int(parts[3])
            ms = int(parts[4]) if len(parts) > 4 else 200
            await ws.send(json.dumps({"t": "d", "x": x, "y": y}))
            await asyncio.sleep(ms / 1000)
            await ws.send(json.dumps({"t": "d", "x": 0, "y": 0}))
        else:
            btn, ms = parts[1], int(parts[2]) if len(parts) > 2 else 120
            await ws.send(json.dumps({"t": "b", "b": btn, "s": 1}))
            await asyncio.sleep(ms / 1000)
            await ws.send(json.dumps({"t": "b", "b": btn, "s": 0}))
        await asyncio.sleep(0.08)
    for ws in conns.values():
        try:
            await ws.send(json.dumps({"t": "rel"}))
            await ws.close()
        except Exception: pass

if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:]))
