"""TTT2 Local Lounge - SELLER-ONLY license key generator.

Usage (run on YOUR laptop, never ship this file to buyers):
    python keygen.py <count> "<buyer name>" "<laptop fingerprint>"

Example:
    python keygen.py 1 "Ahmed" 9F3E-E2FB-EA8F-6C53

The buyer's laptop fingerprint is shown on THEIR activation screen (top box)
and in their server window. Ask them to send it to you (WhatsApp photo works).

Every key is lifetime and FINGERPRINT-BOUND: it is mathematically valid ONLY
on the laptop whose fingerprint you minted it for. If the buyer shares the
key with a friend, the friend's laptop rejects it. Issued keys are appended
to licenses_issued.csv (issued_at, buyer, fingerprint, key) so you can track
who got what.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import ttt2_license

CSV_PATH = Path(__file__).resolve().parent / "licenses_issued.csv"


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        print("ERROR: a laptop fingerprint is REQUIRED.")
        print("Ask the buyer for the fingerprint shown on their activation")
        print("screen, then:  python keygen.py 1 \"<buyer>\" <fingerprint>")
        sys.exit(2)
    count = int(sys.argv[1])
    buyer = sys.argv[2]
    fingerprint = sys.argv[3]
    fp_clean = ttt2_license._fp_clean(fingerprint)
    if len(fp_clean) != 16:
        print(f"ERROR: fingerprint '{fingerprint}' does not look right")
        print("(expected 4 groups of 4 hex chars, e.g. 9F3E-E2FB-EA8F-6C53)")
        sys.exit(2)

    print(f"Generating {count} lifetime license key(s)")
    print(f"  buyer:       {buyer}")
    print(f"  locked to:   {fingerprint}  (one laptop, forever)\n")
    keys = []
    for _ in range(count):
        key = ttt2_license.generate_key(fingerprint)
        assert ttt2_license.validate_key(key, fingerprint), "keygen produced an invalid key!"
        keys.append(key)
        print("  " + key)
    new_file = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["issued_at", "buyer", "fingerprint", "key"])
        for key in keys:
            w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), buyer, fingerprint, key])
    print(f"\nRecorded to {CSV_PATH}")
    print("Give each buyer ONE key. It activates exactly one laptop - theirs.")


if __name__ == "__main__":
    main()
