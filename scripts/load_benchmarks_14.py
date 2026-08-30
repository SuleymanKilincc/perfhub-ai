"""
Batch 14 — Far Cry 6 from two videos, one with the HD texture pack and one
without, and the first clean measurements this game has ever had.

Far Cry 6's cost profile was fitted from two rows and both used the optional
38 GB texture pack, which the model does not represent. So the profile
described a configuration the engine cannot express and then answered for the
one it can — reading -31% against an ordinary install. Those rows are now
marked `texture_pack` and excluded from fitting, the same way free gameplay is.

**The pack's size, from our own table.** An RTX 4060 Ti 8GB with it reads 28 fps
at 1440p Ultra with ray tracing. The RTX 3060 Ti 8GB here, same settings, reads
68. A 2.4x collapse from a texture download, and the reason the second video can
be called pack-free with evidence rather than assumption — an 8 GB card simply
would not survive it.

**Ray tracing costs far less here than the global multiplier says.** The second
video measures it on and off at the same settings and place:

    1080p   108 -> 75    1.44x
    1440p    80 -> 68    1.18x
    4K       44 -> 40    1.10x

4K is the clean read, since at 1080p the ray-tracing-off figure is high enough
that the processor may be setting it. 1.10x against a global RT_GPU_COST_MULT
of 1.70. Far Cry 6's ray tracing is reflections and shadows; Cyberpunk's is a
different order of work. One boolean is averaging implementations that are not
comparable — the same shape as the RT-preset gap, one level up.

Both videos are free gameplay, so none of this reaches the fit. What it does
give is the ratio, at 0.736 without the pack and 0.748 with it — close enough
that the pack does not appear to change frame-time consistency, only the level.

    python scripts/load_benchmarks_14.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Far Cry 6"
CPU = "AMD Ryzen 9 5900X"

# gpu, resolution, settings, upscaling, rt, avg, low, texture_pack, where
ROWS = [
    # Video 1 — GTX 1080 Ti, HD texture pack confirmed installed at 1:46.
    ("NVIDIA GeForce GTX 1080 Ti", "1080p", "High", "Native", 0, 67, 51, 1, "jungle"),
    ("NVIDIA GeForce GTX 1080 Ti", "1080p", "High", "FSR Ultra Performance", 0, 76, 60, 1, "jungle"),
    ("NVIDIA GeForce GTX 1080 Ti", "1440p", "High", "Native", 0, 69, 52, 1, "jungle"),
    ("NVIDIA GeForce GTX 1080 Ti", "1440p", "High", "FSR Ultra Performance", 0, 70, 54, 1, "jungle"),
    ("NVIDIA GeForce GTX 1080 Ti", "4k",    "High", "Native", 0, 45, 32, 1, "jungle"),
    ("NVIDIA GeForce GTX 1080 Ti", "4k",    "High", "FSR Ultra Performance", 0, 60, 42, 1, "jungle"),
    # Video 2 — RTX 3060 Ti, no pack (see above).
    ("NVIDIA GeForce RTX 3060 Ti", "1080p", "Ultra", "Native", 0, 108, 76, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "1440p", "Ultra", "Native", 0, 80, 58, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "1440p", "Ultra", "FSR Quality", 0, 100, 72, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "4k",    "Ultra", "Native", 0, 44, 35, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "4k",    "Ultra", "FSR Ultra Performance", 0, 60, 45, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "1080p", "Ultra", "Native", 1, 75, 52, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "1440p", "Ultra", "Native", 1, 68, 48, 0, "open country"),
    ("NVIDIA GeForce RTX 3060 Ti", "4k",    "Ultra", "Native", 1, 40, 32, 0, "open country"),
]
# The 1440p 75 fps "camp" row from video 2 duplicates the 80 fps open-country
# one at identical settings; a scene difference the model cannot express, so it
# is left out rather than averaged in.


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    added = skipped = 0
    groups = {}
    print(f"  {'kart':16s} {'coz':6s} {'ayar':6s} {'ups':22s} {'rt':2s} {'ort':>4s} {'low':>4s} {'oran':>6s} paket")
    for gpu, res, st_, ups, rt, avg, low, pack, where in ROWS:
        if not cur.execute("SELECT 1 FROM gpus WHERE name=?", (gpu,)).fetchone():
            sys.exit(f"  {gpu} katalogda yok")
        groups.setdefault(pack, []).append(low / avg)
        print(f"  {gpu[14:30]:16s} {res:6s} {st_:6s} {ups:22s} {rt:2d} {avg:4d} {low:4d}"
              f" {low / avg:6.3f} {'VAR' if pack else '-'}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings=? AND upscaling=? AND ray_tracing=?",
            (GAME, CPU, gpu, res, st_, ups, rt)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
                " fps_1pct_low, scene, texture_pack, vram_measured_kind, source,"
                " verified) VALUES (?,?,?,?,?,?,'Kapalı',?,0,32,?,?,'gameplay',?,"
                "'allocated','b19-fc6-two-videos',1)",
                (GAME, CPU, gpu, res, st_, ups, rt, avg, low, pack))

    print()
    for pack, qs in sorted(groups.items()):
        label = "HD doku paketi ile" if pack else "paket olmadan"
        print(f"  {label:20s} n={len(qs)}  oran {sum(qs) / len(qs):.3f}")
    print("  -> paket seviyeyi degistiriyor, kare tutarliligini degil.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}")
    if apply_changes:
        conn.commit()
        print(f"  toplam {cur.execute('SELECT COUNT(*) FROM benchmarks').fetchone()[0]} olcum")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
