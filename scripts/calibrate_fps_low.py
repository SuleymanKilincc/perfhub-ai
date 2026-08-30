"""
Fits the ratio of 1% low to average frame rate, per game.

The point of it is the complaint a single number invites: told "80 fps" and
then seeing 65 in a firefight, a reader concludes the estimate was wrong. It
was not — it answered the average over a benchmark run — but the number people
judge a build by is what happens when the scene gets busy, and that is the 1%
low.

Measured across 336 rows, the ratio turns out to be a property of the *game*
and not of the hardware. Grouped by CPU score from 50 to 100 it sits flat
between 0.744 and 0.772; grouped by game it runs from 0.533 in Counter-Strike 2
to 0.878 in Hitman 3. Which is what one would expect: how far a frame rate dips
when the action starts is about what the engine is doing, not about which
processor is doing it.

So it is stored per game. Titles with no measurement get the global mean and
`fps_low_measured` stays 0, so the interface can tell a measured range from an
assumed one instead of presenting both with the same confidence.

    python scripts/calibrate_fps_low.py [--apply]
"""
import argparse
import os
import sqlite3
import statistics
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

MIN_ROWS = 3


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(games)")}
    for name, decl in (("fps_low_ratio", "REAL"), ("fps_low_measured", "INTEGER DEFAULT 0")):
        if name not in cols:
            print(f"  yeni sutun: games.{name} {decl}")
            if apply_changes:
                cur.execute(f"ALTER TABLE games ADD COLUMN {name} {decl}")

    # Gameplay rows are kept: this ratio is about what a reader sees when the
    # scene fills up, and free play is closer to that than a benchmark loop.
    # But the two are not interchangeable and nothing here can test whether
    # they differ, so which source a game's ratio came from is printed rather
    # than blended out of sight.
    ratios = defaultdict(list)
    scenes = defaultdict(set)
    for r in cur.execute("SELECT game, fps_avg, fps_1pct_low, scene FROM benchmarks"
                         " WHERE fps_1pct_low IS NOT NULL AND fps_avg > 0"):
        ratios[r["game"]].append(r["fps_1pct_low"] / r["fps_avg"])
        scenes[r["game"]].add(r["scene"] or "benchmark")

    every = [q for v in ratios.values() for q in v]
    global_mean = round(statistics.mean(every), 3)
    print(f"\n  {len(every)} olcum, kuresel ortalama {global_mean}")
    print(f"  {'oyun':32s} {'n':>3s} {'oran':>6s} {'yayilim':>12s}")
    fitted = {}
    for game, v in sorted(ratios.items(), key=lambda kv: statistics.mean(kv[1])):
        if len(v) < MIN_ROWS:
            print(f"  {game[:32]:32s} {len(v):3d}  {MIN_ROWS} satirdan az, atlandi")
            continue
        q = round(statistics.mean(v), 3)
        fitted[game] = q
        src = "+".join(sorted(scenes[game]))
        print(f"  {game[:32]:32s} {len(v):3d} {q:6.3f} {min(v):5.2f}-{max(v):.2f}  {src}")

    total = cur.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    print(f"\n  {len(fitted)} oyun olculdu, {total - len(fitted)} oyun kuresel "
          f"ortalamayi ({global_mean}) kullanacak")

    if apply_changes:
        cur.execute("UPDATE games SET fps_low_ratio=?, fps_low_measured=0", (global_mean,))
        for game, q in fitted.items():
            cur.execute("UPDATE games SET fps_low_ratio=?, fps_low_measured=1"
                        " WHERE name=?", (q, game))
        conn.commit()
        print("  yazildi.")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
