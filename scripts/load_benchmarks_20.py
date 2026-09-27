"""
Batch 20 — Battlefield 6 across 17 graphics cards at 1440p and 4K.

Battlefield 6 was one of the eight games measured on one axis only: its 33
rows are Hardware Unboxed's CPU ladder, all 1080p High on an RTX 5090 and all
against the processor, so its `gpu_cost` of 1.50 was a genre prior that no
measurement had ever tested (gap 6e). This batch is the other axis. A
43-card GPU comparison, Ryzen 7 9800X3D, 32 GB DDR5-6000, a repeatable pass
through the third single-player mission, Overkill preset, TAA at native
resolution, no frame generation, no ray tracing (the game has none).

**The numbers come from the charts, not from the AI summary.** The video's
Gemini summary returned a 1080p table for 43 cards and it cannot be used:
  - RX 9070 XT and RX 9070 are absent from it, though both appear in the
    video's own charts (sixth and ninth at 1440p), and the summary's notes
    discuss them;
  - RX 7900 XT appears twice, at 164 and at 132 fps — rows have shifted;
  - its 1%-low/average ratio holds at ~0.77 for eleven rows and then falls in
    near-even steps, where the real charts wander between 0.71 and 0.83 from
    row to row, as measured data does.
That is a model filling in a table, not reading one. The 34 rows below were
read by eye from screenshots of the 1440p and 4K charts: the top seventeen
cards of each, which is everything above the player controls. The eighteenth
row on each chart sits under the controls and its label cannot be read, so it
is not loaded.

**Overkill is loaded as Extreme,** and `tier_max` for the game rises from Ultra
to Extreme to allow it: Battlefield 6 ships Low, Medium, High, Ultra and
Overkill, so the catalogue was one tier short.

Before fitting, the engine read every row 32-36% low — 105 fps predicted for
an RTX 5090 at 1440p where the chart says 192. NVIDIA and AMD were off by
about the same (-35.6% and -31.9%), which says the error sits in the game's
cost and not in the cards' scores. All 34 rows are GPU-bound.

    python scripts/load_benchmarks_20.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Battlefield 6"
CPU = "AMD Ryzen 7 9800X3D"
RAM = 32
SOURCE = "b23-bf6-43gpu"
N, A = "NVIDIA GeForce ", "AMD Radeon "

# card -> (average, 1% low), read from the chart screenshots
ROWS = {
    "1440p": {
        N + "RTX 5090": (192, 137), N + "RTX 4090": (140, 111), N + "RTX 5080": (127, 97),
        A + "RX 7900 XTX": (117, 96), N + "RTX 5070 Ti": (116, 89), A + "RX 9070 XT": (112, 92),
        N + "RTX 4080 SUPER": (111, 89), N + "RTX 4080": (109, 86), A + "RX 9070": (103, 84),
        A + "RX 7900 XT": (99, 82), N + "RTX 4070 Ti SUPER": (96, 72), N + "RTX 5070": (88, 72),
        N + "RTX 3090": (88, 72), A + "RX 7900 GRE": (86, 72), N + "RTX 4070 SUPER": (84, 67),
        A + "RX 6950 XT": (82, 70), A + "RX 7800 XT": (77, 63),
    },
    "4k": {
        N + "RTX 5090": (115, 89), N + "RTX 4090": (83, 71), N + "RTX 5080": (70, 59),
        A + "RX 7900 XTX": (64, 53), A + "RX 9070 XT": (63, 52), N + "RTX 4080 SUPER": (63, 51),
        N + "RTX 5070 Ti": (62, 50), N + "RTX 4080": (61, 49), A + "RX 9070": (57, 46),
        A + "RX 7900 XT": (53, 47), N + "RTX 4070 Ti SUPER": (51, 42), N + "RTX 5070": (48, 39),
        N + "RTX 3090": (48, 39), A + "RX 7900 GRE": (45, 34), A + "RX 6950 XT": (43, 35),
        N + "RTX 4070 SUPER": (43, 35), A + "RX 7800 XT": (41, 31),
    },
}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    cur = conn.cursor()

    gpus = {r[0] for r in cur.execute("SELECT name FROM gpus")}
    missing = [g for tab in ROWS.values() for g in tab if g not in gpus]
    if missing or not cur.execute("SELECT 1 FROM cpus WHERE name=?", (CPU,)).fetchone():
        sys.exit(f"  not in the catalogue: {sorted(set(missing)) or CPU}")

    tier = cur.execute("SELECT tier_max FROM games WHERE name=?", (GAME,)).fetchone()[0]
    print(f"  {GAME}: tier_max {tier} -> Extreme (the game ships Overkill)")

    added = skipped = 0
    for res, tab in ROWS.items():
        for gpu, (avg, low) in tab.items():
            dup = cur.execute(
                "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
                " AND settings='Extreme' AND upscaling='Native' AND ray_tracing=0",
                (GAME, CPU, gpu, res)).fetchone()
            if dup:
                skipped += 1
                continue
            added += 1
            if apply_changes:
                cur.execute(
                    "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings, upscaling,"
                    " frame_gen, ray_tracing, path_tracing, ray_reconstruction, ram_gb,"
                    " fps_avg, fps_1pct_low, scene, source, verified)"
                    " VALUES (?,?,?,?,'Extreme','Native','Kapalı',0,0,0,?,?,?,'benchmark',?,1)",
                    (GAME, CPU, gpu, res, RAM, avg, low, SOURCE))

    ratios = [low / avg for tab in ROWS.values() for avg, low in tab.values()]
    print(f"  1% low / average across the batch: {sum(ratios) / len(ratios):.3f} "
          f"({min(ratios):.2f}-{max(ratios):.2f})")
    print(f"  {added} rows {'added' if apply_changes else 'to add'}"
          f"{f', {skipped} already present' if skipped else ''}")
    if apply_changes:
        cur.execute("UPDATE games SET tier_max='Extreme' WHERE name=?", (GAME,))
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  {total} measurements in total")
        print("  next: calibrate_engine.py --apply, calibrate_fps_low.py --apply,"
              " migrate_gpu_measured.py --apply, export_engine_data.py")
    else:
        print("  (dry run — pass --apply to write)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
