import ctypes, sys, time

# XInput structs
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short), ("sThumbRY", ctypes.c_short)]
class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_uint), ("Gamepad", XINPUT_GAMEPAD)]

xinput = ctypes.WinDLL("xinput1_4")
state = XINPUT_STATE()
names = {0x1000:"A",0x2000:"B",0x4000:"X",0x8000:"Y",0x0010:"START",0x0020:"BACK",
         0x0100:"LB",0x0200:"RB",0x0001:"UP",0x0002:"DOWN",0x0004:"LEFT",0x0008:"RIGHT"}
last = None
deadline = time.time() + 7
while time.time() < deadline:
    for user in (0, 1):
        if xinput.XInputGetState(user, ctypes.byref(state)) == 0:
            g = state.Gamepad
            cur = tuple(sorted(n for m, n in names.items() if g.wButtons & m)) + (g.sThumbLX,)
            if cur != last:
                print(f"user{user}: buttons={cur[:12]} lx={g.sThumbLX}", flush=True)
                last = cur
        else:
            cur = "disconnected"
            if cur != last:
                print(f"user{user}: {cur}", flush=True)
                last = cur
    time.sleep(0.05)
print("reader done", flush=True)
