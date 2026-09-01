"""
Records whether a measurement used DLSS Ray Reconstruction.

CALIBRATION.md has carried this as an open gap since the first batch — "Ray
Reconstruction is not modelled; the one measurement using it is recorded as
RT + DLSS Quality." That was tolerable while it was one row. A Cyberpunk 2077
batch on an RTX 3080 arrives with three, and one of them is path traced, which
is where it stops being tolerable: PT_GPU_COST_MULT is fitted from two rows,
and Ray Reconstruction is a denoiser replacement whose whole reason for
existing is path tracing. A third row that differs from the other two by an
unmodelled feature would not be measuring path tracing.

This is the same shape as texture_pack, and gets the same treatment: a column,
exclusion from every fit, and a named bucket in validation so the cost of the
exclusion stays visible instead of disappearing.

Note what is *not* claimed here. We have no measurement of what Ray
Reconstruction costs, because no source has yet run it on and off at otherwise
identical settings. Looking for a signal in the RTX 3080 batch finds none —
the three rows that use it read 0.79, 0.93 and 1.10 against prediction where
the four that do not read 0.80 to 0.87 — but each of those three has its own
confound (one sits against the CPU ceiling, one is the path-traced row), so
that test could not have detected a moderate effect. Absence of evidence from
a weak test is not evidence of absence, and the asymmetry decides it: if Ray
Reconstruction does nothing, holding three rows out costs a little accuracy;
if it does something, letting them in quietly moves a two-row constant.

Existing rows are backfilled from their source tag; everything else is 0.

    python scripts/migrate_ray_reconstruction.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# source -> ray_reconstruction. Only sources known to have used it.
KNOWN = {"batch5-rayrecon": 1}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    if "ray_reconstruction" not in cols:
        print("  yeni sutun: ray_reconstruction INTEGER DEFAULT 0")
        if apply_changes:
            cur.execute("ALTER TABLE benchmarks ADD COLUMN "
                        "ray_reconstruction INTEGER DEFAULT 0")
            cur.execute("UPDATE benchmarks SET ray_reconstruction = 0 "
                        "WHERE ray_reconstruction IS NULL")
    else:
        print("  ray_reconstruction sutunu zaten var")

    for source, value in KNOWN.items():
        rows = cur.execute(
            "SELECT game, resolution, upscaling, path_tracing, fps_avg"
            " FROM benchmarks WHERE source=?", (source,)).fetchall()
        for r in rows:
            print(f"  {source}: {r['game'][:24]:24s} {r['resolution']:6s} "
                  f"{r['upscaling']:23s} PT={r['path_tracing']} "
                  f"{r['fps_avg']:4.0f} fps -> ray_reconstruction={value}")
        if apply_changes:
            cur.execute("UPDATE benchmarks SET ray_reconstruction=? WHERE source=?",
                        (value, source))

    if apply_changes:
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM benchmarks "
                        "WHERE ray_reconstruction=1").fetchone()[0]
        print(f"\n  ray reconstruction isaretli satir: {n}")
        print("  -> bu satirlar artik hicbir fit'e girmiyor; validate_engine.py")
        print("     onlari ayri bir kova olarak raporluyor.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
