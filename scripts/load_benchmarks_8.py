"""
Batch 8 — Kingdom Come: Deliverance 2, for its 1% low ratio.

Loaded to answer one question and it answered a different one too.

**The ratio.** KCD2 was using the global 0.758 default, and a relayed source put
its busy-scene drop at 30-40% in Kuttenberg. Measured across these nine rows the
ratio is 0.874 — a 13% drop, not 30. That makes it one of the steadiest games in
the set, next to Hitman 3 at 0.878, rather than one of the twitchiest.

The claim is not refuted, though, and the difference matters: this video has no
Kuttenberg measurements. Every row is rural, forest or indoors, and the source's
own summary says so. So what is now recorded is the ratio *outside* the city,
and the city remains unmeasured. If someone benchmarks Kuttenberg and it does
drop 30-40%, that is a per-location effect the model cannot express at all —
one ratio per game — and worth knowing about rather than averaging away.

**The bias.** These rows also make the held-out set useful for the first time.
Every one of the twelve rows it held before was on a GTX 1080 Ti, which the
engine itself flags as outside its validated range, so its 22.4% measured two
things at once and could not separate them. This is an RTX 5080 with a 9800X3D
— modern, inside the range, nothing flagged — and the engine reads +14.5% high
across all nine. That lines up with the +10.7% the older held-out rows show, so
the gap between a benchmark run and someone playing is now visible on hardware
where nothing else is in the way.

Free gameplay, so scene='gameplay' and none of it reaches the cost fit. It does
reach the ratio fit, which has no scene filter — KCD2 will be the only game
whose ratio comes from gameplay rather than a benchmark loop, and
calibrate_fps_low.py now says which is which.

    python scripts/load_benchmarks_8.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Kingdom Come: Deliverance 2"
CPU = "AMD Ryzen 7 9800X3D"
GPU = "NVIDIA GeForce RTX 5080"
RAM = 32
SOURCE = "b13-kcd2-5080"

# "Exp." in the video is Experimental, the game's top preset, which maps onto
# the model's Extreme tier. "Native AA" is the game's own temporal pass at full
# resolution — DLAA in the model's vocabulary.
#
# resolution, settings, upscaling, avg, 1% low, where
ROWS = [
    ("4k",    "Ultra",   "DLAA",         63,  54, "indoors"),
    ("4k",    "Ultra",   "DLAA",         65,  58, "rural"),
    ("4k",    "Ultra",   "DLSS Quality", 100, 85, "rural"),
    ("1440p", "Ultra",   "DLAA",         120, 107, "rural"),
    ("4k",    "Extreme", "DLAA",         60,  50, "rural"),
    ("4k",    "Extreme", "DLSS Quality", 80,  70, "rural"),
    ("1440p", "Extreme", "DLAA",         100, 90, "rural"),
    ("1440p", "Extreme", "DLSS Quality", 110, 95, "indoors"),
    ("1080p", "Extreme", "DLAA",         100, 90, "rural"),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table, name in (("games", GAME), ("cpus", CPU), ("gpus", GPU)):
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")

    print(f"  {'coz':6s} {'preset':8s} {'ups':13s} {'ort':>4s} {'low':>4s} {'oran':>6s}  konum")
    added = skipped = 0
    ratios = []
    for res, settings, ups, avg, low, where in ROWS:
        ratios.append(low / avg)
        print(f"  {res:6s} {settings:8s} {ups:13s} {avg:4d} {low:4d} {low / avg:6.3f}  {where}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings=? AND upscaling=? AND fps_avg=?",
            (GAME, CPU, GPU, res, settings, ups, avg)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
                " fps_1pct_low, scene, vram_measured_kind, source, verified)"
                " VALUES (?,?,?,?,?,?,'Kapalı',0,0,?,?,?,'gameplay','allocated',?,1)",
                (GAME, CPU, GPU, res, settings, ups, RAM, avg, low, SOURCE))

    mean = sum(ratios) / len(ratios)
    print()
    print(f"  oran ortalamasi {mean:.3f}  (kuresel varsayilan 0.758 idi)")
    print(f"  yayilim {min(ratios):.3f}-{max(ratios):.3f}")
    print("  not: bu videoda sehir merkezi (Kuttenberg) olcumu yok — kayitli oran")
    print("       sehir disi icin gecerli.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        held = cur.execute("SELECT COUNT(*) FROM benchmarks WHERE scene='gameplay'").fetchone()[0]
        print(f"  toplam {total} olcum, {held} tanesi fit disi")
        print("  simdi: calibrate_fps_low.py --apply, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
