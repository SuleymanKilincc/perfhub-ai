"""
Batch 12 — Alan Wake 2, one row out of eight.

Alan Wake 2 was chosen because it could have closed three gaps at once: its own
profile rests on a single baseline row, that is why it cannot inform
PT_GPU_COST_MULT (which is down to two Cyberpunk rows), and its 1% low ratio is
the global default. A video with ray tracing *off* at two resolutions would have
fixed all three.

This is not that video. Seven of its eight rows are given as ranges — "80+"
average against "60+" low — and five of those seven work out to exactly 0.750,
which is the signature of a number being rounded rather than read. The one row
with definite figures says 0.855. Those two do not agree, and the disagreement
is the reason not to trust the seven.

So one row is loaded: 4K, no upscaling, no ray tracing, no frame generation,
69 average and 59 low. It is free gameplay, so it is held out like the rest of
that class, and it does not change the picture much — the row we already had at
that resolution reads 70 with DLAA, so this adds an upscaling variation rather
than the second resolution the fit actually needs.

The ratio is left at the global default. calibrate_fps_low requires three rows
before it will fit a game, which is the correct answer to one measurement that
disagrees with seven rejected ones.

What did come out of it is a rule that was too loose. The path-tracing
multiplier excluded games without "at least two baseline rows", and two rows at
one resolution differing only by upscaler pin a cost down no better than one
does. That test is now identifiability, the same one used for the per-game fit.
Alan Wake 2 fails it either way; the difference is that it now fails it for the
right reason.

    python scripts/load_benchmarks_12.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Alan Wake 2"
CPU = "AMD Ryzen 7 9800X3D"
GPU = "NVIDIA GeForce RTX 5090"

# The only row in the batch with figures rather than a floor.
RES, SETTINGS, UPSCALING, AVG, LOW = "4k", "Ultra", "Native", 69, 59


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    dup = cur.execute(
        "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
        " AND settings=? AND upscaling=?",
        (GAME, CPU, GPU, RES, SETTINGS, UPSCALING)).fetchone()
    print(f"  {RES} {SETTINGS} {UPSCALING}, isin izleme kapali, frame gen kapali")
    print(f"  ort {AVG}  %1 low {LOW}  oran {LOW / AVG:.3f}")
    if dup:
        print("  zaten var, atlandi")
    elif apply_changes:
        cur.execute(
            "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
            " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
            " fps_1pct_low, scene, vram_measured_kind, source, verified)"
            " VALUES (?,?,?,?,?,?,'Kapalı',0,0,32,?,?,'gameplay','allocated',"
            "'b17-aw2-5090',1)",
            (GAME, CPU, GPU, RES, SETTINGS, UPSCALING, AVG, LOW))
        conn.commit()
        print("  yazildi.")
    else:
        print("  (kuru calisma — yazmak icin --apply)")

    base = cur.execute(
        "SELECT COUNT(*) FROM benchmarks WHERE game=? AND ray_tracing=0"
        " AND path_tracing=0 AND frame_gen='Kapalı'"
        " AND COALESCE(scene,'benchmark')='benchmark'", (GAME,)).fetchone()[0]
    print(f"\n  {GAME} fite giren temel satir sayisi: {base}")
    print("  -> hala tek cozunurluk. PT carpanina katkida bulunamaz.")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
