"""
Records which ray-tracing preset a measurement used.

The model carries a single `ray_tracing` boolean while games ship several RT
presets, and the difference between them is not small. One Forza Horizon 6 run
on an RTX 3080 Ti at 1440p reads 85 fps at High RT and 40 fps at Extreme — a
2.1x spread hiding behind one flag.

That mattered immediately. A suggestion arrived that the catalogue's RTX 5080
Forza rows were "probably Extreme", which is testable: scaling the 3080 Ti's
Extreme figure by the score ratio (1.45x) predicts 58 fps, and the recorded row
says 85. Working backwards, 85 on a 5080 is 59 on a 3080 Ti — between High (85)
and Extreme (40), so Ultra. Not Extreme. Loading Extreme measurements against
that row would have pushed the whole gap straight into RT_GPU_COST_MULT, which
is fitted from exactly these rows.

So the level is recorded from now on. Existing rows stay NULL rather than being
guessed at: an inference is not a measurement, and writing "Ultra" into a
column that reads as fact would undo the point of having the column.

`RT_GPU_COST_MULT` therefore means *a typical RT preset*, not the maximum, and
the calibration excludes anything explicitly tagged Extreme so one outlier
cannot drag the average. When the model grows real RT levels this column is
what makes that possible.

    python scripts/add_rt_level.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

CPU = "Intel Core i5-12600K"
GPU = "NVIDIA GeForce RTX 3080 Ti"
RAM = 32
SOURCE = "b8-fh6-3080ti"

# game, resolution, settings, upscaling, rt_level, fps, vram
RT_ROWS = [
    # 15:07 in the source video. Closest in demand to the presets the other RT
    # games in the catalogue appear to have been measured at, so this is the
    # one that joins the fit.
    ("Forza Horizon 6", "1440p", "Ultra", "DLAA", "High", 85, None),
    # 18:06. Recorded for completeness and excluded from the fit — see above.
    ("Forza Horizon 6", "1440p", "Ultra", "DLAA", "Extreme", 40, None),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    if "rt_level" not in cols:
        print("  yeni sutun: rt_level" + ("" if apply_changes else "  (kuru calisma)"))
        if apply_changes:
            cur.execute("ALTER TABLE benchmarks ADD COLUMN rt_level TEXT")
    else:
        print("  rt_level sutunu zaten var")

    known = cur.execute(
        "SELECT COUNT(*) FROM benchmarks WHERE ray_tracing=1 AND path_tracing=0"
    ).fetchone()[0]
    tagged = 0
    if "rt_level" in cols or apply_changes:
        tagged = cur.execute(
            "SELECT COUNT(*) FROM benchmarks WHERE rt_level IS NOT NULL").fetchone()[0]
    print(f"  RT acik, PT kapali {known} satir — seviyesi kayitli olan: {tagged}")

    print("\n=== EKLENEN RT SATIRLARI ===")
    added = 0
    for game, res, settings, ups, level, fps, vram in RT_ROWS:
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings=? AND upscaling=? AND ray_tracing=1 AND fps_avg=?",
            (game, CPU, GPU, res, settings, ups, fps)).fetchone()
        if dup:
            print(f"  {level:8s} {res:6s} {fps:4.0f} fps — zaten var")
            continue
        added += 1
        note = "  (fite girer)" if level != "Extreme" else "  (fitten haric)"
        print(f"  {level:8s} {res:6s} {fps:4.0f} fps{note}")
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb,"
                " fps_avg, vram_measured_gb, rt_level, source, verified)"
                " VALUES (?,?,?,?,?,?,'Kapalı',1,0,?,?,?,?,?,1)",
                (game, CPU, GPU, res, settings, ups, RAM, fps, vram, level, SOURCE))

    print(f"\n  {added} satir eklendi" if apply_changes else f"\n  {added} satir eklenecek")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam olcum: {total}")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
