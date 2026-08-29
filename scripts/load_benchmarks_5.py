"""
Batch 5 — a 27-CPU ladder on one RTX 4090, which is the shape of data this
engine has never had.

Every measurement before this used a strong CPU: 74 of 111 rows sat on an X3D
chip, where the CPU term barely binds. That is why CPU_PERF_EXPONENT was set on
principle rather than fitted, why per-game CPU costs were poorly constrained,
and why a wrong one could imply a Ryzen 5 5600 capped at 38 fps in Grand Theft
Auto V without anything noticing.

A single GPU across 27 processors at 1080p is the direct measurement of that
axis. It also satisfies `is_identifiable` on its own: varying the CPU is one of
the three things that separates a game's CPU cost from its GPU cost.

What it says about the exponent, checked before loading anything: dividing each
game's absolute level out and fitting only the slope of its ladder gives 1.10,
against 6.3% shape error at the current 1.00 and 6.1% at 1.10. The ratio between
the fastest and slowest chip implies 1.06. The value stays at 1.00 — a 0.2 point
gain is not a reason to move a constant, and the principled choice turns out to
have been right.

The absolute levels are another matter, and they disagree with what we hold by
-41% to +71%. That is scenes, not error: this source runs Cyberpunk's Phantom
Liberty in Dogtown, which is heavier than the scenes our other rows come from.
Neither number is wrong. The model predicts one figure per game, so the honest
treatment is to average rigorous sources rather than pick one, and to say so.

Source: Hardware Unboxed, "Best Gaming CPUs: Update Late 2024", RTX 4090,
1080p, 32 GB throughout. Memory differs by platform (DDR5-6000 CL30 on AM5,
DDR4-3600 CL14 on AM4, DDR5-7200 on LGA1700, DDR5-8200 CUDIMM on LGA1851),
which the model cannot represent — it takes a capacity, not a speed. On a
CPU-bound test that is a real confound and it is not being modelled.

Presets: "Epic" is mapped to Ultra and "High Quality" to High. Ryzen 7 5700X3D
is skipped — it is not in the catalogue.

    python scripts/load_benchmarks_5.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GPU = "NVIDIA GeForce RTX 4090"
RAM = 32
SOURCE = "b10-hub-cpu-late2024"

# (game, preset) -> [(cpu, avg fps, 1% low), ...]  — 1% low is recorded here
# for provenance; the schema has no column for it and the model does not
# predict it.
GAMES = {
    # game, preset used by the model
    ("Star Wars Jedi: Survivor", "Ultra"): [          # chart says Epic
        ("AMD Ryzen 7 9800X3D", 224, 196), ("AMD Ryzen 7 7800X3D", 206, 185),
        ("AMD Ryzen 9 7950X3D", 204, 184), ("AMD Ryzen 9 7900X3D", 200, 182),
        ("Intel Core i9-14900K", 164, 128), ("Intel Core i7-14700K", 163, 127),
        ("AMD Ryzen 7 5800X3D", 162, 141), ("AMD Ryzen 7 9700X", 161, 140),
        ("AMD Ryzen 9 9950X", 159, 138), ("AMD Ryzen 5 9600X", 158, 136),
        ("Intel Core Ultra 9 285K", 155, 135), ("AMD Ryzen 7 7700X", 155, 133),
        ("AMD Ryzen 9 9900X", 155, 132), ("AMD Ryzen 9 7950X", 154, 131),
        ("AMD Ryzen 9 7900X", 152, 130), ("Intel Core i5-14600K", 152, 117),
        ("AMD Ryzen 7 7700", 151, 131), ("Intel Core Ultra 7 265K", 149, 130),
        ("AMD Ryzen 5 7600X", 149, 127), ("AMD Ryzen 5 7600", 145, 124),
        ("Intel Core Ultra 5 245K", 143, 124), ("Intel Core i9-12900K", 141, 123),
        ("Intel Core i7-12700K", 139, 120), ("Intel Core i5-12600K", 136, 108),
        ("Intel Core i5-12400F", 131, 104), ("AMD Ryzen 7 5700X", 118, 90),
        ("Intel Core i3-12100F", 110, 85),
    ],
    ("The Last of Us Part I", "Ultra"): [
        ("AMD Ryzen 7 9800X3D", 208, 155), ("AMD Ryzen 7 7800X3D", 197, 136),
        ("Intel Core Ultra 9 285K", 196, 145), ("AMD Ryzen 9 7950X3D", 196, 129),
        ("Intel Core Ultra 7 265K", 194, 143), ("Intel Core i9-14900K", 191, 139),
        ("Intel Core i7-14700K", 189, 138), ("Intel Core Ultra 5 245K", 182, 136),
        ("AMD Ryzen 9 9950X", 182, 119), ("AMD Ryzen 9 7950X", 181, 124),
        ("AMD Ryzen 7 9700X", 180, 118), ("AMD Ryzen 7 7700X", 179, 123),
        ("AMD Ryzen 7 7700", 177, 122), ("AMD Ryzen 9 7900X3D", 176, 122),
        ("Intel Core i5-14600K", 175, 126), ("AMD Ryzen 9 9900X", 172, 116),
        ("AMD Ryzen 5 9600X", 172, 116), ("AMD Ryzen 5 7600X", 171, 120),
        ("Intel Core i9-12900K", 170, 124), ("AMD Ryzen 9 7900X", 170, 117),
        ("AMD Ryzen 5 7600", 166, 118), ("Intel Core i7-12700K", 163, 121),
        ("AMD Ryzen 7 5800X3D", 158, 109), ("Intel Core i5-12600K", 149, 113),
        ("Intel Core i5-12400F", 143, 109), ("AMD Ryzen 7 5700X", 136, 98),
        ("Intel Core i3-12100F", 113, 62),
    ],
    ("Cyberpunk 2077", "High"): [                      # Phantom Liberty, Dogtown
        ("AMD Ryzen 7 9800X3D", 219, 148), ("AMD Ryzen 7 7800X3D", 202, 143),
        ("AMD Ryzen 9 7950X3D", 185, 136), ("AMD Ryzen 9 7900X3D", 177, 133),
        ("Intel Core Ultra 9 285K", 176, 134), ("Intel Core Ultra 7 265K", 168, 126),
        ("AMD Ryzen 7 7700X", 166, 123), ("Intel Core i9-14900K", 165, 128),
        ("Intel Core i7-14700K", 164, 126), ("AMD Ryzen 7 7700", 164, 121),
        ("AMD Ryzen 7 5800X3D", 164, 117), ("AMD Ryzen 7 9700X", 162, 122),
        ("Intel Core Ultra 5 245K", 161, 119), ("AMD Ryzen 9 7950X", 161, 118),
        ("Intel Core i5-14600K", 160, 119), ("AMD Ryzen 9 9950X", 160, 119),
        ("AMD Ryzen 9 9900X", 158, 115), ("AMD Ryzen 9 7900X", 157, 117),
        ("AMD Ryzen 5 9600X", 154, 110), ("AMD Ryzen 5 7600X", 154, 110),
        ("Intel Core i9-12900K", 153, 115), ("AMD Ryzen 5 7600", 152, 108),
        ("Intel Core i7-12700K", 146, 113), ("Intel Core i5-12600K", 138, 103),
        ("Intel Core i5-12400F", 133, 99), ("AMD Ryzen 7 5700X", 126, 91),
        ("Intel Core i3-12100F", 90, 68),
    ],
    ("Hogwarts Legacy", "High"): [
        ("AMD Ryzen 7 9800X3D", 170, 111), ("AMD Ryzen 9 7950X3D", 150, 98),
        ("AMD Ryzen 9 7900X3D", 142, 82), ("AMD Ryzen 7 7800X3D", 141, 103),
        ("AMD Ryzen 9 7950X", 125, 77), ("AMD Ryzen 7 9700X", 125, 74),
        ("Intel Core i9-14900K", 124, 86), ("AMD Ryzen 7 7700X", 124, 74),
        ("AMD Ryzen 9 9950X", 123, 73), ("Intel Core i7-14700K", 121, 83),
        ("AMD Ryzen 7 7700", 121, 73), ("AMD Ryzen 9 7900X", 120, 71),
        ("Intel Core Ultra 9 285K", 119, 84), ("Intel Core Ultra 7 265K", 119, 83),
        ("AMD Ryzen 5 9600X", 118, 61), ("Intel Core Ultra 5 245K", 116, 81),
        ("Intel Core i5-14600K", 116, 77), ("AMD Ryzen 9 9900X", 116, 66),
        ("AMD Ryzen 5 7600X", 114, 69), ("Intel Core i9-12900K", 113, 85),
        ("AMD Ryzen 5 7600", 111, 67), ("Intel Core i7-12700K", 110, 80),
        ("AMD Ryzen 7 5800X3D", 110, 68), ("Intel Core i5-12600K", 106, 76),
        ("Intel Core i5-12400F", 101, 73), ("AMD Ryzen 7 5700X", 91, 54),
        ("Intel Core i3-12100F", 74, 44),
    ],
    ("A Plague Tale: Requiem", "Ultra"): [
        ("AMD Ryzen 7 9800X3D", 195, 132), ("AMD Ryzen 7 7800X3D", 178, 127),
        ("AMD Ryzen 9 7950X3D", 168, 101), ("AMD Ryzen 7 9700X", 162, 120),
        ("AMD Ryzen 7 7700X", 159, 117), ("AMD Ryzen 9 9950X", 156, 117),
        ("AMD Ryzen 7 7700", 156, 114), ("AMD Ryzen 5 7600X", 156, 114),
        ("AMD Ryzen 5 7600", 153, 112), ("AMD Ryzen 5 9600X", 153, 111),
        ("Intel Core i9-14900K", 149, 110), ("AMD Ryzen 9 7950X", 149, 95),
        ("AMD Ryzen 9 9900X", 147, 109), ("Intel Core i7-14700K", 147, 108),
        ("AMD Ryzen 7 5800X3D", 144, 106), ("AMD Ryzen 9 7900X3D", 144, 90),
        ("Intel Core i5-14600K", 142, 98), ("AMD Ryzen 9 7900X", 141, 88),
        ("Intel Core i9-12900K", 138, 103), ("Intel Core i7-12700K", 135, 97),
        ("Intel Core i5-12600K", 124, 91), ("Intel Core Ultra 9 285K", 123, 75),
        ("Intel Core Ultra 7 265K", 121, 74), ("Intel Core Ultra 5 245K", 120, 73),
        ("Intel Core i5-12400F", 118, 87), ("AMD Ryzen 7 5700X", 118, 85),
        ("Intel Core i3-12100F", 97, 62),
    ],
    ("Counter-Strike 2", "Medium"): [
        ("AMD Ryzen 7 9800X3D", 668, 362), ("AMD Ryzen 7 7800X3D", 592, 318),
        ("AMD Ryzen 9 7950X3D", 577, 298), ("AMD Ryzen 9 7900X3D", 572, 292),
        ("AMD Ryzen 7 9700X", 526, 266), ("AMD Ryzen 9 9950X", 523, 264),
        ("AMD Ryzen 5 9600X", 521, 260), ("Intel Core i9-14900K", 517, 279),
        ("Intel Core Ultra 9 285K", 514, 262), ("AMD Ryzen 7 7700X", 514, 258),
        ("AMD Ryzen 9 9900X", 514, 256), ("Intel Core i7-14700K", 506, 263),
        ("AMD Ryzen 9 7950X", 498, 259), ("AMD Ryzen 5 7600X", 498, 251),
        ("AMD Ryzen 9 7900X", 497, 258), ("AMD Ryzen 7 7700", 497, 247),
        ("AMD Ryzen 7 5800X3D", 495, 279), ("AMD Ryzen 5 7600", 481, 242),
        ("Intel Core i5-14600K", 461, 254), ("Intel Core Ultra 7 265K", 449, 231),
        ("Intel Core i9-12900K", 428, 238), ("AMD Ryzen 7 5700X", 403, 201),
        ("Intel Core Ultra 5 245K", 402, 221), ("Intel Core i7-12700K", 392, 229),
        ("Intel Core i5-12600K", 344, 207), ("Intel Core i5-12400F", 331, 199),
        ("Intel Core i3-12100F", 247, 151),
    ],
    ("Assetto Corsa Competizione", "Ultra"): [         # chart says Epic
        ("AMD Ryzen 7 9800X3D", 269, 223), ("AMD Ryzen 7 7800X3D", 237, 192),
        ("AMD Ryzen 9 7950X3D", 235, 185), ("AMD Ryzen 9 7900X3D", 230, 183),
        ("AMD Ryzen 7 5800X3D", 191, 158), ("AMD Ryzen 7 9700X", 185, 153),
        ("AMD Ryzen 9 9950X", 172, 146), ("AMD Ryzen 5 9600X", 172, 143),
        ("AMD Ryzen 9 9900X", 169, 143), ("Intel Core i9-14900K", 167, 136),
        ("AMD Ryzen 9 7950X", 159, 136), ("AMD Ryzen 9 7900X", 158, 135),
        ("Intel Core i7-14700K", 157, 128), ("AMD Ryzen 7 7700X", 156, 133),
        ("Intel Core Ultra 9 285K", 154, 135), ("AMD Ryzen 7 7700", 154, 132),
        ("AMD Ryzen 5 7600X", 153, 131), ("AMD Ryzen 5 7600", 150, 128),
        ("Intel Core i5-14600K", 149, 117), ("Intel Core i9-12900K", 147, 129),
        ("Intel Core Ultra 7 265K", 142, 126), ("Intel Core Ultra 5 245K", 139, 122),
        ("Intel Core i7-12700K", 136, 118), ("Intel Core i5-12600K", 128, 111),
        ("AMD Ryzen 7 5700X", 124, 108), ("Intel Core i5-12400F", 122, 106),
        ("Intel Core i3-12100F", 106, 85),
    ],
    ("Remnant II", "Ultra"): [
        ("AMD Ryzen 7 9800X3D", 158, 122), ("AMD Ryzen 7 7800X3D", 138, 120),
        ("AMD Ryzen 9 7950X3D", 137, 119), ("AMD Ryzen 9 7900X3D", 135, 115),
        ("AMD Ryzen 7 9700X", 126, 104), ("AMD Ryzen 9 9950X", 123, 99),
        ("Intel Core Ultra 9 285K", 121, 106), ("Intel Core i9-14900K", 120, 98),
        ("Intel Core Ultra 7 265K", 117, 103), ("Intel Core i7-14700K", 116, 97),
        ("AMD Ryzen 5 9600X", 116, 95), ("AMD Ryzen 9 7950X", 115, 98),
        ("AMD Ryzen 7 7700X", 115, 98), ("AMD Ryzen 9 9900X", 114, 97),
        ("AMD Ryzen 9 7900X", 114, 97), ("AMD Ryzen 5 7600X", 113, 90),
        ("Intel Core i9-12900K", 112, 95), ("AMD Ryzen 7 7700", 112, 95),
        ("Intel Core i5-14600K", 111, 92), ("AMD Ryzen 5 7600", 111, 88),
        ("Intel Core Ultra 5 245K", 110, 97), ("Intel Core i7-12700K", 108, 91),
        ("AMD Ryzen 7 5800X3D", 108, 91), ("Intel Core i5-12600K", 101, 86),
        ("Intel Core i5-12400F", 97, 82), ("AMD Ryzen 7 5700X", 88, 74),
        ("Intel Core i3-12100F", 83, 70),
    ],
}

def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not cur.execute("SELECT 1 FROM gpus WHERE name=?", (GPU,)).fetchone():
        sys.exit(f"  {GPU} katalogda yok")
    known = {r["name"] for r in cur.execute("SELECT name FROM cpus")}

    added = skipped = missing = 0
    print(f"  {'oyun':30s} {'preset':7s} {'n':>3s} {'en hizli':>9s} {'en yavas':>9s}")
    for (game, preset), rows in GAMES.items():
        if not cur.execute("SELECT 1 FROM games WHERE name=?", (game,)).fetchone():
            sys.exit(f"  {game} katalogda yok")
        n = 0
        for cpu, fps, _low in rows:
            if cpu not in known:
                missing += 1
                continue
            dup = cur.execute(
                "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=?"
                " AND resolution='1080p' AND settings=? AND upscaling='Native'"
                " AND frame_gen='Kapalı' AND ray_tracing=0",
                (game, cpu, GPU, preset)).fetchone()
            if dup:
                skipped += 1
                continue
            n += 1
            added += 1
            if apply_changes:
                cur.execute(
                    "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                    " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb,"
                    " fps_avg, scene, vram_measured_kind, source, verified)"
                    " VALUES (?,?,?,'1080p',?,'Native','Kapalı',0,0,?,?,"
                    "'benchmark','allocated',?,1)",
                    (game, cpu, GPU, preset, RAM, fps, SOURCE))
        fastest = max(r[1] for r in rows)
        slowest = min(r[1] for r in rows)
        print(f"  {game[:30]:30s} {preset:7s} {n:3d} {fastest:8.0f}f {slowest:8.0f}f")

    print()
    print(f"  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}"
          f"{f', {missing} CPU katalogda yok' if missing else ''}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_engine.py, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
