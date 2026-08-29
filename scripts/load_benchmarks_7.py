"""
Batch 7 — Battlefield 6 across 33 processors on an RTX 5090.

This is the ladder the catalogue has been short of at the bottom. The other
28-CPU batch stopped at an i3-12100F (46); this one runs down through a Ryzen 5
2600 (30), a 2700X (36), an i5-10600K (40) and a 3600 (38) — parts that are
still in a great many machines and that nothing in the set had ever measured.

Source: Hardware Unboxed, Battlefield 6 CPU benchmark. RTX 5090, 1080p High,
TAA native, 32 GB throughout. Memory differs by platform (DDR5-6000 CL30 on
AM5, DDR4-3600 CL14 on AM4 and LGA1200, DDR5-7200 on LGA1700, DDR5-8200 CUDIMM
on LGA1851), which the model takes no account of — it stores a capacity, not a
speed. On a CPU-bound test that is a real confound, and it bears on the oldest
parts most, since they are the ones on DDR4.

The chart is read from three screenshots and the rows between them are
contiguous as far as can be seen, but a hidden row between the i5-14600K and
the i9-12900K would be invisible here. Nothing depends on the list being
complete — each row stands alone — but a gap would not be detectable.

    python scripts/load_benchmarks_7.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GPU = "NVIDIA GeForce RTX 5090"
RAM = 32
SOURCE = "b12-hub-bf6"

GAMES = {
    ("Battlefield 6", "High"): [
        ("AMD Ryzen 7 9800X3D", 198, 147), ("AMD Ryzen 9 9950X3D", 197, 145),
        ("AMD Ryzen 9 9900X3D", 194, 142), ("AMD Ryzen 5 7600X3D", 159, 132),
        ("AMD Ryzen 9 9950X", 159, 127), ("Intel Core Ultra 9 285K", 157, 131),
        ("AMD Ryzen 7 9700X", 157, 126), ("Intel Core i9-14900K", 154, 129),
        ("AMD Ryzen 7 7700X", 154, 124), ("Intel Core i7-14700K", 150, 126),
        ("Intel Core Ultra 7 265K", 149, 125), ("AMD Ryzen 5 9600X", 148, 118),
        ("AMD Ryzen 5 7600X", 147, 117), ("Intel Core i5-14600K", 144, 116),
        ("Intel Core i9-12900K", 142, 112), ("AMD Ryzen 7 5800X3D", 142, 106),
        ("AMD Ryzen 5 7500F", 141, 112), ("Intel Core Ultra 5 245K", 139, 111),
        ("Intel Core i7-12700K", 138, 108), ("Intel Core i5-12600K", 133, 101),
        ("Intel Core i5-12400F", 122, 93), ("AMD Ryzen 5 8400F", 113, 84),
        ("AMD Ryzen 7 5800X", 111, 83), ("Intel Core i9-11900K", 110, 81),
        ("Intel Core i9-10900K", 103, 79), ("Intel Core i7-10700K", 100, 75),
        ("Intel Core i5-10600K", 95, 70), ("AMD Ryzen 5 5600", 94, 70),
        ("AMD Ryzen 5 3600", 91, 68), ("AMD Ryzen 5 5500", 89, 67),
        ("Intel Core i3-12100F", 85, 51), ("AMD Ryzen 7 2700X", 77, 59),
        ("AMD Ryzen 5 2600", 67, 52),
    ],
}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not cur.execute("SELECT 1 FROM gpus WHERE name=?", (GPU,)).fetchone():
        sys.exit(f"  {GPU} katalogda yok")
    scores = {r["name"]: r["power_score"] for r in cur.execute("SELECT name, power_score FROM cpus")}

    added = skipped = 0
    absent = []
    for (game, preset), rows in GAMES.items():
        if not cur.execute("SELECT 1 FROM games WHERE name=?", (game,)).fetchone():
            sys.exit(f"  {game} katalogda yok — once add_battlefield6.py")
        for cpu, fps, low in rows:
            if cpu not in scores:
                absent.append(cpu)
                continue
            dup = cur.execute(
                "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=?"
                " AND resolution='1080p' AND settings=? AND upscaling='Native'"
                " AND frame_gen='Kapalı' AND ray_tracing=0",
                (game, cpu, GPU, preset)).fetchone()
            if dup:
                skipped += 1
                continue
            added += 1
            if apply_changes:
                cur.execute(
                    "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                    " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb,"
                    " fps_avg, fps_1pct_low, scene, vram_measured_kind, source,"
                    " verified) VALUES (?,?,?,'1080p',?,'Native','Kapalı',0,0,?,?,?,"
                    "'benchmark','allocated',?,1)",
                    (game, cpu, GPU, preset, RAM, fps, low, SOURCE))

        lo_score = min(scores[c] for c, _, _ in rows if c in scores)
        hi_score = max(scores[c] for c, _, _ in rows if c in scores)
        print(f"  {game}: {len(rows)} islemci, puan {lo_score:.0f}-{hi_score:.0f}, "
              f"{min(r[1] for r in rows)}-{max(r[1] for r in rows)} fps")

    print()
    print(f"  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}"
          f"{f', katalogda yok: {sorted(set(absent))}' if absent else ''}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        floor = cur.execute(
            "SELECT MIN(c.power_score) FROM benchmarks b JOIN cpus c ON c.name=b.cpu").fetchone()[0]
        print(f"  toplam {total} olcum, olculen en zayif CPU puani: {floor:.0f}")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
