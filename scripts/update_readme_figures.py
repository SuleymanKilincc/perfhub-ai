"""
Regenerates every number in README.md that comes from the data.

The README quoted 577 measurements and 491 fitted rows for two batches after
the database held 683 and 585. Hand-typed figures go stale the moment the next
batch lands, and a published accuracy claim that is out of date is worse than
none, so the figures are not typed: each is wrapped in a marker,

    <!--v:fitted_err-->6.9<!--/v-->

and this script rewrites what sits inside it from the database, using the same
exclusions the calibration does. Prose around the markers is left alone.

    python scripts/update_readme_figures.py            # rewrite README.md
    python scripts/update_readme_figures.py --check    # exit 1 if it is stale

`--check` is what CI runs, so a batch that changes the accuracy cannot be
merged with a README still claiming the old one.
"""
import argparse
import os
import re
import sqlite3
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
sys.path.append(os.path.join(ROOT, "scripts"))

from core import db_manager
from core import scoring_engine as se

README = os.path.join(ROOT, "README.md")
MARKER = re.compile(r"<!--v:(\w+)-->(.*?)<!--/v-->", re.S)


def bucket(row):
    """Which accuracy group a row belongs to; mirrors validate_engine.py."""
    if row["texture_pack"]:
        return "texture"
    if row["ray_reconstruction"]:
        return "rr"
    if row["vram_limited"]:
        return "vram"
    return "gameplay" if row["scene"] == "gameplay" else "fitted"


def signed(x):
    r = round(x, 1)
    return "0.0" if r == 0 else f"{r:+.1f}"


def compute():
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    cpus = {c["name"]: dict(c) for c in db_manager.get_all_cpus()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}

    groups = {}
    upscaled = {}
    fitted_games = set()
    for r in conn.execute("SELECT * FROM benchmarks"):
        r = dict(r)
        pred = se.estimate_fps(
            cpus[r["cpu"]], gpus[r["gpu"]], games[r["game"]], r["resolution"],
            r["settings"], r["upscaling"], r["frame_gen"], r["ram_gb"],
            ray_tracing=bool(r["ray_tracing"]), path_tracing=bool(r["path_tracing"]))
        signed_err = (pred - r["fps_avg"]) / r["fps_avg"] * 100
        groups.setdefault(bucket(r), []).append(signed_err)
        # Upscaling is its own question: the least-measured major feature.
        if r["upscaling"] not in ("Native", "DLAA") and r["frame_gen"] == "Kapalı":
            upscaled.setdefault("fitted" if bucket(r) == "fitted" else "heldout",
                                []).append(signed_err)
        if bucket(r) == "fitted":
            fitted_games.add(r["game"])

    v = {}
    for name, errs in groups.items():
        v[f"{name}_n"] = len(errs)
        v[f"{name}_err"] = f"{statistics.mean(abs(e) for e in errs):.1f}"
        v[f"{name}_bias"] = signed(statistics.mean(errs))
    fitted = [abs(e) for e in groups["fitted"]]
    v["within10"] = f"{sum(e <= 10 for e in fitted) / len(fitted) * 100:.0f}"
    v["within20"] = f"{sum(e <= 20 for e in fitted) / len(fitted) * 100:.0f}"
    v["measurements"] = sum(len(e) for e in groups.values())
    v["upscaled_fitted_n"] = len(upscaled["fitted"])
    v["upscaled_heldout_n"] = len(upscaled["heldout"])
    v["upscaled_heldout_bias"] = signed(statistics.mean(upscaled["heldout"]))

    measured = {r[0] for r in conn.execute("SELECT DISTINCT game FROM benchmarks")}
    # "Fitted" means a game has at least one row the calibration actually uses.
    # A game measured only in free play or with a texture pack has data but a
    # derived cost profile, and counting it as fitted would overstate the claim.
    v["games"] = len(games)
    v["measured_games"] = len(measured)
    v["fitted_games"] = len(fitted_games)
    v["heldout_only_games"] = len(measured - fitted_games)
    v["derived_games"] = len(games) - len(fitted_games)
    v["cpu_only_games"] = sum(
        1 for n in fitted_games if games[n].get("gpu_measured") == 0)
    v["cpus"], v["gpus"] = len(cpus), len(gpus)
    v["fps_low_games"] = sum(1 for g in games.values() if g.get("fps_low_measured"))

    for key, prefix in (("nvidia", "NVIDIA%"), ("amd", "AMD%"), ("intel", "Intel%")):
        v[f"{key}_rows"] = conn.execute(
            "SELECT COUNT(*) FROM benchmarks WHERE gpu LIKE ?", (prefix,)).fetchone()[0]
        v[f"{key}_cards"] = conn.execute(
            "SELECT COUNT(DISTINCT gpu) FROM benchmarks WHERE gpu LIKE ?",
            (prefix,)).fetchone()[0]
    v["laptop_rows"] = conn.execute(
        "SELECT COUNT(*) FROM benchmarks b JOIN gpus g ON g.name = b.gpu"
        " WHERE g.form_factor = 'laptop'").fetchone()[0]
    conn.close()

    # Leave-one-game-out: the same figure the website's footer is built from.
    import export_engine_data
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    stats = export_engine_data.engine_stats(conn)
    conn.close()
    v["derived_err"] = f"{stats['derived_error_pct']:.0f}"
    v["measured_game_err"] = f"{stats['measured_error_pct']:.1f}"

    import conformance_test
    v["conformance_fields"] = len(conformance_test.FIELDS)

    # The same chip at 8 and 16 GB: the memory model's one direct test.
    import memory_pairs
    ctx = memory_pairs.load()
    s = memory_pairs.summary(ctx, memory_pairs.find_pairs(ctx[3]))
    v["mem_pairs"], v["mem_games"] = s["pairs"], s["games"]
    v["mem_measured_min"], v["mem_measured_max"] = (
        f"{s['measured_min']:.2f}", f"{s['measured_max']:.2f}")
    v["mem_engine_min"], v["mem_engine_max"] = (
        f"{s['engine_min']:.2f}", f"{s['engine_max']:.2f}")

    # The one configuration the README shows with its error, so the example
    # cannot drift from the engine either: a recalibration that moves 165 to
    # 160 changes the table instead of leaving a figure the engine no longer
    # produces.
    conn = db_manager.get_connection()
    cpu_n, gpu_n = "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4090"
    for res in ("1080p", "1440p", "4k"):
        row = conn.execute(
            "SELECT fps_avg, ram_gb FROM benchmarks WHERE game='Cyberpunk 2077' AND cpu=?"
            " AND gpu=? AND resolution=? AND settings='Ultra' AND upscaling='Native'"
            " AND ray_tracing=0 AND path_tracing=0 AND frame_gen='Kapalı'",
            (cpu_n, gpu_n, res)).fetchone()
        pred = se.estimate_fps(cpus[cpu_n], gpus[gpu_n], games["Cyberpunk 2077"], res,
                               "Ultra", "Native", "Kapalı", row[1])
        v[f"cp_{res}_pred"] = pred
        v[f"cp_{res}_meas"] = f"{row[0]:.0f}"
        v[f"cp_{res}_err"] = f"{(pred - row[0]) / row[0] * 100:+.0f}"
    conn.close()
    return {k: str(x) for k, x in v.items()}


def main(check):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    values = compute()
    text = open(README, encoding="utf-8").read()

    missing = sorted({m.group(1) for m in MARKER.finditer(text)} - set(values))
    if missing:
        sys.exit(f"  README uses markers with no value: {missing}")

    stale = []

    def fill(m):
        new = values[m.group(1)]
        if m.group(2) != new:
            stale.append((m.group(1), m.group(2), new))
        return f"<!--v:{m.group(1)}-->{new}<!--/v-->"

    out = MARKER.sub(fill, text)
    unused = sorted(set(values) - {m.group(1) for m in MARKER.finditer(text)})

    for key, old, new in stale:
        print(f"  {key:20s} {old!r:>10} -> {new!r}")
    if check:
        if stale:
            print(f"\n  README.md is stale ({len(stale)} figures). "
                  "Run: python scripts/update_readme_figures.py")
            return 1
        print(f"  README figures match the data ({len(MARKER.findall(text))} markers)")
        return 0
    if stale:
        with open(README, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print(f"\n  {len(stale)} figures updated")
    else:
        print("  README figures already match the data")
    if unused:
        print(f"  (available but unused: {', '.join(unused)})")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    sys.exit(main(ap.parse_args().check))
