"""
Batch 9 — Red Dead Redemption 2, for its 1% low ratio and for one hypothesis.

**The hypothesis.** Kingdom Come: Deliverance 2 came with a relayed claim that
its frame rate drops 30-40% in Kuttenberg, its dense city, against the ~13% the
measurement showed elsewhere. That video had no city rows, so the claim stayed
open: maybe the ratio is a property of the *location* rather than the game, and
one number per game cannot express it.

Red Dead Redemption 2 is the game to ask, because Saint Denis is the
best-known CPU-heavy city in any open world we hold. The answer is no. Saint
Denis reads 0.792 across its three rows and the rural and forest scenes read
0.798 across seven. There is no difference to find. That is not proof for every
game, but it is the first real evidence, and it comes from the title where the
effect should have been easiest to see.

**What is loaded.** Four of the eleven rows. The rest are dropped for reasons
worth stating rather than filtering silently:

  six rows use 2x, 4x or 8x MSAA
      The source put these in an "upscaling" column, but MSAA is
      anti-aliasing and multiplies sample counts rather than reducing them.
      The model has no concept of it, so their frame rates would be
      unpredictable by construction. Their *ratios* are still informative and
      are what the location comparison above rests on — 0.737 to 0.826, in
      line with the clean rows — but the rows themselves are not loaded.

  one row is 16K
      Not in RESOLUTION_PIXELS, and it is the only row at Low rather than Max.
      Its 0.600 is also the one the source itself explains as a VRAM wall.

"Max" maps to Extreme, not Ultra. The RTX 5090 here reads 110 fps at 4K where
an RTX 4090 already in the set reads 120 at Ultra, and the 5090 is the faster
card — so Max is the heavier setting.

The internal benchmark was not used, again. Two videos now, both free roam, so
whether a benchmark loop and free play give different ratios is still unknown.

    python scripts/load_benchmarks_9.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Red Dead Redemption 2"
CPU = "AMD Ryzen 7 9800X3D"
GPU = "NVIDIA GeForce RTX 5090"
RAM = 32
SOURCE = "b14-rdr2-5090"

# resolution, avg, 1% low, where
ROWS = [
    ("4k",    110, 95,  "forest"),
    ("1440p", 150, 120, "Saint Denis"),
    ("1080p", 150, 120, "Strawberry"),
    ("8k",    42,  35,  "forest"),
]

# Ratios from the MSAA rows, kept here as the record behind the location
# comparison even though the rows are not loaded.
MSAA_RATIOS = {
    "Saint Denis": [75 / 100, 95 / 115],
    "rural": [45 / 60, 75 / 91, 70 / 90, 70 / 95],
}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table, name in (("games", GAME), ("cpus", CPU), ("gpus", GPU)):
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")

    print(f"  {'coz':6s} {'ort':>4s} {'low':>4s} {'oran':>6s}  sahne")
    added = skipped = 0
    ratios = []
    for res, avg, low, where in ROWS:
        ratios.append(low / avg)
        print(f"  {res:6s} {avg:4d} {low:4d} {low / avg:6.3f}  {where}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings='Extreme' AND upscaling='Native'",
            (GAME, CPU, GPU, res)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
                " fps_1pct_low, scene, vram_measured_kind, source, verified)"
                " VALUES (?,?,?,?,'Extreme','Native','Kapalı',0,0,?,?,?,'gameplay',"
                "'allocated',?,1)",
                (GAME, CPU, GPU, res, RAM, avg, low, SOURCE))

    city = MSAA_RATIOS["Saint Denis"] + [120 / 150]
    rural = MSAA_RATIOS["rural"] + [95 / 110, 120 / 150, 35 / 42]
    print()
    print("  KONUM KARSILASTIRMASI (MSAA satirlari dahil, sadece oran icin)")
    print(f"    Saint Denis (sehir)  n={len(city)}  {sum(city) / len(city):.3f}")
    print(f"    kirsal / orman       n={len(rural)}  {sum(rural) / len(rural):.3f}")
    print("    -> fark yok. Kuttenberg iddiasinin arkasindaki fikir, etkinin en")
    print("       kolay gorulecegi oyunda gorunmuyor.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}")
    print(f"  yuklenen satirlarin orani: {sum(ratios) / len(ratios):.3f}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_fps_low.py --apply, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
