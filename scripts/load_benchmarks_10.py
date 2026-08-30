"""
Batch 10 — Baldur's Gate 3, and a limitation it makes plain.

Loaded for the 1% low ratio, which comes out at 0.707 across three clean rows.
That places it beside The Last of Us Part I at 0.702 rather than at the bottom
of the range, which is where it was expected to land.

What the batch actually shows is more interesting than the ratio.

**One cost per game cannot describe Baldur's Gate 3.** The engine reads -11.5%
and -12.6% on the two Act 1 rows and +22.6%, +43.6% and +57.1% on the Act 3
Lower City ones. Same game, same settings, same machine; the sign of the error
flips with where the player is standing. Our existing four rows for it came
from somewhere lighter, so the fitted profile describes that and nothing else.

This is a different effect from the one Red Dead Redemption 2 was used to test.
There the question was whether the *ratio* belongs to the location, and Saint
Denis said no — 0.792 against 0.798 for the countryside. Here the ratio is not
what moves. The *level* is, and by a lot: Act 1 runs at 200 fps at 1080p where
Act 3 at 4K runs at 55. A single gpu_cost and cpu_cost per title has no way to
say that, and no amount of measurement will fix it without a per-area notion
the model does not have.

Four of the seven rows are dropped:

  1080p Act 1, 200/196 = 0.980
      A 1% low two percent under the average is not a frame-time
      distribution, it is a reading.
  1080p Act 1, 215/88 = 0.409  and  1440p Act 3, 85/39 = 0.459
      Both below half. The source flagged the second as a traversal stutter;
      the first it did not flag, and it is the same shape. One hitch is not a
      1% low.
  8K, 20/10 = 0.500
      The engine reports vram_spill here, on a 12 GB card. That is the memory
      model working, not a ratio.

Dropping two of the three Act 1 rows means the Act 1 versus Act 3 ratio
comparison cannot be made from this video, only the level one above. The three
that remain are all Act 3 Lower City, so the ratio recorded is that district's.

    python scripts/load_benchmarks_10.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Baldur's Gate 3"
CPU = "AMD Ryzen 7 5800X3D"
GPU = "NVIDIA GeForce RTX 4070"
RAM = 32
SOURCE = "b15-bg3-act3"

# resolution, upscaling, avg, 1% low, what the player was doing
ROWS = [
    ("1440p", "Native",       115, 86, "exploring"),
    ("4k",    "Native",       55,  35, "exploring"),
    ("4k",    "DLSS Quality", 84,  62, "turn-based combat"),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table, name in (("games", GAME), ("cpus", CPU), ("gpus", GPU)):
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")

    print("  Hepsi Act 3 / Lower City.")
    print(f"  {'coz':6s} {'ups':13s} {'ort':>4s} {'low':>4s} {'oran':>6s}  durum")
    added = skipped = 0
    ratios = []
    for res, ups, avg, low, doing in ROWS:
        ratios.append(low / avg)
        print(f"  {res:6s} {ups:13s} {avg:4d} {low:4d} {low / avg:6.3f}  {doing}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings='Ultra' AND upscaling=?",
            (GAME, CPU, GPU, res, ups)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
                " fps_1pct_low, scene, vram_measured_kind, source, verified)"
                " VALUES (?,?,?,?,'Ultra',?,'Kapalı',0,0,?,?,?,'gameplay',"
                "'allocated',?,1)",
                (GAME, CPU, GPU, res, ups, RAM, avg, low, SOURCE))

    print()
    print(f"  oran ortalamasi {sum(ratios) / len(ratios):.3f}")
    print("  not: bu oran Lower City'nin. Act 1 satirlarinin ikisi de elendi,")
    print("       o yuzden act'lar arasi ORAN karsilastirmasi yapilamadi —")
    print("       ama SEVIYE farki dosya basinda yazili ve buyuk.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}")
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
