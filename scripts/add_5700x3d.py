"""
Adds the Ryzen 7 5700X3D, with a score read off measurements rather than a
formula.

It was the one processor in the 27-CPU ladder that the catalogue did not have,
so its rows were skipped on load. That ladder is also the best possible way to
score it: it appears in all eight games alongside chips whose scores are known,
so its position can be interpolated from where its frame rates actually land
instead of being derived from clocks and cores.

The method is a direct ratio against the Ryzen 7 5800X3D, which is the same
architecture, the same core count and the same 3D V-Cache at a higher clock.
Comparing like with like keeps the answer from picking up other processors'
scoring errors.

Interpolating between whichever chips happened to bracket it was tried first
and gave 65, above the 5800X3D's 63 — for a part that is slower than it in all
eight games. The bracket wandered from game to game and dragged every
neighbour's error along with it. The sibling ratio is stable instead: 0.93 to
0.96 across the eight, mean 0.95.

The cross-check against the Ryzen 7 5700X does not agree, and that is worth
saying rather than hiding. It implies 65, because this ladder puts the
5800X3D 1.28x above the 5700X where their scores say 1.19x. The disagreement is
about how much 3D V-Cache is worth, not about this chip, so it is left as a
finding for the CPU scores rather than folded into this one number.

Clock and core figures are the published ones. They do not feed the score; the
scores are a 1080p gaming index (scripts/calibrate_cpu_scores.py) and this one
comes straight from 1080p gaming.

    python scripts/add_5700x3d.py [--apply]
"""
import argparse
import os
import sqlite3
import statistics
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

NAME = "AMD Ryzen 7 5700X3D"
SPEC = dict(cores=8, threads=16, base_clock=3.0, boost_clock=4.1,
            architecture="Zen 3")

# Hardware Unboxed, Best Gaming CPUs Late 2024. RTX 4090, 1080p.
# game -> (5700X3D fps, {catalogued cpu: fps})
LADDERS = {
    "Star Wars Jedi: Survivor": (155, {
        "AMD Ryzen 5 9600X": 158, "Intel Core Ultra 9 285K": 155,
        "AMD Ryzen 7 9700X": 161, "AMD Ryzen 7 7700X": 155,
        "AMD Ryzen 7 5800X3D": 162, "AMD Ryzen 7 5700X": 118}),
    "The Last of Us Part I": (151, {
        "AMD Ryzen 7 5800X3D": 158, "Intel Core i5-12600K": 149,
        "Intel Core i7-12700K": 163, "AMD Ryzen 7 5700X": 136}),
    "Cyberpunk 2077": (157, {
        "AMD Ryzen 9 7900X": 157, "AMD Ryzen 9 9900X": 158,
        "AMD Ryzen 5 9600X": 154, "AMD Ryzen 5 7600X": 154,
        "AMD Ryzen 7 5800X3D": 164, "AMD Ryzen 7 5700X": 126}),
    "Hogwarts Legacy": (102, {
        "AMD Ryzen 7 5800X3D": 110, "Intel Core i5-12600K": 106,
        "Intel Core i5-12400F": 101, "AMD Ryzen 7 5700X": 91}),
    "Assetto Corsa Competizione": (183, {
        "AMD Ryzen 7 5800X3D": 191, "AMD Ryzen 7 9700X": 185,
        "AMD Ryzen 9 9950X": 172, "AMD Ryzen 5 9600X": 172,
        "AMD Ryzen 7 5700X": 124}),
    "Remnant II": (102, {
        "AMD Ryzen 7 5800X3D": 108, "Intel Core i5-12600K": 101,
        "Intel Core i7-12700K": 108, "AMD Ryzen 7 5700X": 88}),
    "A Plague Tale: Requiem": (137, {
        "AMD Ryzen 7 5800X3D": 144, "Intel Core i9-12900K": 138,
        "Intel Core i7-12700K": 135, "AMD Ryzen 7 5700X": 118}),
    "Counter-Strike 2": (476, {
        "AMD Ryzen 7 5800X3D": 495, "AMD Ryzen 5 7600": 481,
        "Intel Core i5-14600K": 461, "AMD Ryzen 7 5700X": 403}),
}


SIBLING = "AMD Ryzen 7 5800X3D"
CROSSCHECK = "AMD Ryzen 7 5700X"


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if cur.execute("SELECT 1 FROM cpus WHERE name=?", (NAME,)).fetchone():
        print(f"  {NAME} zaten katalogda")
        conn.close()
        return

    scores = {r["name"]: r["power_score"] for r in cur.execute("SELECT name, power_score FROM cpus")}

    print(f"  {'oyun':30s} {'5700X3D':>8s} {'5800X3D':>8s} {'oran':>7s}")
    ratios, cross = [], []
    for game, (fps, neighbours) in LADDERS.items():
        missing = [c for c in neighbours if c not in scores]
        if missing:
            sys.exit(f"  katalogda yok: {missing}")
        sib = neighbours.get(SIBLING)
        if sib is None:
            sys.exit(f"  {game}: {SIBLING} satiri yok")
        ratios.append(fps / sib)
        print(f"  {game[:30]:30s} {fps:8.0f} {sib:8.0f} {fps / sib:7.3f}")
        if CROSSCHECK in neighbours:
            cross.append(fps / neighbours[CROSSCHECK])

    r = statistics.mean(ratios)
    score = round(scores[SIBLING] * r)
    print()
    print(f"  oran ortalamasi {r:.3f}  (dagilim {min(ratios):.3f}-{max(ratios):.3f})")
    print(f"  {SIBLING} = {scores[SIBLING]:.0f}  ->  puan {score}")
    if cross:
        alt = scores[CROSSCHECK] * statistics.mean(cross)
        print(f"  capraz kontrol {CROSSCHECK} uzerinden: {alt:.0f}"
              f"{'  — uyusmuyor; bkz. dosya basi' if abs(alt - score) > 2 else ''}")

    if apply_changes:
        cur.execute(
            "INSERT INTO cpus (name, cores, threads, base_clock, boost_clock,"
            " architecture, power_score) VALUES (?,?,?,?,?,?,?)",
            (NAME, SPEC["cores"], SPEC["threads"], SPEC["base_clock"],
             SPEC["boost_clock"], SPEC["architecture"], score))
        conn.commit()
        print(f"\n  {NAME} eklendi (puan {score})")
        print("  simdi: load_benchmarks_5.py --apply ile atlanan 8 satir yuklenir")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
