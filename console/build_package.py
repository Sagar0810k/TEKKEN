"""TTT2 Local Lounge - buyer package builder (SELLER-ONLY).

Produces ONE file:  dist/TTT2_Local_Lounge_SETUP.bat

What the buyer does: double-click it. It extracts the full lounge system
into a TTT2_Local_Lounge folder next to itself, tells the buyer to read
START_HERE.txt, and then DELETES ITSELF - the installer file is gone after
the first extraction, so the raw package cannot simply be passed around.

What is inside: the lounge system ONLY (server, dashboard, phone controller,
fonts, setup helpers). NO license key, NO keygen.py, NO issued-keys CSV, NO
README/project docs, NO seller settings. The software starts LOCKED; the
buyer sees their laptop fingerprint on the activation screen and sends it
to the seller to receive a key minted for that laptop.

Why a self-extracting .bat and not a plain .zip: a zip is passive - Windows
runs nothing during extraction, so no zip can ever "destroy itself". The
installer file CAN: it unpacks and then erases itself.

Usage:  python build_package.py
"""

import base64
import io
import time
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DIST = REPO / "dist"

# Whitelist: ONLY these files ship to buyers. Everything else in the repo
# (keygen.py, licenses_issued.csv, license.json, demo_keygen.bat, README.md,
# *.md docs, images/, tools/, game_files/, the game port tree) stays out.
FILES = [
    ("console", "server.py"),
    ("console", "ttt2_license.py"),
    ("console", "start_server.bat"),
    ("console", "INSTALL.bat"),
    ("console", "requirements.txt"),
    ("console", "static", "controller.html"),
    ("console", "static", "operator.html"),
    ("console", "static", "fonts", "f6.woff2"),
    ("console", "static", "fonts", "f12.woff2"),
]

START_HERE = """TTT2 LOCAL LOUNGE - QUICK SETUP
==============================

Your seller sent you (usually as a Google Drive folder):
  1. TTT2_Local_Lounge_SETUP.bat   - this system (you already ran it)
  2. Game Install.pdf              - the full illustrated step-by-step guide
  3. The Tekken disc image (.iso) and TU3 - as ZIP files: extract both
     before using them
  4. ttt2_setup.exe                - builds the PC game from the ISO + TU3

Follow "Game Install.pdf" step by step. The short version:

  1. Install Python (python.org - tick "Add python.exe to PATH")
  2. Extract the ISO zip and TU3 zip (right-click -> Extract All)
  3. Run ttt2_setup.exe -> give it the extracted ISO and TU3 locations
     -> it builds the game
  4. Double-click console\\INSTALL.bat (installs libraries + the virtual
     controller driver, and asks you to DRAG the game .exe in)
  5. Double-click console\\start_server.bat
     -> send the laptop fingerprint shown on the dashboard to your seller
     -> type the key they send back -> Activate. Forever on this laptop.
  6. Phones on the same Wi-Fi: open the player links or scan the QRs on
     the dashboard. Press "Start game", then OFFLINE MODE -> PAIR PLAY
     is the 4-player 2v2 mode.

If anything fails, run console\\INSTALL.bat again - it fixes
libraries, driver and game path in one go.
"""

SETUP_TEMPLATE = """@echo off
title TTT2 Local Lounge - Setup
setlocal
set "ME=%~f0"
set "DEST=%~dp0TTT2_Local_Lounge"
set "WORK=%TEMP%\\ttt2_setup_%RANDOM%"
set "PAYLOAD=%WORK%\\payload.b64"
set "ZIPFILE=%WORK%\\package.zip"
echo.
echo   TTT2 LOCAL LOUNGE - one-click setup
echo   -----------------------------------
echo   Extracting the system now...
echo   (this installer deletes itself when it is done)
echo.
mkdir "%WORK%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=[IO.File]::ReadAllText($env:ME); $i=$c.IndexOf('---PAYLOAD' + '---'); [IO.File]::WriteAllText($env:PAYLOAD, $c.Substring($i+13).Trim())"
if not exist "%PAYLOAD%" goto fail
certutil -f -decode "%PAYLOAD%" "%ZIPFILE%" >nul 2>&1
if not exist "%ZIPFILE%" goto fail
if exist "%DEST%" rmdir /s /q "%DEST%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [IO.Compression.ZipFile]::ExtractToDirectory($env:ZIPFILE, $env:DEST)"
if errorlevel 1 goto fail
if not exist "%DEST%\\START_HERE.txt" goto fail
del "%PAYLOAD%" "%ZIPFILE%" >nul 2>&1
rmdir "%WORK%" >nul 2>&1
echo   Extracted to:  %DEST%
echo.
echo   NEXT: open that folder and read START_HERE.txt
echo   (activate your license, set your game path, play)
echo.
echo   This installer file is deleting itself now.
echo.
pause
(goto) 2>nul & del "%~f0"
exit /b 0
:fail
echo   SETUP FAILED - take a screenshot and send it to your seller.
echo   (leftover temp files in %WORK%)
pause
exit /b 1

---PAYLOAD---
"""


def _payload_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for parts in FILES:
            src = Path(REPO, *parts)
            if src.exists():
                z.write(src, "/".join(parts))
        z.writestr("console/layouts/", "")
        z.writestr("console/settings.json", '{\n  "game_exe": ""\n}\n')
        z.writestr("START_HERE.txt", START_HERE)
        z.writestr("package_id.txt",
                   "TTT2 Local Lounge package - built {when}\n"
                   "No license key and no seller tools inside.\n".format(
                       when=datetime.now().strftime("%Y-%m-%d %H:%M")))
    return buf.getvalue()


def build() -> dict:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"TTT2_Local_Lounge_SETUP.bat"

    payload = base64.b64encode(_payload_zip()).decode()
    chunks = [payload[i:i + 1024] for i in range(0, len(payload), 1024)]
    text = SETUP_TEMPLATE + "\n".join(chunks) + "\n"
    out.write_text(text, encoding="ascii", newline="\r\n")
    return {"ok": True, "path": str(out), "bytes": out.stat().st_size}


if __name__ == "__main__":
    r = build()
    print(f"built {r['path']} ({r['bytes']:,} bytes)")
    print("Share THIS file with the buyer. It extracts once, then deletes itself.")
