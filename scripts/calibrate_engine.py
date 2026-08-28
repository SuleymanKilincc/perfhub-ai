"""
Fits Cadence's constants and per-game cost profiles to measured benchmarks.

Staged rather than thrown at one opaque optimiser, because each measurement
shape isolates a different part of the model:

    baseline rows (native/DLAA, no RT, no frame gen)  -> per-game cpu/gpu cost
    the same game with RT or PT toggled               -> RT / PT multipliers
    a frame generation ladder on one system           -> FG output + overhead
    GPU and CPU ladders                               -> performance exponents

Every stage prints the error before and after, so a change that does not help
is visible instead of assumed.

    python scripts/calibrate_engine.py            # report the fit
    python scripts/calibrate_engine.py --apply    # write it to the database
"""
import argparse
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import balance_config as bc
from core import db_manager
from core import scoring_engine as se
# The same genre priors the profiles were derived from, so a game whose rows
# cannot pin down its CPU:GPU split falls back to exactly where it started
# rather than to a second, separately maintained guess.
from migrate_game_profiles import (DEFAULT_CPU_RATIO, GENRE_CPU_RATIO,
                                   check_genre_coverage)


def load():
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    cpus = {c["name"]: dict(c) for c in db_manager.get_all_cpus()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}
    # Free-gameplay rows measure a different thing — see
    # scripts/migrate_measurement_kind.py — so they are held out of every fit
    # and used only to check it.
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM benchmarks WHERE COALESCE(scene, 'benchmark') = 'benchmark'")]
    conn.close()

    # A genre with no prior silently becomes 1.0, which is indistinguishable
    # from a deliberate 1.0. Say so rather than let it pass.
    missing = check_genre_coverage(g.get("genre") for g in games.values())
    if missing:
        print(f"  UYARI: prior'i olmayan tur ({len(missing)}): {', '.join(missing)}")
        print("  -> migrate_game_profiles.GENRE_CPU_RATIO'ya eklenmeli\n")

    return games, cpus, gpus, rows


def predict(row, games, cpus, gpus):
    return se.estimate_fps(
        cpus[row["cpu"]], gpus[row["gpu"]], games[row["game"]],
        row["resolution"], row["settings"], row["upscaling"], row["frame_gen"],
        row["ram_gb"], ray_tracing=bool(row["ray_tracing"]),
        path_tracing=bool(row["path_tracing"]))


def err(rows, games, cpus, gpus):
    if not rows:
        return 0.0
    return sum(abs(predict(r, games, cpus, gpus) - r["fps_avg"]) / r["fps_avg"]
               for r in rows) / len(rows) * 100


def frange(lo, hi, step):
    v = lo
    while v <= hi + 1e-9:
        yield round(v, 4)
        v += step


def is_identifiable(rs, cpus):
    """
    Can these rows actually separate a game's CPU cost from its GPU cost?

    Only if something moves the two terms independently. Three things do:
    resolution, because pixel count drives the GPU term and leaves the CPU term
    alone; the CPU itself; and the preset, which sounds like it should scale
    both together but does not — the quality multipliers run 0.42 to 1.70 on
    the GPU against 0.80 to 1.14 on the CPU, so a Very Low to Ultra sweep
    swings the balance between them by 2.8x.

    Changing only the GPU or the upscaler does not qualify. Those move one term
    while the other stays put, which identifies the split only through the
    curvature of the blend — and at k=4 that blend is very nearly a plain max,
    so the signal is almost nothing.

    Counting rows instead of counting *distinct configurations* is what let
    Grand Theft Auto V Enhanced through. Its four rows are a frame-generation
    ladder at one resolution on one machine, which is one configuration seen
    four ways, and the solver quietly parked the cost in the CPU term: it
    implied a Ryzen 5 5600 could not exceed 38 fps in a game that really runs
    well past a hundred. Every measurement we hold is on a strong CPU, where
    that term barely binds, so nothing in the fit noticed.
    """
    return (len({r["resolution"] for r in rs}) >= 2
            or len({r["settings"] for r in rs}) >= 2
            or len({cpus[r["cpu"]]["power_score"] for r in rs}) >= 2)


def fit_game_costs(rows, games, cpus, gpus, verbose=True, use_all_rows=False):
    """
    Fit gpu_cost / cpu_cost for every game with at least two usable rows. A
    single row cannot separate the two costs, so those are skipped — guessing
    a split from one data point would only bake in an assumption.

    Where the rows cannot separate the two (see is_identifiable), only the
    overall magnitude is fitted and the CPU:GPU ratio is held at the genre
    prior. One degree of freedom in the data, one number fitted. The prior is a
    weaker claim than a measurement, but it is an honest one, and it beats a
    number the data never constrained.

    With use_all_rows, ray tracing / frame generation rows are included too.
    That is for games measured only with those features on, where the choice
    is between fitting through the (already calibrated) global multipliers or
    leaving the game on a cloned profile that is plainly wrong. Any error in
    those multipliers gets absorbed into the game's cost, so this pass runs
    second, after they have been fitted.
    """
    if use_all_rows:
        baseline = [r for r in rows if r["upscaling"] in ("Native", "DLAA")]
    else:
        baseline = [r for r in rows
                    if not r["ray_tracing"] and not r["path_tracing"]
                    and r["frame_gen"] == "Kapalı"
                    and r["upscaling"] in ("Native", "DLAA")]
    by_game = defaultdict(list)
    for r in baseline:
        by_game[r["game"]].append(r)

    fitted = {}
    for name, rs in sorted(by_game.items()):
        if len(rs) < 2:
            continue
        g = games[name]
        before = err(rs, games, cpus, gpus)
        free = is_identifiable(rs, cpus)
        ratio = GENRE_CPU_RATIO.get(g.get("genre"), DEFAULT_CPU_RATIO)
        best = None
        for gc in frange(0.10, 8.0, 0.05):
            g["gpu_cost"] = gc
            for cc in (frange(0.10, 8.0, 0.10) if free else [round(gc * ratio, 4)]):
                g["cpu_cost"] = cc
                e = sum(abs(predict(r, games, cpus, gpus) - r["fps_avg"]) / r["fps_avg"]
                        for r in rs)
                if best is None or e < best[0]:
                    best = (e, gc, cc)
        _, gc, cc = best
        g["gpu_cost"], g["cpu_cost"] = gc, cc
        after = err(rs, games, cpus, gpus)
        fitted[name] = (gc, cc, before, after, len(rs))
        if verbose:
            bound = "CPU" if cc > gc else "GPU"
            note = "" if free else f"  oran prior'da sabit ({ratio:.2f})"
            print(f"    {name[:30]:30s} n={len(rs)}  gpu={gc:5.2f} cpu={cc:5.2f} "
                  f"[{bound}]  {before:5.1f}% -> {after:5.1f}%{note}")
    return fitted


def fit_toggle(rows, games, cpus, gpus, flag, const_name, lo, hi):
    """
    Fit a multiplier that a subset of rows switches on, by finding the value
    that minimises error across just those rows.
    """
    subset = [r for r in rows if r[flag] and r["frame_gen"] == "Kapalı"]
    if not subset:
        return None
    original = getattr(bc, const_name)
    before = err(subset, games, cpus, gpus)
    best = None
    for v in frange(lo, hi, 0.02):
        setattr(bc, const_name, v)
        e = err(subset, games, cpus, gpus)
        if best is None or e < best[0]:
            best = (e, v)
    after, value = best
    setattr(bc, const_name, value)
    print(f"    {const_name}: {original} -> {value}   "
          f"({len(subset)} olcum, {before:5.1f}% -> {after:5.1f}%)")
    return value


def main(apply_changes):
    games, cpus, gpus, rows = load()

    print("=== BASLANGIC ===")
    print(f"  {len(rows)} olcum, ortalama hata {err(rows, games, cpus, gpus):5.1f}%")

    print("\n=== ASAMA 1: oyun maliyet profilleri ===")
    fitted = fit_game_costs(rows, games, cpus, gpus)
    print(f"  -> toplam hata: {err(rows, games, cpus, gpus):5.1f}%")

    # Path tracing first: those rows also have ray_tracing set, so fitting RT
    # while they are included would blame the RT multiplier for PT's cost.
    print("\n=== ASAMA 2: path tracing carpani ===")
    pt_rows = [r for r in rows if r["path_tracing"] and r["frame_gen"] == "Kapalı"]
    if pt_rows:
        before = err(pt_rows, games, cpus, gpus)
        best = min(frange(1.5, 5.0, 0.02),
                   key=lambda v: (setattr(bc, "PT_GPU_COST_MULT", v),
                                  err(pt_rows, games, cpus, gpus))[1])
        bc.PT_GPU_COST_MULT = best
        print(f"    PT_GPU_COST_MULT: 3.10 -> {best}   "
              f"({len(pt_rows)} olcum, {before:5.1f}% -> {err(pt_rows, games, cpus, gpus):5.1f}%)")

    print("\n=== ASAMA 3: ray tracing carpani ===")
    # Only games measured both with and without ray tracing can say anything
    # about its cost. Fitting across games that were *only* ever measured with
    # RT on lets their unknown base cost masquerade as an RT effect — the
    # multiplier then drifts to whatever compensates for those profiles, and
    # the two become impossible to separate.
    paired = {g for g in {r["game"] for r in rows}
              if any(r["game"] == g and not r["ray_tracing"] and not r["path_tracing"]
                     for r in rows)
              and any(r["game"] == g and r["ray_tracing"] and not r["path_tracing"]
                      for r in rows)}
    # Rows tagged as the game's most demanding RT preset are held out. The
    # model has one ray-tracing flag, so this multiplier is an average over
    # whatever presets the sources used, and one Extreme measurement — Forza
    # Horizon 6 reads 85 fps at High and 40 at Extreme on the same card — would
    # drag that average toward a setting most of the other rows were not using.
    # See scripts/add_rt_level.py.
    rt_rows = [r for r in rows
               if r["game"] in paired and r["ray_tracing"] and not r["path_tracing"]
               and r["frame_gen"] == "Kapalı"
               and (r.get("rt_level") or "") != "Extreme"]
    print(f"    kullanilan oyunlar: {sorted(paired) or 'yok'}")
    if rt_rows:
        before = err(rt_rows, games, cpus, gpus)
        best = min(frange(1.1, 3.0, 0.02),
                   key=lambda v: (setattr(bc, "RT_GPU_COST_MULT", v),
                                  err(rt_rows, games, cpus, gpus))[1])
        bc.RT_GPU_COST_MULT = best
        print(f"    RT_GPU_COST_MULT: 1.80 -> {best}   "
              f"({len(rt_rows)} olcum, {before:5.1f}% -> {err(rt_rows, games, cpus, gpus):5.1f}%)")

    print("\n=== ASAMA 4: frame generation ek yuku ===")
    fg_rows = [r for r in rows if r["frame_gen"] in ("2x", "3x", "4x")]
    if fg_rows:
        before = err(fg_rows, games, cpus, gpus)
        best = None
        for o2 in frange(0.05, 0.60, 0.05):
            for step in frange(0.02, 0.20, 0.02):
                bc.FG_GPU_OVERHEAD = {"2x": o2, "3x": o2 + step, "4x": o2 + 2 * step}
                e = err(fg_rows, games, cpus, gpus)
                if best is None or e < best[0]:
                    best = (e, o2, step)
        _, o2, step = best
        bc.FG_GPU_OVERHEAD = {"2x": o2, "3x": round(o2 + step, 3), "4x": round(o2 + 2 * step, 3)}
        print(f"    FG_GPU_OVERHEAD: {bc.FG_GPU_OVERHEAD}   "
              f"({len(fg_rows)} olcum, {before:5.1f}% -> {err(fg_rows, games, cpus, gpus):5.1f}%)")

    # Games measured only with ray tracing or frame generation on could not be
    # fitted in stage 1 — their baseline never existed. Now that the global
    # multipliers are calibrated, fit them through those instead of leaving
    # them on a cloned profile.
    print("\n=== ASAMA 5: sadece RT/FG ile olculmus oyunlar ===")
    remaining = {r["game"] for r in rows} - set(fitted)
    if remaining:
        leftover_rows = [r for r in rows if r["game"] in remaining]
        extra = fit_game_costs(leftover_rows, games, cpus, gpus, use_all_rows=True)
        fitted.update(extra)
        if not extra:
            print("    (uygun oyun yok)")
    else:
        print("    (hepsi zaten kalibre)")

    print("\n=== SONUC ===")
    print(f"  toplam hata: {err(rows, games, cpus, gpus):5.1f}%")

    print("\n=== balance_config.py icin ===")
    print(f"  RT_GPU_COST_MULT = {bc.RT_GPU_COST_MULT}")
    print(f"  PT_GPU_COST_MULT = {bc.PT_GPU_COST_MULT}")
    print(f"  FG_GPU_OVERHEAD  = {bc.FG_GPU_OVERHEAD}")

    if apply_changes:
        conn = db_manager.get_connection()
        cur = conn.cursor()
        for name, (gc, cc, *_rest) in fitted.items():
            cur.execute("UPDATE games SET gpu_cost=?, cpu_cost=? WHERE name=?",
                        (round(gc, 4), round(cc, 4), name))
        conn.commit()
        conn.close()
        print(f"\n  {len(fitted)} oyun profili yazildi. "
              f"balance_config.py'yi yukaridaki degerlerle elle guncelleyin.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
