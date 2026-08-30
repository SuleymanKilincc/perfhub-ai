"""
Records whether a part is a desktop or a laptop one, so the two stop mixing.

Nothing in the catalogue distinguished them. A reader could pair a desktop
Ryzen 9 7950X3D with an RTX 4070 Laptop GPU and get a confident frame rate for
a machine that cannot exist — laptop CPUs are soldered to their boards and
laptop GPUs to theirs. The model was not wrong, it was answering about a
computer nobody can buy.

Naming carries the answer and carries it cleanly:

    GPU laptop      Mobile, Laptop, Max-Q                      29 parts
    CPU laptop      the H, HS, HX and U suffixes               70 parts
    GPU integrated  Iris, UHD, and the Radeon xxxM series      pairs with either

Integrated graphics are their own category rather than a third form factor:
an Intel UHD 770 sits in a desktop and a UHD 630 in both, so they constrain
nothing and must not trigger a warning.

Apple is the case the catalogue cannot express. The M-series CPUs are here but
no Apple GPU is, so every pairing offered for them is wrong — an M3 Max has to
be matched with someone else's discrete card to get an answer at all. They are
marked 'apple' so that stays visible instead of being quietly filed as laptop,
and fixing it properly means adding Apple GPU entries.

    python scripts/migrate_form_factor.py [--apply]
"""
import argparse
import os
import re
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# Suffixes Intel and AMD both use for mobile parts. Anchored to the end of the
# model number so a desktop "Ryzen 5 5600" is never caught by the "U" rule.
CPU_LAPTOP = re.compile(r"\d+(HX|HS|H|U)$")
GPU_LAPTOP = re.compile(r"\b(Mobile|Laptop|Max-Q)\b", re.I)
GPU_INTEGRATED = re.compile(r"\b(Iris|UHD Graphics|HD Graphics|Vega \d+ Graphics"
                            r"|Radeon \d{3}M|Radeon Graphics)\b", re.I)


def classify_cpu(name):
    if name.startswith("Apple"):
        return "apple"
    return "laptop" if CPU_LAPTOP.search(name) else "desktop"


def classify_gpu(name):
    if GPU_INTEGRATED.search(name):
        return "integrated"
    return "laptop" if GPU_LAPTOP.search(name) else "desktop"


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table in ("cpus", "gpus"):
        cols = {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}
        if "form_factor" not in cols:
            print(f"  yeni sutun: {table}.form_factor TEXT")
            if apply_changes:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN form_factor TEXT")

    counts = {}
    for table, classify in (("cpus", classify_cpu), ("gpus", classify_gpu)):
        rows = [(r["name"], classify(r["name"]))
                for r in cur.execute(f"SELECT name FROM {table}")]
        for _, ff in rows:
            counts[(table, ff)] = counts.get((table, ff), 0) + 1
        if apply_changes:
            for name, ff in rows:
                cur.execute(f"UPDATE {table} SET form_factor=? WHERE name=?", (ff, name))

    print()
    for (table, ff), n in sorted(counts.items()):
        print(f"  {table:5s} {ff:11s} {n:4d}")

    print("\n  ORNEKLER (dogru siniflandirildigini gormek icin)")
    for table, classify in (("cpus", classify_cpu), ("gpus", classify_gpu)):
        seen = {}
        for r in cur.execute(f"SELECT name FROM {table} ORDER BY name"):
            ff = classify(r["name"])
            seen.setdefault(ff, []).append(r["name"])
        for ff, names in sorted(seen.items()):
            print(f"    {table[:3]} {ff:11s} {names[0][:32]:32s} ... {names[-1][:32]}")

    if apply_changes:
        conn.commit()
        print("\n  yazildi.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
