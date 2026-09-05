"""
Records where in a game a measurement was taken.

The project has now lost this five times. Red Dead Redemption 2's Saint Denis
against its countryside, Starfield's New Atlantis against a planet surface,
Baldur's Gate 3's Act 1 against Act 3's Lower City, Cyberpunk 2077's Night
City against its benchmark route, Hitman's Bangkok against Dartmoor — each one
mattered, each was argued from a loader docstring, and none of it survived
into the table where a later question could reach it.

Batch 18 forces the issue. Three Hitman rows share every column the schema
has — same game, machine, resolution, preset, upscaler, ray-tracing state —
and read 43, 70 and 72 fps, because they are Sapienza, Miami and Chongqing.
Without somewhere to put that, they are three contradictory copies of one
measurement.

They also carry the reason the column is worth having. With ray tracing off
the same locations agree within 6% (249 against 234); with it on they spread
1.67x. So the scene sensitivity is not a property of the game, it is a
property of the ray tracing — which is not a thing that could have been asked
of a table that does not know where anything was measured.

Note what this does not do. The UNIQUE constraint is untouched, so it still
reads (game, cpu, gpu, resolution, settings, upscaling, frame_gen,
ray_tracing, path_tracing, rt_level). Those three rows are accepted only
because SQLite treats NULLs in a UNIQUE index as distinct and their rt_level
is NULL — which is worth knowing, because it means that constraint quietly
stops constraining whenever rt_level is absent. Rebuilding the table to
include location is the honest fix and is not attempted here.

Backfill covers only sources whose rows are all from one place, taken from
their loader docstrings. Mixed batches stay NULL rather than be guessed at.

    python scripts/migrate_location.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# source -> location, for batches measured entirely in one place.
KNOWN = {
    "b15-bg3-act3":         "Act 3 / Lower City",
    "b18-cp2077-3080-play": "Night City",
    "b20-hitman-5060-play": "Bangkok",
}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    if "location" not in cols:
        print("  yeni sutun: location TEXT")
        if apply_changes:
            cur.execute("ALTER TABLE benchmarks ADD COLUMN location TEXT")
    else:
        print("  location sutunu zaten var")

    for source, place in KNOWN.items():
        n = cur.execute("SELECT COUNT(*) FROM benchmarks WHERE source=?",
                        (source,)).fetchone()[0]
        print(f"  {source:24s} {n:3d} satir -> {place}")
        if apply_changes:
            cur.execute("UPDATE benchmarks SET location=? WHERE source=?",
                        (place, source))

    if apply_changes:
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM benchmarks "
                        "WHERE location IS NOT NULL").fetchone()[0]
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"\n  konumu bilinen satir: {n} / {total}")
        print("  karma partiler bilerek NULL birakildi — tahmin edilmedi.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
