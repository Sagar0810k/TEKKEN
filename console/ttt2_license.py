"""TTT2 Local Lounge - offline license gate.

Model (decided 2026-11-13):
- A license key is a lifetime, single-seat grant: ONE key activates ONE laptop.
- Keys are FINGERPRINT-BOUND: the buyer sends their laptop fingerprint (shown
  on the activation screen), the seller mints the key for that fingerprint
  with keygen.py. SIG = HMAC-SHA256(serial|fingerprint, SECRET), so a key is
  mathematically invalid on any other laptop - even if the key text is shared.
- Activation additionally binds a tamper-checked record (license.json) to the
  machine fingerprint. After activation the buyer never needs the key again.
- Without a valid license the server runs in LOCKED mode: no virtual pads,
  no game control, phones redirected, dashboard shows only the activation
  screen.

Key format:  TTT2-SERIAL-SIG   (SERIAL/SIG are 8 hex chars each)
Keep the SECRET in this file private; keygen.py uses the same secret to mint
keys.
"""

import hashlib
import hmac
import json
import os
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Signing secret (embedded - keep private, do not publish this file's secret
# if you fork the project for sale)
# ---------------------------------------------------------------------------
_SECRET = b"TTT2-L0UNGE-2026-l1c3n53-s3cr3t-v1"

KEY_PREFIX = "TTT2"
LICENSE_PATH = Path(__file__).resolve().parent / "license.json"


# ---------------------------------------------------------------------------
# Machine fingerprint
# ---------------------------------------------------------------------------

def machine_fingerprint() -> str:
    """Stable per-machine code, shown on screen and stored in license.json."""
    parts = [socket.gethostname().upper()]
    try:
        import winreg
        for root, subkey in (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"),
        ):
            try:
                with winreg.OpenKey(root, subkey) as k:
                    val, _ = winreg.QueryValueEx(k, "MachineGuid")
                    parts.append(str(val))
            except OSError:
                pass
    except ImportError:
        pass
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:16].upper()
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"


def _fp_clean(text: str) -> str:
    """Normalize a fingerprint for signing: uppercase, no dashes."""
    return "".join(ch for ch in (text or "").upper() if ch.isalnum())


# ---------------------------------------------------------------------------
# Keys (fingerprint-bound)
# ---------------------------------------------------------------------------

def generate_key(fingerprint: str) -> str:
    """Mint a key valid ONLY on the laptop with this fingerprint (seller-side)."""
    serial = uuid.uuid4().hex[:8].upper()
    sig = _sig_for(serial, fingerprint)
    return f"{KEY_PREFIX}-{serial}-{sig}"


def _sig_for(serial: str, fingerprint: str) -> str:
    msg = f"{serial}|{_fp_clean(fingerprint)}".encode()
    return hmac.new(_SECRET, msg, hashlib.sha256).hexdigest()[:8].upper()


def normalize_key(text: str) -> str:
    cleaned = "".join(ch for ch in (text or "").upper() if ch.isalnum() or ch == "-")
    # tolerate pastes missing the TTT2- prefix or with odd dashes
    parts = [p for p in cleaned.split("-") if p]
    if parts and parts[0] == KEY_PREFIX and len(parts) >= 3:
        return f"{KEY_PREFIX}-{parts[1]}-{parts[2]}"
    if len(parts) >= 2 and parts[0] != KEY_PREFIX:
        return f"{KEY_PREFIX}-{parts[0]}-{parts[1]}"
    return cleaned


def validate_key(key: str, fingerprint: str | None = None) -> bool:
    """Signature + fingerprint check - does NOT look at activation state.

    A key minted for laptop A fails on laptop B because the recomputed
    signature (which includes THIS laptop's fingerprint) will not match.
    """
    k = normalize_key(key)
    fp = _fp_clean(fingerprint if fingerprint is not None else machine_fingerprint())
    parts = k.split("-")
    if len(parts) != 3 or parts[0] != KEY_PREFIX:
        return False
    serial, sig = parts[1], parts[2]
    if len(serial) != 8 or len(sig) != 8:
        return False
    return hmac.compare_digest(_sig_for(serial, fp), sig)


def mask_key(key: str) -> str:
    k = normalize_key(key)
    parts = k.split("-")
    if len(parts) != 3:
        return k
    return f"{KEY_PREFIX}-{parts[1]}-********"


# ---------------------------------------------------------------------------
# Activation record (tamper-checked, machine-bound)
# ---------------------------------------------------------------------------

def _record_mac(key: str, fingerprint: str, activated_at: str) -> str:
    msg = f"{key}|{fingerprint}|{activated_at}".encode()
    return hmac.new(_SECRET, msg, hashlib.sha256).hexdigest()


def state() -> dict:
    """Current license state, safe to call on any machine / fresh install."""
    fp = machine_fingerprint()
    base = {"licensed": False, "fingerprint": fp, "key_masked": "",
            "activated_at": "", "error": ""}
    if not LICENSE_PATH.exists():
        return base
    try:
        rec = json.loads(LICENSE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**base, "error": "license file unreadable"}
    key = rec.get("key", "")
    fp_rec = rec.get("fingerprint", "")
    at = rec.get("activated_at", "")
    mac = rec.get("mac", "")
    if not validate_key(key):
        return {**base, "error": "license key in file is invalid"}
    if not hmac.compare_digest(_record_mac(key, fp_rec, at), mac):
        return {**base, "error": "license record was modified"}
    if fp_rec != fp:
        return {**base, "key_masked": mask_key(key),
                "error": "this license is locked to another PC"}
    return {"licensed": True, "fingerprint": fp, "key_masked": mask_key(key),
            "activated_at": at, "error": ""}


def is_licensed() -> bool:
    return state()["licensed"]


def activate(key: str) -> dict:
    """Validate a key and bind it to this machine. One key = this laptop."""
    st = state()
    if st["licensed"]:
        return {"ok": False, "error": f"already licensed on this PC ({st['key_masked']})"}
    k = normalize_key(key)
    if not validate_key(k):
        return {"ok": False, "error": "invalid license key"}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rec = {"key": k, "fingerprint": st["fingerprint"], "activated_at": now,
           "mac": _record_mac(k, st["fingerprint"], now)}
    try:
        LICENSE_PATH.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        os.system(f"attrib +h \"{LICENSE_PATH}\"")  # best-effort hide
    except OSError as exc:
        return {"ok": False, "error": f"could not write license file: {exc}"}
    return {"ok": True, "key_masked": mask_key(k), "activated_at": now}
