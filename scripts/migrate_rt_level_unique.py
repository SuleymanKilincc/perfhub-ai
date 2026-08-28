"""
Adds rt_level to the benchmarks uniqueness constraint.

The constraint exists for a good reason and has already earned its place: it is
what stops the same configuration being recorded twice with different numbers,
which is the failure that left Forza Horizon 6 with three contradictory 4K
rows before a second source settled it.

But a ray-tracing preset is part of a configuration, and the constraint did not
know that. Recording the same card and resolution at both High RT (85 fps) and
Extreme RT (40 fps) — a real pair from one video — was rejected as a duplicate,
so one of the two measurements had to be thrown away.

SQLite cannot alter a constraint in place, so the table is rebuilt. Row counts
are compared before and after and the whole thing runs in one transaction: if
the copy is short by even one row, nothing is written.

    python scripts/migrate_rt_level_unique.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

NEW_SCHEMA = """
CREATE TABLE benchmarks_new (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game         TEXT    NOT NULL,
    cpu          TEXT    NOT NULL,
    gpu          TEXT    NOT NULL,
    resolution   TEXT    NOT NULL,
    settings     TEXT    NOT NULL,
    upscaling    TEXT    DEFAULT 'Native',
    frame_gen    TEXT    DEFAULT 'Kapalı',
    ray_tracing  INTEGER DEFAULT 0,
    path_tracing INTEGER DEFAULT 0,
    ram_gb       INTEGER DEFAULT 32,
    fps_avg      REAL    NOT NULL,
    source       TEXT,
    verified     INTEGER DEFAULT 0,
    vram_measured_gb REAL,
    rt_level     TEXT,
    UNIQUE(game, cpu, gpu, resolution, settings, upscaling, frame_gen,
           ray_tracing, path_tracing, rt_level)
)
"""

COLUMNS = ("id, game, cpu, gpu, resolution, settings, upscaling, frame_gen,"
           " ray_tracing, path_tracing, ram_gb, fps_avg, source, verified,"
           " vram_measured_gb, rt_level")


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    cur = conn.cursor()

    before = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
    print(f"  mevcut satir sayisi: {before}")

    schema = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='benchmarks'"
    ).fetchone()[0]
    if "rt_level)" in schema.replace(" ", "").replace("\n", ""):
        print("  kisit zaten rt_level iceriyor — yapacak bir sey yok")
        conn.close()
        return

    if not apply_changes:
        print("  UNIQUE(... , rt_level) olacak sekilde tablo yeniden kurulacak")
        print("  (kuru calisma — yazmak icin --apply)")
        conn.close()
        return

    try:
        cur.execute("BEGIN")
        cur.execute("DROP TABLE IF EXISTS benchmarks_new")
        cur.executescript(NEW_SCHEMA)
        cur.execute(f"INSERT INTO benchmarks_new ({COLUMNS})"
                    f" SELECT {COLUMNS} FROM benchmarks")

        copied = cur.execute("SELECT COUNT(*) FROM benchmarks_new").fetchone()[0]
        if copied != before:
            raise RuntimeError(f"kopyalama eksik: {copied} != {before}")

        cur.execute("DROP TABLE benchmarks")
        cur.execute("ALTER TABLE benchmarks_new RENAME TO benchmarks")
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    after = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
    print(f"  yeniden kuruldu, satir sayisi: {after}  "
          f"{'(ayni)' if after == before else 'FARKLI — kontrol edin'}")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
