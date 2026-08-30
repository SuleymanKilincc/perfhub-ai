"""
Records whether a measurement used an optional high-resolution texture pack.

Far Cry 6's is the case that forced it. The two rows the game's cost profile is
fitted from are both HD-pack runs, and the pack is explicitly unmodelled — so
the profile describes a configuration the engine cannot represent, and then
answers for the one it can. That is the same mistake as fitting a game's base
cost from path-traced rows, which was fixed two batches ago.

The evidence that the pack matters is in our own table. An RTX 4060 Ti 8GB with
the pack reads 28 fps at 1440p Ultra with ray tracing; an RTX 3060 Ti 8GB
without it reads 68 at the same settings. 2.4x, from a texture download.

Existing rows are backfilled from their source tag; everything else is 0.

    python scripts/migrate_texture_pack.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# source -> texture_pack. Only sources known to have used one.
KNOWN = {"batch6-hdtex": 1}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    if "texture_pack" not in cols:
        print("  yeni sutun: texture_pack INTEGER DEFAULT 0")
        if apply_changes:
            cur.execute("ALTER TABLE benchmarks ADD COLUMN texture_pack INTEGER DEFAULT 0")
            cur.execute("UPDATE benchmarks SET texture_pack = 0 WHERE texture_pack IS NULL")
    else:
        print("  texture_pack sutunu zaten var")

    for source, value in KNOWN.items():
        rows = cur.execute("SELECT game, resolution, fps_avg FROM benchmarks WHERE source=?",
                           (source,)).fetchall()
        for r in rows:
            print(f"  {source}: {r['game'][:24]:24s} {r['resolution']:6s} "
                  f"{r['fps_avg']:4.0f} fps -> texture_pack={value}")
        if apply_changes:
            cur.execute("UPDATE benchmarks SET texture_pack=? WHERE source=?", (value, source))

    if apply_changes:
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM benchmarks WHERE texture_pack=1").fetchone()[0]
        print(f"\n  doku paketi isaretli satir: {n}")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
