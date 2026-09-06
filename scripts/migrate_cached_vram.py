"""
Reclassifies batch 4's VRAM readings, which were not what they were taken for.

Batch 4 loaded twelve overlay readings from a GTX 1080 Ti and argued them
through like this: "at 11 GB nothing is clamped by capacity, so its overlay
numbers are the games' own appetite". They were marked
`vram_measured_kind='used'` on that basis and became the sole VRAM evidence
for seven games.

The argument has the property backwards. Not being clamped means the reading
is not a ceiling; it does not make it a floor. A game caches into whatever is
spare, which is exactly what 11 GB provides — and the VRAM section of this
project's own notes says so in the first line: "Engines cache into whatever
VRAM is spare, so the reported figure partly describes the card".

The table contradicts the label outright:

    Alan Wake 2       1080p Medium, 1080 Ti   9.2 GB "used"
                      1440p Ultra,  RTX 5090 12.0 GB "allocated"
    Cyberpunk 2077    1080p High,   1080 Ti   9.5 GB "used"
                      1440p Ultra,  RTX 4070  7.3 GB "allocated"

A usage figure must sit below an allocation, and a lower resolution at a lower
preset must sit below a higher one. Cyberpunk violates both at once. Alan Wake
2 at 1080p Medium does not need 9.2 GB.

The consequence reached the site. Red Dead Redemption 2's `vram_base_gb` came
from one of these rows and reads 7.0, which puts 11.6 GB on the screen for 4K
Ultra where the game really wants about 6.7 — and 10 GB is what it takes with
8x MSAA, a setting the model has no term for.

Marked `cached` and excluded from the VRAM fit rather than deleted or
relabelled `allocated`. Relabelling was tried first and is not enough: running
them through the existing inversion moves Red Dead Redemption 2 from 11.6 GB
at 4K to 9.4, still well above the ~6.7 the game actually wants. The inversion
assumes a fixed cache overhead of 1.12x plus 0.8 GB, and the only paired
reading this project holds — batch 17, an 8 GB RTX 5060 — measures 1.05 there.
An 11 GB card caches more than an 8 GB one and nothing here knows how much.

That is an unmodelled effect, and the established answer to one of those is to
exclude the rows rather than half-correct them, exactly as texture packs and
ray reconstruction are excluded. Seven games lose their only VRAM evidence and
fall back to derivation, which for Red Dead Redemption 2 lands at 7.4 GB at 4K
against the ~6.7 measured — not right, but no longer 73% out.

    python scripts/migrate_cached_vram.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

SOURCE = "b9-1080ti-3600"


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = list(cur.execute(
        "SELECT game, resolution, settings, vram_measured_gb, vram_measured_kind"
        " FROM benchmarks WHERE source=? AND vram_measured_gb IS NOT NULL"
        " ORDER BY game", (SOURCE,)))
    print(f"  {SOURCE}: {len(rows)} VRAM olcumu, hepsi 11 GB kartta, hepsi 1080p")
    for r in rows:
        print(f"    {r['game'][:30]:30s} {r['resolution']:6s} {r['settings']:8s} "
              f"{r['vram_measured_gb']:5.1f} GB   {r['vram_measured_kind']} -> cached")

    if apply_changes:
        cur.execute("UPDATE benchmarks SET vram_measured_kind='cached'"
                    " WHERE source=? AND vram_measured_gb IS NOT NULL", (SOURCE,))
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM benchmarks WHERE vram_measured_kind='used'"
                        " AND vram_measured_gb IS NOT NULL").fetchone()[0]
        print(f"\n  yazildi. geriye kalan 'used' olcum: {n} (batch 17, 8 GB kart)")
        print("  simdi: calibrate_vram.py --apply")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
