"""
Fits the engine's constants and per-game cost profiles to measured benchmarks.

The measurement batches were designed so each one isolates a different part of
the model, which lets the fit be staged instead of thrown at a single opaque
optimiser:

    GPU ladder      (one CPU, one game, many GPUs)   -> GPU_PERF_EXPONENT
    CPU ladder      (one GPU, one game, many CPUs)   -> CPU_PERF_EXPONENT
    resolution rows (one system, 3 resolutions)      -> RES_PIXEL_EXPONENT
                                                        + per-game cpu/gpu cost
    preset ladders  (one system, all presets)        -> QUALITY_TIERS

Each stage reports the error before and after, so a change that does not help
is visible immediately rather than being taken on faith.

Nothing is written unless --apply is passed.

    python scripts/calibrate_engine.py            # report the fit
    python scripts/calibrate_engine.py --apply    # write it to the database
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import balance_config as bc
from core import db_manager


def load():
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    cpus = {c["name"]: dict(c) for c in db_manager.get_all_cpus()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}
    rows = [dict(r) for r in conn.execute("SELECT * FROM benchmarks")]
    conn.close()
    return games, cpus, gpus, rows


def perf(score, exponent):
    return max(0.05, (max(score, 1.0) / bc.REF_SCORE) ** exponent)


def predict(game, cpu, gpu, res, preset, gpu_exp, cpu_exp, res_exp,
            gpu_ms, cpu_ms, quality=None):
    """
    Simplified forward model used for fitting: native rendering, no ray
    tracing, no frame generation, no memory pressure. The batches used for
    fitting were all recorded that way, so the extra stages would only add
    noise here.
    """
    q = quality or bc.QUALITY_TIERS
    q_gpu, q_cpu, _ = q.get(preset, (1.0, 1.0, 1.0))
    pixels = bc.RESOLUTION_PIXELS.get(res, 1.0) ** res_exp
    ft_gpu = gpu_ms * game["gpu_cost"] * pixels * q_gpu / perf(gpu["power_score"], gpu_exp)
    cpu_score = cpu["power_score"] * (1.18 if "X3D" in cpu["name"].upper() else 1.0)
    ft_cpu = cpu_ms * game["cpu_cost"] * q_cpu / perf(cpu_score, cpu_exp)
    k = bc.BOTTLENECK_BLEND_K
    return 1000.0 / ((ft_cpu ** k + ft_gpu ** k) ** (1.0 / k))


def err_of(rows, games, cpus, gpus, **kw):
    total = 0.0
    for b in rows:
        p = predict(games[b["game"]], cpus[b["cpu"]], gpus[b["gpu"]],
                    b["resolution"], b["settings"], **kw)
        total += abs(p - b["fps_avg"]) / b["fps_avg"]
    return total / len(rows) * 100


def frange(lo, hi, step):
    v = lo
    while v <= hi + 1e-9:
        yield round(v, 4)
        v += step


def main(apply_changes):
    games, cpus, gpus, rows = load()

    native = [r for r in rows
              if r["upscaling"] in ("Native",) and r["frame_gen"] == "Kapalı"
              and not r["ray_tracing"] and not r["path_tracing"]]
    b1 = [r for r in native if r["source"] == "batch1"]
    b2 = [r for r in native if r["source"] == "batch2"]
    b3 = [r for r in native if r["source"] == "batch3"]

    base = dict(gpu_exp=bc.GPU_PERF_EXPONENT, cpu_exp=bc.CPU_PERF_EXPONENT,
                res_exp=bc.RES_PIXEL_EXPONENT, gpu_ms=bc.GPU_MS_CONST,
                cpu_ms=bc.CPU_MS_CONST)

    print("=== BASLANGIC ===")
    print(f"  batch1 (cozunurluk) hata: {err_of(b1, games, cpus, gpus, **base):5.1f}%")
    print(f"  batch2 (GPU merdiveni)  : {err_of(b2, games, cpus, gpus, **base):5.1f}%")
    print(f"  batch3 (CPU merdiveni)  : {err_of(b3, games, cpus, gpus, **base):5.1f}%")

    # ── Stage 1: per-game cost profiles + resolution exponent ──────────────
    # These are fitted together because a game's CPU/GPU split and how fast
    # cost grows with pixels are only separable when you have the same game at
    # several resolutions, which is exactly what batch1 provides.
    print("\n=== ASAMA 1: cozunurluk usu + oyun maliyet profilleri ===")
    best = None
    for res_exp in frange(0.50, 0.95, 0.01):
        fitted, total_err, n = {}, 0.0, 0
        for name in {r["game"] for r in b1}:
            rs = [r for r in b1 if r["game"] == name]
            g = dict(games[name])
            best_g = None
            # Search the two costs on a log-spaced grid.
            for gc in frange(0.2, 6.0, 0.05):
                for cc in frange(0.2, 6.0, 0.10):
                    g["gpu_cost"], g["cpu_cost"] = gc, cc
                    e = sum(abs(predict(g, cpus[r["cpu"]], gpus[r["gpu"]],
                                        r["resolution"], r["settings"],
                                        gpu_exp=base["gpu_exp"], cpu_exp=base["cpu_exp"],
                                        res_exp=res_exp, gpu_ms=base["gpu_ms"],
                                        cpu_ms=base["cpu_ms"]) - r["fps_avg"]) / r["fps_avg"]
                            for r in rs)
                    if best_g is None or e < best_g[0]:
                        best_g = (e, gc, cc)
            fitted[name] = (best_g[1], best_g[2])
            total_err += best_g[0]
            n += len(rs)
        mean = total_err / n * 100
        if best is None or mean < best[0]:
            best = (mean, res_exp, fitted)

    mean, res_exp, fitted = best
    print(f"  en iyi RES_PIXEL_EXPONENT: {bc.RES_PIXEL_EXPONENT} -> {res_exp}")
    print(f"  batch1 hatasi: {err_of(b1, games, cpus, gpus, **base):5.1f}% -> {mean:5.1f}%")
    print("\n  oyun profilleri (eski -> yeni):")
    for name, (gc, cc) in sorted(fitted.items()):
        old = games[name]
        bound = "CPU" if cc > gc else "GPU"
        print(f"    {name[:26]:26s} gpu {old['gpu_cost']:5.2f}->{gc:5.2f}   "
              f"cpu {old['cpu_cost']:5.2f}->{cc:5.2f}   [{bound}-bound]")
        games[name]["gpu_cost"], games[name]["cpu_cost"] = gc, cc

    base["res_exp"] = res_exp

    # ── Stage 2: GPU performance exponent ──────────────────────────────────
    print("\n=== ASAMA 2: GPU puan ussu ===")
    b2_all = b2 + [r for r in b1 if r["game"] == "Cyberpunk 2077" and r["resolution"] == "1440p"]
    before = err_of(b2_all, games, cpus, gpus, **base)
    best_exp = min(frange(0.8, 2.2, 0.02),
                   key=lambda e: err_of(b2_all, games, cpus, gpus, **{**base, "gpu_exp": e}))
    after = err_of(b2_all, games, cpus, gpus, **{**base, "gpu_exp": best_exp})
    print(f"  GPU_PERF_EXPONENT: {bc.GPU_PERF_EXPONENT} -> {best_exp}")
    print(f"  hata: {before:5.1f}% -> {after:5.1f}%")
    base["gpu_exp"] = best_exp

    # ── Stage 3: CPU performance exponent ──────────────────────────────────
    print("\n=== ASAMA 3: CPU puan ussu ===")
    before = err_of(b3, games, cpus, gpus, **base)
    best_pair = min(
        ((e, m) for e in frange(0.4, 2.4, 0.05) for m in frange(1.5, 5.0, 0.05)),
        key=lambda em: err_of(b3, games, cpus, gpus,
                              **{**base, "cpu_exp": em[0], "cpu_ms": em[1]}))
    cpu_exp, cpu_ms = best_pair
    after = err_of(b3, games, cpus, gpus, **{**base, "cpu_exp": cpu_exp, "cpu_ms": cpu_ms})
    print(f"  CPU_PERF_EXPONENT: {bc.CPU_PERF_EXPONENT} -> {cpu_exp}")
    print(f"  CPU_MS_CONST     : {bc.CPU_MS_CONST} -> {cpu_ms}")
    print(f"  hata: {before:5.1f}% -> {after:5.1f}%")
    base["cpu_exp"], base["cpu_ms"] = cpu_exp, cpu_ms

    # ── Summary ────────────────────────────────────────────────────────────
    allrows = b1 + b2 + b3
    print("\n=== TOPLAM (native, RT/FG haric olcumler) ===")
    print(f"  once : {err_of(allrows, games, cpus, gpus, gpu_exp=bc.GPU_PERF_EXPONENT, cpu_exp=bc.CPU_PERF_EXPONENT, res_exp=bc.RES_PIXEL_EXPONENT, gpu_ms=bc.GPU_MS_CONST, cpu_ms=bc.CPU_MS_CONST):5.1f}%")
    print(f"  sonra: {err_of(allrows, games, cpus, gpus, **base):5.1f}%")

    print("\n=== balance_config.py icin yeni degerler ===")
    print(f"  GPU_PERF_EXPONENT  = {base['gpu_exp']}")
    print(f"  CPU_PERF_EXPONENT  = {base['cpu_exp']}")
    print(f"  RES_PIXEL_EXPONENT = {base['res_exp']}")
    print(f"  CPU_MS_CONST       = {base['cpu_ms']}")

    if apply_changes:
        conn = db_manager.get_connection()
        cur = conn.cursor()
        for name, (gc, cc) in fitted.items():
            cur.execute("UPDATE games SET gpu_cost=?, cpu_cost=? WHERE name=?",
                        (round(gc, 4), round(cc, 4), name))
        conn.commit()
        conn.close()
        print(f"\n  {len(fitted)} oyun profili veritabanina yazildi.")
        print("  balance_config.py'yi yukaridaki degerlerle elle guncelleyin.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
