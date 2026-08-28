"""
Records what kind of measurement each benchmark row actually is.

Two distinctions have been made by hand, in commit messages and in decisions
to throw data away, and neither was written down where the code could act on
it. This adds both as columns.

`scene` — benchmark loop or free gameplay. It is the difference that has cost
the most. Counter-Strike 2 reads 515-780 fps in the rows we hold and 240 in a
real match on comparable hardware; Forza Horizon 6 carried three contradictory
4K figures until a second source settled them. Free-gameplay numbers are not
wrong, they are answering a different question, and averaging the two answers
produces something that is true of neither. So gameplay rows stay out of the
cost fit and are reported separately, which also means they can finally be
*kept* rather than discarded: a held-out set the fit has never seen is the only
honest way to find out whether the engine generalises.

`vram_measured_kind` — allocated or used. `calibrate_vram.py` inverts the
allocation model to recover a working set, which is right for an overlay
reporting allocation and wrong by about 25% for one reporting usage. Most
overlays show only one of the two and do not say which. Recording it is the
difference between a measurement and a coin flip.

Existing rows are backfilled to 'benchmark' and 'allocated', which is what they
were collected as.

    python scripts/migrate_measurement_kind.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

COLUMNS = [
    ("scene", "TEXT DEFAULT 'benchmark'"),
    ("vram_measured_kind", "TEXT DEFAULT 'allocated'"),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    existing = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]

    for name, decl in COLUMNS:
        if name in existing:
            print(f"  {name} sutunu zaten var")
            continue
        print(f"  yeni sutun: {name} {decl}")
        if apply_changes:
            cur.execute(f"ALTER TABLE benchmarks ADD COLUMN {name} {decl}")
            # ALTER ... DEFAULT fills existing rows in SQLite, but say it
            # explicitly rather than relying on that.
            default = decl.split("DEFAULT ")[1].strip()
            cur.execute(f"UPDATE benchmarks SET {name} = {default}"
                        f" WHERE {name} IS NULL")

    if apply_changes:
        conn.commit()
        for name, _ in COLUMNS:
            counts = cur.execute(
                f"SELECT {name} v, COUNT(*) n FROM benchmarks GROUP BY {name}").fetchall()
            print(f"  {name}: " + ", ".join(f"{r['v']}={r['n']}" for r in counts))
        print(f"  toplam {total} satir")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
