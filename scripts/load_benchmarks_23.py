"""
Batch 23 — RTX 4060 Ti 8 GB against 16 GB, seven games, each at 1440p and 4K.

A video titled "RTX 4060 Ti 16gb vs RTX 4060 Ti 8gb - Watch This Before Buy":
Core i9-13900K, 32 GB DDR5-7000, the two cards side by side under an overlay,
every game at High with DLSS Quality. Batch 22 had the same chip at 8 and 16 GB
in many games but at one resolution. This is what it lacked: **the same game at
two resolutions**, which is the only thing that can show where a game's working
set crosses 8 GB (gap 6i).

What the frames show, before any model is involved: at 1440p the 8 GB card
loses nothing (ratio 0.98-0.99 in all seven games); at 4K it loses 0-60%
(Diablo IV 0.40, Hogwarts Legacy 0.72, Witcher 3 0.76, Watch Dogs Legion
0.77, Flight Simulator 0.79, Cyberpunk 0.77, Red Dead Redemption 2 1.00).

**Free gameplay, held out.** One overlay reading per game and resolution, taken
from a screenshot of the segment: the overlay's AVG FPS, a running average, so
it is the average of the seconds before the frame, not of a run. Both cards are
shown at the same instant of the same scene, so the *ratio* is sound even where
the absolute figure is noisy; the Cyberpunk 1440p frame is seven seconds into
its segment. 1% lows are not loaded, for the reason given in batch 22.

**Settings, as the user read them from the video's captions** (the screenshots
carried only Cyberpunk's and Red Dead Redemption 2's 1440p caption):
  - every game: High, DLSS Quality;
  - ray tracing on at 1440p and off at 4K for Hogwarts Legacy, The Witcher 3
    and Watch Dogs Legion; off in Diablo IV, Flight Simulator, Red Dead 2;
  - Cyberpunk 2077 at 1440p: ray tracing on, frame generation off (caption).
**Cyberpunk at 4K was not stated.** It is loaded with ray tracing on, which is
an inference — the 16 GB card reads 44 fps and 11.9 GB, a figure that fits ray
tracing and not its absence — and the row is the one to doubt.

**Two identifications are inferences.** The Witcher 3 is loaded as the
Next-Gen edition because the overlay says DirectX 12 and the game has ray
tracing on at 1440p, which only that edition does. The Hogwarts Legacy 4K frame
is a flying shot with no chapter label; it is taken as 4K because the 16 GB card
reads 9.8 GB where the 1440p frame reads 6.6.

**Not loaded:** Horizon Zero Dawn, which is in the video (1440p 94/93 fps, 4K
54/32) but not in the catalogue, and whose edition (original or Remastered) the
screenshots do not settle.

    python scripts/load_benchmarks_23.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager
from core import scoring_engine as se

CPU = "Intel Core i9-13900K"
RAM = 32
SOURCE = "b25-4060ti-8v16-res"
G8 = "NVIDIA GeForce RTX 4060 Ti 8GB"
G16 = "NVIDIA GeForce RTX 4060 Ti 16GB"

# (game, resolution, ray_tracing, timestamp, fps_16gb, fps_8gb)
ROWS = [
    ("Cyberpunk 2077",             "1440p", 1, "0:07", 56, 55),
    ("Cyberpunk 2077",             "4k",    1, "0:44", 44, 34),
    ("Diablo IV",                  "1440p", 0, "1:00", 148, 145),
    ("Diablo IV",                  "4k",    0, "1:30", 77, 31),
    ("Hogwarts Legacy",            "1440p", 1, "2:00", 73, 72),
    ("Hogwarts Legacy",            "4k",    0, "n/a",  43, 31),
    ("Microsoft Flight Simulator", "1440p", 0, "3:42", 83, 82),
    ("Microsoft Flight Simulator", "4k",    0, "4:04", 52, 41),
    ("Red Dead Redemption 2",      "1440p", 0, "4:25", 76, 75),
    ("Red Dead Redemption 2",      "4k",    0, "5:06", 42, 42),
    ("The Witcher 3 Next-Gen",     "1440p", 1, "5:33", 56, 55),
    ("The Witcher 3 Next-Gen",     "4k",    0, "5:50", 45, 34),
    ("Watch Dogs Legion",          "1440p", 1, "6:15", 75, 74),
    ("Watch Dogs Legion",          "4k",    0, "6:37", 53, 41),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}
    cpu = dict(cur.execute("SELECT * FROM cpus WHERE name=?", (CPU,)).fetchone())

    missing = sorted({r[0] for r in ROWS if r[0] not in games})
    if missing:
        sys.exit(f"  not in the catalogue: {missing}")

    print(f"  {'game':28s} {'res':5s} {'RT':2s} {'8/16 meas':>9s} {'8/16 eng':>8s}  "
          f"engine memory (8GB / 16GB)")
    added = skipped = 0
    for name, res, rt, ts, f16, f8 in ROWS:
        eng = {}
        for gpu, f in ((G8, f8), (G16, f16)):
            eng[gpu] = se.estimate_fps_detailed(
                cpu, gpus[gpu], games[name], res, "High", "DLSS Quality", "Kapalı", RAM,
                ray_tracing=bool(rt))
            dup = cur.execute(
                "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
                " AND settings='High' AND upscaling='DLSS Quality' AND frame_gen='Kapalı'"
                " AND ray_tracing=? AND path_tracing=0 AND rt_level IS NULL AND source=?",
                (name, CPU, gpu, res, rt, SOURCE)).fetchone()
            if dup:
                skipped += 1
                continue
            added += 1
            if apply_changes:
                cur.execute(
                    "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings, upscaling,"
                    " frame_gen, ray_tracing, path_tracing, ray_reconstruction, ram_gb,"
                    " fps_avg, scene, source, verified)"
                    " VALUES (?,?,?,?,'High','DLSS Quality','Kapalı',?,0,0,?,?,'gameplay',?,1)",
                    (name, CPU, gpu, res, rt, RAM, f, SOURCE))
        print(f"  {name[:28]:28s} {res:5s} {'on' if rt else 'off':2s} {f8 / f16:9.2f} "
              f"{eng[G8]['fps'] / eng[G16]['fps']:8.2f}  "
              f"{eng[G8]['status']} / {eng[G16]['status']}")

    print(f"\n  {added} rows {'added' if apply_changes else 'to add'}"
          f"{f', {skipped} already present' if skipped else ''}")
    if apply_changes:
        conn.commit()
        print(f"  {cur.execute('SELECT COUNT(*) FROM benchmarks').fetchone()[0]} measurements in total")
    else:
        print("  (dry run — pass --apply to write)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
