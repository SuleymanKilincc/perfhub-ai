"""
Gives a game its own ray-tracing cost multiplier.

CALIBRATION.md has carried this as gap 6b since Far Cry 6 measured 1.10x
against a global `RT_GPU_COST_MULT` of 1.70, and named the fix in the same
sentence: "a per-game notion of how much ray tracing a title actually does".
It stayed a note because one game below the average is a curiosity.

Batch 19 removes the choice. Hitman's own benchmark, Dartmoor, both sides
GPU-bound at 99%, reads 3.46x — and free gameplay on a different card in
batch 18 read 3.25x, and Dubai reads 3.67x. Three independent measurements of
one game, all more than double the global constant. Loading them and letting
the existing stage 3 do its work drags `RT_GPU_COST_MULT` from 1.70 to 2.72
and the whole-model error from 6.5% to 7.4%, while the ray-tracing rows still
sit at 26% because a single value fits neither Far Cry 6's 1.10x nor Hitman's
3.46x. That is not a constant converging on an answer; it is a constant being
pulled apart.

    games.rt_gpu_mult   REAL, NULL = use the global

NULL is the important part. 147 games have no ray-tracing measurement at all
and must keep falling back to the global average, which is exactly what that
average is for. Only titles measured with ray tracing both on and off get
their own number, and `calibrate_engine.py` fits it rather than anyone typing
it here.

The column is added empty. Run calibrate_engine.py --apply to populate it.

    python scripts/migrate_rt_gpu_mult.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(games)")}
    if "rt_gpu_mult" not in cols:
        print("  yeni sutun: games.rt_gpu_mult REAL  (NULL = kuresel ortalama)")
        if apply_changes:
            cur.execute("ALTER TABLE games ADD COLUMN rt_gpu_mult REAL")
    else:
        print("  rt_gpu_mult sutunu zaten var")

    # Which games could have one fitted: ray tracing measured both on and off,
    # in benchmark rows, with no frame generation muddying it.
    rows = list(cur.execute(
        "SELECT game,"
        "  SUM(CASE WHEN ray_tracing=1 AND path_tracing=0 THEN 1 ELSE 0 END) AS on_n,"
        "  SUM(CASE WHEN ray_tracing=0 AND path_tracing=0 THEN 1 ELSE 0 END) AS off_n"
        " FROM benchmarks"
        " WHERE COALESCE(scene,'benchmark')='benchmark' AND COALESCE(texture_pack,0)=0"
        "   AND COALESCE(ray_reconstruction,0)=0 AND COALESCE(vram_limited,0)=0"
        "   AND frame_gen='Kapalı'"
        " GROUP BY game HAVING on_n > 0 AND off_n > 0 ORDER BY game"))
    print(f"\n  isin izleme acik VE kapali olculmus {len(rows)} oyun:")
    for r in rows:
        print(f"    {r['game'][:38]:38s} RT acik {r['on_n']:2d} / kapali {r['off_n']:3d}")
    print("  digerleri NULL kalir ve kuresel ortalamayi kullanir.")

    if apply_changes:
        conn.commit()
        print("\n  sutun eklendi, bos. simdi: calibrate_engine.py --apply")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
