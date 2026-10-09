"""
Batch 22 — RTX 5060 against RTX 5060 Ti 8 GB against RTX 5060 Ti 16 GB, on one
system, in ten games at 1440p.

A video from JEGS TV: Ryzen 7 9800X3D, the three cards side by side under an
on-screen overlay, one preset and upscaler per game. It is the first data the
table holds for the question the VRAM model most needs answered — the same GPU
core at 8 and 16 GB, in many games, with nothing else changed — and it is the
reason batch 21's 8 GB rows were flagged rather than trusted (gap 6i).

**Free gameplay, so held out.** Every clip is play, not a benchmark loop, and
the number used is the large "AVG FPS" caption, not the overlay's running
average, which disagrees with it by up to 14 fps in the same frame (Resident
Evil Requiem reads 74 on the overlay and 65 on the caption for the 8 GB card).
Rows are loaded `scene='gameplay'`: the fits never see them, and the quantity
that matters here — the 8 GB / 16 GB ratio within a game — is scene-independent,
because the scene is the same on both sides.

**1% lows are not loaded.** The overlay's 1% low is a running figure sampled at
an arbitrary moment of the clip, not the run's, so it is left NULL rather than
mixed with the chart-read lows of batch 20-21.

**Assumptions, each one a guess to be checked rather than a reading:**
  - System RAM is not stated. Escape from Tarkov's overlay reads 33 GB in use,
    which rules out 32 GB, so 64 GB is used.
  - Ray tracing is read from the caption when it names it (Cyberpunk and
    Monster Hunter Wilds say off). Where the caption is silent — Forza Horizon
    6, Resident Evil Requiem, Black Myth: Wukong — it is taken as off.
  - Kingdom Come: Deliverance 2 has no caption showing its name (the screenshot
    had the player controls hidden); it was identified from the scene.
  - "Very High" (Black Myth: Wukong, Counter-Strike 2) is loaded as Ultra, and
    Black Myth's "DLSS 75 (Quality)" as DLSS Quality.

**Not loaded:** Assassin's Creed Shadows, Clair Obscur: Expedition 33 and Call
of Duty: Black Ops 7, which are not in the catalogue; Escape from Tarkov, whose
caption says "custom settings", which names nothing the engine can read; and
a fifteenth game the screenshots did not include.

    python scripts/load_benchmarks_22.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager
from core import scoring_engine as se

CPU = "AMD Ryzen 7 9800X3D"
RAM = 64
SOURCE = "b24-jegs-5060ti-8v16"
G5060 = "NVIDIA GeForce RTX 5060"
G8 = "NVIDIA GeForce RTX 5060 Ti 8GB"
G16 = "NVIDIA GeForce RTX 5060 Ti 16GB"

# game -> (preset, upscaling, ray_tracing, timestamp, (5060, 5060 Ti 8GB, 5060 Ti 16GB))
# Averages are the large caption figures, read from screenshots.
CLIPS = {
    "Forza Horizon 6":          ("Extreme", "DLAA",         0, "2:27",  (45, 52, 72)),
    "Resident Evil Requiem":    ("Ultra",   "DLAA",         0, "3:44",  (37, 65, 77)),
    "Kingdom Come: Deliverance 2": ("Ultra", "DLAA",        0, "n/a",   (42, 50, 51)),
    "Path of Exile 2":          ("High",    "DLAA",         0, "6:13",  (61, 73, 74)),
    "Black Myth: Wukong":       ("Ultra",   "DLSS Quality", 0, "7:33",  (50, 58, 57)),
    "Battlefield 6":            ("Ultra",   "DLAA",         0, "10:04", (47, 56, 65)),
    "Monster Hunter Wilds":     ("Ultra",   "DLAA",         0, "15:12", (50, 58, 58)),
    "Cyberpunk 2077":           ("Ultra",   "DLAA",         0, "16:22", (40, 49, 50)),
    "Counter-Strike 2":         ("Ultra",   "Native",       0, "17:35", (163, 184, 182)),
    "PUBG":                     ("Ultra",   "Native",       0, "19:59", (157, 185, 192)),
}


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}
    cpu = dict(cur.execute("SELECT * FROM cpus WHERE name=?", (CPU,)).fetchone())

    missing = [g for g in list(CLIPS) if g not in games] + \
              [g for g in (G5060, G8, G16) if g not in gpus]
    if missing:
        sys.exit(f"  not in the catalogue: {missing}")

    print(f"  {'game':30s} {'preset':8s} {'8/16 meas':>9s} {'8/16 eng':>9s} "
          f"{'5060ti16 meas':>13s} {'eng':>5s} {'err':>5s}  engine memory (8GB / 16GB)")
    added = skipped = 0
    rows = []
    for name, (preset, ups, rt, ts, fps) in CLIPS.items():
        eng = {}
        for gpu, f in zip((G5060, G8, G16), fps):
            d = se.estimate_fps_detailed(cpu, gpus[gpu], games[name], "1440p", preset,
                                         ups, "Kapalı", RAM, ray_tracing=bool(rt))
            eng[gpu] = d
            dup = cur.execute(
                "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution='1440p'"
                " AND settings=? AND upscaling=? AND frame_gen='Kapalı' AND ray_tracing=?"
                " AND path_tracing=0 AND rt_level IS NULL AND source=?",
                (name, CPU, gpu, preset, ups, rt, SOURCE)).fetchone()
            if dup:
                skipped += 1
                continue
            added += 1
            if apply_changes:
                cur.execute(
                    "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings, upscaling,"
                    " frame_gen, ray_tracing, path_tracing, ray_reconstruction, ram_gb,"
                    " fps_avg, scene, source, verified)"
                    " VALUES (?,?,?,'1440p',?,?,'Kapalı',?,0,0,?,?,'gameplay',?,1)",
                    (name, CPU, gpu, preset, ups, rt, RAM, f, SOURCE))
        m = fps[1] / fps[2]
        e = eng[G8]["fps"] / eng[G16]["fps"]
        err16 = (eng[G16]["fps"] - fps[2]) / fps[2] * 100
        rows.append((m, e))
        print(f"  {name[:30]:30s} {preset:8s} {m:9.2f} {e:9.2f} {fps[2]:13d} "
              f"{eng[G16]['fps']:5.0f} {err16:+4.0f}%  "
              f"{eng[G8]['status']} / {eng[G16]['status']}")

    n = len(rows)
    print(f"\n  mean 8/16 ratio: measured {sum(r[0] for r in rows) / n:.3f}, "
          f"engine {sum(r[1] for r in rows) / n:.3f}  ({n} games)")
    print(f"  {added} rows {'added' if apply_changes else 'to add'}"
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
