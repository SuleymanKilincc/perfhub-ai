"""
The VRAM model's direct test: the same graphics chip at 8 and at 16 GB.

Two cards that differ only in memory, measured under identical conditions, give
a ratio — 8 GB frame rate over 16 GB — that nothing else can move. The engine
predicts the same ratio. Where they disagree, the memory model is wrong, and
nothing about the game's cost or the chip's speed can be blamed for it.

The table holds 19 such pairs (RTX 5060 Ti, RTX 4060 Ti, RX 9060 XT), from
three sources: a 43-card Battlefield 6 comparison, a 15-game JEGS TV video, and
older single-game 4060 Ti comparisons. Far Cry 6's HD-texture-pack pair is left
out, as it is everywhere: the model has no term for the pack.

This script reports how far apart they are, then asks the question a refit
would have to answer: is a better set of memory constants better *outside the
games it was fitted on*? Leave-one-game-out says no (see CALIBRATION.md, gap
6i), which is why the constants and the GPU scores were not changed.

    python scripts/memory_pairs.py            # measured vs predicted ratios
    python scripts/memory_pairs.py --refit    # + the refit and its cross-check
"""
import argparse
import itertools
import os
import sqlite3
import statistics
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import balance_config as bc
from core import db_manager
from core import scoring_engine as se

CHIPS = ("NVIDIA GeForce RTX 5060 Ti", "NVIDIA GeForce RTX 4060 Ti",
         "AMD Radeon RX 9060 XT")


def load():
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    cpus = {c["name"]: dict(c) for c in db_manager.get_all_cpus()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM benchmarks WHERE COALESCE(texture_pack,0)=0")]
    conn.close()
    return games, cpus, gpus, rows


def find_pairs(rows):
    """[(chip, row_8gb, row_16gb)] for rows identical in everything but the card."""
    groups = defaultdict(dict)
    for r in rows:
        for chip in CHIPS:
            for tag in ("8GB", "16GB"):
                if r["gpu"] == f"{chip} {tag}":
                    key = (chip, r["game"], r["cpu"], r["resolution"], r["settings"],
                           r["upscaling"], r["frame_gen"], r["ray_tracing"],
                           r["path_tracing"], r["scene"], r["ram_gb"])
                    groups[key][tag] = r
    return [(k[0], v["8GB"], v["16GB"]) for k, v in groups.items()
            if "8GB" in v and "16GB" in v]


def engine_fps(ctx, row, scores=None):
    games, cpus, gpus, _ = ctx
    gpu = dict(gpus[row["gpu"]])
    if scores:
        gpu["power_score"] = scores[row["gpu"]]
    return se.estimate_fps_detailed(
        cpus[row["cpu"]], gpu, games[row["game"]], row["resolution"], row["settings"],
        row["upscaling"], row["frame_gen"], row["ram_gb"],
        ray_tracing=bool(row["ray_tracing"]), path_tracing=bool(row["path_tracing"]))


def ratios(ctx, pairs, scores=None):
    out = []
    for chip, a, b in pairs:
        ea, eb = engine_fps(ctx, a, scores), engine_fps(ctx, b, scores)
        out.append({"chip": chip, "game": a["game"], "scene": a["scene"],
                    "measured": a["fps_avg"] / b["fps_avg"],
                    "engine": ea["fps"] / eb["fps"],
                    "status": f"{ea['status']}/{eb['status']}"})
    return out


def ratio_error(ctx, pairs, scores=None):
    return statistics.mean(abs(r["engine"] - r["measured"]) / r["measured"] * 100
                           for r in ratios(ctx, pairs, scores))


def summary(ctx, pairs):
    rs = ratios(ctx, pairs)
    return {
        "pairs": len(rs),
        "games": len({r["game"] for r in rs}),
        "measured_min": min(r["measured"] for r in rs),
        "measured_max": max(r["measured"] for r in rs),
        "engine_min": min(r["engine"] for r in rs),
        "engine_max": max(r["engine"] for r in rs),
        "error": statistics.mean(abs(r["engine"] - r["measured"]) / r["measured"] * 100
                                 for r in rs),
    }


def main(refit):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ctx = load()
    pairs = find_pairs(ctx[3])
    rs = ratios(ctx, pairs)
    print(f"  {len(rs)} pairs across {len({r['game'] for r in rs})} games\n")
    print(f"  {'chip':28s} {'game':28s} {'scene':9s} {'meas':>5s} {'eng':>5s}  engine status (8GB/16GB)")
    for r in sorted(rs, key=lambda r: r["measured"]):
        print(f"  {r['chip'][-14:]:28s} {r['game'][:28]:28s} {r['scene'] or '':9s} "
              f"{r['measured']:5.2f} {r['engine']:5.2f}  {r['status']}")

    s = summary(ctx, pairs)
    print(f"\n  measured ratio {s['measured_min']:.2f} to {s['measured_max']:.2f}; "
          f"the engine's {s['engine_min']:.2f} to {s['engine_max']:.2f}")
    print(f"  mean |ratio error|: {s['error']:.1f}%")
    by_status = defaultdict(list)
    for r in rs:
        by_status[r["status"].split("/")[0]].append(r["measured"])
    for k, v in sorted(by_status.items()):
        print(f"    engine says {k:11s} n={len(v):2d}  measured mean {statistics.mean(v):.2f}")
    if not refit:
        return

    # Same-chip variants scored alike: the 8 GB cards' scores came from a
    # hierarchy in which they already read low *because of* their memory.
    games, cpus, gpus, _ = ctx
    equal = {n: g["power_score"] for n, g in gpus.items()}
    for chip in CHIPS:
        equal[f"{chip} 8GB"] = gpus[f"{chip} 16GB"]["power_score"]

    orig = (bc.VRAM_TIGHT_PENALTY, bc.VRAM_SPILL_SEVERITY, bc.VRAM_SPILL_FLOOR)

    def err(sel, scores, consts):
        bc.VRAM_TIGHT_PENALTY, bc.VRAM_SPILL_SEVERITY, bc.VRAM_SPILL_FLOOR = consts
        return ratio_error(ctx, sel, scores)

    grid = list(itertools.product([0.90, 0.92, 0.94, 0.96, 0.98],
                                  [0.5, 1.0, 1.5, 2.0, 3.0, 4.0],
                                  [0.4, 0.5, 0.6, 0.7, 0.8]))
    best = lambda sel, scores: min(grid, key=lambda c: err(sel, scores, c))

    print("\n  --- would a refit generalise? ---")
    print(f"  current scores, current constants {orig}: {err(pairs, None, orig):.2f}%")
    print(f"  same-chip scores equal, current constants:    {err(pairs, equal, orig):.2f}%")
    b = best(pairs, equal)
    print(f"  equal scores, refitted on all pairs {b}:  {err(pairs, equal, b):.2f}%  (in sample)")
    cv = []
    for game in sorted({p[1]["game"] for p in pairs}):
        train = [p for p in pairs if p[1]["game"] != game]
        test = [p for p in pairs if p[1]["game"] == game]
        cv.append(err(test, equal, best(train, equal)))
    print(f"  the same refit, leave-one-game-out:           {statistics.mean(cv):.2f}%")
    bc.VRAM_TIGHT_PENALTY, bc.VRAM_SPILL_SEVERITY, bc.VRAM_SPILL_FLOOR = orig
    verdict = ("worse" if statistics.mean(cv) > err(pairs, None, orig) else "better")
    print(f"  -> out of sample it is {verdict} than leaving the model alone")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refit", action="store_true")
    main(ap.parse_args().refit)
