"""
Records the 1% low alongside the average, and backfills it where we have it.

A single number invites the complaint the range exists to prevent: told "80
fps" and then seeing 65 in a firefight, a reader concludes the estimate was
wrong. It was not wrong, it was answering a different question — the average
over a benchmark run — and the number people actually judge a build by is what
happens when the scene gets busy.

The 1% low is that number, and it has been sitting unused in every chart we
have read. 328 rows from the 28-CPU batches carry one.

    python scripts/migrate_fps_low.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import db_manager
import load_benchmarks_5 as b5
import load_benchmarks_6 as b6


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    if "fps_1pct_low" not in cols:
        print("  yeni sutun: fps_1pct_low REAL")
        if apply_changes:
            cur.execute("ALTER TABLE benchmarks ADD COLUMN fps_1pct_low REAL")
    else:
        print("  fps_1pct_low sutunu zaten var")

    filled = misses = 0
    for batch, gpu in ((b5, b5.GPU), (b6, b6.GPU)):
        for (game, preset), rows in batch.GAMES.items():
            for cpu, avg, low in rows:
                r = cur.execute(
                    "SELECT id FROM benchmarks WHERE game=? AND cpu=? AND gpu=?"
                    " AND resolution='1080p' AND settings=? AND upscaling='Native'"
                    " AND frame_gen='Kapalı' AND ray_tracing=0 AND fps_avg=?",
                    (game, cpu, gpu, preset, avg)).fetchone()
                if not r:
                    misses += 1
                    continue
                filled += 1
                if apply_changes and "fps_1pct_low" in cols or apply_changes:
                    cur.execute("UPDATE benchmarks SET fps_1pct_low=? WHERE id=?",
                                (low, r["id"]))

    print(f"  {filled} satira %1 low yazil{'di' if apply_changes else 'acak'}"
          f"{f', {misses} satir eslesmedi' if misses else ''}")
    if apply_changes:
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM benchmarks WHERE fps_1pct_low IS NOT NULL").fetchone()[0]
        t = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  %1 low kayitli: {n}/{t}")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
