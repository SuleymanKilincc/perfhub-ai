"""
Batch 6 — four more games from the same 27-CPU ladder as batch 5.

Same source, same RTX 4090, same 1080p, so the notes on scenes and on memory
differing by platform in load_benchmarks_5.py apply here unchanged. All four
games had derived cost profiles before this and now have measured ones.

Two things about this set are worth recording rather than smoothing over.

Warhammer 40,000: Space Marine 2 was measured with its 4K texture pack
installed. The model has no notion of a texture mod, and the one other case we
hold — Far Cry 6's HD pack — is the single worst prediction in the whole set.
The rows go in because the CPU ladder is what they are here for and a texture
pack costs memory rather than processor time, but the game's fitted VRAM figure
will describe the modded install, not the shipping one.

Star Wars Outlaws barely separates its top ten processors: a 7950X3D reads 142
and a 9800X3D 141, where every other game in the batch puts the 9800X3D clearly
first. Something other than the CPU is binding there — the engine, or the
RTX 4090 itself even at 1080p. Those rows say little about the processors and
the fit will read them as a low CPU cost, which is the right answer for the
wrong reason.

The video's own 14-game average chart is deliberately not loaded. It is a
summary of these measurements, not another measurement, and feeding a mean back
in alongside its own components would count the same runs twice.

    python scripts/load_benchmarks_6.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GPU = "NVIDIA GeForce RTX 4090"
RAM = 32
SOURCE = "b11-hub-cpu-late2024"

GAMES = {
    ("Warhammer 40K: Space Marine 2", "Ultra"): [
        ("AMD Ryzen 7 9800X3D", 138, 122), ("AMD Ryzen 7 7800X3D", 125, 112),
        ("AMD Ryzen 9 9950X", 115, 101), ("AMD Ryzen 9 7950X3D", 112, 98),
        ("AMD Ryzen 9 9900X", 112, 97), ("Intel Core i9-14900K", 112, 96),
        ("AMD Ryzen 9 7950X", 111, 98), ("AMD Ryzen 9 7900X3D", 111, 98),
        ("AMD Ryzen 9 7900X", 111, 97), ("Intel Core i7-14700K", 110, 94),
        ("Intel Core Ultra 9 285K", 109, 96), ("AMD Ryzen 7 7700X", 109, 95),
        ("AMD Ryzen 5 7600X", 108, 94), ("Intel Core i5-14600K", 108, 93),
        ("AMD Ryzen 7 9700X", 108, 93), ("AMD Ryzen 5 9600X", 107, 89),
        ("AMD Ryzen 5 7600", 106, 93), ("AMD Ryzen 7 7700", 106, 92),
        ("Intel Core Ultra 7 265K", 105, 92), ("Intel Core Ultra 5 245K", 102, 82),
        ("Intel Core i9-12900K", 100, 85), ("AMD Ryzen 7 5800X3D", 100, 85),
        ("Intel Core i7-12700K", 97, 83), ("AMD Ryzen 7 5700X3D", 96, 82),
        ("Intel Core i5-12600K", 94, 81), ("Intel Core i5-12400F", 90, 78),
        ("AMD Ryzen 7 5700X", 84, 71), ("Intel Core i3-12100F", 75, 52),
    ],
    ("Star Wars Outlaws", "Ultra"): [
        ("AMD Ryzen 9 7950X3D", 142, 111), ("AMD Ryzen 7 7800X3D", 142, 111),
        ("Intel Core i9-14900K", 142, 109), ("AMD Ryzen 7 9800X3D", 141, 109),
        ("Intel Core i7-14700K", 141, 108), ("AMD Ryzen 9 7900X3D", 136, 105),
        ("Intel Core i9-12900K", 134, 109), ("Intel Core Ultra 9 285K", 134, 104),
        ("Intel Core Ultra 7 265K", 133, 102), ("AMD Ryzen 9 7950X", 132, 103),
        ("Intel Core Ultra 5 245K", 131, 101), ("Intel Core i7-12700K", 130, 108),
        ("AMD Ryzen 9 9950X", 129, 102), ("AMD Ryzen 7 7700X", 129, 99),
        ("AMD Ryzen 7 9700X", 128, 98), ("Intel Core i5-14600K", 128, 97),
        ("AMD Ryzen 7 7700", 127, 96), ("AMD Ryzen 9 7900X", 121, 94),
        ("AMD Ryzen 5 7600X", 120, 95), ("AMD Ryzen 9 9900X", 119, 92),
        ("AMD Ryzen 7 5800X3D", 117, 93), ("AMD Ryzen 5 9600X", 116, 91),
        ("AMD Ryzen 5 7600", 116, 88), ("AMD Ryzen 7 5700X3D", 112, 89),
        ("Intel Core i5-12600K", 107, 89), ("Intel Core i5-12400F", 102, 85),
        ("AMD Ryzen 7 5700X", 89, 65), ("Intel Core i3-12100F", 56, 38),
    ],
    ("Hitman 3", "Ultra"): [
        ("AMD Ryzen 7 9800X3D", 289, 247), ("Intel Core i9-14900K", 276, 237),
        ("Intel Core i7-14700K", 271, 234), ("Intel Core Ultra 9 285K", 269, 239),
        ("AMD Ryzen 7 7800X3D", 268, 238), ("AMD Ryzen 9 7950X3D", 257, 231),
        ("Intel Core Ultra 7 265K", 256, 232), ("Intel Core i5-14600K", 254, 229),
        ("AMD Ryzen 9 9950X", 251, 217), ("AMD Ryzen 9 7950X", 248, 216),
        ("AMD Ryzen 9 7900X3D", 247, 211), ("AMD Ryzen 7 7700X", 246, 216),
        ("AMD Ryzen 9 9900X", 246, 214), ("AMD Ryzen 7 7700", 243, 212),
        ("AMD Ryzen 9 7900X", 243, 208), ("AMD Ryzen 7 9700X", 241, 214),
        ("AMD Ryzen 5 9600X", 240, 210), ("Intel Core i9-12900K", 239, 211),
        ("AMD Ryzen 5 7600X", 238, 206), ("Intel Core Ultra 5 245K", 232, 206),
        ("AMD Ryzen 5 7600", 231, 200), ("Intel Core i7-12700K", 226, 209),
        ("Intel Core i5-12600K", 214, 196), ("AMD Ryzen 7 5800X3D", 213, 192),
        ("Intel Core i5-12400F", 206, 189), ("AMD Ryzen 7 5700X3D", 204, 183),
        ("AMD Ryzen 7 5700X", 184, 151), ("Intel Core i3-12100F", 168, 137),
    ],
    ("Watch Dogs Legion", "Ultra"): [
        ("AMD Ryzen 7 9800X3D", 234, 206), ("AMD Ryzen 7 7800X3D", 205, 152),
        ("AMD Ryzen 9 7950X3D", 203, 150), ("AMD Ryzen 9 7900X3D", 188, 141),
        ("Intel Core i9-14900K", 182, 137), ("Intel Core i7-14700K", 179, 133),
        ("AMD Ryzen 7 5800X3D", 171, 126), ("AMD Ryzen 9 9950X", 170, 122),
        ("AMD Ryzen 7 9700X", 167, 124), ("AMD Ryzen 7 7700X", 165, 122),
        ("AMD Ryzen 7 5700X3D", 164, 121), ("AMD Ryzen 9 7950X", 163, 120),
        ("AMD Ryzen 7 7700", 162, 120), ("Intel Core i5-14600K", 161, 119),
        ("AMD Ryzen 5 9600X", 161, 116), ("Intel Core Ultra 9 285K", 160, 116),
        ("AMD Ryzen 9 7900X", 157, 117), ("AMD Ryzen 9 9900X", 156, 115),
        ("Intel Core Ultra 7 265K", 155, 111), ("Intel Core i9-12900K", 153, 115),
        ("AMD Ryzen 5 7600X", 153, 113), ("Intel Core i7-12700K", 151, 113),
        ("AMD Ryzen 5 7600", 148, 111), ("Intel Core i5-12600K", 139, 106),
        ("Intel Core i5-12400F", 134, 102), ("Intel Core Ultra 5 245K", 130, 93),
        ("AMD Ryzen 7 5700X", 123, 90), ("Intel Core i3-12100F", 93, 67),
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
    print(f"  {'oyun':32s} {'n':>3s} {'en hizli':>9s} {'en yavas':>9s} {'yayilim':>8s}")
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
        hi = max(r[1] for r in rows)
        lo = min(r[1] for r in rows)
        print(f"  {game[:32]:32s} {n:3d} {hi:8.0f}f {lo:8.0f}f {hi / lo:8.2f}x")

    print()
    print(f"  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}"
          f"{f', {missing} CPU katalogda yok' if missing else ''}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
