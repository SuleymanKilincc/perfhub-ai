"""
Batch 21 — the rest of the Battlefield 6 43-card comparison: 1080p Overkill,
the lower half of 1440p Overkill, and the lower half of 1080p High.

Same video, system and pass as batch 20 (Ryzen 7 9800X3D, 32 GB DDR5-6000,
third single-player mission, TAA at native resolution, no frame generation),
and the same rule: every number was read by eye from a screenshot of the chart,
not taken from the video's AI summary. Rows whose label sits under the player
controls or is cut off by the screenshot edge are not loaded.

    1080p Overkill   36 cards, the whole chart except its last, unreadable row
    1440p Overkill   18 cards below the RX 7800 XT, where batch 20 stopped
    1080p High       18 cards; the top of this chart was not captured

This is the first time the catalogue has measurements for Intel Arc cards
(B580 and A770), and the first time it has the same GPU in two memory sizes
under the same conditions — which is what the rest of this note is about.

**Eight gigabytes is not enough for Overkill, and the chart says so twice.**
Two pairs of cards differ only in memory:

                         1080p Overkill        1440p Overkill
    RTX 5060 Ti 16 GB    105 avg / 85 low       70 avg / 58 low
    RTX 5060 Ti  8 GB     96 avg / 37 low       45 avg / 32 low
    RX 9060 XT 16 GB      91 avg / 75 low       64 avg / 53 low
    RX 9060 XT  8 GB      78 avg / 57 low       55 avg / 45 low

and the RTX 3070 (8 GB) ties the RTX 3060 (12 GB) at 1080p Overkill, 49 and 49,
where at 1080p High it leads it by 46%. Those rows are real measurements of
real cards and they are loaded, but they measure the memory model, not the
game's GPU cost. They are marked `vram_limited` and the cost and 1%-low fits
leave them out, the same treatment texture-pack and Ray Reconstruction rows
get: a row whose frame rate is set by something other than the quantity being
fitted must not set that quantity. `validate_engine.py` reports them as their
own group, which makes them the first direct test of the VRAM penalty.

The flag is applied to every card of 8 GB or less at Overkill, not only the
two with a twin: the pairs show the effect is large, and a 5060 or 5050 is not
exempt from it for lacking a 16 GB sibling. At High only the RTX 4060 Ti 8 GB
is flagged, because only there does the twin comparison show it (90 against
104); the other 8 GB cards at High sit where their 12 and 16 GB neighbours put
them, and removing them would be removing data for the answer it gives.

Two catalogue errors surfaced while matching names, and both matter here:
the desktop RTX 5050 was recorded with 6 GB and the RX 9060 with 12 GB. Both
have 8 GB. A 6 GB 5050 would be treated as spilling where the real card is
merely tight, and a 12 GB RX 9060 would be told it has room it does not have.

    python scripts/load_benchmarks_21.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager
from core import scoring_engine as se

GAME = "Battlefield 6"
CPU = "AMD Ryzen 7 9800X3D"
RAM = 32
SOURCE = "b23-bf6-43gpu"
N, A, I = "NVIDIA GeForce ", "AMD Radeon ", "Intel Arc "

VRAM_FIXES = {N + "RTX 5050": 8, A + "RX 9060": 8}

# (resolution, preset) -> card -> (average, 1% low), read from the screenshots
ROWS = {
    ("1080p", "Extreme"): {
        N + "RTX 5090": (238, 155), N + "RTX 4090": (181, 127), N + "RTX 5080": (180, 126),
        N + "RTX 5070 Ti": (168, 118), N + "RTX 4080 SUPER": (154, 111),
        A + "RX 7900 XTX": (152, 117), A + "RX 9070 XT": (150, 115), N + "RTX 4080": (150, 109),
        A + "RX 9070": (144, 108), N + "RTX 5070": (139, 99), N + "RTX 4070 Ti SUPER": (136, 100),
        A + "RX 7900 XT": (135, 98), N + "RTX 3090": (121, 93), N + "RTX 4070 SUPER": (120, 90),
        A + "RX 7900 GRE": (119, 91), A + "RX 6950 XT": (117, 95), A + "RX 7800 XT": (106, 86),
        N + "RTX 3080": (106, 81), A + "RX 6800 XT": (105, 88), N + "RTX 5060 Ti 16GB": (105, 85),
        N + "RTX 4070": (104, 82), N + "RTX 5060 Ti 8GB": (96, 37), A + "RX 7700 XT": (92, 75),
        A + "RX 6800": (92, 74), A + "RX 9060 XT 16GB": (91, 75), N + "RTX 4060 Ti 16GB": (84, 62),
        A + "RX 9060 XT 8GB": (78, 57), A + "RX 6750 XT": (77, 64), N + "RTX 5060": (73, 35),
        A + "RX 7600 XT": (68, 58), I + "B580": (66, 51), I + "A770": (61, 49),
        N + "RTX 5050": (57, 31), A + "RX 7600": (53, 28), N + "RTX 3070": (49, 37),
        N + "RTX 3060": (49, 36),
    },
    ("1440p", "Extreme"): {
        N + "RTX 3080": (75, 61), A + "RX 6800 XT": (72, 62), N + "RTX 4070": (72, 61),
        N + "RTX 5060 Ti 16GB": (70, 58), A + "RX 7700 XT": (65, 55),
        A + "RX 9060 XT 16GB": (64, 53), A + "RX 6800": (63, 51), N + "RTX 4060 Ti 16GB": (57, 38),
        A + "RX 9060 XT 8GB": (55, 45), A + "RX 6750 XT": (53, 45), I + "B580": (47, 37),
        A + "RX 7600 XT": (46, 38), N + "RTX 5060 Ti 8GB": (45, 32), N + "RTX 5060": (44, 30),
        I + "A770": (42, 33), N + "RTX 5050": (41, 28), N + "RTX 3060": (40, 30),
        N + "RTX 3070": (40, 24),
    },
    ("1080p", "High"): {
        A + "RX 6800": (116, 74), A + "RX 7700 XT": (114, 74), N + "RTX 5060": (110, 74),
        A + "RX 9060 XT 8GB": (110, 59), N + "RTX 3070": (105, 70),
        N + "RTX 4060 Ti 16GB": (104, 70), A + "RX 6750 XT": (100, 65),
        N + "RTX 4060 Ti 8GB": (90, 58), N + "RTX 3060 Ti": (89, 62), A + "RX 7600 XT": (88, 67),
        I + "B580": (78, 60), N + "RTX 5050": (73, 56), I + "A770": (72, 58),
        N + "RTX 3060": (72, 55), N + "RTX 4060": (70, 53), A + "RX 6650 XT": (67, 50),
        A + "RX 7600": (67, 48), A + "RX 6600": (64, 47),
    },
}

HIGH_VRAM_LIMITED = {N + "RTX 4060 Ti 8GB"}


def vram_limited(gpu, preset, vram):
    if preset == "Extreme":
        return vram <= 8
    return gpu in HIGH_VRAM_LIMITED


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    gpus = {r["name"]: dict(r) for r in cur.execute("SELECT * FROM gpus")}
    missing = sorted({g for tab in ROWS.values() for g in tab if g not in gpus})
    if missing:
        sys.exit(f"  not in the catalogue: {missing}")

    for name, gb in VRAM_FIXES.items():
        print(f"  {name}: vram {gpus[name]['vram']} GB -> {gb} GB")
        gpus[name]["vram"] = gb
        if apply_changes:
            cur.execute("UPDATE gpus SET vram=? WHERE name=?", (gb, name))

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    if "vram_limited" not in cols:
        print("  new column: benchmarks.vram_limited INTEGER DEFAULT 0")
        if apply_changes:
            cur.execute("ALTER TABLE benchmarks ADD COLUMN vram_limited INTEGER DEFAULT 0")
            cur.execute("UPDATE benchmarks SET vram_limited=0 WHERE vram_limited IS NULL")

    cpu = dict(cur.execute("SELECT * FROM cpus WHERE name=?", (CPU,)).fetchone())
    game = dict(cur.execute("SELECT * FROM games WHERE name=?", (GAME,)).fetchone())

    print(f"\n  {'':34s} {'res':5s} {'preset':7s} {'meas':>5s} {'pred':>5s} {'err':>6s}"
          f"  {'engine memory':12s} flag")
    added = skipped = 0
    errs = {True: [], False: []}
    for (res, preset), tab in ROWS.items():
        for gpu, (avg, low) in tab.items():
            flag = vram_limited(gpu, preset, gpus[gpu]["vram"])
            d = se.estimate_fps_detailed(cpu, gpus[gpu], game, res, preset, "Native",
                                         "Kapalı", RAM)
            err = (d["fps"] - avg) / avg * 100
            errs[flag].append(err)
            print(f"  {gpu[-34:]:34s} {res:5s} {preset:7s} {avg:5d} {d['fps']:5.0f} "
                  f"{err:+5.0f}%  {d['status']:12s} {'VRAM' if flag else ''}")

            dup = cur.execute(
                "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
                " AND settings=? AND upscaling='Native' AND ray_tracing=0",
                (GAME, CPU, gpu, res, preset)).fetchone()
            if dup:
                skipped += 1
                continue
            added += 1
            if apply_changes:
                cur.execute(
                    "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings, upscaling,"
                    " frame_gen, ray_tracing, path_tracing, ray_reconstruction, ram_gb,"
                    " fps_avg, fps_1pct_low, scene, source, verified, vram_limited)"
                    " VALUES (?,?,?,?,?,'Native','Kapalı',0,0,0,?,?,?,'benchmark',?,1,?)",
                    (GAME, CPU, gpu, res, preset, RAM, avg, low, SOURCE, int(flag)))

    print()
    for flag, label in ((False, "fitted rows"), (True, "vram_limited rows")):
        e = errs[flag]
        if e:
            print(f"  {label:18s} n={len(e):2d}  mean abs {sum(map(abs, e)) / len(e):5.1f}%"
                  f"  bias {sum(e) / len(e):+5.1f}%  (before any refit)")
    print(f"  {added} rows {'added' if apply_changes else 'to add'}"
          f"{f', {skipped} already present' if skipped else ''}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  {total} measurements in total")
        print("  next: calibrate_engine.py --apply, calibrate_fps_low.py --apply,"
              " migrate_gpu_measured.py --apply, export_engine_data.py")
    else:
        print("  (dry run — pass --apply to write)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
