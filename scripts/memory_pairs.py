"""
The VRAM model's direct test: the same graphics chip at 8 and at 16 GB.

Two cards that differ only in memory, measured under identical conditions, give
a ratio — 8 GB frame rate over 16 GB — that nothing else can move. The engine
predicts the same ratio. Where they disagree, the memory model is wrong, and
nothing about the game's cost or the chip's speed can be blamed for it.

The table holds such pairs for the RTX 5060 Ti, RTX 4060 Ti and RX 9060 XT, from
four sources: a 43-card Battlefield 6 comparison, a 15-game JEGS TV video, a
7-game 4060 Ti video at two resolutions, and older single-game comparisons. Far Cry 6's HD-texture-pack pair is left
out, as it is everywhere: the model has no term for the pack.

This script reports how far apart they are, then asks the question any change
has to answer: is it better *outside the games it was fitted on*?
Leave-one-game-out is the test, and it has refused changes before (see
CALIBRATION.md, gap 6i).

    python scripts/memory_pairs.py            # measured vs predicted ratios
    python scripts/memory_pairs.py --refit    # + would a change generalise?
    python scripts/memory_pairs.py --resolution   # games measured at 1440p and 4K
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


def resolution_test(ctx, pairs):
    """What the same-game-at-two-resolutions pairs say, and what acting on it costs.

    Fits a working set per game (`vram_base_gb`) together with the memory
    constants, on games that have a pair at both 1440p and 4K, and then asks
    what that regime does to everything it was not fitted on.
    """
    games, cpus, gpus, rows = ctx
    by_game = defaultdict(set)
    for _, a, _ in pairs:
        by_game[a["game"]].add(a["resolution"])
    multi = sorted(g for g, rs in by_game.items() if len(rs) >= 2)
    fit_pairs = [p for p in pairs if p[1]["game"] in multi]
    rest = [p for p in pairs if p[1]["game"] not in multi]
    names = ("UPSCALE_VRAM_FIXED", "VRAM_TIGHT_PENALTY", "VRAM_SPILL_SEVERITY",
             "VRAM_SPILL_FLOOR")
    orig = tuple(getattr(bc, n) for n in names)
    saved = {g: games[g]["vram_base_gb"] for g in multi}

    def set_consts(c):
        for n, v in zip(names, c):
            setattr(bc, n, v)

    def err(sel, consts, bases=None):
        set_consts(consts)
        for g in multi:
            games[g]["vram_base_gb"] = (bases or saved)[g]
        e = [abs(r["engine"] - r["measured"]) / r["measured"] * 100
             for r in ratios(ctx, sel)]
        return e

    print(f"\n  --- {len(multi)} games measured at two resolutions: {', '.join(multi)} ---")
    print("  measured 8 GB / 16 GB ratio by resolution:")
    for g in multi:
        cell = {}
        for _, a, b in [p for p in fit_pairs if p[1]["game"] == g]:
            cell[a["resolution"]] = a["fps_avg"] / b["fps_avg"]
        print(f"    {g:30s} " + "  ".join(f"{k} {v:.2f}" for k, v in sorted(cell.items())))

    bases = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]
    best = None
    for c in itertools.product([0.72, 1.0], [0.94, 0.97], [0.5, 1.0, 2.0, 4.0, 8.0],
                               [0.3, 0.5, 0.8]):
        picks = {g: min(bases, key=lambda b: statistics.mean(
            err([p for p in fit_pairs if p[1]["game"] == g], c, {**saved, g: b})))
            for g in multi}
        e = statistics.mean(err(fit_pairs, c, picks))
        if best is None or e < best[0]:
            best = (e, c, picks)
    harsh_e, harsh, picks = best
    print(f"\n  {'':44s} {'these pairs':>11s} {'all other pairs':>16s}")
    print(f"  {'current model':44s} {statistics.mean(err(fit_pairs, orig)):10.1f}% "
          f"{statistics.mean(err(rest, orig)):15.1f}%")
    print(f"  {'best constants, current working sets':44s} "
          f"{statistics.mean(err(fit_pairs, harsh)):10.1f}% "
          f"{statistics.mean(err(rest, harsh)):15.1f}%")
    print(f"  {'best constants + fitted working sets':44s} {harsh_e:10.1f}% "
          f"{statistics.mean(err(rest, harsh, picks)):15.1f}%")
    print(f"  fitted: fixed={harsh[0]} tight={harsh[1]} severity={harsh[2]} "
          f"floor={harsh[3]}; working sets {picks}")

    # The cost: what that regime does to games nobody measured.
    measured_games = {r["game"] for r in rows}
    cpu = dict(cpus["Intel Core i9-13900K"])
    g8, g16 = (dict(gpus[f"NVIDIA GeForce RTX 4060 Ti {t}"]) for t in ("8GB", "16GB"))
    print("\n  unmeasured games an 8 GB card is predicted to run at under 0.70 of a 16 GB card "
          "(High, DLSS Quality):")
    for label, c in (("current", orig), ("best constants", harsh)):
        set_consts(c)
        for g in multi:
            games[g]["vram_base_gb"] = saved[g]
        for res in ("1440p", "4k"):
            pool = [g for n, g in games.items() if n not in measured_games]
            low = sum(se.estimate_fps(cpu, g8, g, res, "High", "DLSS Quality", "Kapalı", 32)
                      / se.estimate_fps(cpu, g16, g, res, "High", "DLSS Quality", "Kapalı", 32)
                      < 0.70 for g in pool)
            print(f"    {label:15s} {res:5s} {low:3d} of {len(pool)}")
    set_consts(orig)
    for g in multi:
        games[g]["vram_base_gb"] = saved[g]


def main(refit, resolution=False):
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
    if resolution:
        resolution_test(ctx, pairs)
    if not refit:
        return

    # Same-chip variants scored alike: the 8 GB cards' scores came from a
    # hierarchy in which they already read low *because of* their memory.
    games, cpus, gpus, _ = ctx
    equal = {n: g["power_score"] for n, g in gpus.items()}
    for chip in CHIPS:
        equal[f"{chip} 8GB"] = gpus[f"{chip} 16GB"]["power_score"]

    names = ("UPSCALE_VRAM_FIXED", "VRAM_TIGHT_PENALTY", "VRAM_SPILL_SEVERITY",
             "VRAM_SPILL_FLOOR")
    orig = tuple(getattr(bc, n) for n in names)

    def err(sel, scores, consts):
        for n, v in zip(names, consts):
            setattr(bc, n, v)
        return [abs(r["engine"] - r["measured"]) / r["measured"] * 100
                for r in ratios(ctx, sel, scores)]

    fixed_only = [(f,) + orig[1:] for f in (0.72, 0.80, 0.90, 0.95, 1.00)]
    everything = [(f, t, sv, fl) for f in (0.72, 0.85, 1.00)
                  for t in (0.92, 0.94, 0.97) for sv in (0.5, 1.0, 2.0, 4.0)
                  for fl in (0.5, 0.7, 0.8)]
    variants = [
        ("current model", [orig], None),
        ("UPSCALE_VRAM_FIXED only", fixed_only, None),
        ("  + same-chip scores equal", fixed_only, equal),
        ("all four constants", everything, None),
    ]

    print("\n  --- would a change generalise? (leave-one-game-out, all pairs pooled) ---")
    print(f"  {len(pairs)} pairs, {len({p[1]['game'] for p in pairs})} games\n")
    print(f"  {'variant':32s} {'in sample':>10s} {'held out':>9s}   chosen constants")
    best_held = None
    for label, grid, scores in variants:
        pick = lambda sel: min(grid, key=lambda c: statistics.mean(err(sel, scores, c)))
        full = pick(pairs)
        in_sample = statistics.mean(err(pairs, scores, full))
        held = []
        for game in sorted({p[1]["game"] for p in pairs}):
            train = [p for p in pairs if p[1]["game"] != game]
            test = [p for p in pairs if p[1]["game"] == game]
            held += err(test, scores, pick(train))
        held_mean = statistics.mean(held)
        if label != "current model" and (best_held is None or held_mean < best_held[0]):
            best_held = (held_mean, label, full)
        print(f"  {label:32s} {in_sample:9.2f}% {held_mean:8.2f}%   "
              + ", ".join(f"{n.split('_', 1)[1][:9]}={v}" for n, v in zip(names, full)))
    for n, v in zip(names, orig):
        setattr(bc, n, v)
    base = statistics.mean(err(pairs, None, orig))
    print(f"\n  best held-out: {best_held[1].strip()} at {best_held[0]:.2f}% "
          f"against {base:.2f}% for the current model")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refit", action="store_true")
    ap.add_argument("--resolution", action="store_true",
                    help="games measured at two resolutions: fitted working sets and their cost")
    args = ap.parse_args()
    main(args.refit, args.resolution)
