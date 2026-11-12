import ctypes, time

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short), ("sThumbRY", ctypes.c_short)]
class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_uint), ("Gamepad", XINPUT_GAMEPAD)]

xinput = ctypes.WinDLL("xinput9_1_0")
state = XINPUT_STATE()
for user in range(4):
    r = xinput.XInputGetState(user, ctypes.byref(state))
    if r == 0:
        g = state.Gamepad
        print(f"user{user}: CONNECTED buttons=0x{g.wButtons:04X} lx={g.sThumbLX} ly={g.sThumbLY}")
    else:
        print(f"user{user}: not connected (err {r})")

# watch user0/user1 for a few seconds for presses
names = {0x1000:"A",0x2000:"B",0x4000:"X",0x8000:"Y",0x0010:"START",0x0020:"BACK",
         0x0100:"LB",0x0200:"RB",0x0001:"UP",0x0002:"DOWN",0x0004:"LEFT",0x0008:"RIGHT"}
last = {}
deadline = time.time() + 8
while time.time() < deadline:
    for user in (0, 1):
        if xinput.XInputGetState(user, ctypes.byref(state)) == 0:
            g = state.Gamepad
            cur = tuple(sorted(n for m, n in names.items() if g.wButtons & m)) + (g.sThumbLX,)
            if last.get(user) != cur:
                print(f"user{user}: {cur}", flush=True)
                last[user] = cur
    time.sleep(0.05)
print("done", flush=True)
