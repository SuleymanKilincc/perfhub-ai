"""
Batch 11 — Starfield, and the second answer to the location question.

Nine rows, none discarded, which has not happened before in this series. No
ratio above 0.95 or below half, no frame generation, no anti-aliasing filed as
an upscaler. The spread runs 0.731 to 0.771 — the tightest of any game
measured.

**The location question is now answered twice.** It was raised by a claim that
Kingdom Come: Deliverance 2 drops 30-40% in Kuttenberg where it measures 13%
elsewhere, and the worry behind it was real: if the ratio belongs to the place
rather than the game, storing one number per title is wrong.

    Red Dead Redemption 2   Saint Denis 0.792   countryside 0.798
    Starfield               New Atlantis 0.753  planet surface 0.753

Saint Denis and New Atlantis are the two best-known CPU walls in any open world
here, and neither moves the ratio. Different studios, different engines — RAGE
and Creation Engine 2 — and the same answer. One ratio per game is the right
shape.

Note what this does *not* say. Baldur's Gate 3 showed that the frame rate
*level* moves enormously with location: the engine is 12% low in Act 1 and 57%
high in Act 3's Lower City. Location matters, and matters a lot. It just does
not appear to change how far the 1% low sits below the average.

The frame rates run +20.3% against the engine, in line with everything else
free-play has said. The 8K DLSS Performance row is the outlier at +63.8%, which
is the upscaling gain being over-credited where the CPU has already become the
limit — the same shape as the DLSS Quality to Performance step measured here,
130 to 132 fps, where the model expects far more.

    python scripts/load_benchmarks_11.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Starfield"
CPU = "AMD Ryzen 7 9800X3D"
GPU = "NVIDIA GeForce RTX 5090"
RAM = 32
SOURCE = "b16-starfield-5090"

# resolution, upscaling, avg, 1% low, where
ROWS = [
    ("4k",    "DLAA",                   90,  68,  "New Atlantis"),
    ("4k",    "DLSS Quality",           130, 95,  "New Atlantis"),
    ("4k",    "DLSS Performance",       132, 98,  "New Atlantis"),
    ("4k",    "DLSS Ultra Performance", 160, 120, "New Atlantis"),
    ("4k",    "DLSS Quality",           125, 96,  "planet surface"),
    ("8k",    "DLAA",                   30,  22,  "planet surface"),
    ("8k",    "DLSS Performance",       58,  44,  "planet surface"),
    ("1440p", "DLAA",                   122, 94,  "New Atlantis"),
    ("1080p", "DLAA",                   140, 108, "New Atlantis"),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table, name in (("games", GAME), ("cpus", CPU), ("gpus", GPU)):
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")

    print(f"  {'coz':6s} {'ups':23s} {'ort':>4s} {'low':>4s} {'oran':>6s}  konum")
    added = skipped = 0
    by_place = {}
    for res, ups, avg, low, where in ROWS:
        by_place.setdefault(where, []).append(low / avg)
        print(f"  {res:6s} {ups:23s} {avg:4d} {low:4d} {low / avg:6.3f}  {where}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings='Ultra' AND upscaling=? AND fps_avg=?",
            (GAME, CPU, GPU, res, ups, avg)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
                " fps_1pct_low, scene, vram_measured_kind, source, verified)"
                " VALUES (?,?,?,?,'Ultra',?,'Kapalı',0,0,?,?,?,'gameplay',"
                "'allocated',?,1)",
                (GAME, CPU, GPU, res, ups, RAM, avg, low, SOURCE))

    print()
    print("  KONUM KARSILASTIRMASI")
    for place, qs in by_place.items():
        print(f"    {place:16s} n={len(qs)}  {sum(qs) / len(qs):.3f}")
    print("    -> fark yok. RDR2'de Saint Denis 0.792 / kirsal 0.798 idi;")
    print("       iki farkli oyun, iki farkli motor, ayni cevap. Oyun basina")
    print("       tek oran dogru sekil.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}, hicbiri elenmedi")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_fps_low.py --apply, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
